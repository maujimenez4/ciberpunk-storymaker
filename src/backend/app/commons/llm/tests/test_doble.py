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


async def test_el_doble_registra_que_modelo_se_le_pidio():
    """P-02 se prueba sobre el doble o no se prueba: la suite no llama al
    proveedor (CA-4). Que el juez pida Opus y el Escritor Haiku tiene que ser
    **observable sin red**, o la separacion vuelve a ser una intencion.

    `llamadas` sigue siendo de pares y el modelo va aparte a proposito: tres
    features desempaquetan esa lista de dos en dos, y ensancharla las rompe sin
    que ninguna gane nada."""
    doble = DobleDeterminista({"juzga": "un defecto"})

    await doble.completar("juzga esto", semilla=1, modelo="claude-opus-5")
    await doble.completar("juzga aquello", semilla=2)

    assert doble.llamadas == [("juzga esto", 1), ("juzga aquello", 2)]
    assert doble.modelos == ["claude-opus-5", None]
