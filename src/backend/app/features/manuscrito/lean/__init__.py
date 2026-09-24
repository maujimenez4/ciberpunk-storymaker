"""El puente entre la cronologia y Lean.

`generar_lean` produce los datos (T4) y `correr_lean` los pasa por el
compilador con los invariantes de `plantilla.lean` (T5). Se entra por aqui y no
por los modulos, igual que en el resto del repositorio.
"""

from app.features.manuscrito.lean.corredor import (
    HerramientaNoDisponible,
    Resultado,
    correr_lean,
    ruta_de_lean,
)
from app.features.manuscrito.lean.generador import escapar, generar_lean

__all__ = [
    "HerramientaNoDisponible",
    "Resultado",
    "correr_lean",
    "escapar",
    "generar_lean",
    "ruta_de_lean",
]
