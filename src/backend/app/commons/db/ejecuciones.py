"""El registro de cada llamada al modelo (RI-14, RD-06; `architecture.md` §9).

Una fila por llamada, con todo lo que hace falta para **auditar** esa ejecución:
qué prompt se usó y con qué hash, qué versión de biblia, qué IDs se recuperaron,
qué modelo y con qué parámetros, cuántos tokens por capa y cuánto costó.

Desde D-02 ya no se puede prometer *reproducir* el paquete —la ordenación
semántica tiene varianza—, pero sí **auditar**: con los IDs recuperados y el
desglose se sabe exactamente qué se envió, aunque un ensamblado nuevo del mismo
estado devolviera otro orden. Esa distinción está en RF-CTX-13 y es la razón de
que `ids_recuperados` sea obligatorio.
"""

import json
import sqlite3
import uuid
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.commons.domain import Reloj


class RegistroDeEjecucion(BaseModel):
    """Lo que RI-14 exige, campo a campo."""

    model_config = ConfigDict(frozen=True)

    run_id: str = Field(min_length=1)
    escena_id: str | None
    prompt_id: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    prompt_hash: str = Field(min_length=1)
    version_obra_id: str | None
    ids_recuperados: list[str]
    modelo: str = Field(min_length=1)
    parametros: dict[str, object]
    semilla: int | None
    tokens_por_capa: dict[str, int]
    coste: float | None
    veredicto: str | None


class RepositorioDeEjecuciones:
    def __init__(self, ruta: Path | str) -> None:
        self.ruta = str(ruta)

    def registrar(self, registro: RegistroDeEjecucion, reloj: Reloj) -> str:
        ejecucion_id = f"ejec-{uuid.uuid4().hex[:12]}"
        with sqlite3.connect(self.ruta) as conexion:
            conexion.execute("PRAGMA foreign_keys=ON")
            conexion.execute(
                "INSERT INTO ejecucion (ejecucion_id, run_id, escena_id, prompt_id,"
                " prompt_version, prompt_hash, version_obra_id, ids_recuperados,"
                " modelo, parametros, semilla, tokens_por_capa, coste, veredicto,"
                " creada_en) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    ejecucion_id,
                    registro.run_id,
                    registro.escena_id,
                    registro.prompt_id,
                    registro.prompt_version,
                    registro.prompt_hash,
                    registro.version_obra_id,
                    json.dumps(registro.ids_recuperados),
                    registro.modelo,
                    json.dumps(registro.parametros),
                    registro.semilla,
                    json.dumps(registro.tokens_por_capa),
                    registro.coste,
                    registro.veredicto,
                    reloj.ahora().isoformat(),
                ),
            )
        return ejecucion_id

    def leer(self, ejecucion_id: str) -> RegistroDeEjecucion:
        with sqlite3.connect(self.ruta) as conexion:
            fila = conexion.execute(
                "SELECT run_id, escena_id, prompt_id, prompt_version, prompt_hash,"
                " version_obra_id, ids_recuperados, modelo, parametros, semilla,"
                " tokens_por_capa, coste, veredicto FROM ejecucion"
                " WHERE ejecucion_id = ?",
                (ejecucion_id,),
            ).fetchone()
        if fila is None:
            from app.commons.errors import RecursoNoEncontrado

            raise RecursoNoEncontrado("Ejecucion", ejecucion_id)
        return RegistroDeEjecucion(
            run_id=fila[0],
            escena_id=fila[1],
            prompt_id=fila[2],
            prompt_version=fila[3],
            prompt_hash=fila[4],
            version_obra_id=fila[5],
            ids_recuperados=json.loads(fila[6]),
            modelo=fila[7],
            parametros=json.loads(fila[8]),
            semilla=fila[9],
            tokens_por_capa=json.loads(fila[10]),
            coste=fila[11],
            veredicto=fila[12],
        )

    def de_run(self, run_id: str) -> list[str]:
        """Todas las llamadas de un trabajo. El `run_id` las correlaciona (§3.2)."""
        with sqlite3.connect(self.ruta) as conexion:
            return [
                f[0]
                for f in conexion.execute(
                    "SELECT ejecucion_id FROM ejecucion WHERE run_id = ?"
                    " ORDER BY creada_en, rowid",
                    (run_id,),
                )
            ]
