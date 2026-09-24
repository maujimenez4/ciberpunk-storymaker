"""Los tres endpoints de la entrevista: RI-01, RI-02 y RI-03.

**Aqui no hay logica** (`CLAUDE.md` §6). Cada endpoint valida la entrada con su
modelo, llama a un caso de uso de su propia feature y devuelve un modelo de
salida. Lo unico que decide es transporte: que codigo de estado corresponde a
lo que el servicio devolvio, y eso no es una regla de negocio.

Ningun error se captura aqui: lo que el servicio lanza son excepciones de
dominio y las traduce el manejador central de `commons/errors/`.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.db.sesion import obtener_sesion
from app.commons.llm.cliente import ClienteModelo, obtener_cliente_modelo
from app.features.obra.agents import Entrevistador
from app.features.obra.schemas import (
    EntrevistaAbierta,
    EvaluacionSalida,
    ObraCreada,
    RespuestasEntrada,
)
from app.features.obra.service import (
    abrir_entrevista,
    cerrar_entrevista,
    responder_entrevista,
)


def obtener_entrevistador(
    cliente: Annotated[ClienteModelo, Depends(obtener_cliente_modelo)],
) -> Entrevistador:
    """El agente se compone aqui, no dentro del servicio (RI-14).

    Es lo que permite que un test sustituya el cliente de modelo sin tocar el
    codigo de produccion: el servicio recibe el `Entrevistador` ya hecho y no
    sabe de donde salio.
    """
    return Entrevistador(cliente)


Sesion = Annotated[AsyncSession, Depends(obtener_sesion)]
Agente = Annotated[Entrevistador, Depends(obtener_entrevistador)]

# El prefijo no lleva barra final y la ruta de la coleccion es la cadena vacia:
# con `"/"` el OpenAPI publicaria `/entrevistas/`, y RI-13 es un contrato del
# que la spec 002 genera su cliente, asi que la ruta es parte de lo acordado.
router = APIRouter(prefix="/entrevistas", tags=["entrevista"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def abrir(sesion: Sesion) -> EntrevistaAbierta:
    """RI-01. Abre una entrevista vacia y devuelve su id."""
    entrevista = await abrir_entrevista(sesion)
    return EntrevistaAbierta(id=entrevista.id)


@router.post("/{entrevista_id}/respuestas")
async def responder(
    entrevista_id: int,
    entrada: RespuestasEntrada,
    sesion: Sesion,
    entrevistador: Agente,
) -> EvaluacionSalida:
    """RI-02. Aporta datos o texto libre; devuelve faltantes y contradicciones."""
    evaluacion = await responder_entrevista(
        sesion,
        entrevistador,
        entrevista_id,
        entrada.respuestas,
        entrada.texto_aportado,
    )
    return EvaluacionSalida.model_validate(evaluacion.model_dump())


@router.post(
    "/{entrevista_id}/cerrar",
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_200_OK: {"description": "La entrevista ya estaba cerrada (R-5)"}},
)
async def cerrar(
    entrevista_id: int,
    sesion: Sesion,
    entrevistador: Agente,
    respuesta: Response,
) -> ObraCreada:
    """RI-03. Valida el brief con esquema y crea la obra.

    El segundo cierre devuelve 200 y **la misma** obra (R-5). Se baja el codigo
    en vez de dejar el 201 porque un «Created» que no creo nada es lo unico que
    esta respuesta no debe decir.
    """
    cierre = await cerrar_entrevista(sesion, entrevistador, entrevista_id)
    if not cierre.creada:
        respuesta.status_code = status.HTTP_200_OK
    return ObraCreada(obra_id=cierre.obra_id)
