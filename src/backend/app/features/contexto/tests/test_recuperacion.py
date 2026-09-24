"""Recuperacion hibrida: filtrar, **luego** ordenar, y fusionar con recencia.

El test que de verdad distingue es `test_devuelve_lo_pertinente_aunque_lo_mas_
parecido_sea_otra_escena` (R-5). Esta escrito para **caer** si alguien ordena
por parecido sin filtrar antes, y el de al lado —
`test_ordenar_sin_filtrar_traeria_lo_parecido`— guarda que siga siendo asi:
si el corpus dejara de discriminar, el primero pasaria sin filtro y nadie lo
notaria. Es el modo de fallo de `CA-8`, no una hipotesis.
"""

from collections.abc import Sequence

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.db.vectores import empaquetar_vector
from app.features.contexto.almacenes import AlmacenFuerzaBruta, Vecino
from app.features.contexto.recuperacion import (
    FiltroEstructural,
    filtrar_estructuralmente,
    recuperar,
)
from app.features.contexto.tests.conftest import CONSULTA, Corpus


def _filtro(corpus: Corpus, **campos: object) -> FiltroEstructural:
    """El filtro de la escena en curso: invernadero, Nadia y Teo, capitulos 2 a 5."""
    valores: dict[str, object] = {
        "obra_id": corpus.obra_id,
        "presentes": ("Nadia", "Teo"),
        "lugar": "El invernadero",
        "hilos_abiertos": (corpus.hilo_abierto_id,),
        "desde_capitulo": 2,
        "hasta_capitulo": 5,
    }
    valores.update(campos)
    return FiltroEstructural(**valores)  # type: ignore[arg-type]


class AlmacenEspia:
    """Un almacen que apunta que candidatos le llegaron. No inventa distancias."""

    modo = "espia"

    def __init__(self) -> None:
        self.candidatos_recibidos: list[Sequence[int]] = []

    async def vecinos(
        self, consulta: Sequence[float], candidatos: Sequence[int], limite: int
    ) -> list[Vecino]:
        self.candidatos_recibidos.append(list(candidatos))
        return []


# ---------------------------------------------------------------------------
# 1. El filtro estructural existe y FILTRA (CA-8)
# ---------------------------------------------------------------------------


async def test_el_filtro_estructural_descarta_lo_que_no_comparte_nada(
    sesion: AsyncSession, corpus: Corpus
):
    candidatos = await filtrar_estructuralmente(sesion, _filtro(corpus))

    assert {c.escena_id for c in candidatos} == {
        corpus.pertinente.id,
        corpus.pertinente_por_presentes.id,
        corpus.pertinente_por_hilo.id,
    }


async def test_el_rango_de_capitulos_acota_por_arriba_y_por_abajo(
    sesion: AsyncSession, corpus: Corpus
):
    candidatos = await filtrar_estructuralmente(sesion, _filtro(corpus))

    assert corpus.fuera_de_rango.id not in {c.escena_id for c in candidatos}


async def test_una_escena_entra_solo_por_el_hilo_abierto(sesion: AsyncSession, corpus: Corpus):
    """`pertinente_por_hilo` no comparte ni lugar ni presentes: o entra por el hilo o no entra."""
    con_hilo = await filtrar_estructuralmente(sesion, _filtro(corpus))
    sin_hilo = await filtrar_estructuralmente(sesion, _filtro(corpus, hilos_abiertos=()))

    assert corpus.pertinente_por_hilo.id in {c.escena_id for c in con_hilo}
    assert corpus.pertinente_por_hilo.id not in {c.escena_id for c in sin_hilo}


async def test_un_hilo_pagado_no_vuelve_a_traer_su_escena(sesion: AsyncSession, corpus: Corpus):
    """Si los hilos cerrados siguieran trayendo escenas, el filtro creceria con la obra."""
    candidatos = await filtrar_estructuralmente(
        sesion, _filtro(corpus, hilos_abiertos=(corpus.hilo_abierto_id, corpus.hilo_pagado_id))
    )

    assert corpus.parecida_e_impertinente.id not in {c.escena_id for c in candidatos}


# ---------------------------------------------------------------------------
# 2. R-5: lo parecido y lo pertinente difieren, y gana lo pertinente
# ---------------------------------------------------------------------------


async def test_devuelve_lo_pertinente_aunque_lo_mas_parecido_sea_otra_escena(
    sesion: AsyncSession, corpus: Corpus
):
    """R-5. `parecida_e_impertinente` tiene el vector **identico** a la consulta
    y ademas es **mas reciente** que `pertinente`: ni el parecido ni la recencia
    la dejan fuera. Solo el filtro estructural.
    """
    recuperados = await recuperar(
        sesion,
        filtro=_filtro(corpus),
        consulta=CONSULTA,
        almacen=AlmacenFuerzaBruta(sesion),
        orden_actual=6,
        limite=10,
    )
    escenas = [r.escena_id for r in recuperados]

    assert corpus.parecida_e_impertinente.id not in escenas
    assert corpus.pertinente.id in escenas


