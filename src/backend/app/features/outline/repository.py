"""Acceso a datos de la feature `outline`."""

import sqlite3
import uuid
from pathlib import Path

from app.commons.errors import RecursoNoEncontrado
from app.features.outline.schemas import Outline, Ubicacion


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

    def ubicacion_de(self, escena_id: str) -> Ubicacion:
        """De la escena a la obra, subiendo por capitulo y parte.

        Falla si no la encuentra en vez de devolver campos vacios: una
        ubicacion a medias produce una capa constitucional en blanco, y eso se
        detecta mucho despues, en RF-CTX-14, y en otro sitio.
        """
        with self._conexion() as conexion:
            fila = conexion.execute(
                "SELECT e.escena_id, p.obra_id, p.parte_id, c.capitulo_id,"
                " c.numero, c.titulo, p.funcion_estructural, e.orden_discurso"
                " FROM escena e"
                " JOIN capitulo c ON c.capitulo_id = e.capitulo_id"
                " JOIN parte p ON p.parte_id = c.parte_id"
                " WHERE e.escena_id = ?",
                (escena_id,),
            ).fetchone()
        if fila is None:
            raise RecursoNoEncontrado("Escena", escena_id)
        return Ubicacion(
            escena_id=fila[0],
            obra_id=fila[1],
            parte_id=fila[2],
            capitulo_id=fila[3],
            capitulo_numero=fila[4],
            capitulo_titulo=fila[5],
            funcion_estructural=fila[6],
            orden_discurso=fila[7],
        )
