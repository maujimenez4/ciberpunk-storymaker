"""De error de dominio a respuesta HTTP, **en un solo sitio** (`CLAUDE.md` §6).

Un `HTTPException` dentro de un servicio ata el dominio al transporte: el caso
de uso deja de poder probarse fuera de una peticion y el codigo de estado se
decide en tantos sitios como servicios haya. Aqui hay uno.

Este modulo si importa FastAPI, y puede: el segundo contrato de `import-linter`
prohibe el framework en `commons/domain/`, no en `commons/errors/`. Esa es
justamente la frontera: el dominio dice *que* salio mal, esto dice con que
codigo se cuenta.
"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.commons.domain.errores import (
    BriefContradictorio,
    BriefIncompleto,
    ErrorDeDominio,
    RecursoDesconocido,
)

_POR_DEFECTO = status.HTTP_409_CONFLICT


def _codigo(error: ErrorDeDominio) -> int:
    """409 salvo que se sepa algo mejor.

    409 es el que corresponde a la familia entera: el dominio entiende la
    peticion y el estado actual no la admite. `RecursoDesconocido` es la
    excepcion, porque lo que falla no es el estado sino el recurso.
    """
    if isinstance(error, RecursoDesconocido):
        return status.HTTP_404_NOT_FOUND
    return _POR_DEFECTO


def _cuerpo(error: ErrorDeDominio) -> dict[str, Any]:
    """`detail` siempre, y ademas el dato que hace accionable el error.

    CA-2 no se conforma con «no se creo la obra»: pide que se devuelva **que**
    falta o **que** se contradice. Un cuerpo con solo `detail` obligaria al
    frontend a leer una frase para volver a preguntar.
    """
    cuerpo: dict[str, Any] = {"detail": str(error)}
    if isinstance(error, BriefIncompleto):
        cuerpo["faltantes"] = error.faltantes
    elif isinstance(error, BriefContradictorio):
        cuerpo["contradicciones"] = error.contradicciones
    return cuerpo


async def _a_http(peticion: Request, error: Exception) -> JSONResponse:
    """La firma la fija Starlette: recibe `Exception`, no `ErrorDeDominio`."""
    assert isinstance(error, ErrorDeDominio)
    return JSONResponse(status_code=_codigo(error), content=_cuerpo(error))


def registrar_manejadores(app: FastAPI) -> None:
    """Un solo registro para toda la familia.

    Se engancha sobre la raiz `ErrorDeDominio` y no sobre cada hija: asi una
    excepcion de dominio nueva no se convierte en un 500 por olvidar darla de
    alta aqui. Lo que no hereda de `ErrorDeDominio` **no se traduce**: es un
    fallo del sistema y se propaga.
    """
    app.add_exception_handler(ErrorDeDominio, _a_http)
