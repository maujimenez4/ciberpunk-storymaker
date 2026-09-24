"""Composicion: monta routers y manejadores, y nada mas (`CLAUDE.md` §5.1).

Se entra a una feature **solo por su `__init__.py`**, asi que de `obra` se
importa el paquete y no `features.obra.router`.
"""

from fastapi import FastAPI

from app.commons.errors.manejador import registrar_manejadores
from app.features import contexto, obra, outline


def crear_app() -> FastAPI:
    app = FastAPI(title="ciberpunk-storymaker", version="0.1.0")
    registrar_manejadores(app)
    app.include_router(obra.router)
    app.include_router(outline.router)
    app.include_router(contexto.router)
    return app
