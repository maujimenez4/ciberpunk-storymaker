"""Composicion: monta routers y manejadores, y nada mas (`CLAUDE.md` §5.1).

Se entra a una feature **solo por su `__init__.py`**, asi que de `obra` se
importa el paquete y no `features.obra.router`.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.commons.db.vectores import extension_disponible
from app.commons.errors.manejador import registrar_manejadores
from app.features import contexto, escritura, manuscrito, obra, outline


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI) -> AsyncIterator[None]:
    """Lo que se comprueba **al levantar**, y no en la primera peticion.

    R-6 pide que, si `sqlite-vec` no carga, «el sistema arranque y **avise**».
    La deteccion existia desde T7 y era perezosa: el aviso salia en la primera
    recuperacion, es decir, a mitad de escribir un capitulo y no al arrancar el
    proceso. Quien levanta el servidor se enteraba tarde de que la ordenacion
    semantica iba por fuerza bruta.

    `extension_disponible()` prueba la carga sobre una base en memoria propia y
    cachea el resultado, asi que llamarla aqui no toca la base de la obra y no
    la vuelve a probar nunca mas.
    """
    extension_disponible()
    yield


def crear_app() -> FastAPI:
    app = FastAPI(title="ciberpunk-storymaker", version="0.1.0", lifespan=ciclo_de_vida)
    registrar_manejadores(app)
    app.include_router(obra.router)
    app.include_router(outline.router)
    app.include_router(contexto.router)
    app.include_router(escritura.router)
    app.include_router(manuscrito.router)
    return app
