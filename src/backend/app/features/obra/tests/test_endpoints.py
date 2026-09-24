"""Los tres endpoints de la entrevista (RI-01, RI-02, RI-03) y CU-01 entero.

Los cuatro primeros tests son los del plan. Los cinco siguientes cubren lo que
el alcance de esta tarea recogio al cerrar la ola 4 —`TextoAportado` (RF-ENT-05),
los vetos del brief (RF-ENT-02)— y dos guardas que si no se prueban aqui no las
prueba nadie: un faltante que el esquema no ve, y una entrevista que no existe.
"""

import json
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.obra.modelos import Obra, PalabraProhibida, TextoAportado
from app.features.obra.service import abrir_entrevista

COMPLETO: dict[str, Any] = {
    "nombre": "Marta",
    "edad": 34,
    "genero": "romance",
    "tono": "calido",
    "nivel_de_calor": 2,
    "elementos_obligatorios": ["el perro Luna"],
}
CON_VETOS: dict[str, Any] = {**COMPLETO, "tono": "melancolico", "vetos": ["sangre"]}
FALTA_UN_RECUERDO: dict[str, Any] = {**COMPLETO, "tono": "sobrio"}

_COMPLETA = json.dumps({"faltantes": [], "contradicciones": []})


@pytest.fixture
def respuestas_del_modelo() -> dict[str, str]:
    """Lo que el doble devuelve, por escenario.

    La clave es una subcadena del prompt, y el prompt lleva al final el `repr`
    de las respuestas del comprador (`Entrevistador.evaluar`). Se distingue por
    el `tono`, que es distinto en cada escenario y no aparece en la plantilla.
    La ultima entrada es el caso por defecto: una entrevista recien abierta a la
    que casi todo le falta.
    """
    return {
        "'tono': 'erotico'": json.dumps(
            {
                "faltantes": [],
                "contradicciones": [
                    {
                        "campos": ["destinatario.edad", "tono"],
                        "explicacion": "8 anos y tono erotico",
                    }
                ],
            }
        ),
        "'tono': 'sobrio'": json.dumps({"faltantes": ["recuerdos"], "contradicciones": []}),
        "'tono': 'calido'": _COMPLETA,
        "'tono': 'melancolico'": _COMPLETA,
        "ENTREVISTADOR": json.dumps(
            {
                "faltantes": ["edad", "genero", "tono", "nivel_de_calor"],
                "contradicciones": [],
            }
        ),
    }


async def cuenta_obras(sesion: AsyncSession) -> int:
    return (await sesion.execute(select(func.count()).select_from(Obra))).scalar_one()


def test_respuestas_devuelve_faltantes_nombrados(cliente):
    """RF-ENT-03: 'falta algo' no deja volver a preguntar; el nombre si."""
    entrevista = cliente.post("/entrevistas").json()
    r = cliente.post(
        f"/entrevistas/{entrevista['id']}/respuestas",
        json={"respuestas": {"nombre": "Marta"}},
    )
    assert r.status_code == 200
    assert "edad" in r.json()["faltantes"]


async def test_cerrar_con_contradiccion_no_crea_obra(cliente, sesion):
    """CA-2: se vuelve a preguntar; no se escribe nada."""
    entrevista = cliente.post("/entrevistas").json()
    cliente.post(
        f"/entrevistas/{entrevista['id']}/respuestas",
        json={"respuestas": {"edad": 8, "tono": "erotico"}},
    )
    r = cliente.post(f"/entrevistas/{entrevista['id']}/cerrar")
    assert r.status_code == 409
    assert r.json()["contradicciones"][0]["explicacion"]
    assert await cuenta_obras(sesion) == 0


async def test_cerrar_con_un_faltante_que_el_esquema_no_ve_no_crea_obra(cliente, sesion):
    """CA-2, la otra mitad, y la unica guarda que puede caer sola.

    `recuerdos` tiene valor por defecto en `BriefEntrada`, asi que el esquema da
    este brief por bueno. Si la decision se dejara solo en el esquema, un dato
    que el Entrevistador dijo que faltaba crearia la obra igual.
    """
    entrevista = cliente.post("/entrevistas").json()
    cliente.post(
        f"/entrevistas/{entrevista['id']}/respuestas",
        json={"respuestas": FALTA_UN_RECUERDO},
    )
    r = cliente.post(f"/entrevistas/{entrevista['id']}/cerrar")
    assert r.status_code == 409
    assert r.json()["faltantes"] == ["recuerdos"]
    assert await cuenta_obras(sesion) == 0


