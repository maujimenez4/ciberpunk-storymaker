"""Las puntuaciones del juez, leidas de Langfuse: **hoy no estan en la base**.

`_juzgar` (escritura/service.py) las emite como *score* y no las persiste en
`puntuacion`; la tabla existe (plan 6 T2) y nadie escribe en ella con
`origen='juez'`. Hasta que T9 lo haga, la unica copia esta en Langfuse.

Nombre del score: `juez_con_rubrica.<criterio>`, con la justificacion en
`comment`. Sesion: `obra-<id>` (`commons/observabilidad/trazas.py`).

Credenciales **solo del entorno** (RF-OBS-07): `LANGFUSE_PUBLIC_KEY`,
`LANGFUSE_SECRET_KEY` y `LANGFUSE_HOST` (o `LANGFUSE_BASE_URL`). Sin ellas se
devuelve vacio y se avisa: la tabla sigue saliendo.
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

PREFIJO = "juez_con_rubrica."


def _get(ruta: str) -> Any:
    host = os.environ.get("LANGFUSE_HOST") or os.environ.get("LANGFUSE_BASE_URL")
    publica = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secreta = os.environ.get("LANGFUSE_SECRET_KEY")
    if not (host and publica and secreta):
        raise RuntimeError("faltan LANGFUSE_HOST/PUBLIC_KEY/SECRET_KEY en el entorno")
    peticion = urllib.request.Request(f"{host.rstrip('/')}{ruta}")
    credencial = base64.b64encode(f"{publica}:{secreta}".encode()).decode()
    peticion.add_header("Authorization", f"Basic {credencial}")
    with urllib.request.urlopen(peticion, timeout=60) as respuesta:
        return json.loads(respuesta.read().decode("utf-8"))


def puntuaciones_del_juez(obra_id: int) -> list[dict[str, Any]]:
    """Cada score del juez de la obra: criterio, valor, justificacion y traza."""
    try:
        sesion = _get(f"/api/public/sessions/obra-{obra_id}")
        salida = []
        for traza in sesion.get("traces", []):
            detalle = _get(f"/api/public/traces/{traza['id']}")
            for score in detalle.get("scores", []):
                nombre = str(score.get("name", ""))
                if nombre.startswith(PREFIJO):
                    salida.append(
                        {
                            "criterio": nombre.removeprefix(PREFIJO),
                            "valor": float(score["value"]),
                            "justificacion": score.get("comment"),
                            "traza": traza["id"],
                        }
                    )
        return salida
    except (RuntimeError, urllib.error.URLError, KeyError, ValueError) as error:
        print(f"[langfuse] obra {obra_id}: sin puntuaciones del juez ({error})", file=sys.stderr)
        return []


def medias_del_juez(obra_id: int) -> dict[str, list[float]]:
    por_criterio: dict[str, list[float]] = {}
    for p in puntuaciones_del_juez(obra_id):
        por_criterio.setdefault(p["criterio"], []).append(p["valor"])
    return por_criterio
