"""Endpoints de `escritura` (RI-05, RI-09, RI-19).

Los endpoints **no contienen logica** (`CLAUDE.md` §6): validan la entrada,
delegan en el servicio y devuelven un modelo de respuesta. Aqui eso significa
crear el trabajo y devolver su identificador: la escritura de una escena tarda
minutos y una peticion HTTP que la espere se agota antes de terminar, dejando el
trabajo huerfano y al cliente sin saber si ocurrio.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict

from app.commons.domain import Reloj, RelojDelSistema
from app.commons.errors import RecursoNoEncontrado
from app.commons.jobs import RepositorioDeTrabajos

router = APIRouter(tags=["escritura"])


class TrabajoAceptado(BaseModel):
    model_config = ConfigDict(frozen=True)

    trabajo_id: str
    estado: str


class DefectoEnRespuesta(BaseModel):
    """RI-18: codigo **y cita**. Sin la cita, el autor tiene que buscar el
    pasaje a mano, que es justo lo que la escalada deberia ahorrarle."""

    model_config = ConfigDict(frozen=True)

    codigo: str
    cita: str
    detalle: str


class EstadoDeTrabajo(BaseModel):
    model_config = ConfigDict(frozen=True)

    trabajo_id: str
    tipo: str
    estado: str
    intento: int
    causa_fallo: str | None = None
    defectos: list[DefectoEnRespuesta] = []


def obtener_repositorio(peticion: Request) -> RepositorioDeTrabajos:
    return RepositorioDeTrabajos(peticion.app.state.ruta_base_de_datos)


def obtener_reloj() -> Reloj:
    return RelojDelSistema()


@router.post(
    "/escenas/{escena_id}/escribir", status_code=202, response_model=TrabajoAceptado
)
def escribir_escena(
    escena_id: str,
    obra_id: str,
    repositorio: Annotated[RepositorioDeTrabajos, Depends(obtener_repositorio)],
    reloj: Annotated[Reloj, Depends(obtener_reloj)],
) -> TrabajoAceptado:
    """RI-05. Devuelve 202 y el trabajo; no espera a que el modelo escriba."""
    trabajo = repositorio.crear(obra_id, escena_id, "escribir_escena", reloj)
    return TrabajoAceptado(trabajo_id=trabajo.trabajo_id, estado=trabajo.estado.value)


@router.get("/trabajos/{trabajo_id}", response_model=EstadoDeTrabajo)
def consultar_trabajo(
    trabajo_id: str,
    repositorio: Annotated[RepositorioDeTrabajos, Depends(obtener_repositorio)],
) -> EstadoDeTrabajo:
    """RI-09 y RI-18. Lanza `RecursoNoEncontrado`, **nunca** `HTTPException`: el
    handler central lo traduce a 404 (RI-11)."""
    trabajo = repositorio.leer(trabajo_id)
    return EstadoDeTrabajo(
        trabajo_id=trabajo.trabajo_id,
        tipo=trabajo.tipo,
        estado=trabajo.estado.value,
        intento=trabajo.intento,
        causa_fallo=trabajo.causa_fallo,
    )


@router.post(
    "/trabajos/{trabajo_id}/cancelar", status_code=202, response_model=TrabajoAceptado
)
def cancelar_trabajo(
    trabajo_id: str,
    repositorio: Annotated[RepositorioDeTrabajos, Depends(obtener_repositorio)],
    reloj: Annotated[Reloj, Depends(obtener_reloj)],
) -> TrabajoAceptado:
    """RI-19: el efecto es `CANCELADA` en el primer punto seguro."""
    from app.commons.jobs import Estado

    actual = repositorio.leer(trabajo_id)
    if actual.escena_id is None:  # pragma: no cover
        raise RecursoNoEncontrado("Escena del trabajo", trabajo_id)
    trabajo = repositorio.transitar(trabajo_id, Estado.CANCELADA, reloj)
    return TrabajoAceptado(trabajo_id=trabajo.trabajo_id, estado=trabajo.estado.value)
