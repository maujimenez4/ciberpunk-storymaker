from fastapi.testclient import TestClient

from app.main import crear_app


def test_la_app_arranca_y_expone_openapi():
    cliente = TestClient(crear_app())
    respuesta = cliente.get("/openapi.json")
    assert respuesta.status_code == 200
    assert respuesta.json()["info"]["title"] == "ciberpunk-storymaker"
