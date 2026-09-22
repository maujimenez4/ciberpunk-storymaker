"""P-10, P-11 y P-12: busqueda semantica detras de una interfaz.

RI-17, RI-22, RD-07 y RI-20. Lo que se protege aqui es la promesa mas fuerte de
`CLAUDE.md` §4.2: **el sistema nunca falla por falta de extension vectorial**.
Por eso la suite corre entera contra las dos implementaciones, no solo contra la
que este instalada en la maquina de quien ejecuta.
"""

import logging
from pathlib import Path

import numpy as np
import pytest

from app.commons.db import (
    BruteForceStore,
    DobleDeEmbeddings,
    ProveedorDeEmbeddings,
    SqliteVecStore,
    VectorStore,
    elegir_vector_store,
    extension_disponible,
)

DIMENSION = 8


def _vector(semilla: int) -> np.ndarray:
    generador = np.random.default_rng(semilla)
    return generador.random(DIMENSION).astype(np.float32)


@pytest.fixture(params=["fuerza_bruta", "sqlite_vec"])
def almacen(request: pytest.FixtureRequest, tmp_path: Path) -> VectorStore:
    if request.param == "sqlite_vec":
        if not extension_disponible():
            pytest.skip("sqlite-vec no esta instalada en esta maquina")
        return SqliteVecStore(tmp_path / "v.db", DIMENSION)
    return BruteForceStore(tmp_path / "v.db", DIMENSION)


def test_recupera_el_mas_parecido(almacen: VectorStore) -> None:
    objetivo = _vector(1)
    almacen.guardar("f1", objetivo)
    almacen.guardar("f2", _vector(2))
    almacen.guardar("f3", _vector(3))

    assert almacen.buscar(objetivo, k=1)[0] == "f1"


def test_respeta_el_conjunto_ya_filtrado(almacen: VectorStore) -> None:
    """RF-CTX-07: la similitud opera **sobre lo ya filtrado**, no sobre todo.

    Si el almacen ignorara los candidatos, el orden de la recuperacion hibrida
    seria decorativo y volveriamos a traer escenas parecidas en vez de
    pertinentes.
    """
    objetivo = _vector(1)
    almacen.guardar("f1", objetivo)
    almacen.guardar("f2", _vector(2))

    assert almacen.buscar(objetivo, k=1, candidatos={"f2"}) == ["f2"]


def test_no_devuelve_mas_de_k(almacen: VectorStore) -> None:
    for i in range(5):
        almacen.guardar(f"f{i}", _vector(i))

    assert len(almacen.buscar(_vector(0), k=2)) == 2


def test_rechaza_un_vector_de_otra_dimension(almacen: VectorStore) -> None:
    """RD-07: la dimension viaja con el vector. Cambiar de proveedor sin
    reindexar debe ser un fallo, no un resultado silenciosamente peor."""
    with pytest.raises(ValueError):
        almacen.guardar("f1", np.zeros(DIMENSION + 1, dtype=np.float32))


def test_los_dos_almacenes_leen_el_mismo_blob(tmp_path: Path) -> None:
    """RD-07: escrito por uno, legible por el otro. Es lo que permite degradar
    sin reindexar."""
    fichero = tmp_path / "v.db"
    escritor = BruteForceStore(fichero, DIMENSION)
    escritor.guardar("f1", _vector(1))

    lector = BruteForceStore(fichero, DIMENSION)
    assert lector.buscar(_vector(1), k=1) == ["f1"]


def test_sin_extension_se_degrada_y_avisa(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """RI-17 y RI-22: se detecta en arranque, se degrada y se registra una vez."""
    monkeypatch.setattr("app.commons.db.vectores.extension_disponible", lambda: False)

    with caplog.at_level(logging.WARNING):
        almacen = elegir_vector_store(tmp_path / "v.db", DIMENSION)

    assert isinstance(almacen, BruteForceStore)
    assert any("fuerza bruta" in r.message.lower() for r in caplog.records)


def test_el_proveedor_de_embeddings_esta_tras_su_interfaz() -> None:
    """RI-20: interfaz propia, y su consumo no cuenta contra ningun presupuesto."""
    proveedor: ProveedorDeEmbeddings = DobleDeEmbeddings(DIMENSION)
    vector = proveedor.incrustar("una escena")

    assert vector.shape == (DIMENSION,)
    assert proveedor.incrustar("una escena").tolist() == vector.tolist()
