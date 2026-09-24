"""El esquema de `canon`: el ledger, lo que de el se deriva, y lo que no se deriva."""

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, OperationalError

from app.commons.db.base import Base
from app.features.canon.modelos import (
    Embedding,
    Evento,
    HechoUsadoEn,
    HiloNarrativo,
    Plantado,
    ResumenCapitulo,
)

# --------------------------------------------------------------------------
# El ledger es append-only, y lo es en el esquema (RF-MEM-05)
# --------------------------------------------------------------------------


async def test_el_ledger_rechaza_actualizar_un_evento(sesion, obra_con_outline):
    """Una pared, no una puerta con cartel: el disparador vive en la base."""
    evento = _evento(obra_con_outline)
    sesion.add(evento)
    await sesion.flush()

    evento.descripcion = "En realidad no paso"
    with pytest.raises(IntegrityError, match="append-only"):
        await sesion.flush()


async def test_el_ledger_rechaza_borrar_un_evento(sesion, obra_con_outline):
    """Un ledger del que se puede quitar una fila no acredita nada."""
    evento = _evento(obra_con_outline)
    sesion.add(evento)
    await sesion.flush()

    await sesion.delete(evento)
    with pytest.raises(IntegrityError, match="append-only"):
        await sesion.flush()


# --------------------------------------------------------------------------
# `estado_en_t` y la cronologia son vistas derivadas (RF-MEM-03, RF-MEM-05)
# --------------------------------------------------------------------------


async def test_estado_en_t_y_cronologia_no_son_tablas(sesion):
    """No hay repositorio que escriba sobre ellas porque no hay tabla que mapear.

    Se comprueba por los dos lados: no estan en `Base.metadata` -- de donde
    sale toda tabla del proyecto y toda migracion -- y en la base son `view`.
    """
    assert "estado_en_t" not in Base.metadata.tables
    assert "cronologia" not in Base.metadata.tables

    filas = await sesion.execute(
        text("SELECT name, type FROM sqlite_master WHERE name IN ('estado_en_t', 'cronologia')")
    )
    assert sorted(filas.all()) == [("cronologia", "view"), ("estado_en_t", "view")]


@pytest.mark.parametrize("vista", ["estado_en_t", "cronologia"])
async def test_nadie_puede_escribir_sobre_las_vistas(sesion, vista: str):
    """RF-MEM-05: «nunca se editan». Intentarlo es un error de la base.

    El `match` no es adorno: sin el, este test pasaria tambien si la vista **no
    existiera** -- SQLite diria «no such table» y `pytest.raises` se daria por
    satisfecho. Es el falso verde que se vio en el rojo de esta tarea.
    """
    with pytest.raises(OperationalError, match="because it is a view"):
        await sesion.execute(text(f"INSERT INTO {vista} (obra_id) VALUES (1)"))


async def test_estado_en_t_se_reconstruye_desde_el_ledger(sesion, obra_con_outline):
    """`definitions.md` §4.5: de `testigos[]` se deriva quien puede saber el hecho.

    El test **reconstruye** la vista desde los eventos y compara. Si alguien
    convirtiera la vista en una tabla que se escribe a mano, los dos lados
    dejarian de coincidir.
    """
    sesion.add_all(
        [
            _evento(obra_con_outline, testigos=["Nadia", "Teo"]),
            _evento(obra_con_outline, testigos=["Teo"], descripcion="Teo quema la carta"),
        ]
    )
    await sesion.flush()

    eventos = (await sesion.execute(select(Evento).order_by(Evento.id))).scalars().all()
    esperado = sorted((ev.obra_id, testigo, ev.id) for ev in eventos for testigo in ev.testigos)

    filas = await sesion.execute(
        text("SELECT obra_id, personaje, evento_id FROM estado_en_t ORDER BY evento_id, personaje")
    )
    assert sorted(filas.all()) == esperado


async def test_la_cronologia_se_reconstruye_desde_el_ledger(sesion, obra_con_outline):
    """RF-MEM-03: eventos con momento, lugar y presentes, derivados del ledger."""
    sesion.add(_evento(obra_con_outline))
    await sesion.flush()

    evento = (await sesion.execute(select(Evento))).scalars().one()
    filas = await sesion.execute(
        text("SELECT evento_id, tiempo_historia, lugar FROM cronologia ORDER BY evento_id")
    )
    assert filas.all() == [(evento.id, evento.tiempo_historia, evento.lugar)]


