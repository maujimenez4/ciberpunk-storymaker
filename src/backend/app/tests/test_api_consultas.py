"""P-118, P-119 y P-120: los tres endpoints de consulta (RI-06, RI-07, RI-08).

Los tres son de lectura y comparten una propiedad que conviene no perder: **lo
que devuelven es lo que el ciclo uso**, no una reconstruccion aparte. El de
contexto monta el paquete con los mismos almacenes, el de versiones lee el
historial inmutable y el de canon devuelve lo vigente.

Se prueban **despues de correr una escena de verdad**, no contra filas puestas a
mano: un endpoint de consulta que solo se prueba con datos inventados acaba
devolviendo una forma que el resto del sistema nunca produce.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.features.escritura.tests.test_ciclo_completo import (
    dependencias,
    obra_lista,
)
from app.main import crear_app

__all__ = ["obra_lista"]


@pytest.fixture
def cliente_con_una_escena_escrita(obra_lista: Path) -> TestClient:
    app = crear_app(obra_lista, fabrica_dependencias=lambda: dependencias(obra_lista))
    cliente = TestClient(app)
    trabajo = cliente.post("/escenas/es1/escribir", params={"obra_id": "o1"}).json()
    app.state.ejecutor.drenar()
    assert cliente.get(f"/trabajos/{trabajo['trabajo_id']}").json()["estado"] == (
        "INTEGRADA"
    )
    return cliente


def test_las_versiones_salen_con_la_vigente_marcada(
    cliente_con_una_escena_escrita: TestClient,
) -> None:
    """RI-07."""
    cuerpo = cliente_con_una_escena_escrita.get("/escenas/es1/versiones").json()

    assert cuerpo["escena_id"] == "es1"
    assert len(cuerpo["versiones"]) == 1
    version = cuerpo["versiones"][0]
    assert version["vigente"] is True
    assert version["autoria"] == "generado"
    assert version["palabras"] > 0
    # RI-12: el historial no expone la prosa; para eso esta el manuscrito.
    assert "texto" not in version


def test_el_canon_se_consulta_con_su_escena_de_origen(
    cliente_con_una_escena_escrita: TestClient,
) -> None:
    """RI-08 y RF-CAN-04: todo hecho cita la escena que lo establecio."""
    cuerpo = cliente_con_una_escena_escrita.get("/obras/o1/canon").json()

    assert cuerpo["hechos"], "el canon quedo vacio tras integrar una escena"
    for hecho in cuerpo["hechos"]:
        assert hecho["escena_de_origen"] == "es1"


def test_el_canon_se_puede_filtrar_por_entidad(
    cliente_con_una_escena_escrita: TestClient,
) -> None:
    sin_filtro = cliente_con_una_escena_escrita.get("/obras/o1/canon").json()["hechos"]
    filtrado = cliente_con_una_escena_escrita.get(
        "/obras/o1/canon", params={"entidad": "no-existe"}
    ).json()["hechos"]

    assert sin_filtro and not filtrado


def test_el_contexto_expone_el_desglose_por_capa(
    cliente_con_una_escena_escrita: TestClient,
) -> None:
    """RI-06 y RF-CTX-06: el desglose acompana al paquete.

    Es lo que hace auditable una escena sin reproducir la corrida: se ve que
    capa se llevo el presupuesto y que se descarto al recortar.
    """
    cuerpo = cliente_con_una_escena_escrita.get("/escenas/es1/contexto").json()

    assert cuerpo["escena_id"] == "es1"
    assert cuerpo["texto"]
    assert cuerpo["total"] > 0
    assert sum(cuerpo["tokens_por_capa"].values()) == cuerpo["total"], (
        "el desglose tiene que sumar el total (RF-CTX-06)"
    )
    # Las siete con contenido aportan algo; la reserva queda libre (RF-CTX-11).
    assert cuerpo["tokens_por_capa"]["reserva"] == 0
    assert cuerpo["tokens_por_capa"]["constitucional"] > 0


def test_una_escena_que_no_existe_da_404_por_el_handler(
    cliente_con_una_escena_escrita: TestClient,
) -> None:
    """RI-11: ningun servicio lanza `HTTPException`; traduce el handler."""
    assert (
        cliente_con_una_escena_escrita.get("/escenas/no-existe/contexto").status_code
        == 404
    )
