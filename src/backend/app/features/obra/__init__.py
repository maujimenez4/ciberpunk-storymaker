"""La UNICA puerta de entrada a la feature `obra` (`CLAUDE.md` §5.1).

Lo que no esta aqui no se importa desde fuera: ni `router.py`, ni `service.py`,
ni `modelos.py`. `main.py` monta `router` y nada mas.
"""

from app.features.obra.modelos import HechoCanon
from app.features.obra.router import router
from app.features.obra.schemas import BriefEntrada, DestinatarioEntrada, HechoDelBrief

__all__ = ["BriefEntrada", "DestinatarioEntrada", "HechoCanon", "HechoDelBrief", "router"]
