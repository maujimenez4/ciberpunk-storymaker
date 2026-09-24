"""La UNICA puerta de entrada a la feature `contexto` (`CLAUDE.md` §5.1).

Lo que no esta aqui no se importa desde fuera. Hoy estan el presupuesto de la
llamada (T5) y la recuperacion hibrida con sus dos almacenes (T7); el
Ensamblador (T6) entra despues y por esta misma puerta.
"""

from app.features.contexto.almacenes import (
    AlmacenFuerzaBruta,
    AlmacenSqliteVec,
    Vecino,
    VectorStore,
    crear_almacen,
)
from app.features.contexto.presupuesto import (
    TECHO_POR_LLAMADA,
    TOPES,
    Capa,
    Desglose,
    LineaDeCapa,
    Pieza,
    presupuestar,
)
from app.features.contexto.recuperacion import (
    LIMITE_POR_DEFECTO,
    PESO_RECENCIA_POR_DEFECTO,
    Candidato,
    FiltroEstructural,
    Recuperado,
    filtrar_estructuralmente,
    fusionar_con_recencia,
    recuperar,
)

__all__ = [
    "LIMITE_POR_DEFECTO",
    "PESO_RECENCIA_POR_DEFECTO",
    "TECHO_POR_LLAMADA",
    "TOPES",
    "AlmacenFuerzaBruta",
    "AlmacenSqliteVec",
    "Candidato",
    "Capa",
    "Desglose",
    "FiltroEstructural",
    "LineaDeCapa",
    "Pieza",
    "Recuperado",
    "Vecino",
    "VectorStore",
    "crear_almacen",
    "filtrar_estructuralmente",
    "fusionar_con_recencia",
    "presupuestar",
    "recuperar",
]
