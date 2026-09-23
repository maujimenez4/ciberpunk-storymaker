"""Endpoints de `escritura` (RI-05, RI-09, RI-19).

Los endpoints **no contienen logica** (`CLAUDE.md` §6): validan la entrada,
delegan en el servicio y devuelven un modelo de respuesta. Aqui eso significa
crear el trabajo y devolver su identificador: la escritura de una escena tarda
minutos y una peticion HTTP que la espere se agota antes de terminar, dejando el
trabajo huerfano y al cliente sin saber si ocurrio.
"""

import functools
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict

from app.commons.config import cargar_ajustes
from app.commons.db import RepositorioDeEjecuciones
from app.commons.domain import Reloj, RelojDelSistema
from app.commons.errors import RecursoNoEncontrado
from app.commons.jobs import (
    CerrojoPorObra,
    EjecutorDeTrabajos,
    RepositorioDeTrabajos,
    turno_del_proceso,
)
from app.commons.llm import (
    CargadorDePrompts,
    ClienteDeClaudeCode,
    ContadorBPE,
    OrdenadorPorModelo,
)
from app.features.canon import RepositorioDeCanon
from app.features.contexto import AlmacenesDeLaObra
from app.features.escena import RepositorioDeEscenas
from app.features.escritura.service import Dependencias, ejecutar_en_segundo_plano
from app.features.obra import RepositorioDeObras

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


def obtener_ejecutor(peticion: Request) -> EjecutorDeTrabajos:
    ejecutor: EjecutorDeTrabajos = peticion.app.state.ejecutor
    return ejecutor


def obtener_dependencias(peticion: Request) -> Dependencias:
    """Arma el ciclo con el proveedor real.

    Es el unico sitio donde `Ajustes.modelo` tiene lector, que era lo que P-106
    dejo prometido: el modelo deja de estar fijado a fuego y pasa a decidirse
    por entorno, donde RI-21 dice que se decide.

    Los tests lo sustituyen entero con `dependency_overrides`; no hay una rama
    «si es prueba» aqui dentro, que es la forma habitual de que el camino
    probado y el real dejen de ser el mismo.
    """
    ruta = peticion.app.state.ruta_base_de_datos
    ajustes = cargar_ajustes()
    cargador = CargadorDePrompts(peticion.app.state.ruta_prompts)
    cliente = ClienteDeClaudeCode(modelo=ajustes.modelo)
    return Dependencias(
        reloj=RelojDelSistema(),
        contador=ContadorBPE(),
        cargador=cargador,
        turno=turno_del_proceso(ajustes.llamadas_simultaneas),
        cerrojo=CerrojoPorObra(),
        ordenador=OrdenadorPorModelo(cliente, cargador.cargar("ordenador").texto),
        planificador=cliente,
        escritor=cliente,
        extractor=cliente,
        trabajos=RepositorioDeTrabajos(ruta),
        escenas=RepositorioDeEscenas(ruta),
        canon=RepositorioDeCanon(ruta),
        ejecuciones=RepositorioDeEjecuciones(ruta),
        obras=RepositorioDeObras(ruta),
        almacenes=AlmacenesDeLaObra(ruta),
        snapshot_cada_n=ajustes.snapshot_cada_n_escenas,
    )


@router.post(
    "/escenas/{escena_id}/escribir", status_code=202, response_model=TrabajoAceptado
)
def escribir_escena(
    escena_id: str,
    obra_id: str,
    repositorio: Annotated[RepositorioDeTrabajos, Depends(obtener_repositorio)],
    reloj: Annotated[Reloj, Depends(obtener_reloj)],
    ejecutor: Annotated[EjecutorDeTrabajos, Depends(obtener_ejecutor)],
    dep: Annotated[Dependencias, Depends(obtener_dependencias)],
    serie_id: str = "s1",
) -> TrabajoAceptado:
    """RI-05. Devuelve 202 y el trabajo; no espera a que el modelo escriba.

    El trabajo se crea **aqui** y no dentro del ciclo porque el cliente necesita
    su identificador ya, para poder preguntar por el mientras corre.
    """
    trabajo = repositorio.crear(obra_id, escena_id, "escribir_escena", reloj)
    ejecutor.encolar(
        functools.partial(
            ejecutar_en_segundo_plano,
            trabajo.trabajo_id,
            escena_id,
            obra_id,
            serie_id,
            dep,
        )
    )
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
