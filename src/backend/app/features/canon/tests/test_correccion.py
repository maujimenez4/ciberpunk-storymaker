"""P-8 y R-5 (plan 5, T2): corregir sin editar, con llamador de produccion.

Ninguna prueba llama al proveedor (CA-4): aqui solo hay canon.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.conftest import ObraConOutline
from app.features.canon import (
    HechoDesconocido,
    HechoYaSustituido,
    corregir_por_peticion,
    origen_del_hecho,
)
from app.features.obra import HechoCanon


async def _hecho(
    sesion: AsyncSession, obra_id: int, *, origen: str, escena_de_origen: str | None
) -> HechoCanon:
    hecho = HechoCanon(
        obra_id=obra_id,
        entidad="perro",
        atributo="nombre",
        valor="Luna",
        origen=origen,
        escena_de_origen=escena_de_origen,
    )
    sesion.add(hecho)
    await sesion.flush()
    return hecho


async def test_no_se_corrige_un_hecho_que_ya_fue_sustituido(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """R-5. Corregir un hecho muerto ramifica la cadena de `sustituye_a`."""
    viejo = await _hecho(sesion, obra_con_outline.obra.id, origen="brief", escena_de_origen=None)
    await corregir_por_peticion(sesion, hecho_canon_id=viejo.id, nuevo_valor="Nala")

    with pytest.raises(HechoYaSustituido) as fallo:
        await corregir_por_peticion(sesion, hecho_canon_id=viejo.id, nuevo_valor="Lola")

    assert "Nala" in str(fallo.value)


async def test_el_hecho_que_sustituye_cita_al_viejo_y_no_declara_escena(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """Regla de dominio 4 y RF-PET-02: un hecho nuevo, que cita, sin escena."""
    viejo = await _hecho(
        sesion,
        obra_con_outline.obra.id,
        origen="escena",
        escena_de_origen=str(obra_con_outline.escena.id),
    )

    nuevo = await corregir_por_peticion(sesion, hecho_canon_id=viejo.id, nuevo_valor="Nala")

    assert nuevo.origen == "edicion_humana"
    assert nuevo.escena_de_origen is None
    assert nuevo.sustituye_a == viejo.id
    assert viejo.valor == "Luna", "corregir no edita"


async def test_corregir_un_hecho_que_no_existe(sesion: AsyncSession) -> None:
    with pytest.raises(HechoDesconocido):
        await corregir_por_peticion(sesion, hecho_canon_id=999_999, nuevo_valor="Nala")


async def test_el_origen_de_un_hecho_es_el_numero_de_su_capitulo(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """R-1: el del brief no tiene capitulo de origen; el de escena, el suyo."""
    del_brief = await _hecho(
        sesion, obra_con_outline.obra.id, origen="brief", escena_de_origen=None
    )
    de_escena = await _hecho(
        sesion,
        obra_con_outline.obra.id,
        origen="escena",
        escena_de_origen=str(obra_con_outline.escena.id),
    )

    assert await origen_del_hecho(sesion, hecho_canon_id=del_brief.id) is None
    assert await origen_del_hecho(sesion, hecho_canon_id=de_escena.id) == 1
