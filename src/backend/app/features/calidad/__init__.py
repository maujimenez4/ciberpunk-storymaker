"""API publica de la feature `calidad`.

Lo unico importable desde fuera (§5.2 regla 1).
"""

from app.features.calidad.defectos import (
    BLOQUEANTES_EN_G1A,
    CodigoDeDefecto,
    Defecto,
    citar,
)
from app.features.calidad.puerta import (
    VeredictoDeG1a,
    comprobar_forma,
    pasar_g1a,
)
from app.features.calidad.validadores import (
    INDISPONIBLES,
    Afirmacion,
    HechoDeCanon,
    solo_narracion,
    validar_canon,
    validar_conocimiento,
    validar_continuidad_fisica,
    validar_discurso,
    validar_giro_de_valor,
    validar_nivel_de_calor,
    validar_objetos,
)

__all__ = [
    "BLOQUEANTES_EN_G1A",
    "INDISPONIBLES",
    "Afirmacion",
    "VeredictoDeG1a",
    "CodigoDeDefecto",
    "Defecto",
    "HechoDeCanon",
    "citar",
    "comprobar_forma",
    "pasar_g1a",
    "solo_narracion",
    "validar_canon",
    "validar_conocimiento",
    "validar_continuidad_fisica",
    "validar_discurso",
    "validar_giro_de_valor",
    "validar_nivel_de_calor",
    "validar_objetos",
]
