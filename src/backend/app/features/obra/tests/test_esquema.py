import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.features.obra.modelos import HechoCanon, PalabraProhibida


@pytest.mark.parametrize("ambito", ["global", "obra", "brief"])
async def test_los_tres_ambitos_de_veto_se_pueden_guardar(sesion, obra, ambito: str):
    """RF-GUA-01: global, obra y brief. Ni uno mas ni uno menos."""
    sesion.add(PalabraProhibida(ambito=ambito, termino="sangre", obra_id=obra.id))
    await sesion.flush()
    guardadas = (await sesion.execute(select(PalabraProhibida))).scalars().all()
    assert [p.ambito for p in guardadas] == [ambito]


async def test_un_ambito_que_no_existe_no_se_puede_guardar(sesion, obra):
    sesion.add(PalabraProhibida(ambito="inventado", termino="x", obra_id=obra.id))
    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_un_hecho_de_escena_sin_escena_no_se_puede_guardar(sesion, obra):
    """Regla de dominio 4, la mitad que vive en la base de datos."""
    sesion.add(HechoCanon(obra_id=obra.id, enunciado="x", origen="escena", escena_de_origen=None))
    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_un_hecho_del_brief_con_escena_tampoco(sesion, obra):
    """La otra mitad: lo que nacio antes del texto no inventa una escena."""
    sesion.add(HechoCanon(obra_id=obra.id, enunciado="x", origen="brief", escena_de_origen="esc-1"))
    with pytest.raises(IntegrityError):
        await sesion.flush()
