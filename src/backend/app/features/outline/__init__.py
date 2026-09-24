"""La UNICA puerta de entrada a la feature `outline` (`CLAUDE.md` §5.1).

Lo que no esta aqui no se importa desde fuera: ni `modelos.py`, ni `router.py`,
ni `service.py`. `main.py` monta `router` y nada mas.

Lo que si se exporta es **vocabulario**, no tablas: `BeatDeGenero`
(`definitions.md` §6), y `Persona` y `TiempoVerbal` (§5), que son los literales
que el Planificador de escena compara contra la ficha y el Escritor contra el
texto (regla de dominio 10). Se exportan justo para que ninguno de los dos los
vuelva a escribir a mano: tres grafias del mismo valor no fallan aqui, fallan al
integrar. Las **tablas** siguen sin cruzar: las claves ajenas se declaran por
nombre.
"""

from app.features.outline.router import router
from app.features.outline.schemas import (
    BeatDeGenero,
    CapituloDelOutline,
    OutlineCreado,
    Persona,
    TiempoVerbal,
)

__all__ = [
    "BeatDeGenero",
    "CapituloDelOutline",
    "OutlineCreado",
    "Persona",
    "TiempoVerbal",
    "router",
]
