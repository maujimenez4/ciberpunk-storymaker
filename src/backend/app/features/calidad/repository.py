"""Segmento repository de la feature `calidad` (architecture.md §5.1).

RD-14: la tabla `defecto` existia desde la migracion inicial y **nadie la
escribia**. Sin esto, RI-18 no puede cumplirse —el autor que recibe una escena
en `ESCALADA` necesita ver el codigo y la cita, no un contador— y la tasa de
defectos mal formados, que es hoy la unica senal que mide al Continuista
(`architecture.md` §9), no tiene de donde salir.

Se guardan **tambien los mal formados**, marcados como tales. Descartarlos
seria perder justo la senal que dice que el Continuista esta afirmando cosas que
no estan en el texto.
"""

import sqlite3
import uuid
from pathlib import Path

from app.features.calidad.defectos import Defecto


class RepositorioDeDefectos:
    def __init__(self, ruta: Path | str) -> None:
        self.ruta = str(ruta)

    def _conexion(self) -> sqlite3.Connection:
        conexion = sqlite3.connect(self.ruta)
        conexion.execute("PRAGMA foreign_keys=ON")
        return conexion

    def registrar(self, defectos: list[Defecto]) -> list[str]:
        """Devuelve los `defecto_id` en el mismo orden."""
        ids = [f"def-{uuid.uuid4().hex[:12]}" for _ in defectos]
        with self._conexion() as conexion:
            conexion.executemany(
                "INSERT INTO defecto (defecto_id, codigo, version_texto_id, cita,"
                " desplazamiento_inicio, desplazamiento_fin, hecho_canon_id,"
                " bien_formado) VALUES (?,?,?,?,?,?,?,?)",
                [
                    (
                        defecto_id,
                        defecto.codigo.value,
                        defecto.version_texto_id,
                        defecto.cita,
                        defecto.desplazamiento_inicio,
                        defecto.desplazamiento_fin,
                        defecto.hecho_canon_id,
                        defecto.bien_formado,
                    )
                    for defecto_id, defecto in zip(ids, defectos, strict=True)
                ],
            )
        return ids

    def de_version(self, version_texto_id: str) -> list[Defecto]:
        with self._conexion() as conexion:
            filas = conexion.execute(
                "SELECT codigo, version_texto_id, cita, desplazamiento_inicio,"
                " desplazamiento_fin, hecho_canon_id, bien_formado FROM defecto"
                " WHERE version_texto_id = ? ORDER BY rowid",
                (version_texto_id,),
            ).fetchall()
        return [
            Defecto(
                codigo=fila[0],
                version_texto_id=fila[1],
                cita=fila[2],
                desplazamiento_inicio=fila[3],
                desplazamiento_fin=fila[4],
                hecho_canon_id=fila[5],
                bien_formado=bool(fila[6]),
            )
            for fila in filas
        ]
