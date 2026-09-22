"""Modelos de entrada y de salida de la feature `obra` (RI-12).

Separados a proposito: `Brief` es lo que envia el autor y `ObraCreada` lo que se
devuelve. Ninguno es el modelo de base de datos, que no sale de `repository.py`.
"""

import re

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.commons.domain import (
    EDAD_MINIMA_PARA_CONTENIDO_ROMANTICO,
    NivelDeCalor,
    ParametrosDeDiscurso,
)

# RNF-SEG-06. El modelo de amenaza no es un atacante externo: es un brief que
# pide lo que la regla prohibe, confiando en que el prompt ceda. Se corta al
# construir el `Brief`, antes de que ningun texto llegue a ningun modelo.
#
# Es deliberadamente **lexico y conservador**. No pretende entender el texto
# —eso es juicio, y `domain-knowledge.md` §11 dice que el juicio no se cuenta—:
# pretende que el camino facil este cerrado. Leer la prosa sigue siendo la parte
# **I** de RF-CAL-03, que firma una persona (D-09).
_EDADES_MENORES = re.compile(
    # "17 anos", y tambien la edad desnuda tras un verbo de edad: "ella tiene 15"
    # no lleva la palabra anos, y es la forma mas comun de colarla.
    r"\b(?:1[0-7]|[1-9])\s*a[nñ]os?\b"
    r"|\b(?:tiene|tenía|tenia|cumple|cumplió|cumplio|edad\s+de)\s+(?:1[0-7]|[1-9])\b",
    re.IGNORECASE,
)
_MENCION_DE_MENORES = re.compile(
    r"\b(menor(?:es)?\s+de\s+edad|adolescent\w*|instituto|colegial\w*|ni[nñ]\w+)\b",
    re.IGNORECASE,
)
_ELUSION = re.compile(
    r"\b(ignora|olvida|s[aá]lta(?:te)?|omite)\b.{0,40}"
    r"\b(regla|edad|l[ií]mite|restricc)\w*",
    re.IGNORECASE,
)


class Brief(BaseModel):
    """Lo minimo para arrancar una obra (RI-01).

    Los cuatro parametros de discurso son obligatorios: sin ellos la obra no
    tiene restricciones duras que imponer a sus escenas, y toda la cadena de
    validacion posterior se queda sin referencia.
    """

    model_config = ConfigDict(frozen=True)

    titulo: str = Field(min_length=1)
    genero: str = Field(min_length=1)
    subgenero: str = Field(min_length=1)
    extension_objetivo: int = Field(gt=0)
    persona: str = Field(min_length=1)
    tiempo_verbal: str = Field(min_length=1)
    esquema_de_pov: str = Field(min_length=1)
    nivel_de_calor: NivelDeCalor
    logline: str | None = None
    premisa: str | None = None
    tema: str | None = None
    promesa_de_apertura: str | None = None

    def _texto_libre(self) -> str:
        campos = (
            self.titulo,
            self.logline,
            self.premisa,
            self.tema,
            self.promesa_de_apertura,
        )
        return " ".join(t for t in campos if t)

    @model_validator(mode="after")
    def ningun_texto_empuja_contra_la_edad_minima(self) -> "Brief":
        """RNF-SEG-06 y RG-09, por esquema y no por prompt."""
        libres = self._texto_libre()

        if _ELUSION.search(libres):
            raise ValueError(
                "el brief pide saltarse una restriccion de edad o de calor. No se "
                "negocia en el prompt: la regla vive en el esquema "
                "(CLAUDE.md §10, RNF-SEG-02)"
            )

        if not self.nivel_de_calor.implica_contenido_romantico():
            # A puerta cerrada no hay promesa de explicitud, asi que un elenco
            # joven no es contenido romantico con menores. Rechazarlo tambien
            # haria inescribible la novela juvenil entera, y la regla es sobre
            # el contenido, no sobre quien aparece.
            return self

        if _EDADES_MENORES.search(libres) or _MENCION_DE_MENORES.search(libres):
            raise ValueError(
                f"el brief menciona personajes por debajo de "
                f"{EDAD_MINIMA_PARA_CONTENIDO_ROMANTICO} con nivel de calor "
                f"'{self.nivel_de_calor}'. Es regla dura, sin excepcion narrativa "
                f"(definitions.md §11, axioma 9)"
            )
        return self


class ObraCreada(BaseModel):
    """Lo que ve el cliente. Nunca expone la fila de la tabla."""

    model_config = ConfigDict(frozen=True)

    obra_id: str
    serie_id: str
    titulo: str
    persona: str
    tiempo_verbal: str
    esquema_de_pov: str
    nivel_de_calor: NivelDeCalor

    def parametros_para_una_escena(self) -> ParametrosDeDiscurso:
        """RF-OBR-01: los heredan todas sus escenas."""
        return ParametrosDeDiscurso(
            persona=self.persona,
            tiempo_verbal=self.tiempo_verbal,
            esquema_de_pov=self.esquema_de_pov,
            nivel_de_calor=self.nivel_de_calor,
        )
