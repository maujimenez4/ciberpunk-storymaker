"""Modelos de la feature `escena`.

La `FichaDeEscena` es el contrato de salida del Planificador y la entrada de la
capa de instruccion del paquete. Lo que no este declarado aqui, el Escritor no
lo recibe: por eso RF-ESC-02 enumera las restricciones duras una por una, y por
eso los defectos son atribuibles —si falta un dato, es fallo del ensamblado, no
del Escritor (`architecture.md` §3.5)—.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.commons.domain import NivelDeCalor


class FichaInvalida(ValueError):
    """La salida del Planificador no valida contra su esquema (RF-ORQ-15)."""


class PropuestaDeFicha(BaseModel):
    """Lo que **propone** el Planificador.

    No incluye `nivel_de_calor`: es el unico dato de la ficha que el agente no
    decide. Si pudiera proponerlo tendria via para subir el calor por encima de
    lo prometido al lector, y RG-10 dependeria de que el modelo se porte bien.
    Se ignora si viene: el esquema simplemente no lo recoge.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    pov: str = Field(min_length=1)
    presentes: list[str] = Field(min_length=1)
    lugar: str = Field(min_length=1)
    objetivo_del_pov: str = Field(min_length=1)
    obstaculo: str = Field(min_length=1)
    valor_entrada: str = Field(min_length=1)
    valor_salida: str = Field(min_length=1)
    distancia_psiquica: str = Field(min_length=1)
    # Es una proporcion: un 4.0 delata una salida mal formada, no una escena muy
    # dialogada.
    densidad_de_dialogo_objetivo: float = Field(ge=0.0, le=1.0)
    extension_objetivo: int = Field(gt=0)

    @model_validator(mode="after")
    def el_pov_esta_presente_en_su_escena(self) -> "PropuestaDeFicha":
        if self.pov not in self.presentes:
            raise ValueError(
                f"el POV '{self.pov}' no esta entre los presentes {self.presentes}: "
                f"un POV ausente de su escena no puede percibir nada"
            )
        return self

    @model_validator(mode="after")
    def el_giro_de_valor_no_es_nulo(self) -> "PropuestaDeFicha":
        if self.valor_entrada == self.valor_salida:
            raise ValueError(
                f"la escena entra y sale en '{self.valor_entrada}': sin giro de "
                f"valor es relleno (RG-08). Se caza aqui para no gastar una "
                f"llamada de escritura en una escena que el validador rechazara"
            )
        return self


class FichaDeEscena(BaseModel):
    """La ficha completa: lo propuesto mas lo heredado (RF-ESC-02)."""

    model_config = ConfigDict(frozen=True)

    escena_id: str = Field(min_length=1)
    pov: str
    presentes: list[str]
    lugar: str
    objetivo_del_pov: str
    obstaculo: str
    valor_entrada: str
    valor_salida: str
    distancia_psiquica: str
    densidad_de_dialogo_objetivo: float
    extension_objetivo: int
    # Heredados de la obra, no propuestos (RF-OBR-01).
    persona: str
    tiempo_verbal: str
    nivel_de_calor: NivelDeCalor
