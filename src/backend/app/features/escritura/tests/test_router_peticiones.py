"""RI-09, RI-10 y CA-25 por HTTP (plan-5 T8), con el contrato que usa la 002.

La tarea de fondo corre de verdad -- `TestClient` espera a que termine -- sobre la
sesion del test. Solo el ciclo y la revalidacion son dobles (CA-4): la
orquestacion, la correccion del canon, la clasificacion y `publicar` con Lean son
los de produccion.
"""

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.conftest import ObraConOutline
from app.features.escritura import obtener_atencion
from app.features.escritura.router import Atencion
from app.features.escritura.tests.test_peticion import (
    PREEXISTENTE,
    NovelaPublicada,
    _can_01,
    _ciclo_que_escribe,
    _revalida,
    _usar,
    novela_publicada,  # noqa: F401 -- fixture
)
from app.main import crear_app

PERRO = "el perro se llama Nala, no Luna"


def _con_dobles(cliente: TestClient, *pares: Any) -> None:
    cliente.app.dependency_overrides[obtener_atencion] = lambda: Atencion(  # type: ignore[attr-defined]
        componer=lambda sesion: _ciclo_que_escribe(sesion),
        revalidar=_revalida(*pares),
        vectorizar=None,
        observador=None,
    )


async def _token(sesion: AsyncSession, version_id: int) -> str:
    return str(
        (
            await sesion.execute(
                text("SELECT identificador_publico FROM version_publicada WHERE id = :v"),
                {"v": version_id},
            )
        ).scalar_one()
    )


async def _vigente(sesion: AsyncSession, obra_id: int) -> int:
    return int(
        (
            await sesion.execute(
                text("SELECT id FROM version_publicada WHERE obra_id = :o AND vigente = 1"),
                {"o": obra_id},
            )
        ).scalar_one()
    )


async def test_ca25_de_punta_a_punta_por_el_token(
    sesion: AsyncSession,
    obra_con_outline: ObraConOutline,
    novela_publicada: NovelaPublicada,  # noqa: F811
    cliente: TestClient,
) -> None:
    """CA-25. El preexistente no impide publicar; el introducido si, y entonces la
    vigente no cambia y la peticion se conserva con su resultado."""
    token = await _token(sesion, novela_publicada.version_id)
    _con_dobles(cliente, (2, PREEXISTENTE))

    aceptada = cliente.post(
        f"/lectura/{token}/peticiones",
        json={"hecho_canon_id": novela_publicada.hecho_del_perro_id, "texto_pedido": PERRO},
    )
    assert aceptada.status_code == 202, aceptada.text
    assert aceptada.json()["estado"] == "registrada"

    primera = cliente.get(f"/lectura/{token}/peticiones/{aceptada.json()['peticion_id']}").json()
    assert primera["estado"] == "atendida", primera
    assert primera["token_resultante"] not in (None, token)
    assert primera["capitulos"] == [
        {"numero": 3, "estado": "hecho"},
        {"numero": 7, "estado": "hecho"},
    ]
    assert cliente.get(f"/lectura/{token}/estado").json() == {"peticion_en_curso": None}

    # El introducido: un hecho que el 5 usa, y un CAN-01 que el cuadro no tenia.
    await _usar(sesion, obra_con_outline, novela_publicada.hecho_sin_uso_id, 5)
    await sesion.commit()
    vigente = await _vigente(sesion, novela_publicada.obra_id)
    _con_dobles(cliente, (2, PREEXISTENTE), (5, _can_01(novela_publicada.hecho_sin_uso_id)))
    nuevo_token = primera["token_resultante"]

    segunda = cliente.post(
        f"/lectura/{nuevo_token}/peticiones",
        json={"hecho_canon_id": novela_publicada.hecho_sin_uso_id, "texto_pedido": "en la costa"},
    )
    assert segunda.status_code == 202
    estado = cliente.get(f"/lectura/{nuevo_token}/peticiones/{segunda.json()['peticion_id']}")
    assert estado.json()["estado"] == "descartada"
    assert estado.json()["resultado"] and estado.json()["token_resultante"] is None
    assert await _vigente(sesion, novela_publicada.obra_id) == vigente


async def test_un_hecho_ya_sustituido_da_409_y_un_token_malo_404(
    sesion: AsyncSession,
    novela_publicada: NovelaPublicada,  # noqa: F811
    cliente: TestClient,
) -> None:
    """R-5 al registrar, y el enlace roto sin decir por que."""
    token = await _token(sesion, novela_publicada.version_id)
    _con_dobles(cliente)
    cuerpo = {"hecho_canon_id": novela_publicada.hecho_sin_uso_id, "texto_pedido": "otra"}

    assert cliente.post(f"/lectura/{token}/peticiones", json=cuerpo).status_code == 202
    assert cliente.post(f"/lectura/{token}/peticiones", json=cuerpo).status_code == 409
    assert cliente.post("/lectura/no-vale/peticiones", json=cuerpo).status_code == 404
    assert cliente.get("/lectura/no-vale/estado").status_code == 404


async def test_ri09_por_obra_y_ri10_revertir(
    sesion: AsyncSession,
    novela_publicada: NovelaPublicada,  # noqa: F811
    cliente: TestClient,
) -> None:
    """Los dos nombres de la spec: la peticion por `obra_id` y revertir (RF-PET-08)."""
    _con_dobles(cliente)
    respuesta = cliente.post(
        f"/obras/{novela_publicada.obra_id}/peticiones",
        json={"hecho_canon_id": novela_publicada.hecho_del_perro_id, "texto_pedido": PERRO},
    )
    assert respuesta.status_code == 202
    assert await _vigente(sesion, novela_publicada.obra_id) != novela_publicada.version_id

    vuelta = cliente.post(
        f"/obras/{novela_publicada.obra_id}/versiones/{novela_publicada.version_id}/revertir"
    )
    assert vuelta.status_code == 200, vuelta.text
    assert vuelta.json()["token"] == await _token(sesion, novela_publicada.version_id)
    assert await _vigente(sesion, novela_publicada.obra_id) == novela_publicada.version_id


def test_las_rutas_de_la_fase_estan_en_el_openapi() -> None:
    """RI-13: es el contrato del que la 002 genera su cliente."""
    rutas = crear_app().openapi()["paths"]

    for ruta in (
        "/obras/{obra_id}/peticiones",
        "/obras/{obra_id}/versiones/{version}/revertir",
        "/lectura/{token}/peticiones",
        "/lectura/{token}/peticiones/{peticion_id}",
        "/lectura/{token}/estado",
    ):
        assert ruta in rutas, ruta
