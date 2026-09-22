"""Ordenación semántica sin índice vectorial (RI-17, RI-20, RI-22, D-02).

Sustituye a los tests de `VectorStore`. Lo que se comprueba ya no es que el
orden sea acertado —eso lo decide un modelo y no se puede afirmar en un test—
sino que el ordenador **no rompa nada**: que respete el tope, que no invente
identificadores y que la capa nunca llegue vacía por un fallo de formato.
"""

import json

import pytest

from app.commons.llm import (
    TOPE_DE_CANDIDATOS,
    DobleDeModelo,
    DobleDeOrdenador,
    OrdenadorPorModelo,
    OrdenadorSemantico,
)

CANDIDATOS = {
    "f1": "Ada cruzo el taller bajo la lluvia",
    "f2": "Noe conto las monedas del cajon",
    "f3": "la lluvia cortaba la red del taller",
}


def test_el_doble_es_determinista() -> None:
    """RI-13: la suite corre con esto, sin red y sin credenciales."""
    doble: OrdenadorSemantico = DobleDeOrdenador()

    primera = doble.ordenar("lluvia en el taller", CANDIDATOS, k=2)
    segunda = doble.ordenar("lluvia en el taller", CANDIDATOS, k=2)

    assert primera == segunda
    assert len(primera) == 2


def test_el_ordenador_respeta_el_orden_que_devuelve_el_modelo() -> None:
    cliente = DobleDeModelo([json.dumps(["f3", "f1"])])
    ordenador = OrdenadorPorModelo(cliente, "prompt del ordenador")

    assert ordenador.ordenar("lluvia", CANDIDATOS, k=2) == ["f3", "f1"]


def test_descarta_identificadores_que_no_estaban_entre_los_candidatos() -> None:
    """Un modelo puede devolver lo que no existe. Si se colara, el ensamblador
    pediria un fragmento inexistente y la capa llegaria vacia: el fallo que
    RF-CTX-14 existe para cazar."""
    cliente = DobleDeModelo([json.dumps(["f9", "f3"])])
    ordenador = OrdenadorPorModelo(cliente, "p")

    elegidos = ordenador.ordenar("lluvia", CANDIDATOS, k=2)

    assert "f9" not in elegidos
    assert elegidos[0] == "f3"


def test_una_respuesta_ilegible_no_deja_la_capa_vacia() -> None:
    """Se completa por recencia. Una capa vacia es un fallo del almacen y
    detendria el ensamblado (RF-CTX-14); un formato malo del modelo no debe
    disfrazarse de eso."""
    ordenador = OrdenadorPorModelo(DobleDeModelo(["lo siento, no puedo"]), "p")

    elegidos = ordenador.ordenar("lluvia", CANDIDATOS, k=2)

    assert len(elegidos) == 2
    assert all(i in CANDIDATOS for i in elegidos)


def test_nunca_devuelve_mas_de_k() -> None:
    cliente = DobleDeModelo([json.dumps(["f1", "f2", "f3"])])
    ordenador = OrdenadorPorModelo(cliente, "p")

    assert len(ordenador.ordenar("lluvia", CANDIDATOS, k=1)) == 1


def test_sin_candidatos_no_llama_al_modelo() -> None:
    """Llamar para ordenar una lista vacia es gastar cuota en nada, y en este
    sistema el gasto del bucle se vigila explicitamente."""
    cliente = DobleDeModelo([])
    ordenador = OrdenadorPorModelo(cliente, "p")

    assert ordenador.ordenar("lluvia", {}, k=3) == []
    assert cliente.llamadas == []


def test_el_tope_de_candidatos_esta_declarado() -> None:
    """RNF-REN-04: sin tope, el coste del ensamblado creceria con la obra, que es
    justo lo que el presupuesto por capas existe para evitar."""
    assert TOPE_DE_CANDIDATOS == 50


@pytest.mark.parametrize("ordenador", [DobleDeOrdenador()])
def test_ambos_cumplen_la_interfaz(ordenador: OrdenadorSemantico) -> None:
    assert ordenador.ordenar("x", CANDIDATOS, k=1)