# --------------------------------------------------------------------------
# Hilos, plantados, uso de hechos, resumenes e indice
# --------------------------------------------------------------------------


async def test_un_estado_de_hilo_que_no_existe_no_entra(sesion, obra_con_outline):
    """`definitions.md` §4.5: abierto, pagado o vencido. Ninguno mas."""
    sesion.add(_hilo(obra_con_outline, estado="a medias"))
    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_un_hilo_pagado_declara_la_escena_que_lo_cierra(sesion, obra_con_outline):
    """Un hilo «pagado» sin escena de cierre es una promesa dada por cumplida sin cumplirla."""
    sesion.add(_hilo(obra_con_outline, estado="pagado", escena_de_cierre=None))
    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_una_importancia_de_plantado_que_no_existe_no_entra(sesion, obra_con_outline):
    """`definitions.md` §4.5: alta, media o decorativa."""
    sesion.add(
        Plantado(
            obra_id=obra_con_outline.obra.id,
            descripcion="La llave del invernadero",
            escena_de_origen=obra_con_outline.escena.id,
            importancia="urgente",
        )
    )
    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_un_hecho_se_usa_en_varios_capitulos(sesion, obra_con_outline):
    """RF-MEM-02: la relacion hacia adelante, sin la cual no se sabe que regenerar."""
    sesion.add_all(
        [
            HechoUsadoEn(hecho_canon_id=obra_con_outline.hecho_canon.id, capitulo_id=c.id)
            for c in obra_con_outline.capitulos[:3]
        ]
    )
    await sesion.flush()

    usos = (await sesion.execute(select(HechoUsadoEn))).scalars().all()
    assert sorted(u.capitulo_id for u in usos) == sorted(
        c.id for c in obra_con_outline.capitulos[:3]
    )


async def test_el_uso_de_un_hecho_en_un_capitulo_no_se_repite(sesion, obra_con_outline):
    """Contarlo dos veces sobre-reportaria que capitulos hay que rehacer."""
    capitulo = obra_con_outline.capitulos[0]
    sesion.add_all(
        [
            HechoUsadoEn(hecho_canon_id=obra_con_outline.hecho_canon.id, capitulo_id=capitulo.id),
            HechoUsadoEn(hecho_canon_id=obra_con_outline.hecho_canon.id, capitulo_id=capitulo.id),
        ]
    )
    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_un_capitulo_tiene_un_solo_resumen(sesion, obra_con_outline):
    """RF-MEM-04: el resumen se deriva del texto aprobado; dos serian dos verdades."""
    capitulo = obra_con_outline.capitulos[0]
    sesion.add_all(
        [
            ResumenCapitulo(capitulo_id=capitulo.id, texto="Nadia descubre la carta."),
            ResumenCapitulo(capitulo_id=capitulo.id, texto="Otra sintesis."),
        ]
    )
    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_un_embedding_guarda_su_vector_como_blob(sesion, obra_con_outline):
    """`architecture.md` §5.5: `vec0` o BLOB + NumPy, detras de `VectorStore`."""
    sesion.add(
        Embedding(
            obra_id=obra_con_outline.obra.id,
            escena_id=obra_con_outline.escena.id,
            fragmento="La puerta estaba abierta",
            vector=b"\x00\x01\x02\x03",
            dimension=1,
            modelo="doble",
        )
    )
    await sesion.flush()

    guardado = (await sesion.execute(select(Embedding))).scalars().one()
    assert guardado.vector == b"\x00\x01\x02\x03"


def _evento(obra_con_outline, **cambios) -> Evento:
    campos = {
        "obra_id": obra_con_outline.obra.id,
        "escena_id": obra_con_outline.escena.id,
        "descripcion": "Nadia encuentra la carta",
        "tiempo_historia": "dia 2, tarde",
        "lugar": "El invernadero",
        "participantes": ["Nadia"],
        "testigos": ["Nadia"],
    }
    campos.update(cambios)
    return Evento(**campos)


def _hilo(obra_con_outline, **cambios) -> HiloNarrativo:
    campos = {
        "obra_id": obra_con_outline.obra.id,
        "pregunta": "Quien escribio la carta?",
        "escena_de_apertura": obra_con_outline.escena.id,
        "estado": "abierto",
    }
    campos.update(cambios)
    return HiloNarrativo(**campos)
