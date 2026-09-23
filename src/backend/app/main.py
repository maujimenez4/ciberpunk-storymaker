"""Composición de la aplicación: monta routers y dependencias.

`CLAUDE.md` §5.1 y §6. Este fichero es el **único** que conoce a todas las
features, y solo por su `__init__.py`. Nada de lógica aquí: un `main.py` que
decidiera algo se convertiría en el sitio donde acaba lo que no encaja en
ninguna feature, que es exactamente lo que la organización vertical evita.

Tres garantías con test propio:

- **Ninguna operación larga bloquea la petición** (§5.4). El endpoint crea un
  `trabajo` y devuelve su identificador; el cliente consulta `GET /trabajos/{id}`.
  Una petición HTTP que espere a que el modelo escriba una escena se agota antes
  de terminar y deja el trabajo huérfano.
- **Ningún servicio lanza `HTTPException`** (RI-11). Las excepciones de dominio
  las traduce el handler central, y por eso un servicio se puede reutilizar desde
  un trabajo en segundo plano, que es donde corre el ciclo de una escena.
- **Toda ruta declara su modelo de respuesta** (RI-23). El contrato con cualquier
  cliente es el esquema OpenAPI generado, no una descripción escrita aparte que
  se desincroniza a la primera.

`POST /obras/{id}/auditoria` no existe: la auditoría de manuscrito está fuera de
alcance y la spec retiró RI-10 sin renumerar el resto.
"""

import functools
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI

from app.commons.errors import registrar_manejadores
from app.commons.jobs import RepositorioDeTrabajos, montar_ejecutor_de_trabajos
from app.features.canon import router as router_canon
from app.features.contexto import router as router_contexto
from app.features.escena import router as router_escena
from app.features.escritura import (
    Dependencias,
    construir_dependencias,
    ejecutar_en_segundo_plano,
)
from app.features.escritura import router as router_escritura
from app.features.obra import router as router_obra
from app.features.outline import router as router_outline

TITULO = "StoryMaker · backend v1"


def crear_app(
    ruta_base_de_datos: Path | str = "obra.db",
    fabrica_dependencias: Callable[[], Dependencias] | None = None,
) -> FastAPI:
    """`fabrica_dependencias` entra por parametro y no por `Depends` porque la
    reanudacion del arranque corre fuera de una peticion, donde `Depends` no
    llega. Una sola fabrica para los dos caminos: dos serian dos caminos, y el
    que se prueba nunca es el que falla."""
    app = FastAPI(title=TITULO, version="1.0.0")
    app.state.ruta_base_de_datos = str(ruta_base_de_datos)
    # Donde viven los prompts lo decide la composicion, no la feature. Si lo
    # calculara el router con `Path(__file__)`, `escritura` estaria tocando el
    # sistema de ficheros y RF-ORQ-16 dejaria de ser cierta por construccion.
    app.state.ruta_prompts = Path(__file__).resolve().parent / "features"
    app.state.fabrica_dependencias = fabrica_dependencias or functools.partial(
        construir_dependencias, str(ruta_base_de_datos), app.state.ruta_prompts
    )
    registrar_manejadores(app)
    ejecutor = montar_ejecutor_de_trabajos(app)
    _retomar_trabajos_vivos(app, ejecutor)
    app.include_router(router_obra)
    app.include_router(router_outline)
    app.include_router(router_escena)
    app.include_router(router_contexto)
    app.include_router(router_canon)
    app.include_router(router_escritura)
    return app


def _retomar_trabajos_vivos(app: FastAPI, ejecutor: object) -> None:
    """RF-ORQ-05 y CA-3: una caida a mitad de escena no pierde trabajo.

    `vivos()` existia y estaba probado desde la fase 7, pero **no lo llamaba
    nadie**: el estado se persistia con todo cuidado y luego no se leia. Un paso
    interrumpido se repite entero (§3.7), que es posible porque la salida solo
    se persiste al completarse y el `run_id` evita duplicados.
    """
    repositorio = RepositorioDeTrabajos(app.state.ruta_base_de_datos)
    try:
        vivos = repositorio.vivos()
    except Exception:  # noqa: BLE001 - sin base todavia no hay nada que retomar
        return
    for trabajo in vivos:
        if trabajo.escena_id is None:
            continue
        ejecutor.encolar(  # type: ignore[attr-defined]
            functools.partial(
                ejecutar_en_segundo_plano,
                trabajo.trabajo_id,
                trabajo.escena_id,
                trabajo.obra_id,
                "s1",
                app.state.fabrica_dependencias(),
            )
        )
