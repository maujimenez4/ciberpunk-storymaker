"""CU-02: planificar la obra. De un brief salen una biblia versionada y un
outline de diez capitulos con sus beats repartidos.

Aqui viven las reglas de dominio del Arquitecto. No estan en el esquema del
agente a proposito: un outline de nueve capitulos esta perfectamente **bien
formado**, y lo que pasa es que no cumple RF-PLA-02. Son dos fallos distintos —
uno del agente, otro de la planificacion— y mezclarlos dejaria al comprador con
«el modelo devolvio algo raro» cuando lo que ocurre es que falta un hito del
genero.

**Ningun `HTTPException` entra en este fichero** (`CLAUDE.md` §6): lo que sale de
aqui son excepciones de dominio, y el manejador central de `commons/errors/`
decide con que codigo se cuentan.
"""

from collections import Counter
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.domain.errores import ErrorDeDominio, RecursoDesconocido
from app.commons.observabilidad import (
    ClienteObservado,
    Observacion,
    Observador,
    ObservadorNulo,
)
from app.features.outline.agents import (
    HASH_DE_PLANTILLA_V2,
    PROMPT_ID,
    PROMPT_VERSION,
    Arquitecto,
    OutlineGenerado,
)
from app.features.outline.modelos import VersionObra
from app.features.outline.repository import (
    DatosDeObra,
    cuenta_capitulos,
    guardar_outline,
    leer_obra,
    siguiente_numero_de_version,
)
from app.features.outline.schemas import CAPITULOS_DEL_OUTLINE, BeatDeGenero, DiscursoDeLaObra


class ObraDesconocida(RecursoDesconocido):
    """El id que se pide no es de ninguna obra.

    Sin ella, un id mal escrito llega hasta la clave ajena de `capitulo` y sale
    como `IntegrityError`, que es un 500. Se comprueba **antes** de llamar al
    modelo: no se gasta cuota para descubrir que la URL estaba mal.

    Se traduce a 409 y no a 404, que es lo que le corresponde: el manejador
    central solo baja a 404 la `EntrevistaDesconocida`, y ese fichero tiene otro
    dueno en esta fase. Queda anotado en Desviaciones.
    """

    def __init__(self, obra_id: int) -> None:
        self.obra_id = obra_id
        super().__init__(f"No existe la obra {obra_id}")


class ObraYaPlanificada(ErrorDeDominio):
    """La obra ya tiene outline, y planificar otra vez chocaria con la base.

    `uq_capitulo_obra_numero` lo pararia igual, pero como `IntegrityError`: un
    500 por pulsar dos veces. Replanificar de verdad —borrar los capitulos y
    escribir otros— no es esto: seria una peticion de cambio, y la Fase 2 no la
    tiene.
    """

    def __init__(self, obra_id: int, capitulos: int) -> None:
        self.obra_id = obra_id
        super().__init__(f"La obra {obra_id} ya tiene {capitulos} capitulos planificados")


class OutlineIncompleto(ErrorDeDominio):
    """RF-PLA-02: diez capitulos, numerados del 1 al 10 y sin repetir.

    «Diez filas» no basta: dos capitulos con el mismo numero dejan de nombrar
    uno solo, y el outline se lee por numero desde el ensamblado hasta la
    auditoria.
    """

    def __init__(self, numeros: list[int]) -> None:
        self.numeros = list(numeros)
        super().__init__(
            f"Un outline son {CAPITULOS_DEL_OUTLINE} capitulos del 1 al "
            f"{CAPITULOS_DEL_OUTLINE}; llegaron estos numeros: {self.numeros}"
        )


