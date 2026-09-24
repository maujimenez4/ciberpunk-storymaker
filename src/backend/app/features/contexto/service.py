"""De los almacenes a las ocho capas: la tabla de `architecture.md` §4.8.

| Capa | Almacen que la surte |
| --- | --- |
| Constitucional | Biblia vigente y parametros de discurso |
| Estructural | Outline y plan dramatico del capitulo |
| Canon relevante | Grafo de canon, **filtrado por la ficha** |
| Estado en T | La vista derivada del ledger |
| Continuidad local | Escenas N-1 y N-2, en su version **vigente** |
| Memoria recuperada | Indice vectorial, tras la recuperacion hibrida de T7 |
| Instruccion | La ficha de escena |
| Reserva | — no tiene almacen, y por eso no se surte |

**Las tablas de otras features se leen por SQL con su nombre**, no por sus
modelos: `capitulo` y `version_obra` son de `outline`, `escena` de `escena`,
`hecho_canon` de `obra`, `version_texto` y `ejecucion` de `escritura`, y una
feature no entra a los ficheros internos de otra (`CLAUDE.md` §5.1). Es el mismo
trato que `recuperacion.py` le da a `escena` e `hilo_narrativo`, y el que
`outline/repository.py` le da a `obra`.

**El censo de cada capa es la pieza que hace ejecutable RF-CTX-06**, y cada capa
lo calcula a su manera porque «lo que el almacen tenia» significa una cosa
distinta en cada fila de §4.8. Los dos casos que importan:

- **Canon.** El censo son **todos** los hechos de la obra —«un capitulo que
  tiene hechos que la surtirian», R-3— y las piezas son los que la ficha trae.
  Cuando la obra tiene canon y la ficha no trae ninguno, la capa sale vacia
  teniendo con que llenarse, y eso **falla antes de llamar**.
- **Memoria.** `recuperar` devuelve `[]` por tres motivos distintos y solo uno
  es una averia. Se separan en `_surtir_memoria`, que es donde vive el aviso de
  la ola 2.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.domain.errores import ErrorDeDominio
from app.commons.domain.normalizacion import normalizar
from app.commons.llm.contador import ContadorDeTokens
from app.features.contexto.almacenes import VectorStore
from app.features.contexto.capas import CAPAS_CON_ORIGEN, Paquete, Surtido, ensamblar
from app.features.contexto.presupuesto import Capa, Pieza
from app.features.contexto.recuperacion import (
    FiltroEstructural,
    filtrar_estructuralmente,
    recuperar,
)


class CapituloDesconocido(ErrorDeDominio):
    """El id que se pide no es de ningun capitulo."""

    def __init__(self, capitulo_id: int) -> None:
        self.capitulo_id = capitulo_id
        super().__init__(f"No existe el capitulo {capitulo_id}")


class CapituloSinEscena(ErrorDeDominio):
    """El capitulo existe y nadie lo ha planificado todavia.

    No es una capa vacia: es que **no hay ficha**, y la ficha es la entrada del
    Ensamblador (`CLAUDE.md` §9). Ensamblar sin ella produciria un paquete sin
    capa de instruccion, que es una de las dos que nunca se recortan.
    """

    def __init__(self, capitulo_id: int) -> None:
        self.capitulo_id = capitulo_id
        super().__init__(f"El capitulo {capitulo_id} no tiene escena planificada")


@dataclass(frozen=True, slots=True)
class DatosDeLlamada:
    """Lo que el Ensamblador **no** sabe y `ejecucion` necesita (regla de dominio 7).

    La plantilla de prompt, el modelo y la semilla son de quien llama al modelo
    —el Escritor, T8—, no de quien ensambla: `contexto` no tiene `agents.py` ni
    `prompts/`. Llegan por parametro para que la fila nazca completa **antes**
    de la llamada, que es cuando el recuento previo existe (RF-CTX-02).
    """

    run_id: str
    prompt_id: str
    prompt_version: str
    prompt_hash: str
    modelo: str
    semilla: int


@dataclass(frozen=True, slots=True)
class ContextoDelCapitulo:
    """El paquete de un capitulo, con las claves con las que se persiste."""

    capitulo_id: int
    obra_id: int
    escena_id: int
    version_obra_id: int
    paquete: Paquete


@dataclass(frozen=True, slots=True)
class _Ficha:
    """La ficha de escena tal y como la lee este servicio, por SQL."""

    escena_id: int
    orden_discurso: int
    pov: str
    lugar: str
    presentes: tuple[str, ...]
    mencionados: tuple[str, ...]
    fila: Mapping[str, Any]

    @property
    def entidades(self) -> tuple[frozenset[str], frozenset[str]]:
        """Lo que la ficha nombra, en dos grupos y en este orden de importancia.

        `architecture.md` §2.1 dice que la capa de canon recorta primero los
        «personajes mencionados, no presentes»: eso solo es ejecutable si los
        presentes van antes que los mencionados, porque el recorte quita por el
        final (T5).
        """
        presentes = {normalizar(n) for n in (self.pov, self.lugar, *self.presentes)}
        mencionados = {normalizar(n) for n in self.mencionados} - presentes
        return frozenset(presentes), frozenset(mencionados)


async def surtir_capitulo(
    sesion: AsyncSession,
    capitulo_id: int,
    *,
    consulta: Sequence[float] | None = None,
    almacen: VectorStore | None = None,
) -> dict[Capa, Surtido]:
    """Las siete capas con origen, cada una de su almacen y **con su censo**.

    La reserva no sale: su fila de §4.8 no tiene memoria de origen.
    """
    capitulo = await _capitulo(sesion, capitulo_id)
    ficha = await _ficha(sesion, capitulo_id)
    obra_id = int(capitulo["obra_id"])

    return {
        Capa.CONSTITUCIONAL: await _surtir_constitucional(sesion, obra_id, ficha),
        Capa.ESTRUCTURAL: await _surtir_estructural(sesion, obra_id, capitulo),
        Capa.CANON: await _surtir_canon(sesion, obra_id, ficha),
        Capa.ESTADO_EN_T: await _surtir_estado_en_t(sesion, obra_id, ficha),
        Capa.CONTINUIDAD: await _surtir_continuidad(sesion, obra_id, ficha),
        Capa.MEMORIA: await _surtir_memoria(
            sesion, obra_id, capitulo, ficha, consulta=consulta, almacen=almacen
        ),
        Capa.INSTRUCCION: _surtir_instruccion(ficha),
    }


async def ensamblar_capitulo(
    sesion: AsyncSession,
    capitulo_id: int,
    contador: ContadorDeTokens,
    *,
    consulta: Sequence[float] | None = None,
    almacen: VectorStore | None = None,
) -> ContextoDelCapitulo:
    """Surte, ensambla y devuelve el paquete con su desglose. **No llama a nadie.**"""
    capitulo = await _capitulo(sesion, capitulo_id)
    ficha = await _ficha(sesion, capitulo_id)
    surtidos = await surtir_capitulo(sesion, capitulo_id, consulta=consulta, almacen=almacen)

    return ContextoDelCapitulo(
        capitulo_id=capitulo_id,
        obra_id=int(capitulo["obra_id"]),
        escena_id=ficha.escena_id,
        version_obra_id=int(ficha.fila["version_obra_id"]),
        paquete=ensamblar(surtidos, contador),
    )


async def registrar_ejecucion(
    sesion: AsyncSession, contexto: ContextoDelCapitulo, llamada: DatosDeLlamada
) -> int:
    """Crea la fila de `ejecucion` **antes** de la llamada, con el recuento previo.

    Es el momento correcto y no una anticipacion: P-A separa el contador local
    —que decide si el paquete cabe y por tanto si se llama— del recuento real
    del proveedor, que llega despues. `tokens_reales`, `coste` y `veredicto`
    quedan nulos y los completa quien llame (T8).

    **`ids_por_capa` va en `parametros`, y es una desviacion declarada.**
    RF-CTX-09 pide los identificadores de *todas* las capas que los tienen, con
    su capa; el esquema de T2 trae dos columnas de ids —`ids_canon` e
    `ids_recuperados`— y anadir una tercera es esquema y migracion, que no son
    de esta tarea. Las dos columnas se rellenan igual, porque son las que las
    consultas de CU-07 conocen.
    """
    ids = contexto.paquete.ids_por_capa
    parametros = {"ids_por_capa": {capa.value: list(ids[capa]) for capa in CAPAS_CON_ORIGEN}}

    resultado = await sesion.execute(
        text(
            """
            INSERT INTO ejecucion (
                run_id, obra_id, escena_id, version_obra_id,
                prompt_id, prompt_version, prompt_hash,
                modelo, semilla, parametros,
                tokens_por_capa, tokens_previstos, tokens_reales, coste,
                ids_recuperados, ids_canon, veredicto, creado_en
            ) VALUES (
                :run_id, :obra_id, :escena_id, :version_obra_id,
                :prompt_id, :prompt_version, :prompt_hash,
                :modelo, :semilla, :parametros,
                :tokens_por_capa, :tokens_previstos, NULL, NULL,
                :ids_recuperados, :ids_canon, NULL, CURRENT_TIMESTAMP
            )
            RETURNING id
            """
        ),
        {
            "run_id": llamada.run_id,
            "obra_id": contexto.obra_id,
            "escena_id": contexto.escena_id,
            "version_obra_id": contexto.version_obra_id,
            "prompt_id": llamada.prompt_id,
            "prompt_version": llamada.prompt_version,
            "prompt_hash": llamada.prompt_hash,
            "modelo": llamada.modelo,
            "semilla": llamada.semilla,
            "parametros": json.dumps(parametros),
            "tokens_por_capa": json.dumps(contexto.paquete.tokens_por_capa),
            "tokens_previstos": contexto.paquete.tokens_previstos,
            "ids_recuperados": json.dumps(_numericos(ids[Capa.MEMORIA], "emb")),
            "ids_canon": json.dumps(_numericos(ids[Capa.CANON], "hc")),
        },
    )
    return int(resultado.scalar_one())


# ---------------------------------------------------------------------------
# Las siete capas, una a una
# ---------------------------------------------------------------------------


async def _surtir_constitucional(sesion: AsyncSession, obra_id: int, ficha: _Ficha) -> Surtido:
    """Biblia vigente y parametros de discurso: lo que la obra **es**.

    Es la capa que nunca se recorta (RF-CTX-07), asi que se ordena de dentro
    hacia fuera: primero lo que la obra impone —genero, tono, nivel de calor— y
    despues las entradas de la biblia, por clave para que el orden no dependa de
    como el Arquitecto la escribiera.
    """
    fila = (
        (
            await sesion.execute(
                text(
                    "SELECT o.titulo, o.genero, o.tono, o.nivel_de_calor, vo.id AS vo_id, "
                    "vo.numero, vo.biblia "
                    "FROM version_obra AS vo JOIN obra AS o ON o.id = vo.obra_id "
                    "WHERE vo.id = :vo_id"
                ),
                {"vo_id": ficha.fila["version_obra_id"]},
            )
        )
        .mappings()
        .one()
    )

    piezas = [
        Pieza(
            texto=(
                f"Obra: {fila['titulo']}. Genero: {fila['genero']}. "
                f"Tono: {fila['tono']}. Nivel de calor: {fila['nivel_de_calor']}."
            ),
            identificador=f"obra:{obra_id}",
        )
    ]
    biblia = _json(fila["biblia"])
    piezas.extend(
        Pieza(texto=f"{clave}: {biblia[clave]}", identificador=f"vo:{fila['vo_id']}:{clave}")
        for clave in sorted(biblia)
    )
    return Surtido(piezas=tuple(piezas), disponibles=len(piezas))


async def _surtir_estructural(
    sesion: AsyncSession, obra_id: int, capitulo: Mapping[str, Any]
) -> Surtido:
    """Outline y plan dramatico. Se recorta primero **el detalle de los beats lejanos**.

    Por eso el orden es el capitulo en curso y despues los demas por distancia:
    §2.1 dice que se pierde antes lo de lejos, y eso solo es ejecutable si lo de
    lejos va al final.
    """
    filas = (
        (
            await sesion.execute(
                text(
                    "SELECT id, numero, titulo, pov_dominante, gancho_de_apertura, "
                    "tipo_de_corte_final, extension_objetivo, lugar, objetivo, obstaculo, "
                    "giro_de_valor_previsto "
                    "FROM capitulo WHERE obra_id = :obra_id ORDER BY numero"
                ),
                {"obra_id": obra_id},
            )
        )
        .mappings()
        .all()
    )

    actual = int(capitulo["numero"])
    ordenadas = sorted(filas, key=lambda f: (abs(int(f["numero"]) - actual), int(f["numero"])))
    piezas = tuple(
        Pieza(
            texto=(
                f"Capitulo {f['numero']}: {f['titulo']}. POV: {f['pov_dominante']}. "
                f"Lugar: {f['lugar']}. Objetivo: {f['objetivo']}. "
                f"Obstaculo: {f['obstaculo']}. Giro previsto: {f['giro_de_valor_previsto']}. "
                f"Gancho: {f['gancho_de_apertura']}. Corte: {f['tipo_de_corte_final']}. "
                f"Extension objetivo: {f['extension_objetivo']}."
            ),
            identificador=f"cap:{f['id']}",
        )
        for f in ordenadas
    )
    return Surtido(piezas=piezas, disponibles=len(piezas))


async def _surtir_canon(sesion: AsyncSession, obra_id: int, ficha: _Ficha) -> Surtido:
    """Grafo de canon **filtrado por la ficha**, y el censo es el grafo entero.

    Ahi esta R-3. `disponibles` cuenta **todos** los hechos de la obra —«un
    capitulo que tiene hechos que la surtirian»— y las piezas son las que la
    ficha nombra. Si la obra tiene canon y la ficha no trae ni uno, la capa sale
    vacia teniendo con que llenarse, y el Ensamblador falla antes de llamar: un
    paquete sin canon produce prosa que contradice lo ya escrito, y el defecto
    se le atribuiria al Escritor, que no lo cometio.

    Contar aqui `len(piezas)` en vez del grafo haria la regla inalcanzable, que
    es la forma de tener una restriccion sobre la que ningun test puede caer.
    """
    filas = (
        (
            await sesion.execute(
                text(
                    "SELECT id, entidad, atributo, valor, confianza, origen, escena_de_origen "
                    "FROM hecho_canon WHERE obra_id = :obra_id ORDER BY id"
                ),
                {"obra_id": obra_id},
            )
        )
        .mappings()
        .all()
    )

    presentes, mencionados = ficha.entidades
    de_presentes = [f for f in filas if normalizar(str(f["entidad"])) in presentes]
    de_mencionados = [f for f in filas if normalizar(str(f["entidad"])) in mencionados]

    piezas = tuple(
        Pieza(
            texto=(
                f"{f['entidad']} · {f['atributo']}: {f['valor']} "
                f"(origen: {f['origen']}, escena {f['escena_de_origen']})"
            ),
            identificador=f"hc:{f['id']}",
        )
        for f in (*de_presentes, *de_mencionados)
    )
    return Surtido(piezas=piezas, disponibles=len(filas))


async def _surtir_estado_en_t(sesion: AsyncSession, obra_id: int, ficha: _Ficha) -> Surtido:
    """La vista derivada del ledger, acotada a quien esta en la escena.

    Se recorta primero «los conocimientos antiguos ya usados» (§2.1), asi que se
    ordena por `sabe_desde` descendente: lo reciente primero, lo viejo al final,
    que es lo que el recorte se lleva.

    La vista **no se puede escribir** —es una vista, no una tabla— y ese es el
    mecanismo de la regla de dominio 3: el estado en T se deriva.
    """
    filas = (
        (
            await sesion.execute(
                text(
                    "SELECT personaje, evento_id, tiempo_historia, sabe_desde "
                    "FROM estado_en_t WHERE obra_id = :obra_id "
                    "ORDER BY COALESCE(sabe_desde, 0) DESC, evento_id DESC"
                ),
                {"obra_id": obra_id},
            )
        )
        .mappings()
        .all()
    )

    presentes, _ = ficha.entidades
    pertinentes = [f for f in filas if normalizar(str(f["personaje"])) in presentes]
    piezas = tuple(
        Pieza(
            texto=(
                f"{f['personaje']} sabe desde la escena {f['sabe_desde']} ({f['tiempo_historia']})"
            ),
            identificador=f"ev:{f['evento_id']}",
        )
        for f in pertinentes
    )
    return Surtido(piezas=piezas, disponibles=len(pertinentes))


async def _surtir_continuidad(sesion: AsyncSession, obra_id: int, ficha: _Ficha) -> Surtido:
    """Escenas N-1 y N-2, **en su version vigente**, y en ese orden.

    §2.1: se recorta «la escena N-2 antes que la N-1», asi que N-1 va primera.

    El censo cuenta las escenas anteriores **que tienen texto vigente**, no las
    que existen: el capitulo 1 no tiene N-1 y el 2 puede tener una N-1 planificada
    y aun sin escribir. Contar las que existen haria fallar el primer capitulo de
    toda obra, que es el caso mas normal que hay.
    """
    filas = (
        (
            await sesion.execute(
                text(
                    """
                SELECT e.orden_discurso AS orden, vt.id AS vt_id, vt.texto AS texto
                FROM escena AS e
                JOIN capitulo AS c ON c.id = e.capitulo_id
                JOIN version_texto AS vt ON vt.escena_id = e.id AND vt.vigente = 1
                WHERE c.obra_id = :obra_id
                  AND e.orden_discurso IN (:anterior, :penultima)
                ORDER BY e.orden_discurso DESC
                """
                ),
                {
                    "obra_id": obra_id,
                    "anterior": ficha.orden_discurso - 1,
                    "penultima": ficha.orden_discurso - 2,
                },
            )
        )
        .mappings()
        .all()
    )

    piezas = tuple(
        Pieza(
            texto=f"Escena {f['orden']}:\n{f['texto']}",
            identificador=f"vt:{f['vt_id']}",
        )
        for f in filas
    )
    return Surtido(piezas=piezas, disponibles=len(filas))


async def _surtir_memoria(
    sesion: AsyncSession,
    obra_id: int,
    capitulo: Mapping[str, Any],
    ficha: _Ficha,
    *,
    consulta: Sequence[float] | None,
    almacen: VectorStore | None,
) -> Surtido:
    """El indice vectorial, tras la recuperacion hibrida de T7. **Y el aviso.**

    `recuperar` devuelve `[]` por tres motivos distintos y **son tres cosas
    distintas**; si no se separan, RF-CTX-06 se cumple por consecuencia y su
    test pasa sin comprobar nada:

    1. **Nadie trajo vector de consulta.** Hoy nadie puede: `ClienteModelo` no
       tiene metodo de vectorizar (Desviaciones de la ola 2), asi que el indice
       no se llena en produccion. Censo 0.
    2. **El filtro estructural no deja nada pertinente.** No hay memoria que
       venga a cuento, y eso es lo normal en los primeros capitulos. Censo 0.
       Contar aqui el indice entero convertiria el caso normal en averia.
    3. **Hay escenas pertinentes y ninguna esta indexada.** El indice esta sin
       llenar, que no es lo mismo que un almacen que no responde. Censo 0.
       Contar aqui los candidatos del filtro haria fallar un sistema que
       simplemente todavia no ha vectorizado nada.

    Y queda el cuarto, que **si** es averia: hay escenas pertinentes, estan
    indexadas, y no sale nada. Censo > 0, capa vacia, `CapaVacia`.
    """
    if consulta is None or almacen is None:
        return Surtido()

    filtro = FiltroEstructural(
        obra_id=obra_id,
        presentes=(ficha.pov, *ficha.presentes),
        lugar=ficha.lugar,
        hilos_abiertos=await _hilos_abiertos(sesion, obra_id),
        desde_capitulo=1,
        # **Hasta el capitulo anterior, no hasta este.** Se recupera lo ya
        # escrito, y la escena en curso todavia no lo esta. Incluirla no seria
        # inofensivo: la escena siempre comparte lugar y presentes **consigo
        # misma**, asi que seria candidata de su propio filtro y el caso «el
        # filtro no deja nada» dejaria de existir. Lo destapo la mutacion de
        # CA-6, con el test en verde por el motivo equivocado (ver Desviaciones).
        hasta_capitulo=int(capitulo["numero"]) - 1,
    )
    candidatos = await filtrar_estructuralmente(sesion, filtro)
    if not candidatos:
        return Surtido()

    indexadas = await _escenas_indexadas(sesion, [c.escena_id for c in candidatos])
    if not indexadas:
        return Surtido()

    recuperados = await recuperar(
        sesion,
        filtro=filtro,
        consulta=consulta,
        almacen=almacen,
        orden_actual=ficha.orden_discurso,
    )
    piezas = tuple(
        Pieza(texto=r.fragmento, identificador=f"emb:{r.embedding_id}") for r in recuperados
    )
    return Surtido(piezas=piezas, disponibles=len(indexadas))


def _surtir_instruccion(ficha: _Ficha) -> Surtido:
    """La ficha de escena: lo que se pide escribir. Nunca se recorta (RF-CTX-07)."""
    f = ficha.fila
    texto = (
        f"Escribe la escena {f['orden_discurso']}.\n"
        f"POV: {f['pov']}. Lugar: {f['lugar']}. Tiempo: {f['tiempo_historia']}.\n"
        f"Presentes: {', '.join(ficha.presentes)}.\n"
        f"Objetivo del POV: {f['objetivo_del_pov']}. Obstaculo: {f['obstaculo']}.\n"
        f"Resultado: {f['resultado']}. "
        f"Giro de valor: de {f['valor_entrada']} a {f['valor_salida']}.\n"
        f"Extension objetivo: {f['extension_objetivo']} palabras. "
        f"Densidad de dialogo: {f['densidad_de_dialogo_objetivo']}. "
        f"Distancia psiquica: {f['distancia_psiquica']}."
    )
    return Surtido(
        piezas=(Pieza(texto=texto, identificador=f"escena:{ficha.escena_id}"),),
        disponibles=1,
    )


# ---------------------------------------------------------------------------
# Lecturas de apoyo
# ---------------------------------------------------------------------------


async def _capitulo(sesion: AsyncSession, capitulo_id: int) -> Mapping[str, Any]:
    fila = (
        (
            await sesion.execute(
                text("SELECT id, obra_id, numero FROM capitulo WHERE id = :id"),
                {"id": capitulo_id},
            )
        )
        .mappings()
        .first()
    )
    if fila is None:
        raise CapituloDesconocido(capitulo_id)
    # `dict(...)` y no la `RowMapping` en crudo: es lo que hace que el tipo que
    # sale de aqui sea el que se declara, sin apagar el comprobador.
    datos: dict[str, Any] = dict(fila)
    return datos


async def _ficha(sesion: AsyncSession, capitulo_id: int) -> _Ficha:
    fila = (
        (
            await sesion.execute(
                text("SELECT * FROM escena WHERE capitulo_id = :id"), {"id": capitulo_id}
            )
        )
        .mappings()
        .first()
    )
    if fila is None:
        raise CapituloSinEscena(capitulo_id)
    return _Ficha(
        escena_id=int(fila["id"]),
        orden_discurso=int(fila["orden_discurso"]),
        pov=str(fila["pov"]),
        lugar=str(fila["lugar"]),
        presentes=tuple(_json(fila["presentes"])),
        mencionados=tuple(_json(fila["mencionados"])),
        fila=dict(fila),
    )


async def _hilos_abiertos(sesion: AsyncSession, obra_id: int) -> tuple[int, ...]:
    filas = await sesion.execute(
        text("SELECT id FROM hilo_narrativo WHERE obra_id = :o AND estado = 'abierto'"),
        {"o": obra_id},
    )
    return tuple(int(f[0]) for f in filas)


async def _escenas_indexadas(sesion: AsyncSession, escenas: Sequence[int]) -> tuple[int, ...]:
    """Cuales de esas escenas tienen algo en el indice. Es el censo de la memoria."""
    if not escenas:
        return ()
    marcas = ", ".join(f":e{i}" for i in range(len(escenas)))
    filas = await sesion.execute(
        text(f"SELECT DISTINCT escena_id FROM embedding WHERE escena_id IN ({marcas})"),
        {f"e{i}": e for i, e in enumerate(escenas)},
    )
    return tuple(int(f[0]) for f in filas)


def _json(valor: Any) -> Any:
    """SQLAlchemy Core devuelve las columnas JSON en crudo; el ORM ya las decodifica."""
    return json.loads(valor) if isinstance(valor, str | bytes) else valor


def _numericos(identificadores: Sequence[str], prefijo: str) -> list[int]:
    """`hc:41` -> `41`, para las dos columnas de ids que trae el esquema de T2."""
    return [int(i.split(":", 1)[1]) for i in identificadores if i.startswith(f"{prefijo}:")]
