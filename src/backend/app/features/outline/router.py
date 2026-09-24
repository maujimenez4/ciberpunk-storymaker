"""RI-04: `POST /obras/{id}/outline`, biblia y outline de diez capitulos.

**Aqui no hay logica** (`CLAUDE.md` §6). El endpoint valida la entrada, llama al
caso de uso de su feature y devuelve un modelo de salida. Ningun error se
captura: lo que el servicio lanza son excepciones de dominio y las traduce el
manejador central de `commons/errors/`.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.db.sesion import obtener_sesion
from app.commons.llm.cliente import ClienteModelo, obtener_cliente_modelo
from app.commons.observabilidad import ClienteObservado, Observador, obtener_observador
from app.features.outline.agents import Arquitecto
from app.features.outline.schemas import OutlineCreado
from app.features.outline.service import planificar_obra


def obtener_cliente_observado(
    cliente: Annotated[ClienteModelo, Depends(obtener_cliente_modelo)],
) -> ClienteObservado:
    """El cliente de la peticion, envuelto para que el prompt llegue al span.

    FastAPI resuelve una dependencia **una vez por peticion**, asi que el
    Arquitecto y la ruta reciben el mismo objeto: si fueran dos, el span se
    abriria y nadie escribiria dentro.
    """
    return ClienteObservado(cliente)


Observado = Annotated[ClienteObservado, Depends(obtener_cliente_observado)]


def obtener_arquitecto(cliente: Observado) -> Arquitecto:
    """El agente se compone aqui, no dentro del servicio.

    Es lo que permite que un test sustituya el cliente de modelo sin tocar el
    codigo de produccion: el servicio recibe el `Arquitecto` ya hecho y no sabe
    de donde salio (CA-4).
    """
    return Arquitecto(cliente)


Sesion = Annotated[AsyncSession, Depends(obtener_sesion)]
Agente = Annotated[Arquitecto, Depends(obtener_arquitecto)]
Observa = Annotated[Observador, Depends(obtener_observador)]

router = APIRouter(prefix="/obras", tags=["outline"])


@router.post("/{obra_id}/outline", status_code=status.HTTP_201_CREATED)
async def planificar(
    obra_id: int,
    sesion: Sesion,
    arquitecto: Agente,
    observador: Observa,
    cliente: Observado,
) -> OutlineCreado:
    """RI-04. Produce la biblia versionada y el outline de diez capitulos."""
    plan = await planificar_obra(
        sesion, arquitecto, obra_id, observador=observador, cliente=cliente
    )
    return OutlineCreado(
        obra_id=obra_id,
        version_obra_id=plan.version_obra.id,
        version=plan.version_obra.numero,
        capitulos=plan.outline.capitulos,
    )
