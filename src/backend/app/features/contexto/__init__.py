"""API publica de la feature `contexto`.

Lo unico importable desde fuera (§5.2 regla 1).
"""

from app.features.contexto.capas import (
    LIMITE_DURO,
    ORIGEN,
    PROTEGIDAS,
    QUE_CEDE_PRIMERO,
    TOPES,
    Capa,
    CapaEnsamblada,
    Pieza,
)
from app.features.contexto.recoleccion import (
    MUESTRAS_ANCLA,
    Almacenes,
    recolectar,
)
from app.features.contexto.service import (
    ABRE_DATOS,
    CIERRA_DATOS,
    CapaVacia,
    DesgloseDeTokens,
    PaqueteDeContexto,
    ensamblar,
)

__all__ = [
    "ABRE_DATOS",
    "MUESTRAS_ANCLA",
    "Almacenes",
    "CIERRA_DATOS",
    "LIMITE_DURO",
    "ORIGEN",
    "PROTEGIDAS",
    "QUE_CEDE_PRIMERO",
    "TOPES",
    "Capa",
    "CapaEnsamblada",
    "CapaVacia",
    "DesgloseDeTokens",
    "PaqueteDeContexto",
    "Pieza",
    "ensamblar",
    "recolectar",
]