async def test_cerrar_dos_veces_no_crea_dos_obras(cliente, sesion):
    """R-5. El comprador da doble clic; nadie prometio que no lo hiciera."""
    entrevista = cliente.post("/entrevistas").json()
    cliente.post(f"/entrevistas/{entrevista['id']}/respuestas", json={"respuestas": COMPLETO})
    primera = cliente.post(f"/entrevistas/{entrevista['id']}/cerrar")
    segunda = cliente.post(f"/entrevistas/{entrevista['id']}/cerrar")
    assert primera.status_code == 201
    assert segunda.json()["obra_id"] == primera.json()["obra_id"]
    assert await cuenta_obras(sesion) == 1


async def test_el_texto_libre_se_guarda_como_texto_aportado(cliente, sesion):
    """RF-ENT-05: 'se guarda'. Hasta ahora solo se marcaba como dato en el prompt."""
    entrevista = cliente.post("/entrevistas").json()
    cliente.post(
        f"/entrevistas/{entrevista['id']}/respuestas",
        json={"respuestas": {"nombre": "Marta"}, "texto_aportado": "Le gusta el mar."},
    )
    textos = (await sesion.execute(select(TextoAportado))).scalars().all()
    assert [t.contenido for t in textos] == ["Le gusta el mar."]
    assert textos[0].entrevista_id == entrevista["id"]


async def test_un_texto_en_blanco_no_crea_un_texto_aportado(cliente, sesion):
    """R-2: es opcional, y un `TextoAportado` vacio no es un dato de nadie."""
    entrevista = cliente.post("/entrevistas").json()
    cliente.post(
        f"/entrevistas/{entrevista['id']}/respuestas",
        json={"respuestas": {"nombre": "Marta"}, "texto_aportado": "   \n  "},
    )
    assert (await sesion.execute(select(func.count()).select_from(TextoAportado))).scalar_one() == 0


async def test_la_base_tampoco_acepta_un_texto_aportado_en_blanco(sesion):
    """R-2 en la capa que no se puede rodear.

    El test de arriba comprueba la guarda de `guardar_texto_aportado`, que es
    la unica ruta que hay **hoy**. Este comprueba el `CheckConstraint`, que es
    la que seguira habiendo cuando el Extractor escriba por otro lado. Sin este
    test la restriccion estaria en el esquema sin que ningun test pudiera caer
    sobre ella, que es exactamente lo que CA-6 existe para detectar.
    """
    entrevista = await abrir_entrevista(sesion)
    sesion.add(TextoAportado(entrevista_id=entrevista.id, contenido="   ", procedencia="directa"))
    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_los_vetos_del_brief_pasan_al_ambito_brief(cliente, sesion):
    """RF-ENT-02, y postcondicion literal de CU-01: la obra con *sus vetos*."""
    entrevista = cliente.post("/entrevistas").json()
    cliente.post(f"/entrevistas/{entrevista['id']}/respuestas", json={"respuestas": CON_VETOS})
    r = cliente.post(f"/entrevistas/{entrevista['id']}/cerrar")
    assert r.status_code == 201
    vetos = (
        (
            await sesion.execute(
                select(PalabraProhibida).where(PalabraProhibida.obra_id == r.json()["obra_id"])
            )
        )
        .scalars()
        .all()
    )
    assert [(v.ambito, v.termino) for v in vetos] == [("brief", "sangre")]


def test_una_entrevista_que_no_existe_no_es_un_error_del_servidor(cliente):
    """Un id inventado es una peticion equivocada, no una caida.

    Se comprueba tambien el cuerpo, y no solo el 404: sin ruta registrada
    FastAPI ya devuelve 404 por su cuenta, asi que un test que mire solo el
    codigo pasaria en verde con los tres endpoints sin escribir.
    """
    for ruta in ("/entrevistas/9999/respuestas", "/entrevistas/9999/cerrar"):
        r = cliente.post(ruta, json={"respuestas": {}})
        assert r.status_code == 404
        assert "9999" in r.json()["detail"]


def test_los_tres_endpoints_estan_en_el_openapi(cliente):
    """RI-13: es el contrato del que la spec 002 generara su cliente."""
    rutas = cliente.get("/openapi.json").json()["paths"]
    assert "/entrevistas" in rutas
    assert "/entrevistas/{entrevista_id}/respuestas" in rutas
    assert "/entrevistas/{entrevista_id}/cerrar" in rutas
