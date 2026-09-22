"""P-04: cada excepcion de dominio se traduce a su HTTP (RI-11).

Un test por caso, como pide el requisito. Lo que se comprueba no es solo el
codigo: es que la respuesta lleve **lo que hace accionable el fallo** —la capa
que desbordo, el axioma incumplido, si se puede relanzar sin coste—. Un 422
pelado obliga a ir al log, y para eso no hace falta handler.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.commons.errors import (
    ContextBudgetExceeded,
    ErrorDeDominio,
    FalloDeProveedor,
    RecursoNoEncontrado,
    ReglaDeDominioViolada,
    TiempoAgotado,
    registrar_manejadores,
)

CASOS = {
    "presupuesto": ContextBudgetExceeded(
        capa="canon_relevante", tokens=21_000, tope=20_000
    ),
    "turno": TiempoAgotado(paso="ESCRIBIENDO", relanzable_sin_coste=True),
    "dominio": ReglaDeDominioViolada(axioma=13, detalle="tiempo verbal distinto"),
    "ausente": RecursoNoEncontrado(recurso="Escena", identificador="esc-7"),
    "proveedor": FalloDeProveedor(intentos=3),
}


@pytest.fixture
def cliente() -> TestClient:
    app = FastAPI()
    registrar_manejadores(app)

    @app.get("/lanza/{caso}")
    def lanza(caso: str) -> None:
        raise CASOS[caso]

    return TestClient(app, raise_server_exceptions=False)


def test_context_budget_exceeded_da_422_y_nombra_la_capa(cliente: TestClient) -> None:
    respuesta = cliente.get("/lanza/presupuesto")
    assert respuesta.status_code == 422
    cuerpo = respuesta.json()
    assert cuerpo["error"] == "ContextBudgetExceeded"
    assert cuerpo["capa"] == "canon_relevante"


def test_tiempo_agotado_da_503_y_dice_si_es_relanzable(cliente: TestClient) -> None:
    respuesta = cliente.get("/lanza/turno")
    assert respuesta.status_code == 503
    cuerpo = respuesta.json()
    assert cuerpo["error"] == "TiempoAgotado"
    assert cuerpo["relanzable_sin_coste"] is True
    assert cuerpo["paso"] == "ESCRIBIENDO"


def test_regla_de_dominio_violada_da_422_y_nombra_el_axioma(
    cliente: TestClient,
) -> None:
    respuesta = cliente.get("/lanza/dominio")
    assert respuesta.status_code == 422
    cuerpo = respuesta.json()
    assert cuerpo["error"] == "ReglaDeDominioViolada"
    assert cuerpo["axioma"] == 13


def test_recurso_no_encontrado_da_404(cliente: TestClient) -> None:
    respuesta = cliente.get("/lanza/ausente")
    assert respuesta.status_code == 404
    assert respuesta.json()["error"] == "RecursoNoEncontrado"


def test_fallo_de_proveedor_agotado_da_502(cliente: TestClient) -> None:
    respuesta = cliente.get("/lanza/proveedor")
    assert respuesta.status_code == 502
    cuerpo = respuesta.json()
    assert cuerpo["error"] == "FalloDeProveedor"
    assert cuerpo["intentos"] == 3


def test_toda_excepcion_de_dominio_tiene_traduccion() -> None:
    """Sin esto, anadir una excepcion nueva la convierte en un 500 silencioso."""
    app = FastAPI()
    registrar_manejadores(app)
    registradas = set(app.exception_handlers)

    def descendientes(clase: type) -> set[type]:
        hijas = set(clase.__subclasses__())
        return hijas.union(*(descendientes(h) for h in hijas)) if hijas else hijas

    sin_traducir = {c.__name__ for c in descendientes(ErrorDeDominio) - registradas}
    assert not sin_traducir, f"excepciones sin traduccion HTTP: {sin_traducir}"
