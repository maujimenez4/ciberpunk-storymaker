"""Ajustes del proceso, leidos de entorno.

RI-21: valores por defecto explicitos, y el arranque falla de inmediato si falta
una variable obligatoria.

**Aqui no hay ninguna credencial, y es deliberado** (RI-15, RNF-SEG-03, decision
(a) de 2026-09-22). El proveedor es el CLI de Claude Code, que autentica con la
sesion de la cuenta: la credencial vive fuera del proceso y la aplicacion no la
lee, no la guarda y no puede filtrarla. La unica forma segura de tratar un
secreto es no tenerlo.

Hasta hoy quedaban `proveedor_generacion_clave`, `proveedor_generacion_url` y
`proveedor_embeddings_clave`, obligatorias y sin un solo consumidor. Un campo
asi no se nota nunca: obliga a exportar una variable inventada y hace creer que
el sistema necesita algo que no necesita.
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
    modelo: str
    ruta_base_de_datos: str

    # Con valor por defecto explicito.
    llamadas_simultaneas: int = 1  # D-03, architecture.md §2.2
    timeout_turno_s: int = 300  # D-03
    plazo_paso_codigo_s: int = 30  # D-04
    plazo_paso_modelo_s: int = 600  # D-04
    snapshot_cada_n_escenas: int = 5  # D-01

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
