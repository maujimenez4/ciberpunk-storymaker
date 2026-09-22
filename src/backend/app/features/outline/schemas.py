"""Contrato de salida del Arquitecto para el outline, y el contrato de genero.

RF-OUT-01 a RF-OUT-05. Los diez hitos y su orden salen de `domain-knowledge.md`
§8.1. Lo que alli no admite excepcion son dos cosas —la **presencia** y el
**orden**—, y son justo las dos que se comprueban aqui. Las franjas de posicion
no se validan: son aproximadas por definicion, y exigirlas convertiria una guia
en una camisa de fuerza.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OutlineInvalido(ValueError):
    """El outline incumple el contrato de genero o su propia estructura."""


class BeatDeGenero(StrEnum):
    """Los diez hitos obligatorios del romance, **en orden**."""

    CARENCIAS = "carencias"
    ENCUENTRO = "encuentro"
    PUNTO_DE_NO_RETORNO = "punto_de_no_retorno"
    DIVERSION_Y_JUEGOS = "diversion_y_juegos"
    PUNTO_MEDIO = "punto_medio"
    LA_GRIETA = "la_grieta"
    RUPTURA = "ruptura"
    REVELACION_INTERIOR = "revelacion_interior"
    GRAN_GESTO = "gran_gesto"
    HEA_HFN = "hea_hfn"


# El orden de declaracion **es** el orden del contrato: un gran gesto antes de
# la revelacion interior no significa nada, porque el personaje no ha cambiado.
BEATS_OBLIGATORIOS: tuple[str, ...] = tuple(b.value for b in BeatDeGenero)
_POSICION = {beat: i for i, beat in enumerate(BEATS_OBLIGATORIOS)}


class EscenaDeOutline(BaseModel):
    """RF-OUT-03: una escena nace ya con su nucleo dramatico."""

    model_config = ConfigDict(frozen=True)

    orden_discurso: int = Field(ge=1)
    pov: str = Field(min_length=1)
    lugar: str = Field(min_length=1)
    objetivo_del_pov: str = Field(min_length=1)
    obstaculo: str = Field(min_length=1)
    valor_entrada: str = Field(min_length=1)
    valor_salida: str = Field(min_length=1)
    beat_de_genero: BeatDeGenero | None = None

    @model_validator(mode="after")
    def el_giro_de_valor_no_es_nulo(self) -> "EscenaDeOutline":
        if self.valor_entrada == self.valor_salida:
            raise ValueError(
                f"la escena {self.orden_discurso} entra y sale en "
                f"'{self.valor_entrada}': sin giro de valor es relleno (RG-08)"
            )
        return self


class CapituloDeOutline(BaseModel):
    model_config = ConfigDict(frozen=True)

    numero: int = Field(ge=1)
    titulo: str | None = None
    pov_dominante: str | None = None
    escenas: list[EscenaDeOutline] = Field(min_length=1)


class ParteDeOutline(BaseModel):
    model_config = ConfigDict(frozen=True)

    numero: int = Field(ge=1)
    funcion_estructural: str = Field(min_length=1)
    capitulos: list[CapituloDeOutline] = Field(min_length=1)


class Outline(BaseModel):
    """RF-OUT-01: `Parte` -> `Capitulo` -> `Escena`."""

    model_config = ConfigDict(frozen=True)

    partes: list[ParteDeOutline] = Field(min_length=1)

    def escenas_en_orden(self) -> list[EscenaDeOutline]:
        return [
            escena
            for parte in self.partes
            for capitulo in parte.capitulos
            for escena in capitulo.escenas
        ]

    @model_validator(mode="after")
    def cada_beat_obligatorio_en_exactamente_una_escena(self) -> "Outline":
        """RF-OUT-02 y RG-06."""
        asignados: dict[str, list[int]] = {}
        for escena in self.escenas_en_orden():
            if escena.beat_de_genero is not None:
                asignados.setdefault(escena.beat_de_genero.value, []).append(
                    escena.orden_discurso
                )

        ausentes = [b for b in BEATS_OBLIGATORIOS if b not in asignados]
        if ausentes:
            raise ValueError(
                f"hitos de genero sin escena asignada: {ausentes}. RG-06 exige "
                f"exactamente una, y arreglarlo aqui cuesta una linea; en el "
                f"manuscrito cuesta reescribir un capitulo"
            )

        repetidos = {b: o for b, o in asignados.items() if len(o) > 1}
        if repetidos:
            raise ValueError(
                f"hitos asignados a mas de una escena: {repetidos}. Un outline que "
                f"promete dos veces lo mismo cumple a medias las dos"
            )
        return self

    @model_validator(mode="after")
    def los_hitos_respetan_su_orden(self) -> "Outline":
        """RF-OUT-05. `domain-knowledge.md` §8.1: las posiciones son franjas,
        pero el orden no admite excepcion."""
        vistos = [
            (escena.orden_discurso, escena.beat_de_genero.value)
            for escena in self.escenas_en_orden()
            if escena.beat_de_genero is not None
        ]
        vistos.sort()
        anterior = -1
        for orden, beat in vistos:
            posicion = _POSICION[beat]
            if posicion < anterior:
                raise ValueError(
                    f"el hito '{beat}' aparece en la escena {orden}, antes que un "
                    f"hito que deberia precederlo: el orden del contrato de genero "
                    f"no admite excepcion (RF-OUT-05)"
                )
            anterior = posicion
        return self
