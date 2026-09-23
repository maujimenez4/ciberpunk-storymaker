"""Endpoints de `escena` (RI-07).

El historial de versiones es inmutable y sale entero, con la vigente marcada.
No se expone la fila (RI-12) ni se permite editar: editar crea version nueva
(RF-ESC-03), y esa es una operacion del ciclo, no de este endpoint.
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
from app.features.escena.repository import RepositorioDeEscenas
from app.features.escena.service import planificar_escena
from app.features.obra import RepositorioDeObras
from app.features.outline import RepositorioDeOutline

router = APIRouter(tags=["escena"])

TIPO_FICHA = "planificar_escena"


class TrabajoAceptado(BaseModel):
    model_config = ConfigDict(frozen=True)

    trabajo_id: str
    estado: str


class FuentesDeFicha(Protocol):
    """Lo que este router necesita de la fabrica, y nada mas.

    `Protocol` y no `Dependencias`: `escena` es anterior a `escritura` en el
    grafo, y traerla de alli daria un ciclo entre features (§5.2 regla 5).
    """

    reloj: Reloj
    cargador: CargadorDePrompts
    planificador: ClienteDeModelo
    escenas: RepositorioDeEscenas
    obras: RepositorioDeObras
    outline: RepositorioDeOutline
    trabajos: RepositorioDeTrabajos


def obtener_fuentes(peticion: Request) -> FuentesDeFicha:
    fuentes: FuentesDeFicha = peticion.app.state.fabrica_dependencias()
    return fuentes


def obtener_ejecutor(peticion: Request) -> EjecutorDeTrabajos:
    ejecutor: EjecutorDeTrabajos = peticion.app.state.ejecutor
    return ejecutor


def _planificar_y_guardar(escena_id: str, fuentes: FuentesDeFicha) -> None:
    """RF-ESC-01 y RF-ESC-02.

    La ficha **se guarda**: la capa de instruccion del paquete sale de la fila,
    asi que una ficha que solo viviera en la respuesta dejaria al Escritor con
    la propuesta gruesa del outline.
    """
    ubicacion = fuentes.outline.ubicacion_de(escena_id)
    parametros = fuentes.obras.leer(ubicacion.obra_id).parametros_para_una_escena()
    prompt = fuentes.cargador.cargar("planificador")
    encargo = (
        f"{prompt.texto}\n\n## Material\n\n"
        f"Capitulo {ubicacion.capitulo_numero}: {ubicacion.capitulo_titulo}. "
        f"Escena {ubicacion.orden_discurso}.\n\nProduce ahora la ficha."
    )
    ficha = planificar_escena(
        escena_id, parametros, fuentes.planificador, encargo, fuentes.reloj
    )
    fuentes.escenas.guardar_ficha(ficha)


class VersionEnRespuesta(BaseModel):
    model_config = ConfigDict(frozen=True)

    version_texto_id: str
    vigente: bool
    run_id: str
    autoria: str
    palabras: int


class HistorialDeEscena(BaseModel):
    model_config = ConfigDict(frozen=True)

    escena_id: str
    versiones: list[VersionEnRespuesta]


def obtener_repositorio(peticion: Request) -> RepositorioDeEscenas:
    return RepositorioDeEscenas(peticion.app.state.ruta_base_de_datos)


@router.get("/escenas/{escena_id}/versiones", response_model=HistorialDeEscena)
def consultar_versiones(
    escena_id: str,
    repositorio: Annotated[RepositorioDeEscenas, Depends(obtener_repositorio)],
) -> HistorialDeEscena:
    """RI-07. Sin el texto: el historial sirve para **elegir** una version, y
    devolver la prosa entera de todas convertiria una consulta de metadatos en
    una descarga del manuscrito por escena."""
    return HistorialDeEscena(
        escena_id=escena_id,
        versiones=[
            VersionEnRespuesta(
                version_texto_id=version.version_texto_id,
                vigente=version.vigente,
                run_id=version.run_id,
                autoria=version.autoria,
                palabras=len(version.texto.split()),
            )
            for version in repositorio.versiones_de(escena_id)
        ],
    )


@router.post(
    "/escenas/{escena_id}/planificar", status_code=202, response_model=TrabajoAceptado
)
def planificar(
    escena_id: str,
    fuentes: Annotated[FuentesDeFicha, Depends(obtener_fuentes)],
    ejecutor: Annotated[EjecutorDeTrabajos, Depends(obtener_ejecutor)],
) -> TrabajoAceptado:
    """RI-04."""
    ubicacion = fuentes.outline.ubicacion_de(escena_id)
    trabajo = fuentes.trabajos.crear(
        ubicacion.obra_id, escena_id, TIPO_FICHA, fuentes.reloj
    )
    ejecutor.encolar(
        functools.partial(
            ejecutar_paso_simple,
            trabajo.trabajo_id,
            fuentes.trabajos,
            fuentes.reloj,
            functools.partial(_planificar_y_guardar, escena_id, fuentes),
        )
    )
    return TrabajoAceptado(trabajo_id=trabajo.trabajo_id, estado=trabajo.estado.value)
