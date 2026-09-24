"""Tokens, coste y latencia: por llamada, por capitulo y por novela (RF-OBS-03).

**El agujero que este modulo tapa.** Hasta hoy el unico `registrar_ejecucion` de
produccion estaba en `service.py`, y **solo lo usaba el Escritor**. El
Entrevistador, el Arquitecto, el Planificador, el Extractor, el Continuista y el
Critico llaman al modelo y no dejaban rastro: el coste de una novela era una
cifra que se quedaba corta **siempre**, y `RF-OBS-03` la usa despues para
comparar plantillas. Una cifra que falla siempre en la misma direccion es peor
que no tenerla, porque parece un dato.

`registrar_ejecucion` no servia para ellos porque **exige un
`ContextoDelCapitulo`** —un paquete ensamblado, con su desglose por capa— y esos
roles no ensamblan ninguno. De ahi esta segunda puerta: la misma tabla, sin
exigir un paquete que no existe.

**Las tres cifras salen de `ejecucion` y no de Langfuse** (`R-1`). Langfuse es
donde se miran; si fuera de donde salen, dejarian de existir el dia que el
servicio no responde. Y el coste **se deriva** de los tokens y de la tarifa
declarada: el `total_cost_usd` que el SDK devuelve se sigue ignorando a
proposito (`claude_code.py`).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.llm.claude_code import Consumo
from app.features.escritura.modelos import Ejecucion


@dataclass(frozen=True, slots=True)
class ResumenDeConsumo:
    """Lo que costo una unidad de trabajo, y de que esta hecho.

    `por_rol` se agrupa por `prompt_id`, que **ya es el nombre del rol** —
    `"escritor"`, `"continuista"`, `"critico"`— asi que no hace falta columna
    nueva. El desglose no es adorno: sin el, «esta novela costo X» no dice si el
    juez se lleva la mitad.
    """

    llamadas: int = 0
    tokens_entrada: int = 0
    tokens_salida: int = 0
    coste_usd: Decimal = Decimal(0)
    latencia_ms: int = 0
    por_rol: Mapping[str, "ResumenDeConsumo"] = field(default_factory=dict)

    llamadas_sin_consumo: int = 0
    """Las que se registraron y no se cerraron: el proceso murio a mitad.

    Cuentan como llamada y **no bajan el coste**. Sin este numero, una novela
    con la mitad de las llamadas sin cerrar se leeria como una novela barata.
    """

    tokens_de_cache_no_imputados: int = 0
    """`P-18`, y es la mitad que si se puede cerrar aqui.

    **A que precio se imputa la cache de prompt es una tarifa, y una tarifa la
    declara el repositorio con quien la firma.** Este modulo no la inventa. Lo
    que hace es que el hueco **se vea**: medido en produccion, un prompt de
    5.012 tokens devolvio `input_tokens=10` y `cache_read=6.835`, asi que
    imputar solo el primero deja el coste corto por un factor de ~680.

    Puesto al lado del coste, quien lo lea ve el volumen que **no** esta dentro.
    Sigue sin imputarse; deja de ser invisible.
    """


async def registrar_llamada(
    sesion: AsyncSession,
    *,
    run_id: str,
    obra_id: int,
    escena_id: int | None,
    prompt_id: str,
    prompt_version: str,
    prompt_hash: str,
    modelo: str,
    semilla: int,
    tokens_previstos: int,
) -> int:
    """Abre la fila **antes** de llamar al modelo, y devuelve su identificador.

    Antes y no despues: si se registrara al volver, una llamada que revienta o
    un proceso que muere a mitad no dejarian ni rastro de haber ocurrido, y el
    recuento de llamadas —que es lo que se compara entre plantillas— contaria
    solo las que salieron bien.
    """
    ejecucion = Ejecucion(
        run_id=run_id,
        obra_id=obra_id,
        escena_id=escena_id,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        prompt_hash=prompt_hash,
        modelo=modelo,
        semilla=semilla,
        tokens_previstos=tokens_previstos,
    )
    sesion.add(ejecucion)
    await sesion.flush()
    return ejecucion.id


async def cerrar_llamada(
    sesion: AsyncSession,
    ejecucion_id: int,
    *,
    consumo: Consumo | None,
    latencia_ms: int,
    veredicto: str,
) -> None:
    """Cierra la fila con lo que el proveedor devolvio.

    **Un consumo ausente deja nulo, no cero.** «Un cero se guarda, se suma y se
    publica sin que nadie note que el dato no estaba; un nulo se ve.» La
    latencia **si** se guarda igualmente, y no es incoherencia: la llamada tardo
    lo que tardo aunque el proveedor no dijera cuanto gasto.
    """
    ejecucion = await sesion.get(Ejecucion, ejecucion_id)
    if ejecucion is None:  # pragma: no cover - el id lo acaba de dar `registrar_llamada`
        raise ValueError(f"no existe la ejecucion {ejecucion_id}")

    ejecucion.latencia_ms = latencia_ms
    ejecucion.veredicto = veredicto
    if consumo is not None:
        ejecucion.tokens_reales = consumo.tokens_entrada + consumo.tokens_salida
        # El **desglose** entrada/salida va en `parametros`, que es JSON y
        # existe desde la Fase 1. `ejecucion` guarda `tokens_reales`, que es la
        # suma, y la suma no se puede descomponer despues: sin el desglose no se
        # puede rehacer `coste_derivado`, porque entrada y salida **no valen lo
        # mismo**. Dos columnas nuevas serian una segunda migracion en esta
        # fase, y la regla 2 del plan dice que las tablas entran en una:
        # queda anotado en Desviaciones por si se prefiere la columna.
        ejecucion.parametros = {
            **(ejecucion.parametros or {}),
            "tokens_entrada": consumo.tokens_entrada,
            "tokens_salida": consumo.tokens_salida,
        }
        ejecucion.coste = float(consumo.coste_usd)
        ejecucion.cache_read_input_tokens = consumo.cache_read_input_tokens
        ejecucion.cache_creation_input_tokens = consumo.cache_creation_input_tokens
    await sesion.flush()


def _resumir(filas: list[Ejecucion]) -> ResumenDeConsumo:
    """Suma un monton de filas. `Decimal` en el coste y `float` en la columna.

    La columna es `float` desde la Fase 1 y el coste se calcula en `Decimal`:
    convertir al sumar —y no al guardar— mantiene el redondeo donde se decidio,
    que es `coste_derivado`.
    """
    por_rol: dict[str, ResumenDeConsumo] = {}
    for rol in sorted({fila.prompt_id for fila in filas}):
        del_rol = [fila for fila in filas if fila.prompt_id == rol]
        por_rol[rol] = _sumar(del_rol)
    total = _sumar(filas)
    return ResumenDeConsumo(
        llamadas=total.llamadas,
        tokens_entrada=total.tokens_entrada,
        tokens_salida=total.tokens_salida,
        coste_usd=total.coste_usd,
        latencia_ms=total.latencia_ms,
        llamadas_sin_consumo=total.llamadas_sin_consumo,
        tokens_de_cache_no_imputados=total.tokens_de_cache_no_imputados,
        por_rol=por_rol,
    )


def _del_desglose(fila: Ejecucion, campo: str) -> int:
    """Entrada o salida de una fila, o cero si la llamada no llego a cerrarse.

    Cero y no nulo **aqui**: esto suma, y una llamada sin cerrar aporta cero
    tokens de verdad. Lo que no puede valer cero es el **coste**, y ese se
    cuenta aparte en `llamadas_sin_consumo`.
    """
    valor = (fila.parametros or {}).get(campo, 0)
    return int(valor) if isinstance(valor, int | float | str) else 0


def _sumar(filas: list[Ejecucion]) -> ResumenDeConsumo:
    return ResumenDeConsumo(
        llamadas=len(filas),
        tokens_entrada=sum(_del_desglose(fila, "tokens_entrada") for fila in filas),
        tokens_salida=sum(_del_desglose(fila, "tokens_salida") for fila in filas),
        coste_usd=sum(
            (Decimal(str(fila.coste)) for fila in filas if fila.coste is not None),
            Decimal(0),
        ),
        latencia_ms=sum(fila.latencia_ms or 0 for fila in filas),
        llamadas_sin_consumo=sum(1 for fila in filas if fila.coste is None),
        tokens_de_cache_no_imputados=sum(fila.cache_read_input_tokens or 0 for fila in filas),
    )


async def consumo_de_novela(sesion: AsyncSession, *, obra_id: int) -> ResumenDeConsumo:
    """Todo lo que costo una obra, con su desglose por rol.

    Filtra por `obra_id` y no por `run_id`: una novela tiene varias corridas —la
    generacion y cada regeneracion posterior— y `RF-OBS-03` pide el coste **de
    la novela**, no el de la ultima vez que se toco.
    """
    filas = (
        (await sesion.execute(select(Ejecucion).where(Ejecucion.obra_id == obra_id)))
        .scalars()
        .all()
    )
    return _resumir(list(filas))


async def consumo_de_capitulo(sesion: AsyncSession, *, capitulo_id: int) -> ResumenDeConsumo:
    """Lo que costo un capitulo.

    `ejecucion` apunta a `escena_id`, y a esta escala **un capitulo es una
    escena** (`CLAUDE.md` §1): son dos conceptos distintos —uno es unidad de
    lectura y otro de generacion— y hoy van uno a uno. Se resuelve por la
    escena del capitulo en vez de suponer que los identificadores coinciden.
    """
    from app.features.escena.modelos import Escena

    escenas = (
        (await sesion.execute(select(Escena.id).where(Escena.capitulo_id == capitulo_id)))
        .scalars()
        .all()
    )
    if not escenas:
        return ResumenDeConsumo()
    filas = (
        (await sesion.execute(select(Ejecucion).where(Ejecucion.escena_id.in_(escenas))))
        .scalars()
        .all()
    )
    return _resumir(list(filas))
