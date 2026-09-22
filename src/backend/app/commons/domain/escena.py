"""Reglas de dominio que el esquema hace ciertas por construccion.

Dos axiomas de `definitions.md` §11 viven aqui, y ninguno de los dos se delega
al prompt:

- **Axioma 8 (RG-08):** toda escena tiene exactamente un `pov` y un giro de valor
  no nulo. Una escena sin giro es relleno, y es la primera validacion automatica
  que conviene tener.
- **Axioma 9 (RG-09):** ningun contenido romantico o sexual con personajes
  menores de 18 anos. `CLAUDE.md` §10 y RNF-SEG-02 lo dicen sin rodeos: ninguna
  regla de seguridad depende solo del prompt. Un modelo puede ignorar una
  instruccion; un `ValidationError` no se ignora.

Sin framework (§5.2 regla 3): esto se prueba sin base de datos y sin FastAPI.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

EDAD_MINIMA_PARA_CONTENIDO_ROMANTICO = 18


class NivelDeCalor(StrEnum):
    """Escala declarada de `definitions.md` §6, de menor a mayor explicitud."""

    PUERTA_CERRADA = "puerta_cerrada"
    SENSUAL = "sensual"
    ABIERTO = "abierto"
    EXPLICITO = "explicito"

    def implica_contenido_romantico(self) -> bool:
        """Puerta cerrada es la unica que no promete nada explicito."""
        return self is not NivelDeCalor.PUERTA_CERRADA


class RolNarrativo(StrEnum):
    PROTAGONISTA = "protagonista"
    COPROTAGONISTA = "coprotagonista"
    ANTAGONISTA = "antagonista"
    ALIADO = "aliado"
    CATALIZADOR = "catalizador"
    FIGURANTE = "figurante"


class ParametrosDeDiscurso(BaseModel):
    """Se declaran una vez en la `Obra` y se imponen en cada escena.

    `definitions.md` §5: son restriccion dura, no preferencia de estilo. Que
    viajen juntos evita el fallo tipico de heredar tres de los cuatro.
    """

    model_config = ConfigDict(frozen=True)

    persona: str = Field(min_length=1)
    tiempo_verbal: str = Field(min_length=1)
    esquema_de_pov: str = Field(min_length=1)
    nivel_de_calor: NivelDeCalor


class PersonajeEnEscena(BaseModel):
    """Lo que la escena necesita saber de quien aparece en ella."""

    model_config = ConfigDict(frozen=True)

    pj_id: str = Field(min_length=1)
    nombre: str = Field(min_length=1)
    edad: int = Field(ge=0)
    rol_narrativo: RolNarrativo


class EscenaPlanificada(BaseModel):
    """Una escena tal como sale del outline, antes de tener prosa."""

    model_config = ConfigDict(frozen=True)

    escena_id: str = Field(min_length=1)
    # Axioma 8: exactamente un POV. La cadena vacia no es un POV.
    pov: str = Field(min_length=1)
    valor_entrada: str = Field(min_length=1)
    valor_salida: str = Field(min_length=1)
    presentes: list[PersonajeEnEscena] = Field(min_length=1)
    nivel_de_calor: NivelDeCalor = NivelDeCalor.PUERTA_CERRADA

    def tiene_giro_de_valor(self) -> bool:
        return self.valor_entrada != self.valor_salida

    @model_validator(mode="after")
    def el_giro_de_valor_no_es_nulo(self) -> "EscenaPlanificada":
        if not self.tiene_giro_de_valor():
            raise ValueError(
                f"la escena {self.escena_id} no tiene giro de valor: entra y sale "
                f"en '{self.valor_entrada}'. Una escena sin giro es relleno "
                f"(definitions.md §11, axioma 8)"
            )
        return self

    @model_validator(mode="after")
    def ningun_menor_en_contenido_romantico(self) -> "EscenaPlanificada":
        if not self.nivel_de_calor.implica_contenido_romantico():
            return self
        menores = [
            p.pj_id
            for p in self.presentes
            if p.edad < EDAD_MINIMA_PARA_CONTENIDO_ROMANTICO
        ]
        if menores:
            raise ValueError(
                f"nivel de calor '{self.nivel_de_calor}' con personajes menores de "
                f"{EDAD_MINIMA_PARA_CONTENIDO_ROMANTICO}: {menores}. Es regla dura, "
                f"sin excepcion narrativa (definitions.md §11, axioma 9)"
            )
        return self
