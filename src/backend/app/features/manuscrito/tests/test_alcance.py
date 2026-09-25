"""El alcance de una peticion (plan-5 T4): RF-PET-03, RF-PET-04, R-1 y R-3."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.conftest import ObraConOutline
from app.features.manuscrito import alcance_de_la_peticion


async def _usar(sesion: AsyncSession, obra: ObraConOutline, hecho_id: int, *numeros: int) -> None:
    for numero in numeros:
        await sesion.execute(
            text("INSERT INTO hecho_usado_en (hecho_canon_id, capitulo_id) VALUES (:h, :c)"),
            {"h": hecho_id, "c": obra.capitulos[numero - 1].id},
        )
    await sesion.flush()


async def test_un_hecho_del_brief_se_revalida_desde_el_principio(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """R-1. Sin escena de origen no hay ancla: se revalida la novela entera."""
    await _usar(sesion, obra_con_outline, obra_con_outline.hecho_canon.id, 3, 7)

    alcance = await alcance_de_la_peticion(
        sesion,
        obra_id=obra_con_outline.obra.id,
        hecho_canon_id=obra_con_outline.hecho_canon.id,
        desde=None,
    )

    assert alcance.desde is None
    assert alcance.a_regenerar == (3, 7)
    assert alcance.a_revalidar == tuple(range(1, 11))


async def test_se_revalida_desde_el_origen_y_no_desde_lo_regenerado(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """RF-PET-04. Nace en el 3 y se usa en el 7: se regenera el 7 y se revalida del 4 al 10."""
    await _usar(sesion, obra_con_outline, obra_con_outline.hecho_canon.id, 7)

    alcance = await alcance_de_la_peticion(
        sesion,
        obra_id=obra_con_outline.obra.id,
        hecho_canon_id=obra_con_outline.hecho_canon.id,
        desde=3,
    )

    assert alcance.a_regenerar == (7,)
    assert alcance.a_revalidar == (4, 5, 6, 7, 8, 9, 10)


async def test_un_hecho_que_no_usa_ningun_capitulo_no_regenera_nada(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """R-3. Ni error ni version vacia: alcance vacio."""
    alcance = await alcance_de_la_peticion(
        sesion,
        obra_id=obra_con_outline.obra.id,
        hecho_canon_id=obra_con_outline.hecho_canon.id,
        desde=None,
    )

    assert alcance.a_regenerar == ()
    assert alcance.vacio is True
