"""Acceso a datos de la feature `outline`."""

import sqlite3
import uuid
from pathlib import Path

from app.features.outline.schemas import Outline


class RepositorioDeOutline:
    def __init__(self, ruta: Path | str) -> None:
        self.ruta = str(ruta)

    def _conexion(self) -> sqlite3.Connection:
        conexion = sqlite3.connect(self.ruta)
        conexion.execute("PRAGMA foreign_keys=ON")
        return conexion

    def guardar(self, obra_id: str, outline: Outline) -> None:
        """En una transaccion: o entra el outline entero, o no entra nada.

        Medio outline guardado parece despues un outline pobre en vez de un
        fallo, y es el tipo de estado del que cuesta salir.
        """
        with self._conexion() as conexion:
            for parte in outline.partes:
                parte_id = f"parte-{uuid.uuid4().hex[:10]}"
                conexion.execute(
                    "INSERT INTO parte (parte_id, obra_id, numero,"
                    " funcion_estructural) VALUES (?,?,?,?)",
                    (parte_id, obra_id, parte.numero, parte.funcion_estructural),
                )
                for capitulo in parte.capitulos:
                    capitulo_id = f"cap-{uuid.uuid4().hex[:10]}"
                    conexion.execute(
                        "INSERT INTO capitulo (capitulo_id, parte_id, numero, titulo,"
                        " pov_dominante) VALUES (?,?,?,?,?)",
                        (
                            capitulo_id,
                            parte_id,
                            capitulo.numero,
                            capitulo.titulo,
                            capitulo.pov_dominante,
                        ),
                    )
                    for escena in capitulo.escenas:
                        conexion.execute(
                            "INSERT INTO escena (escena_id, capitulo_id,"
                            " orden_discurso, pov, lugar, objetivo_del_pov, obstaculo,"
                            " valor_entrada, valor_salida, beat_de_genero)"
                            " VALUES (?,?,?,?,?,?,?,?,?,?)",
                            (
                                f"esc-{uuid.uuid4().hex[:10]}",
                                capitulo_id,
                                escena.orden_discurso,
                                escena.pov,
                                escena.lugar,
                                escena.objetivo_del_pov,
                                escena.obstaculo,
                                escena.valor_entrada,
                                escena.valor_salida,
                                escena.beat_de_genero.value
                                if escena.beat_de_genero
                                else None,
                            ),
                        )

    def partes_de(self, obra_id: str) -> list[str]:
        with self._conexion() as conexion:
            return [
                f[0]
                for f in conexion.execute(
                    "SELECT parte_id FROM parte WHERE obra_id = ? ORDER BY numero",
                    (obra_id,),
                )
            ]
