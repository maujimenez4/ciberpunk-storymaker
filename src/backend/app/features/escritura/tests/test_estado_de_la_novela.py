"""`GET /obras/{obra_id}/novela`: por donde va la novela, leido de la base.

`POST /obras/{id}/novela` responde 202 y sigue por detras durante los diez
capitulos, pero no devuelve ningun identificador de trabajo -- todavia no
existen -- y `GET /trabajos/{id}` es por capitulo. Sin esta consulta, quien
lanza la novela no tiene forma de saber si ya puede publicar, y el frontend
publicaba en el acto y fallaba.

Cuatro estados, y cada uno con su test:

| Estado | Cuando |
| --- | --- |
| `sin_outline` | La obra no tiene capitulos |
| `escribiendo` | Queda capitulo pendiente y su ultimo trabajo no esta cerrado en fallo |
| `terminada` | Todos los capitulos del outline estan `INTEGRADA` |
| `detenida` | El ultimo trabajo del capitulo pendiente acabo en `ESCALADA`, `FALLIDA` o `CANCELADA` |

Los trabajos se fabrican a mano: lo que se prueba es la lectura, no el ciclo
(CA-4, ninguna prueba llama al proveedor).
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.conftest import ObraConOutline
from app.features.escritura.modelos import Trabajo
from app.features.obra.modelos import Obra


async def _trabajo(
    sesion: AsyncSession,
    plan: ObraConOutline,
    numero: int,
    estado: str,
    *,
    causa: str | None = None,
) -> Trabajo:
    capitulo = plan.capitulos[numero - 1]
    trabajo = Trabajo(
        obra_id=plan.obra.id,
        capitulo_id=capitulo.id,
        tipo="escribir_escena",
        estado=estado,
        run_id=f"cap{capitulo.id}-{estado}",
        causa_fallo=causa,
    )
    sesion.add(trabajo)
    await sesion.flush()
    return trabajo


async def _integrar_hasta(sesion: AsyncSession, plan: ObraConOutline, ultimo: int) -> None:
    for numero in range(1, ultimo + 1):
        await _trabajo(sesion, plan, numero, "INTEGRADA")


def test_una_obra_sin_outline_dice_sin_outline(cliente, obra: Obra) -> None:
    respuesta = cliente.get(f"/obras/{obra.id}/novela")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "obra_id": obra.id,
        "total": 0,
        "integrados": 0,
        "en_curso": None,
        "estado": "sin_outline",
        "motivo": None,
    }


async def test_con_un_capitulo_en_vuelo_dice_escribiendo_y_cual(
    cliente, sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    await _integrar_hasta(sesion, obra_con_outline, 3)
    await _trabajo(sesion, obra_con_outline, 4, "ESCRIBIENDO")

    respuesta = cliente.get(f"/obras/{obra_con_outline.obra.id}/novela")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "obra_id": obra_con_outline.obra.id,
        "total": 10,
        "integrados": 3,
        "en_curso": 4,
        "estado": "escribiendo",
        "motivo": None,
    }


def test_recien_planificada_y_sin_trabajo_todavia_dice_escribiendo_sin_capitulo(
    cliente, obra_con_outline: ObraConOutline
) -> None:
    """Entre el 202 de `POST` y el primer trabajo abierto, o antes de lanzarla.

    El contrato no tiene un quinto estado: hay capitulos, ninguno fallo y
    ninguno se esta escribiendo todavia. `en_curso` va a nulo porque nadie esta
    escribiendo ese capitulo -- inventarlo seria mentir por `en_curso`.
    """
    cuerpo = cliente.get(f"/obras/{obra_con_outline.obra.id}/novela").json()

    assert cuerpo["estado"] == "escribiendo"
    assert cuerpo["total"] == 10
    assert cuerpo["integrados"] == 0
    assert cuerpo["en_curso"] is None
    assert cuerpo["motivo"] is None


async def test_con_los_diez_integrados_dice_terminada(
    cliente, sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    await _integrar_hasta(sesion, obra_con_outline, 10)

    cuerpo = cliente.get(f"/obras/{obra_con_outline.obra.id}/novela").json()

    assert cuerpo == {
        "obra_id": obra_con_outline.obra.id,
        "total": 10,
        "integrados": 10,
        "en_curso": None,
        "estado": "terminada",
        "motivo": None,
    }


@pytest.mark.parametrize("estado", ["ESCALADA", "FALLIDA", "CANCELADA"])
async def test_un_capitulo_cerrado_sin_integrar_detiene_la_novela_y_dice_por_que(
    cliente, sesion: AsyncSession, obra_con_outline: ObraConOutline, estado: str
) -> None:
    """`escribir_novela` para en cuanto un capitulo no queda `INTEGRADA`.

    Los tres finales no exitosos de `maquina.ESTADOS_TERMINALES`. Si la consulta
    dijera «escribiendo», el navegador esperaria para siempre a un bucle que ya
    salio.
    """
    await _integrar_hasta(sesion, obra_con_outline, 6)
    await _trabajo(sesion, obra_con_outline, 7, estado, causa="defecto CAN-01 sin reparar")

    cuerpo = cliente.get(f"/obras/{obra_con_outline.obra.id}/novela").json()

    assert cuerpo["estado"] == "detenida"
    assert cuerpo["total"] == 10
    assert cuerpo["integrados"] == 6
    assert cuerpo["en_curso"] is None
    assert estado in cuerpo["motivo"]
    assert "7" in cuerpo["motivo"]
    assert "defecto CAN-01 sin reparar" in cuerpo["motivo"]


async def test_un_fallido_ya_relanzado_no_detiene_la_novela(
    cliente, sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """Manda el **ultimo** trabajo del capitulo, no cualquiera.

    Un `FALLIDA` se relanza como trabajo nuevo (§3.6): mientras el relanzado
    esta vivo, la novela sigue escribiendose aunque el viejo siga en la tabla.
    """
    await _integrar_hasta(sesion, obra_con_outline, 2)
    await _trabajo(sesion, obra_con_outline, 3, "FALLIDA", causa="caida del proceso")
    await _trabajo(sesion, obra_con_outline, 3, "VALIDANDO")

    cuerpo = cliente.get(f"/obras/{obra_con_outline.obra.id}/novela").json()

    assert cuerpo["estado"] == "escribiendo"
    assert cuerpo["en_curso"] == 3
    assert cuerpo["motivo"] is None


def test_una_obra_que_no_existe_es_404(cliente) -> None:
    assert cliente.get("/obras/9999/novela").status_code == 404


def test_la_consulta_de_la_novela_esta_en_el_openapi(cliente) -> None:
    """RI-13: el cliente del frontend se genera de aqui."""
    openapi = cliente.get("/openapi.json").json()

    assert "get" in openapi["paths"]["/obras/{obra_id}/novela"]
    campos = openapi["components"]["schemas"]["EstadoDeLaNovela"]["properties"]
    assert set(campos) == {"obra_id", "total", "integrados", "en_curso", "estado", "motivo"}
