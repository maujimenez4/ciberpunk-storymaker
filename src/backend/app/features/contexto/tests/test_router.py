"""RI-07: `GET /capitulos/{id}/contexto`, el paquete y su desglose.

Es el endpoint de **depuracion** de CU-07: responde que se enviaria al modelo y
cuanto cuesta cada capa, sin llamar a nadie y sin dejar rastro. Un `GET` que
escribiera `ejecucion` haria que mirar cambiara lo mirado.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.conftest import ObraConOutline
from app.features.contexto.presupuesto import TOPES, Capa
from app.features.contexto.router import obtener_contador
from app.features.obra.modelos import HechoCanon


class ContadorDePalabras:
    def contar(self, texto: str) -> int:
        return len(texto.split())


@pytest.fixture
def cliente_con_contador(cliente: TestClient) -> TestClient:
    """El contador de produccion descargaria su vocabulario: en la suite, no.

    `ContadorTiktoken` baja `cl100k_base` la primera vez que cuenta (P-A y las
    Desviaciones de T1), y la suite corre **sin red** (RNF-FIA-01, CA-4).
    """
    cliente.app.dependency_overrides[obtener_contador] = ContadorDePalabras  # type: ignore[attr-defined]
    return cliente


async def _hecho_pertinente(sesion: AsyncSession, base: ObraConOutline) -> HechoCanon:
    hecho = HechoCanon(
        obra_id=base.obra.id,
        entidad="Nadia",
        atributo="oficio",
        valor="botanica",
        origen="escena",
        escena_de_origen=str(base.escena.id),
    )
    sesion.add(hecho)
    await sesion.flush()
    return hecho


async def test_ri_07_devuelve_el_paquete_con_su_desglose_por_capa(
    cliente_con_contador: TestClient, sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """El desglose viaja **junto al paquete** (RF-CTX-05), con las ocho capas."""
    hecho = await _hecho_pertinente(sesion, obra_con_outline)

    respuesta = cliente_con_contador.get(f"/capitulos/{obra_con_outline.capitulos[0].id}/contexto")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert {linea["capa"] for linea in cuerpo["capas"]} == {capa.value for capa in Capa}
    assert cuerpo["tokens_previstos"] == sum(linea["tokens"] for linea in cuerpo["capas"])
    for linea in cuerpo["capas"]:
        assert linea["tokens"] <= linea["tope"] == TOPES[Capa(linea["capa"])]
    canon = next(c for c in cuerpo["capas"] if c["capa"] == Capa.CANON.value)
    assert canon["identificadores"] == [f"hc:{hecho.id}"]


async def test_ri_07_no_deja_rastro_en_ejecucion(
    cliente_con_contador: TestClient, sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """Depurar es mirar. Una fila de `ejecucion` describe una llamada, y no la hubo."""
    await _hecho_pertinente(sesion, obra_con_outline)

    cliente_con_contador.get(f"/capitulos/{obra_con_outline.capitulos[0].id}/contexto")

    filas = await sesion.execute(text("SELECT count(*) FROM ejecucion"))
    assert filas.scalar_one() == 0


async def test_ri_07_con_la_capa_de_canon_vacia_responde_409_y_no_prosa(
    cliente_con_contador: TestClient, obra_con_outline: ObraConOutline
) -> None:
    """R-3 llega hasta la API: el fallo del almacen se ve, no se disimula.

    El unico hecho de la obra es sobre el perro y la ficha nombra a Nadia y a
    Teo, asi que la capa de canon sale vacia teniendo con que llenarse. El
    manejador central lo traduce sin que esta feature sepa de codigos HTTP.
    """
    respuesta = cliente_con_contador.get(f"/capitulos/{obra_con_outline.capitulos[0].id}/contexto")

    assert respuesta.status_code == 409
    assert "canon" in respuesta.json()["detail"]


async def test_ri_07_sobre_un_capitulo_que_no_existe_no_revienta(
    cliente_con_contador: TestClient,
) -> None:
    respuesta = cliente_con_contador.get("/capitulos/9999/contexto")

    assert respuesta.status_code == 409


def test_ri_07_esta_en_el_openapi_con_su_modelo(cliente: TestClient) -> None:
    """CA-33 cuenta los endpoints por el OpenAPI, no por el codigo."""
    esquema = cliente.get("/openapi.json").json()

    assert "/capitulos/{capitulo_id}/contexto" in esquema["paths"]
