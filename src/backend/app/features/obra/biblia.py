"""La biblia: contrato de salida del Arquitecto y su versionado.

RF-OBR-02 y RF-OBR-03. Dos ideas sostienen este modulo:

**La salida del agente se valida contra un esquema** (RF-ORQ-15). Lo que no
valida es fallo del paso, no texto que se arrastre al siguiente. Un Arquitecto
que devuelve media biblia produciria un outline construido sobre huecos, y el
sintoma aparecería diez escenas mas tarde como un defecto de continuidad.

**La biblia no se edita en sitio.** Cambiarla crea una version nueva (RD-12), y
cada escena recuerda con cual se escribio (RF-ESC-06). Editar la vigente dejaria
las escenas anteriores apoyadas en hechos que ya no existen y sin rastro del
porque, que es exactamente lo que el ledger existe para evitar.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.commons.domain import RolNarrativo


class SalidaDeAgenteInvalida(ValueError):
    """La salida de un agente no valida contra su esquema (RF-ORQ-15)."""


class PersonajeDeBiblia(BaseModel):
    """Solo la parte fija (RD-03). La movil se deriva del ledger."""

    model_config = ConfigDict(frozen=True)

    pj_id: str = Field(min_length=1)
    nombre: str = Field(min_length=1)
    edad: int = Field(ge=0)
    rol_narrativo: RolNarrativo
    herida_original: str | None = None
    mentira_que_se_cree: str | None = None
    deseo_consciente: str | None = None
    necesidad_inconsciente: str | None = None
    miedo_central: str | None = None


class LugarDeBiblia(BaseModel):
    model_config = ConfigDict(frozen=True)

    lug_id: str = Field(min_length=1)
    nombre: str = Field(min_length=1)
    tipo: str | None = None
    sensorialidad_fija: list[str] = Field(default_factory=list)


class DistanciaDeBiblia(BaseModel):
    """`tiempo_de_viaje` no es un adorno: es lo unico que hace detectable el
    teletransporte de RF-CAL-04 (`definitions.md` §4.4)."""

    model_config = ConfigDict(frozen=True)

    origen_id: str = Field(min_length=1)
    destino_id: str = Field(min_length=1)
    tiempo_de_viaje: str = Field(min_length=1)


class ReglaDeMundoDeBiblia(BaseModel):
    model_config = ConfigDict(frozen=True)

    regla_id: str = Field(min_length=1)
    enunciado: str = Field(min_length=1)
    alcance: str | None = None


class Biblia(BaseModel):
    """Contrato de salida del Arquitecto (`architecture.md` §3.4)."""

    model_config = ConfigDict(frozen=True)

    tropo: str = Field(min_length=1)
    promesa_de_apertura: str = Field(min_length=1)
    personajes: list[PersonajeDeBiblia] = Field(min_length=1)
    lugares: list[LugarDeBiblia] = Field(min_length=1)
    distancias: list[DistanciaDeBiblia] = Field(min_length=1)
    reglas_de_mundo: list[ReglaDeMundoDeBiblia] = Field(default_factory=list)

    @model_validator(mode="after")
    def cada_lugar_tiene_tiempo_de_viaje(self) -> "Biblia":
        """Sin esto RF-CAL-04 no puede decidir nada y el defecto CON-01 se
        vuelve indetectable para los lugares que falten."""
        con_distancia = {d.origen_id for d in self.distancias} | {
            d.destino_id for d in self.distancias
        }
        huerfanos = sorted(
            lugar.lug_id for lugar in self.lugares if lugar.lug_id not in con_distancia
        )
        if huerfanos:
            raise ValueError(
                f"lugares sin ningun tiempo_de_viaje declarado: {huerfanos}. "
                f"Sin el, RF-CAL-04 no puede detectar un desplazamiento imposible"
            )
        return self


class VersionDeBiblia(BaseModel):
    """Una fila de `version_obra`, ya en forma de modelo (RI-12)."""

    model_config = ConfigDict(frozen=True)

    version_obra_id: str
    obra_id: str
    numero: int
    biblia: Biblia
