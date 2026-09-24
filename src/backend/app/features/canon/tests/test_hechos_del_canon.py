"""El grafo que el Continuista contrasta, leido del canon.

**Por que hacia falta.** P-17 metio al Continuista en el ciclo, pero
`CapituloAContrastar` pide `tuple[HechoDeCanon, ...]` y `features/canon` no
exportaba ninguna proyeccion de hechos: solo `leer_nombres_del_canon`. Sin
esto el Continuista contrastaria contra un **grafo vacio**, que es peor que no
llamarlo: **diria que todo esta bien**, y esa es la forma de fallo que este
repositorio lleva el dia entero cazando.
"""

from app.features.calidad import HechoDeCanon
from app.features.canon import leer_hechos_del_canon
from app.features.obra.modelos import HechoCanon, Obra


async def _hecho(sesion, obra, **campos) -> HechoCanon:
    hecho = HechoCanon(obra_id=obra.id, **campos)
    sesion.add(hecho)
    await sesion.flush()
    return hecho


async def test_un_hecho_del_brief_llega_sin_escena_de_origen(sesion, obra):
    """Regla de dominio 4: los de `origen: brief` no la tienen y **no deben
    inventarla**, porque existian antes del texto."""
    await _hecho(sesion, obra, entidad="Marta", atributo="ojos", valor="verdes", origen="brief")

    hechos = await leer_hechos_del_canon(sesion, obra_id=obra.id)

    assert len(hechos) == 1
    assert hechos[0].origen.value == "brief"
    assert hechos[0].escena_de_origen is None


async def test_un_hecho_de_escena_llega_con_la_suya(sesion, obra):
    await _hecho(
        sesion,
        obra,
        entidad="Luna",
        atributo="raza",
        valor="galgo",
        origen="escena",
        escena_de_origen="3",
    )

    (hecho,) = await leer_hechos_del_canon(sesion, obra_id=obra.id)

    assert hecho.escena_de_origen == "3"


async def test_un_hecho_sustituido_no_entra_en_el_grafo(sesion, obra):
    """**El caso que decide esta funcion.**

    Corregir no edita (§4.2): un hecho equivocado no se modifica, se registra
    otro que lo sustituye y cita al anterior. Si la lectura devolviera los dos,
    el Continuista veria «ojos verdes» y «ojos marrones» sobre la misma entidad
    y emitiria un `CAN-01` **por una correccion que el sistema hizo bien**.

    Se comprueba tambien lo contrario -que el nuevo si esta-, porque una
    funcion que devolviera la tupla vacia pasaria la primera mitad sola.
    """
    viejo = await _hecho(
        sesion, obra, entidad="Marta", atributo="ojos", valor="verdes", origen="brief"
    )
    await _hecho(
        sesion,
        obra,
        entidad="Marta",
        atributo="ojos",
        valor="marrones",
        origen="edicion_humana",
        sustituye_a=viejo.id,
    )

    valores = {h.valor for h in await leer_hechos_del_canon(sesion, obra_id=obra.id)}

    assert valores == {"marrones"}, f"el hecho sustituido sigue en el grafo: {valores}"


async def test_no_se_mezclan_las_obras(sesion, obra):
    """El grafo de una obra no puede traer hechos de otra: el Continuista
    marcaria como contradiccion un hecho que no es de esta novela."""
    otra = Obra(
        titulo="Otra",
        genero="romance",
        tono="calido",
        nivel_de_calor=1,
        elementos_obligatorios=["algo"],
    )
    sesion.add(otra)
    await sesion.flush()
    await _hecho(sesion, obra, entidad="Marta", atributo="ojos", valor="verdes", origen="brief")
    await _hecho(sesion, otra, entidad="Otro", atributo="ojos", valor="azules", origen="brief")

    hechos = await leer_hechos_del_canon(sesion, obra_id=obra.id)

    assert [h.entidad for h in hechos] == ["Marta"]


async def test_el_orden_es_estable(sesion, obra):
    """Dos lecturas del mismo canon dan la misma tupla. Sin esto, el paquete de
    contexto cambia entre ejecuciones y **el determinismo de §3.6 se pierde**
    sin que nada falle."""
    for entidad, atributo in (("Zoe", "pelo"), ("Ana", "ojos"), ("Ana", "altura")):
        await _hecho(sesion, obra, entidad=entidad, atributo=atributo, valor="x", origen="brief")

    primera = await leer_hechos_del_canon(sesion, obra_id=obra.id)
    segunda = await leer_hechos_del_canon(sesion, obra_id=obra.id)

    assert primera == segunda
    assert [(h.entidad, h.atributo) for h in primera] == [
        ("Ana", "altura"),
        ("Ana", "ojos"),
        ("Zoe", "pelo"),
    ]


async def test_lo_que_devuelve_es_la_proyeccion_y_no_la_fila(sesion, obra):
    """`calidad` se prueba sin base de datos, y una fila de SQLAlchemy arrastra
    su sesion detras. Lo que cruza la frontera es la proyeccion."""
    await _hecho(sesion, obra, entidad="Marta", atributo="ojos", valor="verdes", origen="brief")

    (hecho,) = await leer_hechos_del_canon(sesion, obra_id=obra.id)

    assert isinstance(hecho, HechoDeCanon)
