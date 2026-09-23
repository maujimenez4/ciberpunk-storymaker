"""Endpoints de `outline` (RI-03).

El Arquitecto, en su segunda intervencion, divide la obra en partes, capitulos y
escenas. No es el ciclo de una escena: nace, hace su paso y termina
(`architecture.md` §3.3).
"""

import functools
from typing import Annotated, Protocol

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict

from app.commons.domain import Reloj
from app.commons.jobs import (
    EjecutorDeTrabajos,
    RepositorioDeTrabajos,
    ejecutar_paso_simple,
)
from app.commons.llm import CargadorDePrompts, ClienteDeModelo
from app.features.outline.repository import RepositorioDeOutline
from app.features.outline.service import generar_outline

router = APIRouter(tags=["outline"])

TIPO_OUTLINE = "generar_outline"


class TrabajoAceptado(BaseModel):
    model_config = ConfigDict(frozen=True)

    trabajo_id: str
    estado: str


class FuentesDeOutline(Protocol):
    """Lo que este router necesita de la fabrica, y nada mas.

    Se declara como `Protocol` y no se importa `Dependencias`: esta feature es
    anterior a `escritura` en el grafo, y traerla de alli daria un ciclo entre
    features (§5.2 regla 5). `Dependencias` lo cumple por forma.
    """

    reloj: Reloj
    cargador: CargadorDePrompts
    arquitecto: ClienteDeModelo
    outline: RepositorioDeOutline
    trabajos: RepositorioDeTrabajos


def obtener_fuentes(peticion: Request) -> FuentesDeOutline:
    fuentes: FuentesDeOutline = peticion.app.state.fabrica_dependencias()
    return fuentes


def obtener_ejecutor(peticion: Request) -> EjecutorDeTrabajos:
    ejecutor: EjecutorDeTrabajos = peticion.app.state.ejecutor
    return ejecutor


@router.post(
    "/obras/{obra_id}/outline", status_code=202, response_model=TrabajoAceptado
)
def generar_el_outline(
    obra_id: str,
    fuentes: Annotated[FuentesDeOutline, Depends(obtener_fuentes)],
    ejecutor: Annotated[EjecutorDeTrabajos, Depends(obtener_ejecutor)],
) -> TrabajoAceptado:
    """RI-03. La cobertura de beats se comprueba **antes** de guardar: mover una
    escena en el outline cuesta una linea y en el manuscrito, un capitulo."""
    prompt = fuentes.cargador.cargar("arquitecto")
    encargo = f"{prompt.texto}\n\nProduce ahora el outline de la obra."
    trabajo = fuentes.trabajos.crear(obra_id, None, TIPO_OUTLINE, fuentes.reloj)
    ejecutor.encolar(
        functools.partial(
            ejecutar_paso_simple,
            trabajo.trabajo_id,
            fuentes.trabajos,
            fuentes.reloj,
            functools.partial(
                generar_outline,
                obra_id,
                fuentes.arquitecto,
                encargo,
                fuentes.outline,
                fuentes.reloj,
            ),
        )
    )
    return TrabajoAceptado(trabajo_id=trabajo.trabajo_id, estado=trabajo.estado.value)
