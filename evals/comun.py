"""Lo que comparten los tres scripts de evals: rutas, manifiesto y base de datos.

Solo biblioteca estandar a proposito: anadir una dependencia exige preguntar
(`CLAUDE.md` §3 regla 7) y para hablar HTTP y leer SQLite no hace falta.
"""

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent.parent
EVALS = RAIZ / "evals"
BRIEFS = EVALS / "briefs"
RESULTADOS = EVALS / "resultados"
CORRIDAS = RESULTADOS / "corridas.json"
TABLA = RESULTADOS / "tabla.md"

# Para poder importar `app` (brief y rubrica) al correr `python evals/x.py`.
if str(RAIZ / "src" / "backend") not in sys.path:
    sys.path.insert(0, str(RAIZ / "src" / "backend"))


def ruta_db(explicita: str | None = None) -> Path:
    """La misma que usa el backend: `STORYMAKER_DB`, o `storymaker.db` en la raiz."""
    if explicita:
        return Path(explicita)
    return Path(os.environ.get("STORYMAKER_DB", str(RAIZ / "storymaker.db")))


def conectar(ruta: Path, *, solo_lectura: bool = True) -> sqlite3.Connection:
    """Solo lectura por defecto: la tabla y el corredor no escriben en la obra."""
    if not ruta.exists():
        raise SystemExit(f"No existe la base {ruta}. Arranca el backend o pasa --db.")
    modo = "ro" if solo_lectura else "rw"
    conexion = sqlite3.connect(f"file:{ruta.as_posix()}?mode={modo}", uri=True, timeout=30)
    conexion.row_factory = sqlite3.Row
    return conexion


def manifiesto() -> list[dict[str, Any]]:
    datos = json.loads((BRIEFS / "manifiesto.json").read_text(encoding="utf-8"))
    return sorted(datos["briefs"], key=lambda b: b["orden_de_prioridad"])


def brief(entrada: dict[str, Any]) -> dict[str, Any]:
    cargado: dict[str, Any] = json.loads((BRIEFS / entrada["fichero"]).read_text(encoding="utf-8"))
    return cargado


def leer_corridas(ruta: Path = CORRIDAS) -> dict[str, Any]:
    if not ruta.exists():
        return {"corridas": {}}
    cargado: dict[str, Any] = json.loads(ruta.read_text(encoding="utf-8"))
    return cargado


def guardar_corridas(datos: dict[str, Any], ruta: Path = CORRIDAS) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(".tmp")
    temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    temporal.replace(ruta)
