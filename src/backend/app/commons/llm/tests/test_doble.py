import pytest

from app.commons.llm.doble import DobleDeterminista, RespuestaNoPreparada


async def test_el_doble_devuelve_lo_preparado_y_cuenta_las_llamadas():
    doble = DobleDeterminista({"hola": "adios"})
    assert await doble.completar("hola", semilla=1) == "adios"
    assert doble.llamadas == [("hola", 1)]


async def test_un_prompt_no_preparado_falla_en_vez_de_inventar():
    doble = DobleDeterminista({})
    with pytest.raises(RespuestaNoPreparada):
        await doble.completar("cualquier cosa", semilla=1)
