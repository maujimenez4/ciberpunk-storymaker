"""El observador es uno por proceso (`obtener_observador` cacheado, P-22.2).

Estos tests cambian el entorno y vuelven a pedirlo: sin vaciar la cache, el
segundo recibiria el observador que construyo el primero -- o el que dejo el
arranque de una app en otro modulo de la suite -- y probaria el entorno de otro.
"""

from collections.abc import Iterator

import pytest

from app.commons.observabilidad import obtener_observador


@pytest.fixture(autouse=True)
def _observador_recien_construido() -> Iterator[None]:
    obtener_observador.cache_clear()
    yield
    obtener_observador.cache_clear()
