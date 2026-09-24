"""La UNICA puerta de entrada a la feature `calidad` (`CLAUDE.md` §5.1).

Detras de ella viven la puerta mecanica G1a y, desde la Fase 3, el
**Continuista**: el rol que contrasta un capitulo contra el grafo de canon. Lo
que se exporta de el es lo que un orquestador necesita —el agente, su entrada,
su salida y su fallo— y nada mas: el esquema con el que se valida lo que el
modelo devuelve es interno, porque nadie fuera lo construye.
"""

from app.features.calidad.agents import (
    CapituloAContrastar,
    Continuista,
    HechoDeCanon,
    OrigenDeHecho,
    RevisionDeContinuidad,
    SalidaMalFormada,
)
from app.features.calidad.cobertura import (
    CODIGO_DE_ELEMENTO_AUSENTE,
    Cobertura,
    ElementoAusente,
    ElementoCubierto,
    HechoUsado,
    cobertura_de_obligatorios,
)
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
    "CODIGO_DE_ELEMENTO_AUSENTE",
    "CapituloAContrastar",
    "CapituloAValidar",
    "Cobertura",
    "Continuista",
    "Defecto",
    "DefectoMalFormado",
    "DefectosClasificados",
    "ElementoAusente",
    "ElementoCubierto",
    "HechoDeCanon",
    "HechoUsado",
    "MotivoMalFormado",
    "NombreDeCanon",
    "OrigenDeHecho",
    "ParametrosDeDiscurso",
    "Persona",
    "PuntoDeEjecucion",
    "RangoDeExtension",
    "ResultadoDePuerta",
    "RevisionDeContinuidad",
    "SalidaMalFormada",
    "TiempoVerbal",
    "Validador",
    "clasificar",
    "cobertura_de_obligatorios",
    "comprobar_forma",
    "cruzar_g1a",
    "discurso",
    "extension_de_capitulo",
    "nombres_literales",
]
