"""Endpoints de `canon` (RI-08).

Consulta del grafo. Es de lectura y no lleva trabajo detras: el canon ya esta
escrito cuando alguien pregunta por el.

**Todo hecho sale con su escena de origen** (RF-CAN-04, regla 4 de §8). Sin ella
el canon seria una lista de afirmaciones sin procedencia, y contrastar una
contradiccion obligaria a releer el manuscrito entero.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict

from app.features.canon.repository import RepositorioDeCanon

router = APIRouter(tags=["canon"])


class HechoEnRespuesta(BaseModel):
    model_config = ConfigDict(frozen=True)

    hc_id: str
    entidad: str
    atributo: str
    valor: str
    escena_de_origen: str
    sustituye_a: str | None = None


class CanonDeObra(BaseModel):
    """Entrada y salida separadas (RI-12): nunca se expone la fila."""

    model_config = ConfigDict(frozen=True)

    obra_id: str
    hechos: list[HechoEnRespuesta]


def obtener_repositorio(peticion: Request) -> RepositorioDeCanon:
    return RepositorioDeCanon(peticion.app.state.ruta_base_de_datos)


@router.get("/obras/{obra_id}/canon", response_model=CanonDeObra)
def consultar_canon(
    obra_id: str,
    repositorio: Annotated[RepositorioDeCanon, Depends(obtener_repositorio)],
    entidad: str | None = None,
    atributo: str | None = None,
) -> CanonDeObra:
    """RI-08. Solo lo vigente: un hecho sustituido ya no es canon."""
    hechos = repositorio.hechos_de_obra(obra_id, entidad=entidad, atributo=atributo)
    return CanonDeObra(
        obra_id=obra_id,
        hechos=[HechoEnRespuesta(**hecho.model_dump()) for hecho in hechos],
    )
