"""Traduccion central de excepciones de dominio a HTTP (RI-11)."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.commons.errors.errores import (
    ContextBudgetExceeded,
    ErrorDeDominio,
    FalloDeProveedor,
    RecursoNoEncontrado,
    ReglaDeDominioViolada,
    TiempoAgotado,
)

# Un sitio y solo uno donde vive la correspondencia. Anadir una excepcion sin
# anadirla aqui lo caza el test de cobertura de P-04.
CODIGOS: dict[type[ErrorDeDominio], int] = {
    ContextBudgetExceeded: 422,
    ReglaDeDominioViolada: 422,
    RecursoNoEncontrado: 404,
    TiempoAgotado: 503,
    FalloDeProveedor: 502,
}


def _manejador(
    estado: int,
) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
    async def manejar(_: Request, error: Exception) -> JSONResponse:
        assert isinstance(error, ErrorDeDominio)
        return JSONResponse(
            status_code=estado,
            content={
                "error": type(error).__name__,
                "detalle": str(error),
                **error.datos(),
            },
        )

    return manejar


def registrar_manejadores(app: FastAPI) -> None:
    """Monta la traduccion en la aplicacion. La llama `main.py`, nadie mas."""
    for excepcion, estado in CODIGOS.items():
        app.add_exception_handler(excepcion, _manejador(estado))
