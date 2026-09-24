"""RI-04: `POST /obras/{id}/outline`, biblia y outline de diez capitulos.

El endpoint no decide nada (`CLAUDE.md` §6): valida la entrada, llama al caso de
uso y traduce lo que el servicio devolvio a transporte. Que un beat sin asignar
salga con 409 y no con 500 es cosa del manejador central de `commons/errors/`.
"""

import json
from typing import Any

import pytest
from sqlalchemy import func, select

from app.features.outline.modelos import Capitulo, VersionObra
from app.features.outline.schemas import BeatDeGenero


def _capitulos(**cambios_del_octavo: Any) -> list[dict[str, Any]]:
    capitulos = [
        {
            "numero": n,
            "titulo": f"Capitulo {n}",
            "pov_dominante": "Nadia" if n % 2 else "Teo",
            "lugar": "El invernadero",
            "objetivo": "Que Teo confiese",
            "obstaculo": "Teo no habla de su madre",
            "valor_entrada": "confianza",
            "valor_salida": "sospecha",
            "gancho_de_apertura": "La puerta estaba abierta",
            "tipo_de_corte_final": "pregunta",
            "extension_objetivo": 1200,
            "beat_de_genero": beat.value,
        }
        for n, beat in enumerate(BeatDeGenero, start=1)
    ]
    capitulos[7].update(cambios_del_octavo)
    return capitulos


# La biblia declara los parametros de discurso con los literales de
# `definitions.md` §5: sin ellos no se puede construir ninguna ficha de escena.
BIBLIA: dict[str, Any] = {
    "protagonista": "Nadia",
    "persona": "3ª limitada",
    "tiempo_verbal": "pasado",
    "nivel_de_calor": 2,
}


@pytest.fixture
def respuestas_del_modelo() -> dict[str, str]:
    """Dos escenarios, distinguidos por el titulo de la obra que va en el brief.

    El doble elige por subcadena del prompt, y el prompt lleva el brief dentro
    de su marca de dato: el titulo es lo unico que cambia entre los dos.
    """
    return {
        "Sin ruptura": json.dumps({"biblia": BIBLIA, "capitulos": _capitulos(beat_de_genero=None)}),
        "# Arquitecto": json.dumps({"biblia": BIBLIA, "capitulos": _capitulos()}),
    }


async def test_el_endpoint_crea_la_biblia_versionada_y_los_diez_capitulos(cliente, obra, sesion):
    """RI-04 y CU-02 entero: la postcondicion es el outline en la base."""
    respuesta = cliente.post(f"/obras/{obra.id}/outline")

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["version"] == 1
    assert [c["numero"] for c in cuerpo["capitulos"]] == list(range(1, 11))
    assert cuerpo["capitulos"][0]["beat_de_genero"] == BeatDeGenero.CARENCIAS.value
    assert cuerpo["capitulos"][0]["objetivo"] == "Que Teo confiese"
    assert (await sesion.execute(select(func.count()).select_from(VersionObra))).scalar_one() == 1
    assert (await sesion.execute(select(func.count()).select_from(Capitulo))).scalar_one() == 10


async def test_un_beat_sin_asignar_responde_409_y_no_deja_outline(cliente, sesion, obra):
    """CA-32 por HTTP. El nombre de la obra elige el escenario del doble."""
    obra.titulo = "Sin ruptura"
    await sesion.flush()

    respuesta = cliente.post(f"/obras/{obra.id}/outline")

    assert respuesta.status_code == 409  # un beat sin asignar SI es conflicto de estado
    assert (await sesion.execute(select(func.count()).select_from(Capitulo))).scalar_one() == 0


async def test_planificar_una_obra_inexistente_no_responde_500(cliente):
    respuesta = cliente.post("/obras/9999/outline")

    assert respuesta.status_code == 404  # RecursoDesconocido: no existe, no es conflicto


async def test_el_endpoint_esta_en_el_openapi_con_su_modelo(cliente):
    """RI-04 es contrato: la spec 002 genera su cliente del OpenAPI (CA-33)."""
    esquema = cliente.get("/openapi.json").json()

    assert "/obras/{obra_id}/outline" in esquema["paths"]
    assert "post" in esquema["paths"]["/obras/{obra_id}/outline"]


async def test_el_outline_queda_confirmado_y_lo_ve_otra_sesion(cliente, obra, motor) -> None:
    """RI-04 escribe en el fichero, no solo en la sesion de quien pregunta.

    Lo destapo T11 al cerrar la fase: `planificar_obra` no confirmaba, asi que
    contra la aplicacion levantada el endpoint respondia y **no dejaba ni un
    capitulo en disco**. La suite no lo veia por una razon que conviene
    entender: sus tests comparten la sesion del `cliente`, asi que lo escrito y
    sin confirmar se lee igual de bien que lo confirmado.

    Es la misma clase de fallo que la Fase 1 encontro tres veces --una
    afirmacion que solo es cierta dentro de la suite-- y por eso este test abre
    **otra sesion** sobre el mismo motor.
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    respuesta = cliente.post(f"/obras/{obra.id}/outline")
    assert respuesta.status_code == 201, respuesta.text

    async with AsyncSession(motor) as otra:
        capitulos = (await otra.execute(select(func.count()).select_from(Capitulo))).scalar_one()
        versiones = (await otra.execute(select(func.count()).select_from(VersionObra))).scalar_one()

    assert capitulos == 10, "sin `commit`, otra sesion no ve ningun capitulo"
    assert versiones == 1
