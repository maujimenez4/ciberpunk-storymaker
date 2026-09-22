"""Ensamblado del manuscrito (RF-MAN-01, RF-MAN-02; `architecture.md` §11).

Dos reglas, y la segunda es la que suele olvidarse:

**Se ensambla con las versiones vigentes, en `orden_discurso`.** No en
`tiempo_historia`: el manuscrito es lo que el lector lee, y una analepsis se lee
donde el autor la puso, no donde ocurrió. Los dos relojes se separaron
precisamente para poder decir esto sin ambigüedad (RF-ESC-05).

**Cada fragmento registra su autoría**: generado, editado o humano. Sin ese
registro no se puede responder a la pregunta que cualquier editorial hará —qué
parte de esto lo escribió una persona—, y reconstruirlo después es imposible
porque el texto no lo dice.
"""

import sqlite3
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class FragmentoDeManuscrito(BaseModel):
    model_config = ConfigDict(frozen=True)

    escena_id: str
    orden_discurso: int
    texto: str
    autoria: str


class Manuscrito(BaseModel):
    model_config = ConfigDict(frozen=True)

    obra_id: str
    fragmentos: list[FragmentoDeManuscrito]

    @property
    def texto(self) -> str:
        return "\n\n".join(f.texto for f in self.fragmentos)

    def autorias(self) -> dict[str, int]:
        """RF-MAN-02: cuántos fragmentos de cada procedencia."""
        cuenta: dict[str, int] = {}
        for fragmento in self.fragmentos:
            cuenta[fragmento.autoria] = cuenta.get(fragmento.autoria, 0) + 1
        return cuenta


class RepositorioDeManuscrito:
    def __init__(self, ruta: Path | str) -> None:
        self.ruta = str(ruta)

    def ensamblar(self, obra_id: str) -> Manuscrito:
        """Solo las versiones **vigentes** (RF-ESC-03), en orden de discurso.

        Una escena sin versión vigente simplemente no aparece: está planificada
        pero no escrita, y meterla vacía daría un manuscrito con huecos que
        parecen texto perdido.
        """
        with sqlite3.connect(self.ruta) as conexion:
            filas = conexion.execute(
                "SELECT e.escena_id, e.orden_discurso, v.texto, v.autoria"
                " FROM escena e"
                " JOIN version_texto v ON v.escena_id = e.escena_id AND v.vigente = 1"
                " JOIN capitulo c ON c.capitulo_id = e.capitulo_id"
                " JOIN parte p ON p.parte_id = c.parte_id"
                " WHERE p.obra_id = ?"
                " ORDER BY p.numero, c.numero, e.orden_discurso",
                (obra_id,),
            ).fetchall()
        return Manuscrito(
            obra_id=obra_id,
            fragmentos=[
                FragmentoDeManuscrito(
                    escena_id=f[0], orden_discurso=f[1], texto=f[2], autoria=f[3]
                )
                for f in filas
            ],
        )
