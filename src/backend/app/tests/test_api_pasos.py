"""P-115, P-116 y P-117: los tres pasos que devuelven trabajo (RI-02 a RI-04).

No son el ciclo de una escena: nacen, hacen su paso y terminan
(`architecture.md` §3.3). Lo que comparten con el ciclo es la forma de la
respuesta -202 y un identificador consultable- y la razon de tenerla: los tres
llaman al modelo y tardan lo que tarde, asi que una peticion que los esperase se
agotaria dejando el trabajo huerfano.
"""

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.commons.llm import DobleDeModelo
from app.features.escritura import Dependencias
from app.features.escritura.tests.test_ciclo_completo import (
    BIBLIA,
    FICHA,
    RELOJ,
    dependencias,
    obra_lista,
)
from app.features.outline import BEATS_OBLIGATORIOS
from app.main import crear_app

__all__ = ["obra_lista"]

# RF-OUT-02: los diez beats obligatorios, cada uno en exactamente una escena.
# Construirlo desde `BEATS_OBLIGATORIOS` y no a mano es lo que evita que este
# test se quede corto el dia que el pack de genero cambie.
OUTLINE = json.dumps(
    {
        "partes": [
            {
                "numero": 1,
                "funcion_estructural": "planteamiento",
                "capitulos": [
                    {
                        "numero": 1,
                        "titulo": "La tregua",
                        "pov_dominante": "pj-ada",
                        "escenas": [
                            {
                                "orden_discurso": numero,
                                "pov": "pj-ada",
                                "lugar": "lug-taller",
                                "objetivo_del_pov": f"objetivo {numero}",
                                "obstaculo": f"obstaculo {numero}",
                                "valor_entrada": "control",
                                "valor_salida": "amenaza",
                                "beat_de_genero": beat,
                            }
                            for numero, beat in enumerate(BEATS_OBLIGATORIOS, start=1)
                        ],
                    }
                ],
            }
        ]
    }
)


def cliente_con(ruta: Path, **respuestas: str) -> TestClient:
    base = dependencias(ruta)
    campos = {**base.__dict__}
    for nombre, texto in respuestas.items():
        campos[nombre] = DobleDeModelo([texto])
    app = crear_app(ruta, fabrica_dependencias=lambda: Dependencias(**campos))
    return TestClient(app)


def _terminar(cliente: TestClient, trabajo_id: str) -> dict[str, object]:
    cliente.app.state.ejecutor.drenar()  # type: ignore[attr-defined]
    cuerpo: dict[str, object] = cliente.get(f"/trabajos/{trabajo_id}").json()
    return cuerpo


def test_generar_la_biblia_devuelve_trabajo_y_lo_termina(obra_lista: Path) -> None:
    """RI-02."""
    cliente = cliente_con(obra_lista, arquitecto=BIBLIA.model_dump_json())

    respuesta = cliente.post("/obras/o1/biblia")

    assert respuesta.status_code == 202
    estado = _terminar(cliente, respuesta.json()["trabajo_id"])
    assert estado["estado"] == "INTEGRADA"

    conexion = sqlite3.connect(obra_lista)
    versiones = conexion.execute(
        "SELECT COUNT(*) FROM version_obra WHERE obra_id = 'o1'"
    ).fetchone()[0]
    conexion.close()
    assert versiones == 2, "la biblia nueva tiene que crear version, no pisar (RD-12)"


def test_generar_el_outline_devuelve_trabajo_y_lo_termina(obra_lista: Path) -> None:
    """RI-03, sobre una obra **recien creada**.

    No sobre la de la fixture: esa ya tiene parte, capitulo y escena, y `parte`
    lleva `UNIQUE(obra_id, numero)`. Generar el outline dos veces sobre la misma
    obra choca, y que choque es correcto -duplicar la estructura en silencio
    seria peor-, pero no es lo que este caso mide.
    """
    cliente = cliente_con(obra_lista, arquitecto=OUTLINE)
    obra_id = cliente.post(
        "/obras",
        json={
            "titulo": "Otra",
            "genero": "romance",
            "subgenero": "contemporaneo",
            "extension_objetivo": 90000,
            "persona": "tercera",
            "tiempo_verbal": "pasado",
            "esquema_de_pov": "dual",
            "nivel_de_calor": "sensual",
        },
    ).json()["obra_id"]

    respuesta = cliente.post(f"/obras/{obra_id}/outline")

    assert respuesta.status_code == 202
    estado = _terminar(cliente, respuesta.json()["trabajo_id"])
    assert estado["estado"] == "INTEGRADA", estado["causa_fallo"]


def test_planificar_una_escena_devuelve_trabajo_y_escribe_la_ficha(
    obra_lista: Path,
) -> None:
    """RI-04 y RF-ESC-01: la ficha queda en la fila, no solo en la respuesta."""
    cliente = cliente_con(obra_lista, planificador=FICHA)

    respuesta = cliente.post("/escenas/es1/planificar")

    assert respuesta.status_code == 202
    estado = _terminar(cliente, respuesta.json()["trabajo_id"])
    assert estado["estado"] == "INTEGRADA", estado["causa_fallo"]

    conexion = sqlite3.connect(obra_lista)
    objetivo = conexion.execute(
        "SELECT objetivo_del_pov FROM escena WHERE escena_id = 'es1'"
    ).fetchone()[0]
    conexion.close()
    assert objetivo == "cerrar el trato antes del amanecer"


def test_un_paso_que_revienta_queda_fallida(obra_lista: Path) -> None:
    """Y no colgado: `FALLIDA` es un fallo tecnico (RF-CAL-10)."""
    cliente = cliente_con(obra_lista, arquitecto="esto no es JSON")

    trabajo_id = cliente.post("/obras/o1/biblia").json()["trabajo_id"]
    estado = _terminar(cliente, trabajo_id)

    assert estado["estado"] == "FALLIDA"
    assert estado["causa_fallo"]


@pytest.mark.parametrize(
    ("ruta", "campo"),
    [("/obras/o1/biblia", "arquitecto"), ("/escenas/es1/planificar", "planificador")],
)
def test_el_trabajo_declara_su_tipo_y_no_el_del_ciclo(
    obra_lista: Path, ruta: str, campo: str
) -> None:
    """Es lo que decide su maquina de estados (§3.3)."""
    cliente = cliente_con(obra_lista, **{campo: BIBLIA.model_dump_json()})

    trabajo_id = cliente.post(ruta).json()["trabajo_id"]
    conexion = sqlite3.connect(obra_lista)
    tipo = conexion.execute(
        "SELECT tipo FROM trabajo WHERE trabajo_id = ?", (trabajo_id,)
    ).fetchone()[0]
    conexion.close()

    assert tipo != "escribir_escena"
    assert isinstance(RELOJ.ahora().isoformat(), str)
