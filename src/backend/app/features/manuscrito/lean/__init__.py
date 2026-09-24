"""El puente entre la cronologia y Lean.

`generar_lean` produce el fichero de datos (T4) y la plantilla de invariantes
vive junto a el (T5). Se entra por aqui y no por `generador.py`, igual que en el
resto del repositorio.
"""

from app.features.manuscrito.lean.generador import escapar, generar_lean

__all__ = ["escapar", "generar_lean"]
