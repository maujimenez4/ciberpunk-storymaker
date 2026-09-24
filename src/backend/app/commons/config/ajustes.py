import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Ajustes:
    """Se lee del entorno y de ningun otro sitio (RF-OBS-07)."""

    ruta_db: Path
    clave_proveedor: str | None

    @staticmethod
    def desde_entorno() -> "Ajustes":
        return Ajustes(
            ruta_db=Path(os.environ.get("STORYMAKER_DB", "storymaker.db")),
            clave_proveedor=os.environ.get("ANTHROPIC_API_KEY"),
        )