class BeatsMalAsignados(ErrorDeDominio):
    """RF-PLA-03 y CA-32: cada beat obligatorio, en **exactamente un** capitulo.

    Los dos lados se cuentan por separado y se devuelven nombrados. No es
    simetria decorativa: un beat **sin asignar** es una novela a la que le falta
    un hito del contrato del genero, y uno **duplicado** deja ademas a otro
    fuera y rompe el orden, que es lo unico que `domain-knowledge.md` §8.1 dice
    que no admite excepcion. Quien lo lea tiene que poder volver a planificar
    sabiendo cual.

    Es error de dominio y no un aviso, con esas palabras en la spec: un romance
    sin ruptura no es un romance flojo, es una devolucion.
    """

    def __init__(
        self,
        sin_asignar: list[BeatDeGenero],
        duplicados: list[BeatDeGenero],
    ) -> None:
        self.sin_asignar = list(sin_asignar)
        self.duplicados = list(duplicados)
        super().__init__(
            "El outline no cubre el contrato del genero. "
            f"Sin asignar: {[b.value for b in self.sin_asignar]}. "
            f"En mas de un capitulo: {[b.value for b in self.duplicados]}"
        )


class DiscursoNoDeclarado(ErrorDeDominio):
    """La biblia no declara los parametros de discurso, o los declara mal.

    `persona` y `tiempo_verbal` se declaran una vez a nivel de obra y se imponen
    en cada escena como restriccion dura (`definitions.md` §5). **Hoy la biblia
    es el unico sitio donde viven**, porque no son columnas de `obra`: el
    Planificador de escena los lee de aqui para construir la ficha y el Escritor
    los necesita para la regla de dominio 10. Una biblia sin ellos no deja
    escribir ni una escena, asi que el outline se rechaza entero en vez de
    guardarse a medias.

    La grafia importa tanto como la presencia: «tercera persona limitada» no es
    `3ª limitada`, y quien compare despues no encontraria el valor.
    """

    def __init__(self, motivo: str) -> None:
        self.motivo = motivo
        super().__init__(f"La biblia no declara los parametros de discurso: {motivo}")


class GiroDeValorAusente(ErrorDeDominio):
    """RF-PLA-04: el giro de valor previsto de cada capitulo.

    Un capitulo que entra y sale del mismo valor es relleno (`definitions.md`
    §4.1), y con diez capitulos no hay ninguno de sobra. Se para aqui porque el
    `CheckConstraint` que lo sostiene esta en `escena`, y el outline se escribe
    antes de que exista ninguna escena: sin esta guarda, el capitulo plano
    llegaria intacto hasta el Planificador.
    """

    def __init__(self, capitulos: list[int]) -> None:
        self.capitulos = list(capitulos)
        super().__init__(f"Sin giro de valor previsto en los capitulos {self.capitulos}")


@dataclass(frozen=True)
class PlanDeObra:
    """Lo que CU-02 deja: la biblia congelada y el outline que la acompana.

    Lleva el `OutlineGenerado` entero y no solo las filas guardadas porque el
    plan dramatico de cada capitulo —lugar, objetivo, obstaculo, giro previsto y
    beat— **no tiene columna donde persistirse** (ver Desviaciones), y esta es la
    unica forma de que salga completo de la llamada que lo produjo.
    """

    version_obra: VersionObra
    outline: OutlineGenerado


def _biblia_con_discurso(outline: OutlineGenerado, obra: DatosDeObra) -> dict[str, Any]:
    """La biblia que se congela, con el nivel de calor puesto por la obra.

    **El `nivel_de_calor` no lo decide el Arquitecto**: lo declaro el comprador y
    es columna de `obra`. Se sobrescribe en vez de comprobarse porque es una
    restriccion dura (regla de dominio 5) y `CLAUDE.md` §10 dice que ninguna
    depende solo del prompt: si el modelo devuelve otro, el que vale es el de la
    obra, y no hay nada que negociar.

    `persona` y `tiempo_verbal` si son suyos —son decisiones de discurso—, asi
    que esos se **validan**, no se imponen.
    """
    biblia = {**outline.biblia, "nivel_de_calor": obra.nivel_de_calor}
    try:
        DiscursoDeLaObra.model_validate(biblia)
    except ValidationError as error:
        raise DiscursoNoDeclarado(str(error.errors(include_url=False))) from error
    return biblia


