"""Endpoints de `escena` (RI-07).

El historial de versiones es inmutable y sale entero, con la vigente marcada.
No se expone la fila (RI-12) ni se permite editar: editar crea version nueva
(RF-ESC-03), y esa es una operacion del ciclo, no de este endpoint.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict

from app.features.escena.repository import RepositorioDeEscenas

router = APIRouter(tags=["escena"])


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
