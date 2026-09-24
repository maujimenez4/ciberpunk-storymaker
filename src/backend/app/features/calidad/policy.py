"""El hook de *policy*: el segundo de los dos que pide RF-GUA-07.

`CLAUDE.md` §11 dice por que son dos y por que estan fuera del bucle del
modelo: «un guardarrail que vive dentro del codigo que vigila se puede saltar
cambiando ese codigo; un hook es un punto de enganche declarado, y su ausencia
se ve». El veto funcionaba desde la Fase 1 y **no tenia nombre**: vivia dentro
de `escribir_capitulo`, asi que no se podia enumerar, no se podia contar y no
se podia echar de menos.

Aqui no se reescribe nada de lo que ya estaba probado. La comparacion sigue
siendo `commons.domain.normalizacion.contiene_veto` —por palabra y sobre texto
normalizado (RF-GUA-02)— y el codigo sigue siendo `SEG-02`. Lo que cambia es
que ahora hay **un catalogo con un punto declarado**, y que cada decision sale
con el nombre de la regla que la tomo, que es lo que el encargo §7 pide cuando
habla del «audit log de las decisiones del policy engine».

**Este modulo no escribe en la base de datos.** Decide; quien persiste es el
servicio que lo llama, igual que la puerta G1a devuelve un resultado y no lo
guarda. Separarlo es lo que permite probar el veto sin un ciclo alrededor.
"""

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from app.commons.domain.normalizacion import contiene_veto, normalizar
from app.features.calidad.schemas import Defecto
from app.features.calidad.validadores import PuntoDeEjecucion

CODIGO_DE_PALABRA_PROHIBIDA = "SEG-02"
"""El de `definitions.md` §8. Viaja como defecto de la taxonomia y no como un
caso aparte: asi vuelve al Escritor con su cita, como cualquier otro."""

_PALABRA = re.compile(r"\w+", re.UNICODE)


@dataclass(frozen=True, slots=True)
class CapituloAPolicy:
    """Lo que el hook necesita, y nada mas. Ni base de datos, ni contexto."""

    version_texto_id: str
    texto: str
    vetos: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DecisionDePolicy:
    """Una decision con su regla. `decision` es `permitido` o `bloqueado`, las
    dos, porque un registro que solo guarda los bloqueos no puede contestar por
    que aquella novela salio como salio (`commons/db/auditoria.py`)."""

    regla: str
    decision: str
    motivo: str
    evidencia: dict[str, Any]
    defecto: Defecto | None = None


@dataclass(frozen=True, slots=True)
class ReglaDePolicy:
    """Una regla con su nombre y su punto. Lo que no se puede nombrar no se
    puede contar (RF-VAL-01), y lo que no se puede enumerar no se echa de
    menos (RF-GUA-07)."""

    nombre: str
    punto: PuntoDeEjecucion
    aplicar: Callable[["CapituloAPolicy"], "DecisionDePolicy"]


@dataclass(frozen=True, slots=True)
class ResultadoDePolicy:
    decisiones: tuple[DecisionDePolicy, ...]
    defectos: tuple[Defecto, ...]
    termino_vetado: str | None

    @property
    def bloquea(self) -> bool:
        return bool(self.defectos)


def localizar_veto(texto: str, vetos: Sequence[str]) -> tuple[str, int, int] | None:
    """El termino vetado **y donde esta**, o `None`.

    Sin el desplazamiento la cita no seria subcadena exacta en su posicion
    (regla de dominio 8), el defecto saldria **mal formado** y no bloquearia
    nada. Una palabra prohibida que no bloquea es peor que no comprobarla,
    porque parece comprobada.
    """
    veto = contiene_veto(texto, vetos)
    if veto is None:
        return None
    objetivo = normalizar(veto)
    encontrada = next(p for p in _PALABRA.finditer(texto) if normalizar(p.group(0)) == objetivo)
    return veto, encontrada.start(), encontrada.end()


def palabras_vetadas(capitulo: CapituloAPolicy) -> DecisionDePolicy:
    """Los tres ambitos de RF-GUA-01 llegan ya fundidos en `vetos`: quien los
    lee de SQLite es el servicio, y esta regla no sabe de tablas."""
    encontrado = localizar_veto(capitulo.texto, capitulo.vetos)
    if encontrado is None:
        return DecisionDePolicy(
            regla="palabras_vetadas",
            decision="permitido",
            motivo="sin veto",
            evidencia={"version_texto": capitulo.version_texto_id},
        )
    veto, inicio, fin = encontrado
    return DecisionDePolicy(
        regla="palabras_vetadas",
        decision="bloqueado",
        motivo=f"veto: {veto}",
        evidencia={
            "version_texto": capitulo.version_texto_id,
            "termino": veto,
            "desplazamiento": [inicio, fin],
        },
        defecto=Defecto(
            codigo=CODIGO_DE_PALABRA_PROHIBIDA,
            version_texto_id=capitulo.version_texto_id,
            cita=capitulo.texto[inicio:fin],
            desplazamiento_inicio=inicio,
            desplazamiento_fin=fin,
        ),
    )


CATALOGO_DE_POLICY: tuple[ReglaDePolicy, ...] = (
    ReglaDePolicy("palabras_vetadas", PuntoDeEjecucion.HOOK_DE_POLICY, palabras_vetadas),
)
"""Hoy una regla, y el catalogo existe igual: es el punto de enganche, y un
punto con una regla se puede ampliar sin tocar a quien lo llama."""


def aplicar_policy(capitulo: CapituloAPolicy) -> ResultadoDePolicy:
    """Corre el catalogo entero y devuelve TODAS las decisiones, no solo las
    que bloquean."""
    decisiones = tuple(regla.aplicar(capitulo) for regla in CATALOGO_DE_POLICY)
    defectos = tuple(d.defecto for d in decisiones if d.defecto is not None)
    vetado = next(
        (str(d.evidencia["termino"]) for d in decisiones if d.decision == "bloqueado"),
        None,
    )
    return ResultadoDePolicy(decisiones=decisiones, defectos=defectos, termino_vetado=vetado)