def _comprobar_numeracion(outline: OutlineGenerado) -> None:
    numeros = [capitulo.numero for capitulo in outline.capitulos]
    if sorted(numeros) != list(range(1, CAPITULOS_DEL_OUTLINE + 1)):
        raise OutlineIncompleto(numeros)


def _comprobar_beats(outline: OutlineGenerado) -> None:
    """Cada beat obligatorio, en exactamente un capitulo (RF-PLA-03, CA-32)."""
    asignados = Counter(
        capitulo.beat_de_genero
        for capitulo in outline.capitulos
        if capitulo.beat_de_genero is not None
    )
    sin_asignar = [beat for beat in BeatDeGenero if asignados[beat] == 0]
    duplicados = [beat for beat in BeatDeGenero if asignados[beat] > 1]
    if sin_asignar or duplicados:
        raise BeatsMalAsignados(sin_asignar, duplicados)


def _comprobar_giros_de_valor(outline: OutlineGenerado) -> None:
    planos = [
        capitulo.numero
        for capitulo in outline.capitulos
        if capitulo.valor_entrada == capitulo.valor_salida
    ]
    if planos:
        raise GiroDeValorAusente(sorted(planos))


async def planificar_obra(
    sesion: AsyncSession,
    arquitecto: Arquitecto,
    obra_id: int,
    *,
    observador: Observador | None = None,
    cliente: ClienteObservado | None = None,
) -> PlanDeObra:
    """CU-02 entero, y en este orden.

    **Se valida todo antes de escribir nada.** Media planificacion guardada es
    peor que ninguna: dejaria en la base unos capitulos que el comprador nunca
    aprobo y que el Planificador leeria como si fueran el outline.

    **La llamada al Arquitecto abre la traza `outline`** en la sesion de la obra
    (`CLAUDE.md` §4.3), con el span `arquitecto`. `cliente` es el mismo objeto
    con el que se construyo el Arquitecto: es el que deja el prompt y la salida
    en el span. La traza se abre **despues** de comprobar que la obra existe:
    una sesion de una obra que no existe es ruido en el panel.
    """
    obra = await leer_obra(sesion, obra_id)
    if obra is None:
        raise ObraDesconocida(obra_id)

    ya_planificados = await cuenta_capitulos(sesion, obra_id)
    if ya_planificados:
        raise ObraYaPlanificada(obra_id, ya_planificados)

    observador = observador if observador is not None else ObservadorNulo()
    async with (
        observador.traza(obra_id=obra_id, nombre="outline") as traza,
        Observacion(traza=traza, cliente=cliente).span("arquitecto") as span,
    ):
        span.prompt(PROMPT_ID, PROMPT_VERSION, HASH_DE_PLANTILLA_V2)

        def _cumple_las_reglas(propuesto: OutlineGenerado) -> None:
            # Las reglas de la planificacion, para que un incumplimiento tenga un
            # reintento dirigido con el motivo (corrida real: `gran_gesto` sin
            # asignar daba 409 y costaba un clic y tres minutos).
            _biblia_con_discurso(propuesto, obra)
            _comprobar_numeracion(propuesto)
            _comprobar_beats(propuesto)
            _comprobar_giros_de_valor(propuesto)

        outline = await arquitecto.planificar(obra.como_brief(), _cumple_las_reglas)
    biblia = _biblia_con_discurso(outline, obra)
    _comprobar_numeracion(outline)
    _comprobar_beats(outline)
    _comprobar_giros_de_valor(outline)

    numero = await siguiente_numero_de_version(sesion, obra_id)
    version, _ = await guardar_outline(
        sesion,
        obra_id,
        numero,
        biblia,
        outline.capitulos,
    )
    # Y se confirma, que es lo que faltaba: sin esto el endpoint respondia 201 y
    # no dejaba un solo capitulo en el fichero. La suite no lo veia porque sus
    # tests comparten la sesion del `cliente`, asi que lo escrito y sin
    # confirmar se lee igual de bien que lo confirmado.
    await sesion.commit()
    return PlanDeObra(version_obra=version, outline=outline)
