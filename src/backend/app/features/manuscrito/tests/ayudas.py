"""Ayudas compartidas por los tests de `manuscrito`."""

import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def cubrir_los_obligatorios(sesion: AsyncSession, obra_id: int) -> None:
    """Un hecho por elemento obligatorio, usado en el primer capitulo.

    Desde P-33 no se publica una novela a la que le falte un elemento del brief
    (regla de dominio 11), asi que toda fixture que publica tiene que cubrirlos.
    """
    crudo = (
        await sesion.execute(
            text("SELECT elementos_obligatorios FROM obra WHERE id = :o"), {"o": obra_id}
        )
    ).scalar_one()
    elementos = json.loads(crudo) if isinstance(crudo, str) else list(crudo or [])
    capitulo_id = (
        await sesion.execute(
            text("SELECT id FROM capitulo WHERE obra_id = :o ORDER BY numero LIMIT 1"),
            {"o": obra_id},
        )
    ).scalar_one()
    for elemento in elementos:
        hecho_id = (
            await sesion.execute(
                text(
                    "INSERT INTO hecho_canon (obra_id, entidad, atributo, valor, confianza, origen) "
                    "VALUES (:o, :e, 'aparece', 'si', 1.0, 'brief') RETURNING id"
                ),
                {"o": obra_id, "e": str(elemento)},
            )
        ).scalar_one()
        await sesion.execute(
            text("INSERT INTO hecho_usado_en (hecho_canon_id, capitulo_id) VALUES (:h, :c)"),
            {"h": hecho_id, "c": capitulo_id},
        )
    await sesion.flush()
