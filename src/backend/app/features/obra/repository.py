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
from app.features.obra.biblia import Biblia, VersionDeBiblia
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

    def crear_version_de_biblia(
        self, obra_id: str, biblia: Biblia, creada_en: datetime
    ) -> VersionDeBiblia:
        """RD-12 y RF-OBR-03: version nueva, nunca edicion en sitio."""
        version_id = f"vobra-{uuid.uuid4().hex[:12]}"
        with self._conexion() as conexion:
            siguiente = conexion.execute(
                "SELECT COALESCE(MAX(numero), 0) + 1 FROM version_obra"
                " WHERE obra_id = ?",
                (obra_id,),
            ).fetchone()[0]
            conexion.execute(
                "INSERT INTO version_obra (version_obra_id, obra_id, numero, biblia,"
                " creada_en) VALUES (?,?,?,?,?)",
                (
                    version_id,
                    obra_id,
                    siguiente,
                    biblia.model_dump_json(),
                    creada_en.isoformat(),
                ),
            )
        return self.leer_version(version_id)

    def leer_version(self, version_obra_id: str) -> VersionDeBiblia:
        with self._conexion() as conexion:
            fila = conexion.execute(
                "SELECT version_obra_id, obra_id, numero, biblia FROM version_obra"
                " WHERE version_obra_id = ?",
                (version_obra_id,),
            ).fetchone()
        if fila is None:
            raise RecursoNoEncontrado("VersionDeObra", version_obra_id)
        return VersionDeBiblia(
            version_obra_id=fila[0],
            obra_id=fila[1],
            numero=fila[2],
            biblia=Biblia.model_validate_json(fila[3]),
        )

    def versiones_de(self, obra_id: str) -> list[VersionDeBiblia]:
        with self._conexion() as conexion:
            ids = [
                f[0]
                for f in conexion.execute(
                    "SELECT version_obra_id FROM version_obra WHERE obra_id = ?"
                    " ORDER BY numero",
                    (obra_id,),
                )
            ]
        return [self.leer_version(i) for i in ids]
