import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Ajustes:
    """Se lee del entorno y de ningun otro sitio (RF-OBS-07)."""

    ruta_db: Path
    clave_proveedor: str | None

    # Observabilidad (RF-OBS-07). Las tres del entorno y de ningun otro sitio:
    # `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` y `LANGFUSE_HOST`, este con
    # `LANGFUSE_BASE_URL` de respaldo. Se documentan en `.env.example`.
    #
    # `None` cuando faltan, y no cadena vacia: quien decide la degradacion es
    # `obtener_observador`, y necesita distinguir «no esta» de «esta en blanco»
    # sin adivinar. Las tres o ninguna -- media configuracion falla en la
    # primera llamada, ya dentro de la generacion.
    langfuse_clave_publica: str | None = None
    langfuse_clave_secreta: str | None = None
    langfuse_host: str | None = None

    @staticmethod
    def desde_entorno() -> "Ajustes":
        return Ajustes(
            ruta_db=Path(os.environ.get("STORYMAKER_DB", "storymaker.db")),
            clave_proveedor=os.environ.get("ANTHROPIC_API_KEY"),
            langfuse_clave_publica=os.environ.get("LANGFUSE_PUBLIC_KEY"),
            langfuse_clave_secreta=os.environ.get("LANGFUSE_SECRET_KEY"),
            langfuse_host=_host_de_langfuse(),
        )


def _host_de_langfuse() -> str | None:
    """`LANGFUSE_HOST`, y si no esta, `LANGFUSE_BASE_URL`. **Manda HOST.**

    `LANGFUSE_BASE_URL` es el nombre del SDK v3 de Langfuse, y es el que trae un
    `.env` copiado del panel. Leyendo solo `LANGFUSE_HOST`, ese `.env` dejaba el
    observador en el nulo **sin un error**: arrancaba, avisaba y no media nada.

    **Un HOST en blanco cuenta como ausente**, y no por comodidad: `.env.example`
    trae `LANGFUSE_HOST=` vacio, y quien lo copia y rellena solo
    `LANGFUSE_BASE_URL` volveria a caer en el nulo sin saber por que.
    """
    return os.environ.get("LANGFUSE_HOST") or os.environ.get("LANGFUSE_BASE_URL")
