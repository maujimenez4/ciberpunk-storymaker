"""La peticion de cambio, de punta a punta (plan-5 T7). CU-06, y el orden es `CA-25`.

**Por que vive en `escritura` y no en `manuscrito`, como decia el plan.** Atender
una peticion compone tres features: `canon` corrige el hecho, `escritura`
regenera y `manuscrito` clasifica y publica. `escritura -> canon -> obra ->
manuscrito` ya existe, asi que `manuscrito -> escritura` cerraria un ciclo
(`CLAUDE.md` §5.1 regla 5). Esta feature ya dependia de `canon`, y ahora de
`manuscrito` por su `__init__`: la flecha va en una sola direccion. La tabla y
sus estados siguen siendo de `manuscrito` (`manuscrito/peticiones.py`).

**El orden, que no es intercambiable:** corregir el canon (RF-PET-02) ->
regenerar **sin consolidar** lo que usa el hecho (RF-PET-03) -> revalidar los
posteriores al origen (RF-PET-04) -> clasificar contra el cuadro guardado
(RF-PET-05) -> y solo si no hay introducidos, consolidar y publicar (RF-PET-06).
Consolidar antes de clasificar dejaria en el ledger los eventos de una prosa que
puede acabar descartada, y el ledger no se borra (decision previa del plan).

**Consolidar y publicar van en un mismo SAVEPOINT.** Si `publicar` rechaza
-- Lean, un obligatorio que falta --, el punto de retorno deshace la
consolidacion **sin** un `DELETE` sobre `evento`: se deshace una transaccion, no
se borra el ledger. Y la prosa se retira como en cualquier descarte.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.domain.errores import ErrorDeDominio
from app.commons.jobs.turnos import CerrojoDeEscena, PresupuestoConcurrente
from app.commons.llm.contador import ContadorDeTokens
from app.commons.observabilidad import Observador
from app.features.calidad import CapituloAValidar, Defecto, cruzar_g1a
from app.features.canon import (
    HechoDesconocido,
    Vector,
    corregir_por_peticion,
    exigir_hecho_vivo,
    origen_del_hecho,
)
from app.features.escritura.ciclo import (
    RANGO_DE_CAPITULO,
    Agentes,
    ResultadoDelCiclo,
    _nombres_del_canon,
    _restricciones,
    ejecutar_ciclo,
    leer_trabajo,
)
from app.features.escritura.maquina import ESTADOS_TERMINALES, Estado
from app.features.escritura.modelos import Trabajo
from app.features.escritura.regeneracion import (
    PREFIJO_DE_REGENERACION,
    Ejecutar,
    consolidar_la_regeneracion,
    regenerar_capitulo,
    retirar_prosa_de_la_corrida,
)
from app.features.escritura.service import _discurso
from app.features.manuscrito import (
    TERMINADAS,
    Clasificacion,
    Peticion,
    alcance_de_la_peticion,
    anotar_hecho_nuevo,
    cerrar_peticion,
    clasificar_contra_el_cuadro,
    cuadro_guardado,
    huella_de,
    leer_peticion,
    marcar_regenerando,
    publicar,
)
from app.features.manuscrito import registrar_peticion as _registrar_fila


class Revalidar(Protocol):
    """RF-PET-04: los defectos que hoy tienen los capitulos, en `(numero, Defecto)`."""

    async def __call__(
        self, sesion: AsyncSession, *, obra_id: int, numeros: Sequence[int]
    ) -> list[tuple[int, Defecto]]: ...


@dataclass(frozen=True, slots=True)
class ResultadoDeLaPeticion:
    peticion_id: int
    estado: str
    hecho_nuevo_id: int | None
    version_producida_id: int | None
    capitulos_regenerados: tuple[int, ...]
    preexistentes: tuple[Defecto, ...]
    introducidos: tuple[Defecto, ...]
    resultado: str


@dataclass(frozen=True, slots=True)
class _Regenerado:
    numero: int
    capitulo_id: int
    escena_id: int
    resultado: ResultadoDelCiclo


async def registrar_peticion(
    sesion: AsyncSession, *, obra_id: int, hecho_canon_id: int, texto_pedido: str
) -> Peticion:
    """RF-PET-01, con las dos guardas que tienen que salir **en la respuesta**.

    Un hecho de otra obra es desconocido (404), y uno ya sustituido es R-5
    (409): el trabajo de fondo corre despues, y alli ya no hay a quien decirselo.
    """
    duena = (
        await sesion.execute(
            text("SELECT obra_id FROM hecho_canon WHERE id = :h"), {"h": hecho_canon_id}
        )
    ).scalar_one_or_none()
    if duena is None or int(duena) != obra_id:
        raise HechoDesconocido(hecho_canon_id)
    await exigir_hecho_vivo(sesion, hecho_canon_id=hecho_canon_id)
    return await _registrar_fila(
        sesion, obra_id=obra_id, hecho_canon_id=hecho_canon_id, texto_pedido=texto_pedido
    )


def _marca(peticion_id: int, desde_trabajo: int) -> str:
    return f"pet{peticion_id}-desde{desde_trabajo}"


def _desde_trabajo(run_id: str | None) -> int | None:
    """El ultimo trabajo que existia al empezar: los de la peticion son los de despues."""
    if not run_id or "-desde" not in run_id:
        return None
    try:
        return int(run_id.rsplit("-desde", 1)[1])
    except ValueError:
        return None


async def atender_peticion(
    sesion: AsyncSession,
    *,
    peticion_id: int,
    ejecutar: Ejecutar,
    cerrojo: CerrojoDeEscena,
    revalidar: Revalidar,
    vectorizar: Callable[[str], Vector] | None = None,
    observador: Observador | None = None,
) -> ResultadoDeLaPeticion:
    """CU-06 entero. **El cerrojo es de peticiones, no el de escenas** (R-4).

    `ejecutar_ciclo` toma el cerrojo de escena por obra, y `asyncio.Lock` no es
    reentrante: envolver la peticion con el mismo cerrojo la bloquearia contra
    si misma en el primer capitulo. Dos peticiones sobre la misma obra se
    esperan por este; dos escenas, por el suyo.
    """
    peticion = await leer_peticion(sesion, peticion_id)
    corridas: list[tuple[int, str]] = []
    async with cerrojo.por_obra(peticion.obra_id):
        try:
            return await _atender(
                sesion, peticion, ejecutar, revalidar, corridas, vectorizar, observador
            )
        except ErrorDeDominio as fallo:
            # RF-PET-07: no se publica, y no queda rastro de la prosa. La
            # correccion del canon SI se queda: es lo que el lector pidio.
            await _retirar(sesion, corridas)
            cerrada = await cerrar_peticion(
                sesion, peticion_id, estado="descartada", resultado=f"no se publico: {fallo}"
            )
            await sesion.commit()
            return _resultado(cerrada, (), None)


async def _atender(
    sesion: AsyncSession,
    peticion: Peticion,
    ejecutar: Ejecutar,
    revalidar: Revalidar,
    corridas: list[tuple[int, str]],
    vectorizar: Callable[[str], Vector] | None,
    observador: Observador | None,
) -> ResultadoDeLaPeticion:
    # 1. R-7: `regenerando` y confirmada **antes** de la primera llamada.
    ultimo = int(
        (await sesion.execute(text("SELECT COALESCE(MAX(id), 0) FROM trabajo"))).scalar_one()
    )
    await marcar_regenerando(sesion, peticion.id, run_id=_marca(peticion.id, ultimo))
    await sesion.commit()

    # 2. RF-PET-02. No edita: escribe el hecho que sustituye.
    nuevo = await corregir_por_peticion(
        sesion, hecho_canon_id=peticion.hecho_canon_id, nuevo_valor=peticion.texto_pedido
    )
    await anotar_hecho_nuevo(sesion, peticion.id, nuevo.id)
    await sesion.commit()

    # 3. RF-PET-03 y RF-PET-04.
    alcance = await alcance_de_la_peticion(
        sesion,
        obra_id=peticion.obra_id,
        hecho_canon_id=peticion.hecho_canon_id,
        desde=await origen_del_hecho(sesion, hecho_canon_id=peticion.hecho_canon_id),
    )
    if alcance.vacio:
        cerrada = await cerrar_peticion(
            sesion,
            peticion.id,
            estado="atendida",
            resultado="ningun capitulo se apoya en el hecho: el canon queda corregido "
            "y no habia prosa que rehacer",
        )
        await sesion.commit()
        return _resultado(cerrada, (), None)

    # 4. Solo lo que usa el hecho, y sin tocar memoria larga.
    regenerados: list[_Regenerado] = []
    for numero in alcance.a_regenerar:
        capitulo_id = await _capitulo_id(sesion, peticion.obra_id, numero)
        resultado = await regenerar_capitulo(
            sesion, obra_id=peticion.obra_id, capitulo_id=capitulo_id, ejecutar=ejecutar
        )
        escena_id = (await leer_trabajo(sesion, resultado.trabajo_id)).escena_id
        if escena_id is not None:
            corridas.append((escena_id, resultado.run_id))
        if (
            resultado.estado != Estado.INTEGRADA.value
            or resultado.escritura is None
            or not resultado.escritura.aprobado
            or escena_id is None
        ):
            # Regla de dominio 14 por el camino nuevo: un capitulo que no paso
            # su puerta no se publica, tampoco en una peticion.
            await _retirar(sesion, corridas)
            cerrada = await cerrar_peticion(
                sesion,
                peticion.id,
                estado="descartada",
                resultado=f"el capitulo {numero} no paso su puerta de calidad al regenerarse"
                + (f": {resultado.causa_fallo}" if resultado.causa_fallo else ""),
            )
            await sesion.commit()
            return _resultado(cerrada, alcance.a_regenerar, None)
        regenerados.append(_Regenerado(numero, capitulo_id, escena_id, resultado))

    # 5 y 6. Revalidar sobre los posteriores al origen **y** los regenerados, y
    # clasificar contra el cuadro de la version de origen.
    revisados = sorted(set(alcance.a_revalidar) | set(alcance.a_regenerar))
    hallados = await revalidar(sesion, obra_id=peticion.obra_id, numeros=revisados)
    cuadro = await cuadro_guardado(sesion, version_publicada_id=peticion.version_publicada_id)
    clasificacion = clasificar_contra_el_cuadro(hallados=hallados, cuadro=cuadro)

    # 7. RF-PET-06: **solo** un introducido impide publicar.
    if clasificacion.impide_publicar:
        await _retirar(sesion, corridas)
        cerrada = await cerrar_peticion(
            sesion,
            peticion.id,
            estado="descartada",
            resultado=_motivo(hallados, cuadro),
        )
        await sesion.commit()
        return _resultado(cerrada, alcance.a_regenerar, clasificacion)

    # El cuadro de la tirada nueva: lo que no se revalido sigue como estaba, y
    # lo revalidado es lo que se hallo hoy (todo preexistente, si se llega aqui).
    nuevo_cuadro = [(c, d) for c, d in cuadro if c not in revisados] + list(hallados)
    async with sesion.begin_nested():
        for regenerado in regenerados:
            await consolidar_la_regeneracion(
                sesion,
                resultado=regenerado.resultado,
                obra_id=peticion.obra_id,
                escena_id=regenerado.escena_id,
                capitulo_id=regenerado.capitulo_id,
                vectorizar=vectorizar,
            )
        version = await publicar(
            sesion, peticion.obra_id, observador=observador, defectos_vigentes=nuevo_cuadro
        )
    cerrada = await cerrar_peticion(
        sesion,
        peticion.id,
        estado="atendida",
        resultado=f"publicada la version {version.ordinal}, con "
        f"{len(clasificacion.preexistentes)} defectos que ya estaban",
        version_producida_id=version.id,
    )
    await sesion.commit()
    return _resultado(cerrada, alcance.a_regenerar, clasificacion)


def _motivo(hallados: Sequence[tuple[int, Defecto]], cuadro: Sequence[tuple[int, Defecto]]) -> str:
    conocidos = {huella_de(d, capitulo=c) for c, d in cuadro}
    nuevos = [
        f"{d.codigo} en el capitulo {c}"
        for c, d in hallados
        if huella_de(d, capitulo=c) not in conocidos
    ]
    return "la regeneracion introdujo defectos que la version publicada no tenia: " + ", ".join(
        nuevos
    )


def _resultado(
    peticion: Peticion, capitulos: tuple[int, ...], clasificacion: Clasificacion | None
) -> ResultadoDeLaPeticion:
    return ResultadoDeLaPeticion(
        peticion_id=peticion.id,
        estado=peticion.estado,
        hecho_nuevo_id=peticion.hecho_nuevo_id,
        version_producida_id=peticion.version_producida_id,
        capitulos_regenerados=capitulos,
        preexistentes=() if clasificacion is None else clasificacion.preexistentes,
        introducidos=() if clasificacion is None else clasificacion.introducidos,
        resultado=peticion.resultado or "",
    )


async def _retirar(sesion: AsyncSession, corridas: Sequence[tuple[int, str]]) -> None:
    for escena_id, run_id in corridas:
        await retirar_prosa_de_la_corrida(sesion, escena_id=escena_id, run_id=run_id)
    await sesion.flush()


async def _capitulo_id(sesion: AsyncSession, obra_id: int, numero: int) -> int:
    return int(
        (
            await sesion.execute(
                text("SELECT id FROM capitulo WHERE obra_id = :o AND numero = :n"),
                {"o": obra_id, "n": numero},
            )
        ).scalar_one()
    )


async def avance_de_la_peticion(sesion: AsyncSession, peticion: Peticion) -> list[tuple[int, str]]:
    """RF-ESP-02 de la 002: `pendiente` · `escribiendo` · `hecho`, por capitulo.

    Se deriva de los trabajos de regeneracion posteriores a la marca que la
    peticion guardo en su `run_id` al empezar: nada en memoria, asi que una
    caida del proceso no deja la espera mintiendo.
    """
    alcance = await alcance_de_la_peticion(
        sesion, obra_id=peticion.obra_id, hecho_canon_id=peticion.hecho_canon_id, desde=None
    )
    if peticion.estado in TERMINADAS:
        return [(n, "hecho") for n in alcance.a_regenerar]
    desde = _desde_trabajo(peticion.run_id)
    if desde is None:
        return [(n, "pendiente") for n in alcance.a_regenerar]
    terminales = {e.value for e in ESTADOS_TERMINALES}
    avance: list[tuple[int, str]] = []
    for numero in alcance.a_regenerar:
        estado = (
            await sesion.execute(
                text(
                    "SELECT t.estado FROM trabajo AS t JOIN capitulo AS c ON c.id = t.capitulo_id "
                    "WHERE c.obra_id = :o AND c.numero = :n AND t.run_id LIKE :prefijo "
                    "AND t.id > :desde ORDER BY t.id DESC LIMIT 1"
                ),
                {
                    "o": peticion.obra_id,
                    "n": numero,
                    "prefijo": f"{PREFIJO_DE_REGENERACION}%",
                    "desde": desde,
                },
            )
        ).scalar_one_or_none()
        if estado is None:
            avance.append((numero, "pendiente"))
        elif estado in terminales:
            avance.append((numero, "hecho"))
        else:
            avance.append((numero, "escribiendo"))
    return avance


async def revalidar_mecanicamente(
    sesion: AsyncSession, *, obra_id: int, numeros: Sequence[int]
) -> list[tuple[int, Defecto]]:
    """La revalidacion de produccion: la puerta G1a **mecanica** sobre el texto vigente.

    **Punto ciego declarado:** no vuelve a llamar al Continuista, que es quien
    halla `CAN-01`; un capitulo no regenerado que sigue diciendo «Luna» despues
    de corregir a «Nala» no se detecta aqui. Hacerlo es una llamada al modelo
    por capitulo revalidado, y eso lo decide quien firma el presupuesto.
    """
    nombres = await _nombres_del_canon(sesion, obra_id)
    hechos = [
        str(i)
        for i in (
            await sesion.execute(
                text("SELECT id FROM hecho_canon WHERE obra_id = :o"), {"o": obra_id}
            )
        )
        .scalars()
        .all()
    ]
    hallados: list[tuple[int, Defecto]] = []
    for numero in numeros:
        fila = (
            (
                await sesion.execute(
                    text(
                        "SELECT v.id AS id, v.texto AS texto, e.version_obra_id AS vo "
                        "FROM capitulo AS c JOIN escena AS e ON e.capitulo_id = c.id "
                        "JOIN version_texto AS v ON v.escena_id = e.id AND v.vigente = 1 "
                        "WHERE c.obra_id = :o AND c.numero = :n"
                    ),
                    {"o": obra_id, "n": numero},
                )
            )
            .mappings()
            .first()
        )
        if fila is None:
            continue
        restricciones = await _restricciones(sesion, obra_id, int(fila["vo"]))
        resultado = cruzar_g1a(
            CapituloAValidar(
                version_texto_id=str(fila["id"]),
                texto=str(fila["texto"]),
                rango_de_extension=RANGO_DE_CAPITULO,
                discurso=_discurso(restricciones),
                nombres_del_canon=tuple(nombres),
            ),
            hechos,
        )
        hallados.extend((numero, d) for d in resultado.bloqueantes)
    return hallados


def ciclo_de_la_peticion(
    sesion: AsyncSession,
    *,
    agentes: Agentes,
    contador: ContadorDeTokens,
    presupuesto: PresupuestoConcurrente,
    cerrojo: CerrojoDeEscena,
    vectorizar: Callable[[str], Vector] | None = None,
    modelo: str = "desconocido",
    observador: Observador | None = None,
) -> Ejecutar:
    """El `Ejecutar` de produccion: el ciclo de siempre, con `consolidar` explicito."""

    async def ejecutar(trabajo: Trabajo, *, consolidar: bool) -> ResultadoDelCiclo:
        assert trabajo.capitulo_id is not None
        return await ejecutar_ciclo(
            sesion,
            trabajo,
            capitulo_id=trabajo.capitulo_id,
            agentes=agentes,
            contador=contador,
            presupuesto=presupuesto,
            cerrojo=cerrojo,
            vectorizar=vectorizar,
            modelo=modelo,
            observador=observador,
            consolidar=consolidar,
        )

    return ejecutar
