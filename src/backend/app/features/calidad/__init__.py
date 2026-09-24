"""La UNICA puerta de entrada a la feature `calidad` (`CLAUDE.md` §5.1)."""

from app.features.calidad.defectos import (
    CODIGOS_DE_LA_TAXONOMIA,
    DefectoMalFormado,
    DefectosClasificados,
    MotivoMalFormado,
    clasificar,
    comprobar_forma,
)
from app.features.calidad.puerta import ResultadoDePuerta, cruzar_g1a
from app.features.calidad.schemas import (
    Defecto,
    NombreDeCanon,
    ParametrosDeDiscurso,
    Persona,
    RangoDeExtension,
    TiempoVerbal,
)
from app.features.calidad.validadores import (
    CATALOGO,
    CapituloAValidar,
    PuntoDeEjecucion,
    Validador,
    discurso,
    extension_de_capitulo,
    nombres_literales,
)

__all__ = [
    "CATALOGO",
    "CODIGOS_DE_LA_TAXONOMIA",
    "CapituloAValidar",
    "Defecto",
    "DefectoMalFormado",
    "DefectosClasificados",
    "MotivoMalFormado",
    "NombreDeCanon",
    "ParametrosDeDiscurso",
    "Persona",
    "PuntoDeEjecucion",
    "RangoDeExtension",
    "ResultadoDePuerta",
    "TiempoVerbal",
    "Validador",
    "clasificar",
    "comprobar_forma",
    "cruzar_g1a",
    "discurso",
    "extension_de_capitulo",
    "nombres_literales",
]
