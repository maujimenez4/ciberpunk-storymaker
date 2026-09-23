"""P-91, P-92, P-93 y P-95: la API y su contrato.

RI-05, RI-09, RI-11, RI-12, RI-18, RI-19 y RI-23.
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.features.escritura.router import obtener_dependencias
from app.features.escritura.tests.test_ciclo_completo import dependencias
from app.main import crear_app

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture
def app(base_de_datos: Path) -> FastAPI:
    conexion = sqlite3.connect(base_de_datos)
    conexion.execute("INSERT INTO serie (serie_id, titulo) VALUES ('s1','S')")
    conexion.execute(
        "INSERT INTO obra (obra_id, serie_id, titulo, genero, subgenero,"
        " extension_objetivo, persona, tiempo_verbal, esquema_de_pov, nivel_de_calor)"
        " VALUES ('o1','s1','O','romance','contemporaneo',90000,'tercera','pasado',"
        "'dual','sensual')"
    )
    conexion.execute(
        "INSERT INTO parte (parte_id, obra_id, numero, funcion_estructural)"
        " VALUES ('pa1','o1',1,'planteamiento')"
    )
    conexion.execute(
        "INSERT INTO capitulo (capitulo_id, parte_id, numero) VALUES ('ca1','pa1',1)"
    )
    conexion.execute(
        "INSERT INTO escena (escena_id, capitulo_id, orden_discurso, pov)"
        " VALUES ('es1','ca1',1,'pj-ada')"
    )
    conexion.commit()
    conexion.close()

    aplicacion = crear_app(base_de_datos)
    # Desde P-112 el endpoint arma el ciclo con el proveedor real, que lee
    # `Ajustes`. Aqui se mira el **contrato** de la API -202, modelos de
    # respuesta, errores por handler-, no el ciclo, asi que entran dobles. Nada
    # llega a ejecutarse: estos casos no drenan el ejecutor.
    aplicacion.dependency_overrides[obtener_dependencias] = lambda: dependencias(
        base_de_datos
    )
    return aplicacion


@pytest.fixture
def cliente(app: FastAPI) -> TestClient:
    return TestClient(app)


# --- P-91: las operaciones largas no bloquean -------------------------------


def test_escribir_una_escena_devuelve_trabajo_y_no_espera(cliente: TestClient) -> None:
    """RI-05 y §5.4. Una petición que esperase a que el modelo escriba se agota
    antes de terminar y deja el trabajo huérfano."""
    respuesta = cliente.post("/escenas/es1/escribir", params={"obra_id": "o1"})

    assert respuesta.status_code == 202
    assert respuesta.json()["trabajo_id"].startswith("trab-")
    assert respuesta.json()["estado"] == "PLANIFICANDO"


def test_el_trabajo_se_consulta_despues(cliente: TestClient) -> None:
    """RI-09: el cliente pregunta por el estado en vez de esperar."""
    creado = cliente.post("/escenas/es1/escribir", params={"obra_id": "o1"}).json()

    consulta = cliente.get(f"/trabajos/{creado['trabajo_id']}")

    assert consulta.status_code == 200
    assert consulta.json()["estado"] == "PLANIFICANDO"


def test_se_puede_cancelar_un_trabajo(cliente: TestClient) -> None:
    """RI-19."""
    creado = cliente.post("/escenas/es1/escribir", params={"obra_id": "o1"}).json()

    respuesta = cliente.post(f"/trabajos/{creado['trabajo_id']}/cancelar")

    assert respuesta.json()["estado"] == "CANCELADA"


# --- P-95: lo que expone el estado del trabajo ------------------------------


def test_el_estado_expone_lo_que_exige_ri_18(cliente: TestClient) -> None:
    creado = cliente.post("/escenas/es1/escribir", params={"obra_id": "o1"}).json()

    cuerpo = cliente.get(f"/trabajos/{creado['trabajo_id']}").json()

    for campo in ("trabajo_id", "tipo", "estado", "intento", "causa_fallo", "defectos"):
        assert campo in cuerpo


def test_el_estado_es_uno_de_los_diez(cliente: TestClient) -> None:
    from app.commons.jobs import Estado

    creado = cliente.post("/escenas/es1/escribir", params={"obra_id": "o1"}).json()

    cuerpo = cliente.get(f"/trabajos/{creado['trabajo_id']}").json()

    assert cuerpo["estado"] in {e.value for e in Estado}


# --- P-92: ningún servicio lanza HTTPException ------------------------------


def test_un_trabajo_que_no_existe_da_404_por_el_handler(cliente: TestClient) -> None:
    """RI-11. El servicio lanza `RecursoNoEncontrado`; lo traduce el handler."""
    respuesta = cliente.get("/trabajos/trab-inventado")

    assert respuesta.status_code == 404
    assert respuesta.json()["error"] == "RecursoNoEncontrado"


def test_ningun_servicio_ni_repositorio_lanza_http_exception() -> None:
    """§5.2 regla 4. Un servicio que conoce códigos HTTP no se puede reutilizar
    desde un trabajo en segundo plano, que es donde corre el ciclo de escena."""
    sospechosos = [
        fichero
        for fichero in RAIZ.rglob("*.py")
        if fichero.name in ("service.py", "repository.py", "ciclo.py")
        and "tests" not in fichero.parts
        and "HTTPException" in fichero.read_text(encoding="utf-8")
    ]

    assert not sospechosos, f"lanzan HTTPException: {sospechosos}"


# --- P-93: OpenAPI como contrato ---------------------------------------------


def test_toda_ruta_declara_su_modelo_de_respuesta(app: FastAPI) -> None:
    """RI-23. Se comprueba **sobre el esquema OpenAPI**, no sobre `app.routes`.

    El primer intento iteraba `app.routes` filtrando `APIRoute`, y pasaba en
    vacio: esta version de FastAPI envuelve los routers incluidos, asi que la
    lista no contenia ninguna de las rutas reales. Un test de contrato que mira
    la estructura interna del framework se rompe en silencio cuando esa
    estructura cambia; el esquema generado es justo lo que RI-23 llama el
    contrato, y es lo que ve un cliente.
    """
    esquema = app.openapi()
    sin_modelo = [
        f"{metodo.upper()} {ruta}"
        for ruta, operaciones in esquema["paths"].items()
        for metodo, operacion in operaciones.items()
        if not any(
            "content" in respuesta
            for codigo, respuesta in operacion.get("responses", {}).items()
            if codigo.startswith("2")
        )
    ]

    assert not sin_modelo, f"rutas sin modelo de respuesta: {sin_modelo}"


def test_el_esquema_expone_las_rutas_que_se_montaron(app: FastAPI) -> None:
    """Guardia del test anterior: si las rutas desaparecieran del esquema, aquel
    pasaria en vacio y nadie se enteraria."""
    rutas = set(app.openapi()["paths"])

    assert "/escenas/{escena_id}/escribir" in rutas
    assert "/trabajos/{trabajo_id}" in rutas
    assert len(rutas) >= 3


def test_el_esquema_openapi_se_publica(cliente: TestClient) -> None:
    respuesta = cliente.get("/openapi.json")

    assert respuesta.status_code == 200
    assert "/trabajos/{trabajo_id}" in respuesta.json()["paths"]


def test_la_auditoria_de_manuscrito_no_esta_expuesta(app: FastAPI) -> None:
    """Está fuera de alcance. La spec retiró RI-10 sin renumerar el resto, y
    una ruta que existiera sin implementación sería peor que su ausencia."""
    assert not any("auditoria" in ruta for ruta in app.openapi()["paths"])
