"""P-112: el endpoint encola el ciclo y el trabajo avanza (RI-05, RF-ORQ-03).

`POST /escenas/{id}/escribir` creaba la fila de `trabajo`, devolvia 202 y **nadie
la ejecutaba**: `encolar()` no se llamaba desde ningun sitio salvo un test. El
trabajo se quedaba en `PLANIFICANDO` para siempre y el cliente podia consultarlo
mil veces sin que cambiara nada.

Es la diferencia entre una API que parece funcionar y una que funciona: los dos
casos devuelven 202.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.features.escritura.router import obtener_dependencias
from app.features.escritura.tests.test_ciclo_completo import dependencias, obra_lista
from app.main import crear_app

__all__ = ["obra_lista"]  # la fixture se reutiliza tal cual


@pytest.fixture
def cliente(obra_lista: Path) -> TestClient:
    app = crear_app(obra_lista)
    # El proveedor real construiria el CLI de Claude Code; aqui, dobles.
    app.dependency_overrides[obtener_dependencias] = lambda: dependencias(obra_lista)
    return TestClient(app)


def test_escribir_una_escena_encola_el_ciclo_y_el_trabajo_avanza(
    cliente: TestClient,
) -> None:
    respuesta = cliente.post("/escenas/es1/escribir", params={"obra_id": "o1"})

    assert respuesta.status_code == 202
    trabajo_id = respuesta.json()["trabajo_id"]
    assert respuesta.json()["estado"] == "PLANIFICANDO"

    # El endpoint no espera (RI-01 a RI-09): el ciclo corre despues. Se drena a
    # mano en vez de dormir esperando al hilo, que haria el test inestable.
    cliente.app.state.ejecutor.drenar()  # type: ignore[attr-defined]

    estado = cliente.get(f"/trabajos/{trabajo_id}").json()
    assert estado["estado"] == "INTEGRADA"
    assert estado["trabajo_id"] == trabajo_id


def test_el_trabajo_que_revienta_queda_fallida_y_no_colgado(
    obra_lista: Path,
) -> None:
    """Un ciclo que lanza no puede dejar el trabajo en el estado intermedio.

    Sin esto, el hilo del ejecutor se traga la excepcion y el cliente ve
    `ENSAMBLANDO` para siempre: un fallo que se presenta como lentitud, que es
    la forma mas cara de presentarse.
    """
    from app.features.escritura import Dependencias

    app = crear_app(obra_lista)
    rotas = dependencias(obra_lista)
    # Un cargador de prompts que apunta a ninguna parte: el paso revienta.
    app.dependency_overrides[obtener_dependencias] = lambda: Dependencias(
        **{**rotas.__dict__, "cargador": type(rotas.cargador)(Path("/no/existe"))}
    )
    cliente = TestClient(app)

    trabajo_id = cliente.post("/escenas/es1/escribir", params={"obra_id": "o1"}).json()[
        "trabajo_id"
    ]
    cliente.app.state.ejecutor.drenar()  # type: ignore[attr-defined]

    estado = cliente.get(f"/trabajos/{trabajo_id}").json()
    assert estado["estado"] == "FALLIDA"
    assert estado["causa_fallo"]


def test_al_arrancar_se_retoman_los_trabajos_no_terminales(obra_lista: Path) -> None:
    """P-113, RF-ORQ-05 y CA-3.

    `vivos()` existia y estaba probado, pero **nadie lo llamaba al arrancar**.
    Una caida a mitad de escena dejaba el trabajo en su estado intermedio para
    siempre: el estado se persistia con todo cuidado y luego no lo leia nadie.

    La reanudacion ocurre en el arranque, donde `dependency_overrides` no llega,
    asi que la fabrica de dependencias la recibe `crear_app`. Es composicion, y
    su sitio es `main.py`.
    """
    from app.commons.domain import RelojFijo
    from app.commons.jobs import RepositorioDeTrabajos
    from app.features.escritura.tests.test_ciclo_completo import RELOJ

    trabajos = RepositorioDeTrabajos(obra_lista)
    interrumpido = trabajos.crear("o1", "es1", "escribir_escena", RELOJ)

    app = crear_app(obra_lista, fabrica_dependencias=lambda: dependencias(obra_lista))
    with TestClient(app) as cliente:  # el `with` dispara el lifespan
        # `parar()` y no `drenar()`: el lifespan ya arranco el hilo, asi que la
        # cola puede estar vacia con el trabajo todavia en curso. `parar()` hace
        # join, que es lo unico que garantiza que termino.
        cliente.app.state.ejecutor.parar()  # type: ignore[attr-defined]
        estado = cliente.get(f"/trabajos/{interrumpido.trabajo_id}").json()

    assert estado["estado"] == "INTEGRADA", (
        "el trabajo interrumpido no se retomo al arrancar"
    )
    assert isinstance(RELOJ, RelojFijo)


def test_un_trabajo_terminal_no_se_retoma(obra_lista: Path) -> None:
    """Reanudar uno ya cerrado lo volveria a escribir y a cobrar."""
    from app.commons.jobs import Estado, RepositorioDeTrabajos
    from app.features.escritura.tests.test_ciclo_completo import RELOJ

    trabajos = RepositorioDeTrabajos(obra_lista)
    cerrado = trabajos.crear("o1", "es1", "escribir_escena", RELOJ)
    trabajos.transitar(cerrado.trabajo_id, Estado.CANCELADA, RELOJ)

    app = crear_app(obra_lista, fabrica_dependencias=lambda: dependencias(obra_lista))
    with TestClient(app) as cliente:
        cliente.app.state.ejecutor.parar()  # type: ignore[attr-defined]
        estado = cliente.get(f"/trabajos/{cerrado.trabajo_id}").json()

    assert estado["estado"] == "CANCELADA"
