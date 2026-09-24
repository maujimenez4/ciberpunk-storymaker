"""Lo de mas abajo del indice vectorial: el float32, la distancia y la deteccion.

Aqui no hay ni `Embedding` ni recuperacion: esto es infraestructura de base de
datos (`commons/db/`), y se prueba sin saber que hay una obra detras.
"""

import math
import warnings

import pytest

from app.commons.db.vectores import (
    AvisoDeDegradacion,
    desempaquetar_vector,
    distancia_coseno,
    empaquetar_vector,
    extension_disponible,
)


@pytest.fixture(autouse=True)
def _deteccion_sin_memoria():
    """La deteccion se cachea por proceso, y eso cruzaria tests entre si.

    Sin esto, el primer test que mire un modo deja decidido el de todos los
    demas, y peor: un test que falle a mitad se lleva por delante a los
    siguientes. Se limpia antes y despues, no solo despues.
    """
    extension_disponible.cache_clear()
    yield
    extension_disponible.cache_clear()


def test_empaquetar_y_desempaquetar_devuelven_el_mismo_vector():
    vector = [1.0, 0.0, -0.5, 0.25]
    blob = empaquetar_vector(vector)

    assert len(blob) == 4 * len(vector)
    assert desempaquetar_vector(blob) == pytest.approx(vector)


def test_el_blob_es_float32_y_no_float64():
    """`vec_distance_cosine` lee float32: si esto cambia, la extension no lee lo mismo."""
    assert len(empaquetar_vector([1.0])) == 4


def test_distancia_coseno_de_un_vector_consigo_mismo_es_cero():
    assert distancia_coseno([0.3, 0.7, 0.1], [0.3, 0.7, 0.1]) == pytest.approx(0.0, abs=1e-6)


def test_distancia_coseno_entre_ortogonales_es_uno():
    assert distancia_coseno([1.0, 0.0], [0.0, 1.0]) == pytest.approx(1.0, abs=1e-6)


def test_distancia_coseno_no_depende_de_la_norma():
    """Coseno: escalar un vector no cambia su direccion, luego no cambia la distancia."""
    a = distancia_coseno([1.0, 2.0], [3.0, 1.0])
    b = distancia_coseno([10.0, 20.0], [3.0, 1.0])

    assert a == pytest.approx(b, abs=1e-6)


def test_distancia_coseno_con_el_vector_nulo_no_revienta():
    """Un vector sin direccion no se parece a nada. NaN aqui envenenaria el orden."""
    distancia = distancia_coseno([0.0, 0.0], [1.0, 1.0])

    assert not math.isnan(distancia)
    assert distancia == pytest.approx(1.0)


def test_distancia_coseno_exige_la_misma_dimension():
    with pytest.raises(ValueError):
        distancia_coseno([1.0, 0.0], [1.0, 0.0, 0.0])


def test_sin_extension_el_sistema_no_revienta_y_avisa(monkeypatch):
    """R-6, primera mitad: degradar en silencio es peor que fallar.

    Se fuerza la ausencia con la variable de entorno, que es el mismo
    interruptor con el que la suite corre en los dos modos (RNF-FIA-02, CA-28).
    """
    monkeypatch.setenv("STORYMAKER_SIN_SQLITE_VEC", "1")
    with pytest.warns(AvisoDeDegradacion):
        disponible = extension_disponible()

    assert disponible is False


def test_el_aviso_se_da_una_vez_por_proceso_y_no_por_llamada(monkeypatch):
    """Un aviso por consulta seria ruido, y el ruido se acaba silenciando entero."""
    monkeypatch.setenv("STORYMAKER_SIN_SQLITE_VEC", "1")
    with pytest.warns(AvisoDeDegradacion):
        extension_disponible()

    with warnings.catch_warnings():
        warnings.simplefilter("error", AvisoDeDegradacion)
        assert extension_disponible() is False


def test_con_la_extension_instalada_se_detecta_y_no_avisa(monkeypatch):
    """La otra mitad: cuando carga, carga y nadie se entera."""
    monkeypatch.delenv("STORYMAKER_SIN_SQLITE_VEC", raising=False)
    pytest.importorskip("sqlite_vec")

    with warnings.catch_warnings():
        warnings.simplefilter("error", AvisoDeDegradacion)
        assert extension_disponible() is True
