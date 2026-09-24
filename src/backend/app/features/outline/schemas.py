"""Modelos de entrada y de salida de la feature `outline`, y el vocabulario del
contrato del genero.

Los modelos de base de datos no salen de aqui (`CLAUDE.md` §6): lo que el
endpoint devuelve son estos, y no las filas de `capitulo`. No es ceremonia —
`capitulo` no tiene columnas para el plan dramatico del capitulo, que vive en
`escena`, y una respuesta construida desde la fila perderia justo eso.
"""

import re
import unicodedata
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

EXTENSION_MINIMA = 1000
EXTENSION_MAXIMA = 1500
CAPITULOS_DEL_OUTLINE = 10


class BeatDeGenero(StrEnum):
    """Los diez hitos obligatorios del romance (`definitions.md` §6).

    **El conjunto es cerrado y el orden es el del contrato**, no alfabetico: es
    el orden en que el lector los espera, y `domain-knowledge.md` §8.1 dice que
    la presencia y el orden son lo unico que no admite excepcion. Que sea un
    `StrEnum` es lo que hace que un beat inventado no llegue a ser un beat: lo
    para el esquema del agente, no una comprobacion escrita a mano.

    Son diez, y el outline tiene diez capitulos: con `beat_de_genero` de
    cardinalidad 0..1 en cada capitulo (`definitions.md` §4.1), «cada beat en
    exactamente un capitulo» acaba siendo una biyeccion. No se codifica asi a
    proposito: la regla que RF-PLA-03 enuncia es la de los beats, y el dia que
    el outline tenga doce capitulos seguira siendo la misma.
    """

    CARENCIAS = "presentacion_de_carencias"
    ENCUENTRO = "encuentro"
    PUNTO_DE_NO_RETORNO = "punto_de_no_retorno"
    DIVERSION_Y_JUEGOS = "diversion_y_juegos"
    PUNTO_MEDIO = "punto_medio"
    LA_GRIETA = "la_grieta"
    RUPTURA = "ruptura"
    REVELACION_INTERIOR = "revelacion_interior"
    GRAN_GESTO = "gran_gesto"
    HEA_HFN = "hea_hfn"


class Persona(StrEnum):
    """Los tres valores de `definitions.md` §5, con **su** grafia.

    La ordinal femenina abreviada no es un descuido de este fichero: es el
    literal del documento, y `CLAUDE.md` §2 dice que el mismo concepto se llama
    igual en el esquema de datos, en los prompts y en la interfaz. Tres tareas
    de tres olas distintas comparan contra estas cadenas —el Planificador para
    validar la ficha, el Escritor para la regla de dominio 10—, y una grafia
    propia aqui las rompe a las tres sin que falle nada aqui.
    """

    PRIMERA = "1ª"
    TERCERA_LIMITADA = "3ª limitada"
    TERCERA_OMNISCIENTE = "3ª omnisciente"


class TiempoVerbal(StrEnum):
    """Los dos de `definitions.md` §5. El conjunto es cerrado."""

    PASADO = "pasado"
    PRESENTE = "presente"


class TipoDeCorte(StrEnum):
    """Los tres cortes de `definitions.md` §4.1 (`Capitulo`, criterio de cierre)."""

    TENSION = "tensión"
    PREGUNTA = "pregunta"
    REVELACION = "revelación"


class DiscursoDeLaObra(BaseModel):
    """Los parametros de discurso que la biblia declara (`definitions.md` §5).

    Se declaran una vez a nivel de obra y se imponen en cada escena como
    restriccion dura. **Hoy viven solo en la biblia**, porque `persona` y
    `tiempo_verbal` no son columnas de `obra` (ver Desviaciones): es el unico
    sitio de donde el Planificador puede leerlos.

    `extra=ignore`, y es la unica excepcion de esta feature: la biblia es un
    documento abierto —premisa, personajes, reglas del mundo— y esto valida solo
    la parte que el sistema entiende. El `forbid` esta donde importa, en el
    outline, que otras tareas consumen campo a campo.
    """

    model_config = ConfigDict(extra="ignore")

    persona: Persona
    tiempo_verbal: TiempoVerbal
    nivel_de_calor: int = Field(ge=0, le=4)


class CapituloDelOutline(BaseModel):
    """Un capitulo del outline: lo que RF-PLA-04 exige, capitulo a capitulo.

    `extra=forbid` no es celo. Sin el, un modelo que escribe `beat` en vez de
    `beat_de_genero` produce un capitulo que valida, sale con su beat en blanco
    y **pierde el dato en silencio**. La Fase 1 lo descubrio ejecutando, con un
    brief que salia «completo» perdiendo justo lo que faltaba.

    `extension_objetivo` repite aqui el rango que `capitulo` sostiene con un
    `CheckConstraint`. La duplicidad es deliberada: si solo lo parase la base,
    una extension fuera de rango seria un `IntegrityError` —un 500— en vez de lo
    que es, un agente que devolvio algo fuera de su esquema (RF-ORQ-09).
    """

    model_config = ConfigDict(extra="forbid")

    numero: int = Field(ge=1, le=CAPITULOS_DEL_OUTLINE)
    titulo: str = Field(min_length=1, max_length=200)
    pov_dominante: str = Field(min_length=1, max_length=120)
    lugar: str = Field(min_length=1, max_length=200)
    objetivo: str = Field(min_length=1, max_length=500)
    obstaculo: str = Field(min_length=1, max_length=500)
    valor_entrada: str = Field(min_length=1, max_length=120)
    valor_salida: str = Field(min_length=1, max_length=120)
    gancho_de_apertura: str = Field(min_length=1, max_length=500)
    tipo_de_corte_final: TipoDeCorte
    extension_objetivo: int = Field(ge=EXTENSION_MINIMA, le=EXTENSION_MAXIMA)
    beat_de_genero: BeatDeGenero | None = None

    @field_validator("tipo_de_corte_final", mode="before")
    @classmethod
    def el_corte_que_nombra(cls, valor: object) -> object:
        """Una frase que nombra **uno solo** de los tres cortes dice cual es.

        El modelo tiende a describir el corte en vez de nombrarlo -- «corta en
        pregunta: quien escribio la carta» --, y la corrida del 2026-09-24 perdio
        los diez capitulos por eso. Se toma el corte que la frase nombra, sin
        acentos ni mayusculas; si nombra dos o ninguno, no se adivina y el
        valor sigue tal cual para que el enum lo rechace.
        """
        if not isinstance(valor, str):
            return valor
        palabras = set(re.findall(r"\w+", _sin_acentos(valor.lower())))
        nombrados = [corte for corte in TipoDeCorte if _sin_acentos(corte.value) in palabras]
        return nombrados[0] if len(nombrados) == 1 else valor


def _sin_acentos(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


class OutlineCreado(BaseModel):
    """Lo que RI-04 devuelve: la version de la biblia y los diez capitulos.

    Lleva los capitulos enteros, con su plan dramatico, y no solo sus ids: el
    plan de cada capitulo **no tiene columna donde persistirse hoy** (ver
    Desviaciones), asi que esta respuesta es el unico sitio donde sale completo.
    """

    obra_id: int
    version_obra_id: int
    version: int
    capitulos: list[CapituloDelOutline]
