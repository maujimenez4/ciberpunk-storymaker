"""El *lifespan* de `crear_app` cierra el observador al apagar (plan 8 T7, P-22.2).

El SDK de Langfuse manda por lotes y en segundo plano: un proceso que se apaga
sin `flush` pierde lo ultimo que encolo, que en una corrida real son los spans
del ultimo capitulo. Y el cierre **no puede tumbar el apagado** si Langfuse esta
caido (Review Focus 5): va por el blindaje, y el fallo se cuenta.

Se cierra el mismo observador que reciben las rutas: el de `obtener_observador`,
o su sobrescritura si la hay. Sin red y sin la dependencia (`CA-4`).
"""

from contextlib import contextmanager
from typing import Any

from fastapi.testclient import TestClient

from app.commons.observabilidad import (
    ObservadorEnMemoria,
    ObservadorLangfuse,
    blindar,
    obtener_observador,
)
from app.main import crear_app


class _LangfuseCaido:
    """Traza bien y revienta al vaciar la cola."""

    @contextmanager
    def start_as_current_span(self, *, name: str) -> Any:
        raise AssertionError("no se traza nada en este test")
        yield  # pragma: no cover

    def flush(self) -> None:
        raise ConnectionError("Langfuse no responde")


def test_al_apagar_se_cierra_el_observador_de_las_rutas() -> None:
    registro = ObservadorEnMemoria()
    app = crear_app()
    app.dependency_overrides[obtener_observador] = lambda: registro

    with TestClient(app):
        assert registro.cerrado is False

    assert registro.cerrado is True


def test_con_langfuse_caido_el_apagado_termina_y_el_fallo_se_cuenta() -> None:
    observador = blindar(
        ObservadorLangfuse(
            clave_publica="pk-lf-x",
            clave_secreta="sk-lf-x",
            host="https://example.invalid",
            cliente=_LangfuseCaido(),
        )
    )
    app = crear_app()
    app.dependency_overrides[obtener_observador] = lambda: observador

    with TestClient(app):
        pass

    assert observador.fallos == 1
