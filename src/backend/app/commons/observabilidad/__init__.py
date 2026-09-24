"""Observabilidad: el sitio por donde salen todos los numeros de la Fase 6.

`commons/` **no importa de ninguna feature** y este paquete tampoco: lo que
recibe son cadenas, numeros y `Puntuacion`. `lint-imports` ya lo prohibe.

`obtener_observador()` es la dependencia de FastAPI (RI-14), y es tambien donde
se decide la degradacion: sin las tres credenciales devuelve `ObservadorNulo` y
el sistema arranca, avisa y genera. **Nunca lanza.**
"""

import logging

from app.commons.config.ajustes import Ajustes
from app.commons.observabilidad.blindaje import ObservadorBlindado, blindar
from app.commons.observabilidad.dobles import (
    ObservadorEnMemoria,
    ObservadorNulo,
    SpanEnMemoria,
    TrazaEnMemoria,
)
from app.commons.observabilidad.langfuse import ObservadorLangfuse
from app.commons.observabilidad.trazas import (
    Observador,
    Puntuacion,
    Span,
    Traza,
    sesion_de,
)

_log = logging.getLogger(__name__)

SIN_CREDENCIALES = (
    "Observabilidad desactivada: faltan LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY "
    "o LANGFUSE_HOST. El sistema genera igual y no se mide nada."
)
"""El aviso sale **al arrancar**, no a mitad de escribir un capitulo.

Es la leccion de `sqlite-vec`, escrita en el plan con estas palabras: «la
deteccion existia y era perezosa; el aviso salia a mitad de escribir un
capitulo». Ese error ya se pago una vez.
"""


def obtener_observador() -> Observador:
    """El observador de produccion, o el nulo. Nunca lanza.

    Las tres credenciales o ninguna: media configuracion es el caso que se cuela
    -- alguien pone la publica, olvida el host -- y un cliente construido a
    medias no falla al arrancar sino en la primera llamada, ya dentro de la
    generacion.

    Y sale **blindado**, no a pelo: R-1 no puede depender de que quien lo pida
    se acuerde de envolverlo.
    """
    ajustes = Ajustes.desde_entorno()
    publica = ajustes.langfuse_clave_publica
    secreta = ajustes.langfuse_clave_secreta
    host = ajustes.langfuse_host

    if not (publica and secreta and host):
        _log.warning(SIN_CREDENCIALES)
        return ObservadorNulo()

    return blindar(ObservadorLangfuse(clave_publica=publica, clave_secreta=secreta, host=host))


__all__ = [
    "SIN_CREDENCIALES",
    "Observador",
    "ObservadorBlindado",
    "ObservadorEnMemoria",
    "ObservadorLangfuse",
    "ObservadorNulo",
    "Puntuacion",
    "Span",
    "SpanEnMemoria",
    "Traza",
    "TrazaEnMemoria",
    "blindar",
    "obtener_observador",
    "sesion_de",
]
