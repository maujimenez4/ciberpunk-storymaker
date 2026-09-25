"""RI-05 y RI-06: lanzar el ciclo de un capitulo, y consultar su trabajo.

**Aqui no hay logica** (`CLAUDE.md` §6). Los dos endpoints validan la entrada,
llaman a un caso de uso de su feature y devuelven un modelo de salida; los
errores de dominio los traduce el manejador central de `commons/errors/`, y por
eso este fichero no nombra ni un codigo HTTP de error.

**Lo que si se decide aqui es la composicion, y es la mitad de T11.** Tres
piezas del proceso viven en este fichero porque no pueden vivir en ningun otro:

| Pieza | Por que aqui |
| --- | --- |
| `PresupuestoConcurrente` | Es **uno por proceso** (RF-ORQ-10). Si lo creara el ciclo, habria uno por trabajo y el techo se cumpliria «por consecuencia y no por regla» |
| `CerrojoDeEscena` | Igual: una escena en vuelo **por obra** no se puede acotar con un cerrojo por peticion |
| Los tres agentes | Se componen con el cliente inyectado, que es lo que deja a un test sustituirlo sin tocar produccion (CA-4) |

**Escribir un capitulo es un trabajo en segundo plano**, no una peticion que
espera (`CLAUDE.md` §6): el endpoint crea el `Trabajo`, responde 202 con su id y
el ciclo sigue. Por eso la tarea de fondo **abre su propia sesion**: desde
FastAPI 0.106 las dependencias con `yield` se cierran antes de enviar la
respuesta, asi que la sesion de la peticion ya no existe cuando la tarea corre.
`obtener_sesion_de_fondo` es lo que hace esa fabrica sustituible en pruebas.
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Literal, Protocol, runtime_checkable

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.db.sesion import obtener_motor, obtener_sesion
from app.commons.jobs.turnos import CerrojoDeEscena, PresupuestoConcurrente
from app.commons.llm.cliente import ClienteModelo, obtener_cliente_modelo
from app.commons.llm.contador import ContadorDeTokens, ContadorTiktoken
from app.commons.observabilidad import ClienteObservado, Observador, obtener_observador
from app.features.calidad import Continuista, Critico, rubrica_vigente
from app.features.canon import Extractor, Vector, vectorizador_de
from app.features.escena import Planificador
from app.features.escritura.agents import Escritor
from app.features.escritura.ciclo import Agentes, abrir_trabajo, ejecutar_ciclo, leer_trabajo
from app.features.escritura.novela import (
    avance_de_la_novela,
    ciclo_de_la_novela,
    escribir_novela,
    numero_de_capitulo,
)
from app.features.escritura.peticion import (
    Revalidar,
    atender_peticion,
    avance_de_la_peticion,
    ciclo_de_la_peticion,
    registrar_peticion,
    revalidar_mecanicamente,
)
from app.features.escritura.reanudacion import planificar_reanudacion
from app.features.escritura.regeneracion import Ejecutar
from app.features.escritura.service import intentos_descartados
from app.features.manuscrito import (
    PeticionDesconocida,
    leer_peticion,
    peticion_en_curso,
    token_de_la_version,
    version_por_token,
)

FabricaDeSesion = Callable[[], AbstractAsyncContextManager[AsyncSession]]


@lru_cache(maxsize=1)
def obtener_presupuesto() -> PresupuestoConcurrente:
    """El portero del proceso. **Uno, y el mismo para todos los trabajos.**

    `lru_cache` y no una variable de modulo para que la instancia nazca la
    primera vez que alguien la pide y no al importar: importar `app.main` no
    debe construir nada del ciclo (es lo que T1 dejo probado del cliente real).

    Que sea uno solo es RF-ORQ-10 y no una optimizacion: el techo concurrente es
    **la suma de los tokens en vuelo del proceso**, y una instancia por trabajo
    contaria cada trabajo contra un techo propio. El sistema cumpliria el limite
    mientras hubiera un solo trabajo —«por consecuencia y no por regla»— y lo
    incumpliria en cuanto hubiera dos, sin que fallara ni uno de los dieciseis
    tests de T10, porque ninguno mira quien lo instancia.
    """
    return PresupuestoConcurrente()


@lru_cache(maxsize=1)
def obtener_cerrojo() -> CerrojoDeEscena:
    """Una escena en vuelo **por obra** (RF-ORQ-08), y por el mismo motivo: un
    cerrojo por peticion no acota nada."""
    return CerrojoDeEscena()


def obtener_contador() -> ContadorDeTokens:
    """El contador **previo** de P-A: el que decide si el paquete cabe y por
    tanto si se llega a llamar (RF-CTX-02).

    Es la misma composicion que hace `contexto/router.py`, duplicada a
    proposito: `CLAUDE.md` §5.1, regla 4 —se duplica primero y sube a `commons/`
    al tercer uso real—, y `obtener_contador` no sale por el `__init__.py` de
    `contexto` porque es transporte, no dominio.
    """
    return ContadorTiktoken()


@runtime_checkable
class _ClienteQueDeclaraModelo(Protocol):
    @property
    def modelo(self) -> str: ...


def _nombre_del_modelo(cliente: ClienteModelo) -> str:
    """Que modelo queda escrito en `ejecucion` (regla de dominio 7).

    Se pregunta al cliente en vez de importarlo de `commons/llm/claude_code.py`,
    que arrastra el SDK al importar y dejaria de ser cierto que importar
    `app.main` no abre ningun proceso.

    Si el cliente no lo declara se guarda **el nombre de su clase**, que para un
    doble es `DobleDeterminista`: es informacion verdadera y auditable, y mejor
    que un «desconocido» que no distingue «no habia modelo» de «no se pregunto».
    """
    if isinstance(cliente, _ClienteQueDeclaraModelo):
        return cliente.modelo
    return type(cliente).__name__


def obtener_agentes(
    cliente: Annotated[ClienteModelo, Depends(obtener_cliente_modelo)],
) -> Agentes:
    """Los roles del ciclo, compuestos aqui y no dentro del servicio (RI-14).

    **El Continuista se construye aqui, y esa linea es P-17.** Mientras no
    estuviera, el cableado del ciclo podia estar escrito y probado y la novela
    salia igual sin una sola comprobacion de continuidad: lo que decide si un rol
    corre no es que exista el campo, es que alguien lo rellene en el camino que
    usa la peticion.

    **Y los cinco se construyen sobre el cliente observado**, el mismo objeto que
    va en `observado`: es lo que lleva el prompt renderizado y la salida de cada
    rol a su span (`CLAUDE.md` §4.3). La misma leccion que P-17: el observador
    estaba escrito y probado, y en esta funcion no aparecia.
    """
    observado = ClienteObservado(cliente)
    return Agentes(
        planificador=Planificador(observado),
        escritor=Escritor(observado),
        extractor=Extractor(observado),
        continuista=Continuista(observado),
        # `rubrica_vigente()` y no `RUBRICA_V1`: `CA-20` pide que la rubrica
        # del juez y la que se le presenta al Autor sean **la misma**, y dos
        # objetos iguales pero distintos midirian dos reglas.
        critico=Critico(observado, rubrica_vigente()),
        observado=observado,
    )


@asynccontextmanager
async def _sesion_propia() -> AsyncIterator[AsyncSession]:
    """Una sesion para la tarea de fondo, que vive mas que la peticion."""
    async with AsyncSession(obtener_motor(), expire_on_commit=False) as sesion:
        yield sesion


def obtener_sesion_de_fondo() -> FabricaDeSesion:
    """La fabrica de sesiones del trabajo en segundo plano.

    Es una dependencia y no una llamada directa para que un test la sustituya
    por la suya: sin eso, la tarea de fondo escribiria en la base de la maquina
    y el test contaria filas sobre otra.
    """
    return _sesion_propia


Sesion = Annotated[AsyncSession, Depends(obtener_sesion)]
Fabrica = Annotated[FabricaDeSesion, Depends(obtener_sesion_de_fondo)]
Contador = Annotated[ContadorDeTokens, Depends(obtener_contador)]
Portero = Annotated[PresupuestoConcurrente, Depends(obtener_presupuesto)]
Cerrojo = Annotated[CerrojoDeEscena, Depends(obtener_cerrojo)]
Roles = Annotated[Agentes, Depends(obtener_agentes)]
Cliente = Annotated[ClienteModelo, Depends(obtener_cliente_modelo)]
Observa = Annotated[Observador, Depends(obtener_observador)]
"""Llega **blindado** o nulo (`obtener_observador`), y baja a la tarea de fondo
como `cliente` y `contador`: por argumento, sin globales."""

router = APIRouter(tags=["escritura"])


class TrabajoLanzado(BaseModel):
    """Lo que devuelve RI-05: el identificador con el que se consulta despues."""

    id: int
    estado: str
    run_id: str


class EstadoDelTrabajo(BaseModel):
    """RI-06. Es la unidad de trabajo de `architecture.md` §3.2, sin la fila.

    **Lleva el capitulo, y eso es lo que RI-06 pide cuando dice «legible por
    capitulo»**: hasta la Fase 3 salia `escena_id` y nada mas, y con diez
    trabajos abiertos no habia forma de saber cual era el del capitulo siete sin
    consultar otra tabla. Va el numero de outline junto al identificador por lo
    mismo que `Checkpoint` lo lleva: quien pregunta razona en numeros, y una
    clave primaria no dice cuanto queda.
    """

    id: int
    obra_id: int
    capitulo_id: int | None
    numero_de_capitulo: int | None
    escena_id: int | None
    tipo: str
    estado: str
    intento: int
    run_id: str
    causa_fallo: str | None


@router.post("/capitulos/{capitulo_id}/escribir", status_code=status.HTTP_202_ACCEPTED)
async def escribir(
    capitulo_id: int,
    tareas: BackgroundTasks,
    sesion: Sesion,
    fabrica: Fabrica,
    agentes: Roles,
    contador: Contador,
    presupuesto: Portero,
    cerrojo: Cerrojo,
    cliente: Cliente,
    observador: Observa,
) -> TrabajoLanzado:
    """RI-05. Crea el trabajo, lo devuelve, y el ciclo sigue por detras."""
    trabajo = await abrir_trabajo(sesion, capitulo_id=capitulo_id)
    await sesion.commit()
    tareas.add_task(
        _correr_el_ciclo,
        fabrica,
        trabajo.id,
        capitulo_id,
        agentes=agentes,
        contador=contador,
        presupuesto=presupuesto,
        cerrojo=cerrojo,
        modelo=_nombre_del_modelo(cliente),
        # El vector del capitulo integrado, para que el indice se llene en
        # produccion. `vectorizador_de` vive en `canon` a proposito: repetir la
        # traduccion en cada sitio que ejecute un ciclo la escribiria mal en
        # alguno, y el sintoma seria un `embedding.modelo` equivocado que no
        # rompe nada hoy y hace incomparables los vectores manana.
        vectorizar=vectorizador_de(cliente),
        observador=observador,
    )
    return TrabajoLanzado(id=trabajo.id, estado=trabajo.estado, run_id=trabajo.run_id)


@router.get("/trabajos/{trabajo_id}")
async def consultar(trabajo_id: int, sesion: Sesion) -> EstadoDelTrabajo:
    """RI-06. El estado del trabajo, que es lo que el frontend consulta."""
    trabajo = await leer_trabajo(sesion, trabajo_id)
    return EstadoDelTrabajo(
        id=trabajo.id,
        obra_id=trabajo.obra_id,
        capitulo_id=trabajo.capitulo_id,
        numero_de_capitulo=await numero_de_capitulo(sesion, capitulo_id=trabajo.capitulo_id),
        escena_id=trabajo.escena_id,
        tipo=trabajo.tipo,
        estado=trabajo.estado,
        intento=trabajo.intento,
        run_id=trabajo.run_id,
        causa_fallo=trabajo.causa_fallo,
    )


class DefectoCitado(BaseModel):
    """Un bloqueante de un intento descartado: su codigo y el pasaje citado."""

    codigo: str
    cita: str


class IntentoDescartadoSalida(BaseModel):
    """P-20: un intento que la puerta rechazo, con lo necesario para decidir.

    Distingue «el modelo escribio mal tres veces» de «un validador rechaza
    siempre»: si los tres llevan el mismo codigo sobre textos distintos, el
    sospechoso es el validador.
    """

    numero: int
    texto: str
    defectos: list[DefectoCitado]
    termino_vetado: str | None


@router.get("/trabajos/{trabajo_id}/intentos")
async def consultar_intentos(trabajo_id: int, sesion: Sesion) -> list[IntentoDescartadoSalida]:
    """P-20. Los intentos rechazados del trabajo, escale o no. 404 si no existe."""
    await leer_trabajo(sesion, trabajo_id)
    return [
        IntentoDescartadoSalida.model_validate(fila, from_attributes=True)
        for fila in await intentos_descartados(sesion, trabajo_id)
    ]


class NovelaLanzada(BaseModel):
    """Lo que devuelve el arranque de la novela: **por donde va a empezar**.

    No lleva identificadores de trabajo porque todavia no existen —los abre el
    bucle, uno por capitulo— y prometerlos obligaria a abrirlos por adelantado,
    que es justo lo que la secuencia prohibe. Lo que se devuelve es lo unico
    cierto en ese instante: de que obra se trata y cual es el capitulo pendiente.
    El progreso de la novela se consulta despues por `GET /obras/{id}/novela`,
    y el de cada capitulo por `GET /trabajos/{id}` (RI-06).
    """

    obra_id: int
    desde_el_capitulo: int | None
    terminada: bool


@router.post("/obras/{obra_id}/novela", status_code=status.HTTP_202_ACCEPTED)
async def escribir_la_novela(
    obra_id: int,
    tareas: BackgroundTasks,
    sesion: Sesion,
    fabrica: Fabrica,
    agentes: Roles,
    contador: Contador,
    presupuesto: Portero,
    cerrojo: Cerrojo,
    cliente: Cliente,
    observador: Observa,
) -> NovelaLanzada:
    """`CA-1`: arranca —o reanuda— la novela entera, y responde con por donde va.

    **Es un trabajo de fondo y no una peticion que espera** (`CLAUDE.md` §6):
    diez capitulos son diez llamadas al modelo, y una respuesta HTTP que las
    aguardara no es una respuesta, es un tiempo de espera.

    **Y arrancar y reanudar son el mismo endpoint**, porque son la misma
    llamada: `escribir_novela` pide siempre el primer capitulo no integrado, asi
    que sobre una obra recien planificada empieza por el uno y sobre una que se
    cayo sigue por donde estaba. Dos endpoints obligarian a quien llama a saber
    cual de los dos casos tiene, que es precisamente lo que no se sabe despues
    de una caida.
    """
    plan = await planificar_reanudacion(sesion, obra_id=obra_id)
    tareas.add_task(
        _correr_la_novela,
        fabrica,
        obra_id,
        agentes=agentes,
        contador=contador,
        presupuesto=presupuesto,
        cerrojo=cerrojo,
        modelo=_nombre_del_modelo(cliente),
        vectorizar=vectorizador_de(cliente),
        observador=observador,
    )
    return NovelaLanzada(
        obra_id=obra_id,
        desde_el_capitulo=None if plan.pendiente is None else plan.pendiente.numero,
        terminada=plan.terminada,
    )


class EstadoDeLaNovela(BaseModel):
    """Por donde va la novela: lo que el navegador consulta mientras espera.

    `en_curso` es el **numero de outline** del capitulo que se esta escribiendo,
    no su id, por lo mismo que `EstadoDelTrabajo` lleva `numero_de_capitulo`.
    `motivo` solo va relleno cuando `estado` es `detenida`.
    """

    obra_id: int
    total: int
    integrados: int
    en_curso: int | None
    estado: Literal["sin_outline", "escribiendo", "terminada", "detenida"]
    motivo: str | None


@router.get("/obras/{obra_id}/novela")
async def consultar_la_novela(obra_id: int, sesion: Sesion) -> EstadoDeLaNovela:
    """Cuantos capitulos hay, cuantos estan integrados, y si la novela sigue."""
    avance = await avance_de_la_novela(sesion, obra_id=obra_id)
    return EstadoDeLaNovela.model_validate(avance, from_attributes=True)


async def _correr_el_ciclo(
    fabrica: FabricaDeSesion,
    trabajo_id: int,
    capitulo_id: int,
    *,
    agentes: Agentes,
    contador: ContadorDeTokens,
    presupuesto: PresupuestoConcurrente,
    cerrojo: CerrojoDeEscena,
    modelo: str,
    vectorizar: Callable[[str], Vector],
    observador: Observador,
) -> None:
    """La tarea de fondo: abre sesion, relee el trabajo y ejecuta el ciclo.

    Relee el `Trabajo` en vez de arrastrar el objeto de la peticion porque la
    sesion es otra, y un objeto de SQLAlchemy pertenece a la suya. Es ademas lo
    que `architecture.md` §3.4 pide de cada paso: persistir la salida y volver a
    leerla, que es lo que hace que reanudar sea identico a ejecutar.
    """
    async with fabrica() as sesion:
        trabajo = await leer_trabajo(sesion, trabajo_id)
        await ejecutar_ciclo(
            sesion,
            trabajo,
            capitulo_id=capitulo_id,
            agentes=agentes,
            contador=contador,
            presupuesto=presupuesto,
            cerrojo=cerrojo,
            modelo=modelo,
            vectorizar=vectorizar,
            observador=observador,
        )


async def _correr_la_novela(
    fabrica: FabricaDeSesion,
    obra_id: int,
    *,
    agentes: Agentes,
    contador: ContadorDeTokens,
    presupuesto: PresupuestoConcurrente,
    cerrojo: CerrojoDeEscena,
    modelo: str,
    vectorizar: Callable[[str], Vector],
    observador: Observador,
) -> None:
    """La tarea de fondo de la novela: abre su sesion y recorre los capitulos.

    Abre sesion propia por lo mismo que `_correr_el_ciclo`: desde FastAPI 0.106
    la de la peticion ya esta cerrada cuando la tarea corre. Y aqui pesa mas,
    porque esta tarea vive lo que tarden diez capitulos.

    **Se reanuda sola ante un fallo transitorio**, hasta `_REANUDACIONES_AUTOMATICAS`
    veces: un `database is locked` con varias obras a la vez, o una salida mal
    formada de un agente que ya agoto su reintento. La novela ya sabe reanudarse
    desde su checkpoint (CA-5); en la corrida real del 2026-09-24 cada uno de esos
    fallos la dejaba parada con la pantalla diciendo «escribiendo». Una escalada
    no es excepcion: detiene la novela a proposito y no se reintenta.
    """
    for intento in range(_REANUDACIONES_AUTOMATICAS + 1):
        try:
            async with fabrica() as sesion:
                await escribir_novela(
                    sesion,
                    obra_id=obra_id,
                    ejecutar=ciclo_de_la_novela(
                        sesion,
                        agentes=agentes,
                        contador=contador,
                        presupuesto=presupuesto,
                        cerrojo=cerrojo,
                        modelo=modelo,
                        vectorizar=vectorizar,
                        observador=observador,
                    ),
                )
            return
        except Exception as error:
            if intento == _REANUDACIONES_AUTOMATICAS or not _es_transitorio(error):
                raise
            _log.warning(
                "obra %s: %s; se reanuda en %s s (intento %s de %s)",
                obra_id,
                type(error).__name__,
                _ESPERA_ANTES_DE_REANUDAR,
                intento + 1,
                _REANUDACIONES_AUTOMATICAS,
            )
            await asyncio.sleep(_ESPERA_ANTES_DE_REANUDAR)


_REANUDACIONES_AUTOMATICAS = 3
_ESPERA_ANTES_DE_REANUDAR = 10
_log = logging.getLogger(__name__)


def _es_transitorio(error: BaseException) -> bool:
    """Un cerrojo de SQLite o una salida mal formada de un agente: se reintenta."""
    nombre = type(error).__name__
    return ("database is locked" in str(error)) or nombre == "SalidaMalFormada"


# --- La peticion de cambio (plan-5 T8, RI-09) -------------------------------
#
# Vive aqui y no en `manuscrito/router.py` por lo mismo que la orquestacion vive
# en `escritura/peticion.py`: atenderla compone el ciclo, y el ciclo -- con su
# portero, su cerrojo y sus agentes -- se compone en este fichero. Las rutas del
# lector van por el **token** (RNF-SEG-01, D-01 de la 002), igual que la lectura.


@lru_cache(maxsize=1)
def obtener_cerrojo_de_peticiones() -> CerrojoDeEscena:
    """R-4: una peticion en vuelo por obra. **Otro** cerrojo que el de escenas:
    `ejecutar_ciclo` toma aquel dentro, y no es reentrante."""
    return CerrojoDeEscena()


@dataclass(frozen=True)
class Atencion:
    """Lo que la tarea de fondo necesita para atender una peticion, ya compuesto.

    Es una dependencia para que un test sustituya el ciclo y la revalidacion sin
    tocar produccion (CA-4): la orquestacion, la base y la publicacion son reales.
    """

    componer: Callable[[AsyncSession], Ejecutar]
    revalidar: Revalidar
    vectorizar: Callable[[str], Vector] | None
    observador: Observador | None


def obtener_atencion(
    agentes: Roles,
    contador: Contador,
    presupuesto: Portero,
    cerrojo: Cerrojo,
    cliente: Cliente,
    observador: Observa,
) -> Atencion:
    vectorizar = vectorizador_de(cliente)
    modelo = _nombre_del_modelo(cliente)

    def componer(sesion: AsyncSession) -> Ejecutar:
        return ciclo_de_la_peticion(
            sesion,
            agentes=agentes,
            contador=contador,
            presupuesto=presupuesto,
            cerrojo=cerrojo,
            vectorizar=vectorizar,
            modelo=modelo,
            observador=observador,
        )

    return Atencion(
        componer=componer,
        revalidar=revalidar_mecanicamente,
        vectorizar=vectorizar,
        observador=observador,
    )


class PeticionEntrada(BaseModel):
    """RF-PET-01. El id dice **que** se corrige; el texto, que deberia poner (D-02)."""

    hecho_canon_id: int
    texto_pedido: str = Field(min_length=1, max_length=2000)


class PeticionAceptada(BaseModel):
    peticion_id: int
    estado: Literal["registrada"]


class CapituloEnRegeneracion(BaseModel):
    numero: int
    estado: Literal["pendiente", "escribiendo", "hecho"]


class EstadoDeLaPeticion(BaseModel):
    """Lo que la espera de la 002 consulta (RF-ESP-02)."""

    peticion_id: int
    estado: Literal["registrada", "regenerando", "atendida", "descartada"]
    resultado: str | None
    capitulos: list[CapituloEnRegeneracion]
    token_resultante: str | None


class EstadoDeLaLectura(BaseModel):
    """H-3 de la 002: si hay una regeneracion en curso que este navegador no pidio."""

    peticion_en_curso: int | None


lectura = APIRouter(prefix="/lectura", tags=["lectura"])

NO_ENCONTRADO = "No hay nada en este enlace."
"""El mismo texto que `manuscrito/router.py`: un token que no vale no dice por que."""

AtencionDep = Annotated[Atencion, Depends(obtener_atencion)]
CerrojoDePeticiones = Annotated[CerrojoDeEscena, Depends(obtener_cerrojo_de_peticiones)]


async def _obra_del_token(sesion: AsyncSession, token: str) -> int:
    version = await version_por_token(sesion, token)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    return version.obra_id


async def _lanzar_peticion(
    sesion: AsyncSession,
    tareas: BackgroundTasks,
    fabrica: FabricaDeSesion,
    atencion: Atencion,
    cerrojo: CerrojoDeEscena,
    *,
    obra_id: int,
    entrada: PeticionEntrada,
) -> PeticionAceptada:
    peticion = await registrar_peticion(
        sesion,
        obra_id=obra_id,
        hecho_canon_id=entrada.hecho_canon_id,
        texto_pedido=entrada.texto_pedido,
    )
    await sesion.commit()
    tareas.add_task(_atender_en_segundo_plano, fabrica, peticion.id, atencion, cerrojo)
    return PeticionAceptada(peticion_id=peticion.id, estado="registrada")


@lectura.post("/{token}/peticiones", status_code=status.HTTP_202_ACCEPTED)
async def pedir_un_cambio_desde_la_lectura(
    token: str,
    entrada: PeticionEntrada,
    tareas: BackgroundTasks,
    sesion: Sesion,
    fabrica: Fabrica,
    atencion: AtencionDep,
    cerrojo: CerrojoDePeticiones,
) -> PeticionAceptada:
    """RI-09 por el token. 202 y el trabajo sigue detras (`CLAUDE.md` §6); 409 si
    el hecho ya fue sustituido (R-5), 404 si no es de esta obra."""
    obra_id = await _obra_del_token(sesion, token)
    return await _lanzar_peticion(
        sesion, tareas, fabrica, atencion, cerrojo, obra_id=obra_id, entrada=entrada
    )


@router.post("/obras/{obra_id}/peticiones", status_code=status.HTTP_202_ACCEPTED)
async def pedir_un_cambio(
    obra_id: int,
    entrada: PeticionEntrada,
    tareas: BackgroundTasks,
    sesion: Sesion,
    fabrica: Fabrica,
    atencion: AtencionDep,
    cerrojo: CerrojoDePeticiones,
) -> PeticionAceptada:
    """RI-09 tal como la spec lo nombra, por `obra_id`: la del Autor."""
    return await _lanzar_peticion(
        sesion, tareas, fabrica, atencion, cerrojo, obra_id=obra_id, entrada=entrada
    )


@lectura.get("/{token}/peticiones/{peticion_id}")
async def consultar_la_peticion(token: str, peticion_id: int, sesion: Sesion) -> EstadoDeLaPeticion:
    """El estado de la peticion y su avance por capitulo. 404 si es de otra obra."""
    obra_id = await _obra_del_token(sesion, token)
    peticion = await leer_peticion(sesion, peticion_id)
    if peticion.obra_id != obra_id:
        raise PeticionDesconocida(peticion_id)
    token_resultante = (
        None
        if peticion.estado != "atendida" or peticion.version_producida_id is None
        else await token_de_la_version(sesion, peticion.version_producida_id)
    )
    return EstadoDeLaPeticion.model_validate(
        {
            "peticion_id": peticion.id,
            "estado": peticion.estado,
            "resultado": peticion.resultado,
            "capitulos": [
                {"numero": n, "estado": e} for n, e in await avance_de_la_peticion(sesion, peticion)
            ],
            "token_resultante": token_resultante,
        }
    )


@lectura.get("/{token}/estado")
async def estado_de_la_lectura(token: str, sesion: Sesion) -> EstadoDeLaLectura:
    obra_id = await _obra_del_token(sesion, token)
    return EstadoDeLaLectura(peticion_en_curso=await peticion_en_curso(sesion, obra_id=obra_id))


async def _atender_en_segundo_plano(
    fabrica: FabricaDeSesion,
    peticion_id: int,
    atencion: Atencion,
    cerrojo: CerrojoDeEscena,
) -> None:
    """Sesion propia, como `_correr_el_ciclo`: la de la peticion ya se cerro."""
    async with fabrica() as sesion:
        await atender_peticion(
            sesion,
            peticion_id=peticion_id,
            ejecutar=atencion.componer(sesion),
            cerrojo=cerrojo,
            revalidar=atencion.revalidar,
            vectorizar=atencion.vectorizar,
            observador=atencion.observador,
        )
