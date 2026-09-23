"""Endpoints de `obra` (RI-01).

Los endpoints **no contienen logica** (`CLAUDE.md` §6): validan la entrada,
delegan en el servicio y devuelven un modelo de respuesta.

Este es el unico de los nueve que no devuelve un trabajo. Crear la fila de una
obra no llama al modelo y termina en milisegundos; un 202 aqui obligaria al
cliente a preguntar por un identificador que ya tiene.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.commons.domain import Reloj, RelojDelSistema
from app.features.obra.repository import RepositorioDeObras
from app.features.obra.schemas import Brief, ObraCreada
from app.features.obra.service import crear_obra

router = APIRouter(tags=["obra"])


def obtener_repositorio(peticion: Request) -> RepositorioDeObras:
    return RepositorioDeObras(peticion.app.state.ruta_base_de_datos)


def obtener_reloj() -> Reloj:
    return RelojDelSistema()


@router.post("/obras", status_code=201, response_model=ObraCreada)
def crear(
    brief: Brief,
    repositorio: Annotated[RepositorioDeObras, Depends(obtener_repositorio)],
    reloj: Annotated[Reloj, Depends(obtener_reloj)],
) -> ObraCreada:
    """RI-01. El brief adversario lo rechaza el **esquema** (RNF-SEG-06), antes
    de llegar aqui: asi la defensa vale igual desde un trabajo en segundo plano,
    donde no hay peticion que validar."""
    return crear_obra(brief, repositorio, reloj)


@router.get("/obras/{obra_id}", response_model=ObraCreada)
def leer(
    obra_id: str,
    repositorio: Annotated[RepositorioDeObras, Depends(obtener_repositorio)],
) -> ObraCreada:
    """Lanza `RecursoNoEncontrado`, **nunca** `HTTPException` (RI-11)."""
    return repositorio.leer(obra_id)
