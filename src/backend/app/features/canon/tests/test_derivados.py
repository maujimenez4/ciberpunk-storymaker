"""RF-MEM-03 y RF-MEM-05: lo derivado se deriva, y se deriva de lo que el Extractor escribe.

La Tarea 2 ya probo que `estado_en_t` y `cronologia` son vistas y que
reconstruyen el ledger cuando alguien mete los eventos a mano. Lo que falta, y
es lo que se prueba aqui, es que **la ruta real** —una extraccion consolidada—
produce un ledger del que esas dos vistas salen igual: si el servicio perdiera
los `testigos[]` o el `tiempo_historia` por el camino, el esquema seguiria
correcto y la derivacion seguiria vacia.

**Que se deriva hoy, dicho aqui y no en el informe:** `estado_en_t` deriva
«quien sabe que», que es el mecanismo de la regla de dominio 2. La parte movil
del `Personaje` de `definitions.md` §4.3 —ubicacion, estado emocional, heridas—
**no se deriva todavia**, porque no hay tabla `personaje` de la que colgarla.
Lo anoto la Tarea 2 en Desviaciones y aqui se trabaja con lo que hay.
"""

from sqlalchemy import select, text

from app.features.canon.modelos import Evento
from app.features.canon.schemas import EventoExtraido, Extraccion
from app.features.canon.service import consolidar_escena

EXTRACCION = Extraccion(
    eventos=[
        EventoExtraido(
            descripcion="Nadia encuentra la carta",
            tiempo_historia="dia 1, manana",
            lugar="El invernadero",
            participantes=["Nadia"],
            testigos=["Nadia", "Teo"],
        ),
        EventoExtraido(
            descripcion="Teo quema la carta",
            tiempo_historia="dia 1, noche",
            lugar="La cocina",
            participantes=["Teo"],
            testigos=["Teo"],
            excluye=["la carta"],
        ),
    ],
    resumen="Aparece y desaparece la carta.",
)


async def _consolidar(sesion, obra_con_outline):
    return await consolidar_escena(
        sesion,
        obra_id=obra_con_outline.obra.id,
        escena_id=obra_con_outline.escena.id,
        capitulo_id=obra_con_outline.capitulos[0].id,
        extraccion=EXTRACCION,
    )


async def test_quien_sabe_que_sale_del_ledger_que_escribe_el_extractor(sesion, obra_con_outline):
    """Regla de dominio 3: el estado en T se **deriva**, no se escribe.

    Se reconstruye desde los eventos y se compara con la vista. Si alguien
    convirtiera `estado_en_t` en una tabla que el servicio rellena, los dos
    lados dejarian de coincidir.
    """
    await _consolidar(sesion, obra_con_outline)

    eventos = (await sesion.execute(select(Evento).order_by(Evento.id))).scalars().all()
    esperado = sorted((ev.obra_id, testigo, ev.id) for ev in eventos for testigo in ev.testigos)

    filas = await sesion.execute(text("SELECT obra_id, personaje, evento_id FROM estado_en_t"))
    assert sorted(filas.all()) == esperado
    assert len(esperado) == 3


async def test_el_sabe_desde_toma_el_orden_de_discurso_de_la_escena(sesion, obra_con_outline):
    """Regla de dominio 2: sin `sabe_desde` no hay forma de comprobarla."""
    await _consolidar(sesion, obra_con_outline)

    filas = await sesion.execute(text("SELECT DISTINCT sabe_desde FROM estado_en_t"))
    assert filas.scalars().all() == [obra_con_outline.escena.orden_discurso]


async def test_la_cronologia_conserva_momento_lugar_y_presentes(sesion, obra_con_outline):
    """RF-MEM-03. Es la entrada del validador formal, que la lee entera."""
    await _consolidar(sesion, obra_con_outline)

    filas = await sesion.execute(
        text("SELECT tiempo_historia, lugar, participantes FROM cronologia ORDER BY evento_id")
    )
    assert filas.all() == [
        ("dia 1, manana", "El invernadero", '["Nadia"]'),
        ("dia 1, noche", "La cocina", '["Teo"]'),
    ]


async def test_el_evento_conserva_a_quien_excluye(sesion, obra_con_outline):
    """`definitions.md` §4.5: sin `excluye[]`, «que nadie reaparezca despues de
    morir» no es comprobable, es un juicio de lectura. El servicio no puede
    tirarlo por el camino."""
    await _consolidar(sesion, obra_con_outline)

    filas = await sesion.execute(text("SELECT excluye FROM cronologia ORDER BY evento_id"))
    assert filas.scalars().all() == ["[]", '["la carta"]']
