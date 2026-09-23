"""Endpoints de `obra` (RI-01).

Los endpoints **no contienen logica** (`CLAUDE.md` §6): validan la entrada,
delegan en el servicio y devuelven un modelo de respuesta.

Este es el unico de los nueve que no devuelve un trabajo. Crear la fila de una
obra no llama al modelo y termina en milisegundos; un 202 aqui obligaria al
cliente a preguntar por un identificador que ya tiene.
"""

import functools
from typing import Annotated, Protocol

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict

from app.commons.domain import Reloj, RelojDelSistema
from app.commons.jobs import (
    EjecutorDeTrabajos,
    RepositorioDeTrabajos,
    ejecutar_paso_simple,
)
from app.commons.llm import CargadorDePrompts, ClienteDeModelo
from app.features.obra.repository import RepositorioDeObras
from app.features.obra.schemas import Brief, ObraCreada
from app.features.obra.service import crear_obra, generar_biblia

router = APIRouter(tags=["obra"])

TIPO_BIBLIA = "generar_biblia"


class TrabajoAceptado(BaseModel):
    model_config = ConfigDict(frozen=True)

    trabajo_id: str
    estado: str


class FuentesDeTrabajo(Protocol):
    """Lo que este router necesita de la fabrica, y nada mas.

    Se declara como `Protocol` y no se importa `Dependencias`: esta feature es
    anterior a `escritura` en el grafo de dependencias, y traerla de alli daria
    un ciclo entre features (§5.2 regla 5). `Dependencias` lo cumple por forma
    sin que ninguno de los dos lo sepa.
    """

    reloj: Reloj
    cargador: CargadorDePrompts
    arquitecto: ClienteDeModelo
    obras: RepositorioDeObras
    trabajos: RepositorioDeTrabajos


def obtener_fuentes(peticion: Request) -> FuentesDeTrabajo:
    fuentes: FuentesDeTrabajo = peticion.app.state.fabrica_dependencias()
    return fuentes


def obtener_ejecutor(peticion: Request) -> EjecutorDeTrabajos:
    ejecutor: EjecutorDeTrabajos = peticion.app.state.ejecutor
    return ejecutor


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


@router.post("/obras/{obra_id}/biblia", status_code=202, response_model=TrabajoAceptado)
def generar_la_biblia(
    obra_id: str,
    fuentes: Annotated[FuentesDeTrabajo, Depends(obtener_fuentes)],
    ejecutor: Annotated[EjecutorDeTrabajos, Depends(obtener_ejecutor)],
) -> TrabajoAceptado:
    """RI-02. El Arquitecto produce la biblia y se guarda como **version nueva**
    (RD-12): editar la vigente dejaria las escenas anteriores apoyadas en hechos
    que ya no existen y sin rastro del porque."""
    obra = fuentes.obras.leer(obra_id)
    prompt = fuentes.cargador.cargar("arquitecto")
    material = (
        f"{prompt.texto}\n\n## Obra\n\n"
        f"{obra.titulo}. Persona {obra.persona}, tiempo verbal "
        f"{obra.tiempo_verbal}, esquema de POV {obra.esquema_de_pov}, "
        f"nivel de calor {obra.nivel_de_calor.value}.\n\n"
        "Produce ahora la biblia."
    )
    trabajo = fuentes.trabajos.crear(obra_id, None, TIPO_BIBLIA, fuentes.reloj)
    ejecutor.encolar(
        functools.partial(
            ejecutar_paso_simple,
            trabajo.trabajo_id,
            fuentes.trabajos,
            fuentes.reloj,
            functools.partial(
                generar_biblia,
                obra_id,
                fuentes.arquitecto,
                material,
                fuentes.obras,
                fuentes.reloj,
            ),
        )
    )
    return TrabajoAceptado(trabajo_id=trabajo.trabajo_id, estado=trabajo.estado.value)
