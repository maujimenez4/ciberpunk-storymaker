"""La UNICA puerta de entrada a la feature `calidad` (`CLAUDE.md` §5.1).

Detras de ella viven la puerta mecanica G1a y, desde la Fase 3, el
**Continuista**: el rol que contrasta un capitulo contra el grafo de canon. Lo
que se exporta de el es lo que un orquestador necesita —el agente, su entrada,
su salida y su fallo— y nada mas: el esquema con el que se valida lo que el
modelo devuelve es interno, porque nadie fuera lo construye.

Y desde T9 sale tambien el **cierre del manuscrito**: `ManuscritoAValidar`,
`ValidadorDeManuscrito`, `CATALOGO_DE_MANUSCRITO`, `CierreDelManuscrito` y
`cerrar_manuscrito`. Es la puerta G4 de `verification.md` §8.1 en lo unico que
la Fase 3 puede ejecutar de ella —la cobertura de la personalizacion—, y sale
por aqui porque quien la corre, el orquestador de la novela, vive en
`escritura`. `cobertura_de_obligatorios` sigue exportada: es la funcion, y se
prueba sin catalogo.
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
from app.features.calidad.policy import (
    CATALOGO_DE_POLICY,
    CODIGO_DE_PALABRA_PROHIBIDA,
    CapituloAPolicy,
    DecisionDePolicy,
    ReglaDePolicy,
    ResultadoDePolicy,
    aplicar_policy,
    localizar_veto,
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
    CATALOGO_DE_MANUSCRITO,
    CapituloAValidar,
    CierreDelManuscrito,
    ManuscritoAValidar,
    PuntoDeEjecucion,
    Validador,
    ValidadorDeManuscrito,
    cerrar_manuscrito,
    discurso,
    extension_de_capitulo,
    nombres_literales,
)

__all__ = [
    "CATALOGO",
    "CATALOGO_DE_MANUSCRITO",
    "CATALOGO_DE_POLICY",
    "CODIGOS_DE_LA_TAXONOMIA",
    "CODIGO_DE_ELEMENTO_AUSENTE",
    "CODIGO_DE_PALABRA_PROHIBIDA",
    "CapituloAContrastar",
    "CapituloAPolicy",
    "CapituloAValidar",
    "CierreDelManuscrito",
    "Cobertura",
    "Continuista",
    "DecisionDePolicy",
    "Defecto",
    "DefectoMalFormado",
    "DefectosClasificados",
    "ElementoAusente",
    "ElementoCubierto",
    "HechoDeCanon",
    "HechoUsado",
    "ManuscritoAValidar",
    "MotivoMalFormado",
    "NombreDeCanon",
    "OrigenDeHecho",
    "ParametrosDeDiscurso",
    "Persona",
    "PuntoDeEjecucion",
    "RangoDeExtension",
    "ReglaDePolicy",
    "ResultadoDePolicy",
    "ResultadoDePuerta",
    "RevisionDeContinuidad",
    "SalidaMalFormada",
    "TiempoVerbal",
    "Validador",
    "ValidadorDeManuscrito",
    "aplicar_policy",
    "cerrar_manuscrito",
    "clasificar",
    "cobertura_de_obligatorios",
    "comprobar_forma",
    "cruzar_g1a",
    "discurso",
    "extension_de_capitulo",
    "localizar_veto",
    "nombres_literales",
]
