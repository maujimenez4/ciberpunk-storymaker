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

from pathlib import Path

from fastapi import FastAPI

from app.commons.errors import registrar_manejadores
from app.commons.jobs import montar_ejecutor_de_trabajos
from app.features.escritura import router as router_escritura

TITULO = "StoryMaker · backend v1"


def crear_app(ruta_base_de_datos: Path | str = "obra.db") -> FastAPI:
    app = FastAPI(title=TITULO, version="1.0.0")
    app.state.ruta_base_de_datos = str(ruta_base_de_datos)
    registrar_manejadores(app)
    montar_ejecutor_de_trabajos(app)
    app.include_router(router_escritura)
    return app
