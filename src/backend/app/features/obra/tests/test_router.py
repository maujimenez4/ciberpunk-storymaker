"""P-114: crear una obra desde un brief (RI-01).

Es el unico endpoint de los nueve que **no** devuelve un trabajo: crear la fila
de una obra es inmediato y no llama al modelo. Devolver 202 aqui obligaria al
cliente a hacer *polling* para saber un identificador que ya existe.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import crear_app

BRIEF = {
    "titulo": "Ceniza y neon",
    "genero": "romance",
    "subgenero": "romantasy",
    "extension_objetivo": 90000,
    "persona": "tercera",
    "tiempo_verbal": "pasado",
    "esquema_de_pov": "dual",
    "nivel_de_calor": "sensual",
}


@pytest.fixture
def cliente(base_de_datos: Path) -> TestClient:
    return TestClient(crear_app(base_de_datos))


def test_crear_una_obra_desde_un_brief_devuelve_201(cliente: TestClient) -> None:
    respuesta = cliente.post("/obras", json=BRIEF)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["titulo"] == "Ceniza y neon"
    assert cuerpo["obra_id"]
    # RF-OBR-01: los parametros de discurso quedan en la obra para que sus
    # escenas los hereden por codigo y no por prompt.
    assert cuerpo["persona"] == "tercera"
    assert cuerpo["nivel_de_calor"] == "sensual"


def test_la_obra_creada_se_puede_consultar_despues(cliente: TestClient) -> None:
    obra_id = cliente.post("/obras", json=BRIEF).json()["obra_id"]

    assert cliente.get(f"/obras/{obra_id}").json()["obra_id"] == obra_id


def test_un_brief_adversario_lo_rechaza_el_esquema_no_el_endpoint(
    cliente: TestClient,
) -> None:
    """RNF-SEG-06 y regla 6 de §8: la validacion es de esquema.

    El 422 lo produce Pydantic antes de llegar al servicio. Que la defensa este
    en el modelo y no en el endpoint es lo que hace que valga igual desde un
    trabajo en segundo plano, donde no hay peticion que validar.
    """
    respuesta = cliente.post(
        "/obras", json={**BRIEF, "premisa": "una protagonista de 16 anos y su amante"}
    )

    assert respuesta.status_code == 422


def test_un_nivel_de_calor_inventado_no_entra(cliente: TestClient) -> None:
    assert (
        cliente.post("/obras", json={**BRIEF, "nivel_de_calor": "brutal"}).status_code
        == 422
    )
