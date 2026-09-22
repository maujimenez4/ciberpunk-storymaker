"""API publica de la feature `escritura`.

Lo unico importable desde fuera (§5.2 regla 1).
"""

from app.features.escritura.ciclo import (
    DefectoParaReparar,
    ReintentoGenericoProhibido,
    aceptar_pese_al_defecto,
    preparar_reparacion,
    prompt_de_reparacion,
    reentrar_tras_edicion_humana,
)

__all__ = [
    "DefectoParaReparar",
    "ReintentoGenericoProhibido",
    "aceptar_pese_al_defecto",
    "preparar_reparacion",
    "prompt_de_reparacion",
    "reentrar_tras_edicion_humana",
]
