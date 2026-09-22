"""Ajustes del proceso, leidos de entorno.

RI-21: valores por defecto explicitos, y el arranque falla de inmediato si falta
una variable obligatoria. RI-15: las claves se leen de entorno, nunca del
repositorio ni de la base de datos.
"""

from pydantic import ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PREFIJO = "STORYMAKER_"


class AjustesInvalidos(Exception):
    """La configuracion no permite arrancar. No es un error de dominio."""


class Ajustes(BaseSettings):
    """Los valores por defecto son las decisiones D-01 a D-04 de la spec."""

    model_config = SettingsConfigDict(env_prefix=PREFIJO, frozen=True)

    # Sin valor por defecto: sin estas no se arranca.
    proveedor_generacion_clave: str
    proveedor_generacion_url: str
    modelo: str
    proveedor_embeddings_clave: str
    ruta_base_datos: str

    # Con valor por defecto explicito.
    llamadas_simultaneas: int = 1  # D-03, architecture.md §2.2
    timeout_turno_s: int = 300  # D-03
    plazo_paso_codigo_s: int = 30  # D-04
    plazo_paso_modelo_s: int = 600  # D-04
    snapshot_cada_n_escenas: int = 5  # D-01
    dimension_embeddings: int = 1024  # D-02

    @model_validator(mode="after")
    def el_plazo_del_paso_supera_la_espera_de_turno(self) -> "Ajustes":
        """RI-24: si el plazo vence antes que el turno, RNF-TOK-05 no se ejecuta."""
        if self.plazo_paso_modelo_s <= self.timeout_turno_s:
            raise ValueError(
                f"plazo_paso_modelo_s ({self.plazo_paso_modelo_s}) debe superar "
                f"timeout_turno_s ({self.timeout_turno_s}): si no, la espera de "
                f"turno nunca llega a vencer y RNF-TOK-05 queda sin efecto"
            )
        return self


def _nombre_de_entorno(campo: object) -> str:
    return f"{PREFIJO}{campo}".upper() if isinstance(campo, str) else str(campo)


def cargar_ajustes() -> Ajustes:
    """Construye los ajustes o falla nombrando lo que impide arrancar."""
    try:
        return Ajustes()  # type: ignore[call-arg]
    except ValidationError as error:
        motivos = []
        for fallo in error.errors():
            campo = fallo["loc"][0] if fallo["loc"] else ""
            if fallo["type"] == "missing":
                motivos.append(f"{_nombre_de_entorno(campo)}: falta y es obligatoria")
            else:
                motivos.append(f"{campo or 'ajustes'}: {fallo['msg']}")
        raise AjustesInvalidos("; ".join(motivos)) from error
