"""La UNICA puerta de entrada a la feature `escena` (`CLAUDE.md` §5.1).

Lo que sale de aqui es el Planificador de escena y su producto: la **ficha de
escena**, que es la entrada del Ensamblador (T6) y, por el paquete, la del
Escritor (T8). La tabla `Escena` **no se exporta**: las claves ajenas se
declaran por nombre y quien necesite la ficha recibe la ficha, no la fila.
"""

from app.features.escena.agents import (
    HASH_DE_PLANTILLA_V1,
    PROMPT_ID,
    PROMPT_VERSION,
    Planificador,
    SalidaMalFormada,
)
from app.features.escena.repository import ids_de_escenas_de_capitulo
from app.features.escena.schemas import (
    DiscursoNoDeclarado,
    FichaDeEscena,
    RestriccionesDeDiscurso,
)
from app.features.escena.service import planificar_escena

__all__ = [
    "HASH_DE_PLANTILLA_V1",
    "PROMPT_ID",
    "PROMPT_VERSION",
    "DiscursoNoDeclarado",
    "FichaDeEscena",
    "Planificador",
    "RestriccionesDeDiscurso",
    "SalidaMalFormada",
    "ids_de_escenas_de_capitulo",
    "planificar_escena",
]
