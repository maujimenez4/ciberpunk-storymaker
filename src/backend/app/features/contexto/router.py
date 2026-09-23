"""Endpoints de `contexto` (RI-06).

Depuracion: devuelve el paquete que se le enviaria al Escritor y su desglose por
capa. Es la forma de mirar por que una escena salio como salio sin tener que
reproducir la corrida entera.

**No importa `escritura`.** Necesita los mismos colaboradores que el ciclo
-almacenes, ordenador, contador- pero importarlos de alli daria un ciclo entre
features (§5.2 regla 5), porque `escritura` ya importa a `contexto`. Se declaran
como `Protocol`: quien monta la aplicacion pasa algo que lo cumpla, y
`Dependencias` lo cumple por forma sin que ninguno de los dos lo sepa.
"""

from typing import Annotated, Protocol

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict

from app.commons.llm import ContadorDeTokens, OrdenadorSemantico
from app.features.contexto.recoleccion import Almacenes, recolectar
from app.features.contexto.service import ensamblar

router = APIRouter(tags=["contexto"])


class FuentesDeContexto(Protocol):
    """Lo que hace falta para montar un paquete, y nada mas."""

    almacenes: Almacenes
    ordenador: OrdenadorSemantico
    contador: ContadorDeTokens


class ContextoDeEscena(BaseModel):
    model_config = ConfigDict(frozen=True)

    escena_id: str
    texto: str
    tokens_por_capa: dict[str, int]
    total: int
    descartado_por_capa: dict[str, list[str]]
    ids_recuperados: list[str]


def obtener_fuentes(peticion: Request) -> FuentesDeContexto:
    fabrica = peticion.app.state.fabrica_dependencias
    fuentes: FuentesDeContexto = fabrica()
    return fuentes


@router.get("/escenas/{escena_id}/contexto", response_model=ContextoDeEscena)
def consultar_contexto(
    escena_id: str,
    fuentes: Annotated[FuentesDeContexto, Depends(obtener_fuentes)],
    consulta: str = "",
) -> ContextoDeEscena:
    """RI-06 y RF-CTX-06.

    Si una capa con origen llega vacia, esto lanza `CapaVacia` igual que el
    ciclo (RF-CTX-14). Es lo que se quiere: el endpoint de depuracion tiene que
    fallar donde falla el ciclo, no ensenar un paquete que el ciclo rechazaria.
    """
    capas = recolectar(
        escena_id=escena_id,
        almacenes=fuentes.almacenes,
        ordenador=fuentes.ordenador,
        consulta=consulta,
    )
    paquete = ensamblar(capas, fuentes.contador)
    return ContextoDeEscena(
        escena_id=escena_id,
        texto=paquete.texto,
        tokens_por_capa=paquete.desglose.por_capa,
        total=paquete.desglose.total,
        descartado_por_capa=paquete.descartado_por_capa,
        ids_recuperados=paquete.ids_recuperados,
    )
