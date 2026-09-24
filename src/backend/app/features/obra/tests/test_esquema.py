import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.features.obra.modelos import HechoCanon, Obra, PalabraProhibida, Serie


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


async def test_una_serie_puede_existir_y_una_obra_pertenecer_a_ella(sesion):
    """RD-04: `Serie` contemplada desde la migracion inicial.

    No se anade por lo que hace hoy -- hoy no hace nada -- sino por lo que
    cuesta anadirla tarde: `definitions.md` §4.1 avisa de que si existe, el
    canon se comparte entre obras **desde el primer dia**, y meterla despues
    obliga a reescribir referencias que ya apuntan a otro sitio.
    """
    serie = Serie(titulo="Los dias de Cadiz", canon_compartido=True)
    sesion.add(serie)
    await sesion.flush()

    primera = Obra(
        titulo="Uno", genero="romance", tono="calido", nivel_de_calor=2, serie_id=serie.id
    )
    segunda = Obra(
        titulo="Dos", genero="romance", tono="calido", nivel_de_calor=2, serie_id=serie.id
    )
    sesion.add_all([primera, segunda])
    await sesion.flush()

    assert primera.serie_id == segunda.serie_id == serie.id


async def test_una_obra_sin_serie_sigue_siendo_legitima(sesion):
    """La mayoria de las obras no son de ninguna serie: `serie_id` es nulo."""
    obra = Obra(titulo="Suelta", genero="romance", tono="calido", nivel_de_calor=2)
    sesion.add(obra)
    await sesion.flush()
    assert obra.serie_id is None


@pytest.mark.parametrize("origen", ["escena", "brief", "edicion_humana"])
async def test_los_tres_origenes_declarados_se_guardan(sesion, obra, origen: str):
    """`definitions.md` §4.5 declara el conjunto, y es cerrado."""
    escena = "esc-1" if origen == "escena" else None
    sesion.add(HechoCanon(obra_id=obra.id, enunciado="x", origen=origen, escena_de_origen=escena))
    await sesion.flush()


async def test_un_origen_que_no_existe_no_se_puede_guardar(sesion, obra):
    """Sin esto, `origen='cualquier_cosa'` entra y nadie lo para."""
    sesion.add(
        HechoCanon(obra_id=obra.id, enunciado="x", origen="inventado", escena_de_origen=None)
    )
    with pytest.raises(IntegrityError):
        await sesion.flush()
