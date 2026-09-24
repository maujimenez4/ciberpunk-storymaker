"""RI-07: `GET /capitulos/{id}/contexto`, el paquete y su desglose de tokens.

**Aqui no hay logica** (`CLAUDE.md` §6). El endpoint llama al caso de uso de su
feature y devuelve un modelo de salida; los errores de dominio —`CapaVacia`,
`CapituloDesconocido`, `ContextBudgetExceeded`— los traduce el manejador central
de `commons/errors/`, y por eso esta feature no nombra ni un codigo HTTP.

Es un endpoint de **depuracion**, y eso decide dos cosas. Es un `GET`, asi que
**no escribe `ejecucion`**: una fila de `ejecucion` describe una llamada al
modelo, y mirar el paquete no es llamar. Y devuelve el desglose entero, con las
ocho capas y sus topes, porque lo que se depura con esto es el reparto.

Los modelos de salida viven en este fichero y no en un `schemas.py` porque el
plan lista tres ficheros para esta tarea y son dos modelos sin validacion: lo
unico que hacen es no exponer los objetos del dominio (`CLAUDE.md` §6).
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.db.sesion import obtener_sesion
from app.commons.llm.contador import ContadorDeTokens, ContadorTiktoken
from app.features.contexto.capas import CAPAS_CON_ORIGEN, Paquete
from app.features.contexto.presupuesto import Capa
from app.features.contexto.service import ensamblar_capitulo


def obtener_contador() -> ContadorDeTokens:
    """El contador se compone aqui, y por eso un test puede sustituirlo.

    Es el contador **previo** de P-A: el que decide si el paquete cabe y por
    tanto si se llega a llamar (RF-CTX-02). `ContadorTiktoken` descarga su
    vocabulario la primera vez que cuenta, asi que la suite lo sustituye y no
    paga esa vez (RNF-FIA-01, CA-4).
    """
    return ContadorTiktoken()


Sesion = Annotated[AsyncSession, Depends(obtener_sesion)]
Contador = Annotated[ContadorDeTokens, Depends(obtener_contador)]

router = APIRouter(prefix="/capitulos", tags=["contexto"])


class LineaDelDesglose(BaseModel):
    """Una capa: lo que costo, lo que cabia, y que entro y que se quito.

    `identificadores` y `descartados` van separados a proposito: es la
    diferencia entre lo que el modelo vera y lo que no, y RF-CTX-09 dice que
    solo lo primero se persiste.
    """

    capa: str
    tope: int
    tokens: int
    piezas: int
    identificadores: list[str]
    descartados: int


class PaqueteDeContexto(BaseModel):
    """Lo que se enviaria al modelo, con su desglose (`definitions.md` §7)."""

    capitulo_id: int
    escena_id: int
    version_obra_id: int
    tokens_previstos: int
    reserva_libre: int
    capas: list[LineaDelDesglose]
    texto: str


@router.get("/{capitulo_id}/contexto")
async def contexto_del_capitulo(
    capitulo_id: int, sesion: Sesion, contador: Contador
) -> PaqueteDeContexto:
    """RI-07. Ensambla el paquete y lo devuelve **sin llamar a ningun modelo**."""
    contexto = await ensamblar_capitulo(sesion, capitulo_id, contador)
    return PaqueteDeContexto(
        capitulo_id=contexto.capitulo_id,
        escena_id=contexto.escena_id,
        version_obra_id=contexto.version_obra_id,
        tokens_previstos=contexto.paquete.tokens_previstos,
        reserva_libre=contexto.paquete.desglose.reserva_libre,
        capas=_capas(contexto.paquete),
        texto=contexto.paquete.texto,
    )


def _capas(paquete: Paquete) -> list[LineaDelDesglose]:
    """Las ocho, en el orden de `architecture.md` §2.1 y tambien las vacias.

    Una capa ausente y una capa vacia no son lo mismo, y quien depura no
    deberia tener que adivinar cual era.
    """
    return [
        LineaDelDesglose(
            capa=capa.value,
            tope=linea.tope,
            tokens=linea.tokens,
            piezas=len(linea.piezas),
            identificadores=list(paquete.ids_por_capa.get(capa, ()))
            if capa in CAPAS_CON_ORIGEN
            else [],
            descartados=len(linea.descartadas),
        )
        for capa, linea in ((capa, paquete.desglose.lineas[capa]) for capa in Capa)
    ]
