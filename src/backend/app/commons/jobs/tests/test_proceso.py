"""P-13: los trabajos corren en el proceso de la API (architecture.md §2.2 r3, §10).

No es una preferencia de despliegue: el turno unico de §2.2 es **por proceso**.
Si los trabajos corrieran en un worker aparte habria dos turnos donde el diseno
cuenta uno, y el limite de llamadas simultaneas quedaria duplicado en silencio
—sin error, sin aviso, solo el doble de factura y de latencia—.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.commons.jobs import (
    TurnoDeModelo,
    montar_ejecutor_de_trabajos,
    turno_del_proceso,
)


def test_el_turno_es_el_mismo_objeto_en_todo_el_proceso() -> None:
    """Un turno por proceso significa **un** objeto, no uno por modulo."""
    assert turno_del_proceso() is turno_del_proceso()


def test_el_ejecutor_usa_el_turno_del_proceso() -> None:
    """Si el ejecutor creara el suyo, habria dos turnos donde el diseno cuenta uno."""
    app = FastAPI()
    ejecutor = montar_ejecutor_de_trabajos(app)

    assert ejecutor.turno is turno_del_proceso()


def test_el_turno_solo_deja_pasar_a_uno() -> None:
    turno = TurnoDeModelo(simultaneas=1)

    assert turno.tomar(espera_s=0) is True
    assert turno.tomar(espera_s=0) is False

    turno.liberar()
    assert turno.tomar(espera_s=0) is True


def test_el_turno_se_libera_aunque_el_paso_falle() -> None:
    """RF-ORQ-13: un turno que no se libera cuelga el proceso entero."""
    turno = TurnoDeModelo(simultaneas=1)

    with pytest.raises(RuntimeError), turno.en_uso(espera_s=0):
        raise RuntimeError("el paso exploto")

    assert turno.tomar(espera_s=0) is True


def test_los_trabajos_se_ejecutan_en_el_proceso_de_la_api() -> None:
    """El ejecutor vive colgado de la aplicacion, no de un worker externo."""
    app = FastAPI()
    ejecutor = montar_ejecutor_de_trabajos(app)
    hechos: list[str] = []

    @app.post("/lanza")
    def lanza() -> dict[str, str]:
        ejecutor.encolar(lambda: hechos.append("trabajo hecho"))
        return {"estado": "encolado"}

    with TestClient(app) as cliente:
        assert cliente.post("/lanza").json() == {"estado": "encolado"}

    assert hechos == ["trabajo hecho"]
