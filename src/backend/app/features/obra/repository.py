"""Acceso a datos de la feature `obra`.

Lo unico que conoce la forma de las tablas. Fuera de aqui circulan modelos de
`schemas.py`, nunca filas (RI-12).
"""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from app.commons.domain import NivelDeCalor
from app.commons.errors import RecursoNoEncontrado
from app.features.obra.schemas import Brief, ObraCreada

SERIE_IMPLICITA = "serie-unica"


class RepositorioDeObras:
    def __init__(self, ruta: Path | str) -> None:
        self.ruta = str(ruta)

    def _conexion(self) -> sqlite3.Connection:
        conexion = sqlite3.connect(self.ruta)
        conexion.execute("PRAGMA foreign_keys=ON")
        return conexion

    def crear(self, brief: Brief, creada_en: datetime) -> ObraCreada:
        obra_id = f"obra-{uuid.uuid4().hex[:12]}"
        with self._conexion() as conexion:
            # RD-11: el canon cuelga de la serie desde el primer dia. La v1
            # maneja una serie implicita, pero la fila existe.
            conexion.execute(
                "INSERT OR IGNORE INTO serie (serie_id, titulo) VALUES (?, ?)",
                (SERIE_IMPLICITA, "serie implicita de la v1"),
            )
            conexion.execute(
                "INSERT INTO obra (obra_id, serie_id, titulo, logline, premisa, tema,"
                " genero, subgenero, extension_objetivo, promesa_de_apertura,"
                " persona, tiempo_verbal, esquema_de_pov, nivel_de_calor)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    obra_id,
                    SERIE_IMPLICITA,
                    brief.titulo,
                    brief.logline,
                    brief.premisa,
                    brief.tema,
                    brief.genero,
                    brief.subgenero,
                    brief.extension_objetivo,
                    brief.promesa_de_apertura,
                    brief.persona,
                    brief.tiempo_verbal,
                    brief.esquema_de_pov,
                    brief.nivel_de_calor.value,
                ),
            )
        return self.leer(obra_id)

    def leer(self, obra_id: str) -> ObraCreada:
        with self._conexion() as conexion:
            fila = conexion.execute(
                "SELECT obra_id, serie_id, titulo, persona, tiempo_verbal,"
                " esquema_de_pov, nivel_de_calor FROM obra WHERE obra_id = ?",
                (obra_id,),
            ).fetchone()
        if fila is None:
            raise RecursoNoEncontrado("Obra", obra_id)
        return ObraCreada(
            obra_id=fila[0],
            serie_id=fila[1],
            titulo=fila[2],
            persona=fila[3],
            tiempo_verbal=fila[4],
            esquema_de_pov=fila[5],
            nivel_de_calor=NivelDeCalor(fila[6]),
        )
