"""Los dos modos de `VectorStore`, y lo unico que los dos tienen prohibido.

RNF-FIA-02 y CA-28 piden que la suite corra **con y sin** la extension. El
interruptor es `STORYMAKER_SIN_SQLITE_VEC`, y estos tests fuerzan ademas las
dos implementaciones a la vez para que ningun modo quede sin mirar en la
ejecucion que si tiene la extension.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.db.vectores import extension_disponible
from app.features.contexto import almacenes
from app.features.contexto.almacenes import (
    AlmacenFuerzaBruta,
    AlmacenSqliteVec,
    VectorStore,
    crear_almacen,
)
from app.features.contexto.tests.conftest import CONSULTA, Corpus


async def _almacenes(sesion: AsyncSession) -> list[VectorStore]:
    """Los dos si la extension esta; solo el de fuerza bruta si no."""
    almacenes: list[VectorStore] = [AlmacenFuerzaBruta(sesion)]
    if extension_disponible():
        almacenes.append(AlmacenSqliteVec(sesion))
    return almacenes


async def test_el_almacen_no_devuelve_nada_fuera_de_los_candidatos(
    sesion: AsyncSession, corpus: Corpus
):
    """La juntura de `CA-8`: si el almacen se saltara la lista, filtrar antes no serviria.

    El orden semantico va **sobre el conjunto ya filtrado**, y quien lo hace
    cumplir es el almacen: recibe los candidatos y no puede ampliarlos.
    """
    candidatos = [corpus.pertinente.id, corpus.pertinente_por_hilo.id]

    for almacen in await _almacenes(sesion):
        vecinos = await almacen.vecinos(CONSULTA, candidatos, limite=10)
        devueltas = {vecino.escena_id for vecino in vecinos}

        assert devueltas <= set(candidatos), almacen.modo
        assert corpus.parecida_e_impertinente.id not in devueltas, almacen.modo


async def test_el_almacen_ordena_de_menos_a_mas_distancia(sesion: AsyncSession, corpus: Corpus):
    candidatos = [
        corpus.pertinente.id,
        corpus.pertinente_por_presentes.id,
        corpus.pertinente_por_hilo.id,
    ]

    for almacen in await _almacenes(sesion):
        vecinos = await almacen.vecinos(CONSULTA, candidatos, limite=10)

        assert [v.escena_id for v in vecinos] == [
            corpus.pertinente_por_presentes.id,
            corpus.pertinente_por_hilo.id,
            corpus.pertinente.id,
        ], almacen.modo


async def test_los_dos_modos_dan_el_mismo_resultado(sesion: AsyncSession, corpus: Corpus):
    """R-6: que la extension este o no cambia el como, no el que."""
    if not extension_disponible():
        pytest.skip("sin sqlite-vec: este test compara los dos modos")

    candidatos = [
        corpus.pertinente.id,
        corpus.parecida_e_impertinente.id,
        corpus.pertinente_por_presentes.id,
        corpus.pertinente_por_hilo.id,
    ]

    bruta = await AlmacenFuerzaBruta(sesion).vecinos(CONSULTA, candidatos, limite=10)
    vec = await AlmacenSqliteVec(sesion).vecinos(CONSULTA, candidatos, limite=10)

    assert [v.escena_id for v in bruta] == [v.escena_id for v in vec]
    for uno, otro in zip(bruta, vec, strict=True):
        assert uno.distancia == pytest.approx(otro.distancia, abs=1e-5)


async def test_el_limite_recorta_por_el_final_que_es_lo_menos_parecido(
    sesion: AsyncSession, corpus: Corpus
):
    candidatos = [
        corpus.pertinente.id,
        corpus.pertinente_por_presentes.id,
        corpus.pertinente_por_hilo.id,
    ]

    for almacen in await _almacenes(sesion):
        vecinos = await almacen.vecinos(CONSULTA, candidatos, limite=1)

        assert [v.escena_id for v in vecinos] == [corpus.pertinente_por_presentes.id], almacen.modo


async def test_sin_candidatos_no_se_pregunta_a_nadie(sesion: AsyncSession, corpus: Corpus):
    """Un filtro que no deja nada no es un filtro roto: es una capa vacia."""
    for almacen in await _almacenes(sesion):
        assert await almacen.vecinos(CONSULTA, [], limite=10) == [], almacen.modo


async def test_el_almacen_elegido_es_el_de_fuerza_bruta_sin_extension(
    sesion: AsyncSession, monkeypatch
):
    """R-6: el sistema arranca igual, con el otro almacen."""
    monkeypatch.setenv("STORYMAKER_SIN_SQLITE_VEC", "1")
    extension_disponible.cache_clear()

    with pytest.warns(Warning):
        almacen = await crear_almacen(sesion)

    assert isinstance(almacen, AlmacenFuerzaBruta)
    assert almacen.modo == "fuerza bruta"


async def test_el_almacen_elegido_es_sqlite_vec_cuando_la_extension_carga(
    sesion: AsyncSession, monkeypatch
):
    monkeypatch.delenv("STORYMAKER_SIN_SQLITE_VEC", raising=False)
    extension_disponible.cache_clear()
    pytest.importorskip("sqlite_vec")

    almacen = await crear_almacen(sesion)

    assert isinstance(almacen, AlmacenSqliteVec)
    assert almacen.modo == "sqlite-vec"


async def test_la_fuerza_bruta_compara_todos_los_candidatos_de_una_vez(
    sesion: AsyncSession, corpus: Corpus, monkeypatch
):
    """`architecture.md` §5.5: «BLOB + **NumPy**», y NumPy no es un adorno aqui.

    Lo que cambia respecto al bucle en Python no es el resultado -- el test de
    los dos modos lo sujeta -- sino que el conjunto **ya filtrado** se compara
    en **una** operacion. Se mira contandola: tres candidatos, una llamada.
    """
    llamadas: list[int] = []
    original = almacenes.distancias_coseno

    def contando(consulta, matriz):
        llamadas.append(len(matriz))
        return original(consulta, matriz)

    monkeypatch.setattr(almacenes, "distancias_coseno", contando)

    candidatos = [
        corpus.pertinente.id,
        corpus.pertinente_por_presentes.id,
        corpus.pertinente_por_hilo.id,
    ]
    vecinos = await AlmacenFuerzaBruta(sesion).vecinos(CONSULTA, candidatos, limite=10)

    assert len(vecinos) == 3
    assert llamadas == [3]
