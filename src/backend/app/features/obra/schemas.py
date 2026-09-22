"""Modelos de entrada y de salida de la feature `obra` (RI-12).

Separados a proposito: `Brief` es lo que envia el autor y `ObraCreada` lo que se
devuelve. Ninguno es el modelo de base de datos, que no sale de `repository.py`.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.commons.domain import NivelDeCalor, ParametrosDeDiscurso


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
