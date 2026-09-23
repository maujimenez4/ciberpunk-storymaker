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
from app.features.escritura.router import (
    DefectoEnRespuesta,
    EstadoDeTrabajo,
    TrabajoAceptado,
    construir_dependencias,
    router,
)
from app.features.escritura.service import (
    Dependencias,
    ResultadoDeEscena,
    SinTurno,
    ciclo_de_escena,
    ejecutar_en_segundo_plano,
)

__all__ = [
    "DefectoEnRespuesta",
    "Dependencias",
    "ResultadoDeEscena",
    "SinTurno",
    "ciclo_de_escena",
    "construir_dependencias",
    "ejecutar_en_segundo_plano",
    "DefectoParaReparar",
    "EstadoDeTrabajo",
    "TrabajoAceptado",
    "router",
    "ReintentoGenericoProhibido",
    "aceptar_pese_al_defecto",
    "preparar_reparacion",
    "prompt_de_reparacion",
    "reentrar_tras_edicion_humana",
]