async def test_ordenar_sin_filtrar_traeria_lo_parecido(sesion: AsyncSession, corpus: Corpus):
    """La otra mitad de R-5: el corpus **discrimina**, y esto lo guarda.

    Sin este test, un corpus en el que lo parecido fuera ya lo pertinente
    dejaria pasar el test de arriba sin filtro ninguno, y `CA-8` volveria a
    estar «probado» sin estar implementado.
    """
    todas = [
        corpus.fuera_de_rango.id,
        corpus.pertinente.id,
        corpus.parecida_e_impertinente.id,
        corpus.pertinente_por_presentes.id,
        corpus.pertinente_por_hilo.id,
    ]

    vecinos = await AlmacenFuerzaBruta(sesion).vecinos(CONSULTA, todas, limite=1)

    assert vecinos[0].escena_id in {corpus.parecida_e_impertinente.id, corpus.fuera_de_rango.id}


# ---------------------------------------------------------------------------
# 3. El orden de los tres pasos
# ---------------------------------------------------------------------------


async def test_al_almacen_solo_le_llega_lo_ya_filtrado(sesion: AsyncSession, corpus: Corpus):
    """«Orden semantico **sobre el conjunto ya filtrado**», comprobado y no confiado."""
    espia = AlmacenEspia()

    await recuperar(
        sesion,
        filtro=_filtro(corpus),
        consulta=CONSULTA,
        almacen=espia,
        orden_actual=6,
        limite=10,
    )

    assert len(espia.candidatos_recibidos) == 1
    assert set(espia.candidatos_recibidos[0]) == {
        corpus.pertinente.id,
        corpus.pertinente_por_presentes.id,
        corpus.pertinente_por_hilo.id,
    }


async def test_sin_candidatos_no_se_llama_al_almacen(sesion: AsyncSession, corpus: Corpus):
    """Un filtro que no deja nada es una capa vacia, no una consulta a ciegas."""
    espia = AlmacenEspia()

    recuperados = await recuperar(
        sesion,
        filtro=_filtro(corpus, desde_capitulo=9, hasta_capitulo=10),
        consulta=CONSULTA,
        almacen=espia,
        orden_actual=6,
        limite=10,
    )

    assert recuperados == []
    assert espia.candidatos_recibidos == []


# ---------------------------------------------------------------------------
# 4. La fusion con recencia
# ---------------------------------------------------------------------------


async def test_sin_peso_de_recencia_el_orden_es_el_semantico(sesion: AsyncSession, corpus: Corpus):
    recuperados = await recuperar(
        sesion,
        filtro=_filtro(corpus),
        consulta=CONSULTA,
        almacen=AlmacenFuerzaBruta(sesion),
        orden_actual=6,
        limite=10,
        peso_recencia=0.0,
    )

    assert [r.escena_id for r in recuperados] == [
        corpus.pertinente_por_presentes.id,
        corpus.pertinente_por_hilo.id,
        corpus.pertinente.id,
    ]


async def test_con_todo_el_peso_en_la_recencia_manda_lo_reciente(
    sesion: AsyncSession, corpus: Corpus
):
    """La fusion **hace algo**: con los dos extremos el orden no es el mismo."""
    recuperados = await recuperar(
        sesion,
        filtro=_filtro(corpus),
        consulta=CONSULTA,
        almacen=AlmacenFuerzaBruta(sesion),
        orden_actual=6,
        limite=10,
        peso_recencia=1.0,
    )

    assert [r.escena_id for r in recuperados] == [
        corpus.pertinente_por_hilo.id,
        corpus.pertinente_por_presentes.id,
        corpus.pertinente.id,
    ]


async def test_el_peso_de_recencia_esta_acotado(sesion: AsyncSession, corpus: Corpus):
    with pytest.raises(ValueError):
        await recuperar(
            sesion,
            filtro=_filtro(corpus),
            consulta=CONSULTA,
            almacen=AlmacenFuerzaBruta(sesion),
            orden_actual=6,
            peso_recencia=1.5,
        )


async def test_el_limite_recorta_por_puntuacion_y_no_por_distancia(
    sesion: AsyncSession, corpus: Corpus
):
    recuperados = await recuperar(
        sesion,
        filtro=_filtro(corpus),
        consulta=CONSULTA,
        almacen=AlmacenFuerzaBruta(sesion),
        orden_actual=6,
        limite=1,
        peso_recencia=1.0,
    )

    assert [r.escena_id for r in recuperados] == [corpus.pertinente_por_hilo.id]


async def test_lo_recuperado_trae_el_fragmento_y_su_escena(sesion: AsyncSession, corpus: Corpus):
    """`ejecucion` guarda los IDs recuperados (RF-CTX-09): sin ellos no hay auditoria."""
    recuperados = await recuperar(
        sesion,
        filtro=_filtro(corpus),
        consulta=CONSULTA,
        almacen=AlmacenFuerzaBruta(sesion),
        orden_actual=6,
        limite=10,
    )

    primero = recuperados[0]
    assert primero.embedding_id > 0
    assert f"escena {primero.escena_id}" in primero.fragmento
    assert 0.0 <= primero.puntuacion <= 1.0


async def test_la_consulta_debe_tener_la_dimension_del_indice(sesion: AsyncSession, corpus: Corpus):
    """Un vector de otra dimension no es «menos parecido»: es incomparable."""
    with pytest.raises(ValueError):
        await AlmacenFuerzaBruta(sesion).vecinos([1.0, 0.0], [corpus.pertinente.id], limite=10)


def test_el_vector_de_consulta_no_se_reempaqueta_a_otra_precision():
    """Guarda de la frontera con `vec_distance_cosine`: los dos lados, float32."""
    assert len(empaquetar_vector(CONSULTA)) == 12
