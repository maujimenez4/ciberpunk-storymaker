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
    PROMPT_ID,
    PROMPT_ID_CRITICO,
    PROMPT_VERSION,
    PROMPT_VERSION_CRITICO,
    CapituloAContrastar,
    CapituloAJuzgar,
    ConocimientoEnT,
    Continuista,
    ContrasteDeConocimiento,
    Critico,
    HechoDeCanon,
    Juicio,
    OrigenDeHecho,
    PlantillaAusente,
    PuntuacionDelCritico,
    RevisionDeContinuidad,
    RubricaDiscordante,
    SalidaMalFormada,
    # Plan 8 T7 (P-22.3): quien abre el span del Continuista y del Critico es
    # `escritura`, y el span lleva la plantilla que se envio. Salen funciones y
    # no hashes ya calculados porque las plantillas se leen al usarlas, nunca al
    # importar (ver `_leer`).
    hash_de_critico_v1,
    hash_de_plantilla,
    # Plan 8 T6: `escritura` cuenta el prompt del Critico para pedirle turno al
    # portero cuando lo lanza en paralelo. Contar otra cosa que lo que se envia
    # seria reservar de menos.
    plantilla_critico_v1,
    plantilla_v2,
    render_critico,
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
from app.features.calidad.rubrica import (
    # `RUBRICA_V1` **no sale a proposito**. `CA-20` pide que la rubrica del juez
    # y la que se le presenta al Autor sean *la misma*, y `rubrica_vigente()`
    # devuelve la misma instancia mientras la constante invita a construir una
    # copia igual pero distinta: dos objetos equivalentes miden dos reglas, y la
    # distancia de `RF-JUZ-05` dejaria de comparar lo que dice comparar.
    Criterio,
    Rubrica,
    hash_de_rubrica,
    rubrica_vigente,
)
from app.features.calidad.schemas import (
    Defecto,
    NombreDeCanon,
    ParametrosDeDiscurso,
    Persona,
    RangoDeExtension,
    TiempoVerbal,
)
from app.features.calidad.scores import (
    # Salen por aqui porque quien tiene el span es el orquestador, y vive en
    # `escritura` y en `manuscrito`: traducir un resultado a *scores* es de
    # `calidad`, emitirlos es de quien corre la puerta.
    NOMBRE_DEL_JUEZ,
    emitir,
    puntuaciones_de_g1a,
    puntuaciones_de_g4,
    puntuaciones_de_policy,
    puntuaciones_del_juez,
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
    "NOMBRE_DEL_JUEZ",
    "PROMPT_ID",
    "PROMPT_ID_CRITICO",
    "PROMPT_VERSION",
    "PROMPT_VERSION_CRITICO",
    "CapituloAContrastar",
    "CapituloAJuzgar",
    "CapituloAPolicy",
    "CapituloAValidar",
    "CierreDelManuscrito",
    "Cobertura",
    "ConocimientoEnT",
    "Continuista",
    "ContrasteDeConocimiento",
    "Criterio",
    "Critico",
    "DecisionDePolicy",
    "Defecto",
    "DefectoMalFormado",
    "DefectosClasificados",
    "ElementoAusente",
    "ElementoCubierto",
    "HechoDeCanon",
    "HechoUsado",
    "Juicio",
    "ManuscritoAValidar",
    "MotivoMalFormado",
    "NombreDeCanon",
    "OrigenDeHecho",
    "ParametrosDeDiscurso",
    "Persona",
    "PlantillaAusente",
    "PuntoDeEjecucion",
    "PuntuacionDelCritico",
    "RangoDeExtension",
    "ReglaDePolicy",
    "ResultadoDePolicy",
    "ResultadoDePuerta",
    "RevisionDeContinuidad",
    "Rubrica",
    "RubricaDiscordante",
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
    "emitir",
    "extension_de_capitulo",
    "hash_de_critico_v1",
    "hash_de_plantilla",
    "hash_de_rubrica",
    "localizar_veto",
    "nombres_literales",
    "plantilla_critico_v1",
    "plantilla_v2",
    "puntuaciones_de_g1a",
    "puntuaciones_de_g4",
    "puntuaciones_de_policy",
    "puntuaciones_del_juez",
    "render_critico",
    "rubrica_vigente",
]
