"""API publica de commons/jobs."""

from app.commons.jobs.estados import (
    EN_CURSO,
    TERMINALES,
    TERMINALES_DEFINITIVOS,
    TRANSICIONES,
    Estado,
    TransicionInvalida,
    exigir,
    puede_ir,
)
from app.commons.jobs.proceso import (
    EjecutorDeTrabajos,
    TurnoDeModelo,
    montar_ejecutor_de_trabajos,
    turno_del_proceso,
)
from app.commons.jobs.trabajos import (
    MAXIMO_DE_REPARACIONES,
    RepositorioDeTrabajos,
    Trabajo,
)

__all__ = [
    "EN_CURSO",
    "MAXIMO_DE_REPARACIONES",
    "TERMINALES",
    "TERMINALES_DEFINITIVOS",
    "TRANSICIONES",
    "EjecutorDeTrabajos",
    "Estado",
    "RepositorioDeTrabajos",
    "Trabajo",
    "TransicionInvalida",
    "exigir",
    "puede_ir",
    "TurnoDeModelo",
    "montar_ejecutor_de_trabajos",
    "turno_del_proceso",
]
