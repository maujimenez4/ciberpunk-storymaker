"""Idempotencia por `run_id`: repetir un paso no vuelve a escribir (RF-ORQ-03).

`architecture.md` §3.2 lo dice en una linea —el `run_id` «es la clave de
idempotencia»— y §3.7 lo convierte en el mecanismo de la reanudacion: «un paso
interrumpido se **repite entero**, nunca se reanuda a medias: es posible porque
la salida solo se persiste al completarse y porque el `run_id` evita
duplicados». Este fichero es ese «evita duplicados», y sin el la reanudacion de
T8 arregla una cosa —no perder capitulos— y rompe otra: duplicarlos.

**La idempotencia no es borrar y reescribir.** El ledger es *append-only* y la
Fase 2 lo sujeto en el esquema con `trg_evento_sin_delete`: un `DELETE` sobre
`evento` no es una alternativa mas lenta, es una sentencia que el motor
rechaza. Asi que el guardia decide **antes** de escribir, no limpia despues.

**Y no hay tabla de pasos cumplidos.** La decision se toma con lo que ya esta
en la base, que es el mismo principio que `obra/modelos.py` dejo escrito al
hacer idempotente el cierre de la entrevista: *la idempotencia vive en el dato,
no en la memoria del proceso*. Una tabla aparte seria un segundo relato de lo
ocurrido, que puede divergir del primero justo cuando importa —tras una caida—
y que ademas es esquema y migracion, que no son de esta tarea.

## La clave: `run_id` + paso + ordinal

El `run_id` solo no basta, y merece decirse porque es donde se equivoca la
intuicion. Una corrida escribe en `version_texto` hasta **tres** veces: la
primera vuelta y las dos reparaciones dirigidas de RF-ORQ-04. Con la clave en
el `run_id` a secas, la segunda vuelta seria indistinguible de una repeticion y
el reintento no llegaria a escribirse nunca. Por eso `Paso` lleva tambien de
que paso se trata y **cual de sus vueltas**.

## Los cuatro rastros, y lo que cada uno puede preguntar

| Tabla | Como se reconoce lo ya escrito | Alcance |
| --- | --- | --- |
| `version_texto` | filas de esa escena **con ese `run_id`** | corrida |
| `ejecucion` | filas **con ese `run_id`** | corrida |
| `evento` | filas de esa escena **con ese `run_id`** | corrida |
| `hecho_canon` | filas con esa `escena_de_origen` **y ese `run_id`** | corrida |

**Las dos ultimas se preguntaban por escena hasta la Fase 5**, porque `evento`
y `hecho_canon` no tenian columna `run_id`. Era exacto mientras `EXTRAYENDO`
escribiera una sola vez por escena, y dejo de serlo el dia que una peticion del
lector regenera un capitulo ya integrado (P-6): el rastro por escena daba por
escrita **la corrida de ayer** y la consolidacion de la regeneracion no corria,
dejando en el canon los hechos de la prosa que el lector pidio cambiar. Las
filas anteriores a la migracion tienen `run_id` nulo y no cuentan para ninguna
corrida, que es lo correcto: ninguna corrida de hoy las escribio.

## Lo que el guardia **no** hace

No abre punto de guardado ni confirma nada: decide si el paso corre y devuelve
lo que el paso devolvio. La atomicidad es del paso —`consolidar_escena` ya trae
la suya— y es la condicion que `architecture.md` §3.7 pone para que esto
funcione: un paso que persistiera a medias dejaria rastro sin haber terminado y
el guardia daria por hecho lo que quedo por hacer.

Tampoco se traga los fallos: un paso que revienta revienta, y al no dejar
rastro el siguiente intento vuelve a correrlo entero.

**Las tablas de otras features se leen por SQL con su nombre** —`evento` es de
`canon` y `hecho_canon` de `obra`—, que es el mismo trato que `ciclo.py` y
`contexto/service.py` dan a las suyas: una feature no entra a los ficheros
internos de otra (`CLAUDE.md` §5.1).
"""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

TABLAS_PROTEGIDAS = ("version_texto", "ejecucion", "evento", "hecho_canon")
"""Las cuatro que un paso repetido podria duplicar, y que R-4 nombra una a una.

Estan aqui para que la lista sea legible desde fuera y para que anadir una
quinta sea un cambio visible y no un `SELECT` mas escondido en un metodo.
"""


@dataclass(frozen=True, slots=True)
class Paso:
    """La clave de idempotencia: que corrida, que paso y cual de sus vueltas.

    `nombre` es el del estado que lo ejecuta (`architecture.md` §3.3):
    `ESCRIBIENDO`, `EXTRAYENDO`… No se valida contra la lista de estados a
    proposito, porque un paso no tiene por que ser un estado —`ENSAMBLANDO` y
    `VALIDANDO` comparten uno— y porque esa lista es de `modelos.py`, que no es
    de esta tarea.
    """

    run_id: str
    nombre: str
    ordinal: int = 0

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("Un paso sin `run_id` no tiene clave de idempotencia")
        if not self.nombre:
            raise ValueError("Un paso sin nombre no se distingue de los demas de su corrida")
        if self.ordinal < 0:
            raise ValueError(f"El ordinal de un paso no puede ser negativo: {self.ordinal}")

    @property
    def clave(self) -> str:
        """La clave en una linea, para trazas y mensajes. No se persiste."""
        return f"{self.run_id}:{self.nombre}:{self.ordinal}"


class Rastro(Protocol):
    """Lo que un paso deja escrito en una tabla, preguntado desde fuera.

    Devuelve **el nombre de la tabla** y no un booleano: quien orqueste quiere
    poder decir *por que* dio el paso por hecho, y con un `bool` un paso de dos
    tablas no podria contarlo.
    """

    async def tabla_escrita(self, sesion: AsyncSession, paso: Paso) -> str | None: ...


@dataclass(frozen=True, slots=True)
class RastroEnVersionTexto:
    """La prosa de esta corrida en esta escena (RF-ESC-02).

    Se cuenta y se compara contra el ordinal: tras la primera vuelta hay una
    fila, tras la primera reparacion dos. El paso `k` ya escribio si la corrida
    dejo mas de `k` versiones — que es lo que deja pasar el reintento y frena la
    repeticion.
    """

    escena_id: int

    async def tabla_escrita(self, sesion: AsyncSession, paso: Paso) -> str | None:
        escritas = (
            await sesion.execute(
                text(
                    "SELECT COUNT(*) FROM version_texto "
                    "WHERE escena_id = :escena_id AND run_id = :run_id"
                ),
                {"escena_id": self.escena_id, "run_id": paso.run_id},
            )
        ).scalar_one()
        return "version_texto" if int(escritas) > paso.ordinal else None


@dataclass(frozen=True, slots=True)
class RastroEnEjecucion:
    """Las llamadas al modelo de esta corrida (regla de dominio 7).

    No lleva escena: `ejecucion.escena_id` es nulo en los trabajos de manuscrito
    y el `run_id` ya es de un solo trabajo, asi que acotar por escena excluiria
    precisamente las filas que no la tienen.
    """

    async def tabla_escrita(self, sesion: AsyncSession, paso: Paso) -> str | None:
        escritas = (
            await sesion.execute(
                text("SELECT COUNT(*) FROM ejecucion WHERE run_id = :run_id"),
                {"run_id": paso.run_id},
            )
        ).scalar_one()
        return "ejecucion" if int(escritas) > paso.ordinal else None


@dataclass(frozen=True, slots=True)
class RastroEnEvento:
    """El ledger de **esta corrida** en esta escena (P-6, Fase 5).

    Basta con que haya uno: `EXTRAYENDO` escribe los suyos dentro del punto de
    guardado de `consolidar_escena`, asi que o estan todos o no esta ninguno.
    """

    escena_id: int

    async def tabla_escrita(self, sesion: AsyncSession, paso: Paso) -> str | None:
        hay = (
            await sesion.execute(
                text(
                    "SELECT COUNT(*) FROM evento WHERE escena_id = :escena_id AND run_id = :run_id"
                ),
                {"escena_id": self.escena_id, "run_id": paso.run_id},
            )
        ).scalar_one()
        return "evento" if int(hay) > 0 else None


@dataclass(frozen=True, slots=True)
class RastroEnHechoCanon:
    """Los hechos que **esta corrida** establecio en esta escena (regla 4, P-6).

    Por `escena_de_origen` y no por obra: los hechos de `origen: brief` no la
    tienen, existian antes del texto, y contarlos daria por consolidada una
    escena que todavia no ha escrito nada. Y por corrida, por lo mismo que
    `RastroEnEvento`.

    `escena_de_origen` es texto y no una clave ajena —lo dice `obra/modelos.py`—
    asi que el identificador se compara como cadena.
    """

    escena_id: int

    async def tabla_escrita(self, sesion: AsyncSession, paso: Paso) -> str | None:
        hay = (
            await sesion.execute(
                text(
                    "SELECT COUNT(*) FROM hecho_canon "
                    "WHERE escena_de_origen = :escena AND run_id = :run_id"
                ),
                {"escena": str(self.escena_id), "run_id": paso.run_id},
            )
        ).scalar_one()
        return "hecho_canon" if int(hay) > 0 else None


@dataclass(frozen=True, slots=True)
class RastroCompuesto:
    """Un paso que escribe en varias tablas a la vez, como `EXTRAYENDO`.

    Corrio si **alguna** de ellas tiene rastro, no si todas: las escrituras del
    paso comparten punto de guardado, y exigir las dos daria por no ejecutado un
    paso que si lo fue —por ejemplo el de una escena cuyos hechos ya estaban
    todos en el canon y no anadio ninguno—.
    """

    rastros: tuple[Rastro, ...]

    async def tabla_escrita(self, sesion: AsyncSession, paso: Paso) -> str | None:
        for rastro in self.rastros:
            tabla = await rastro.tabla_escrita(sesion, paso)
            if tabla is not None:
                return tabla
        return None


@dataclass(frozen=True, slots=True)
class ResultadoDelPaso:
    """Si el paso corrio, que devolvio, y —si no— quien lo delato.

    `valor` es `None` en la repeticion y eso no es una perdida: quien reanuda no
    necesita el valor, necesita que la base quede como si el paso hubiera
    corrido una vez. Lo que ya se escribio se lee de la tabla, que es donde
    esta.
    """

    paso: Paso
    repetido: bool
    valor: Any = None
    tabla: str | None = None


async def donde_ya_escribio(sesion: AsyncSession, paso: Paso, rastro: Rastro) -> str | None:
    """La tabla que demuestra que este paso ya corrio, o `None` si no hay ninguna."""
    return await rastro.tabla_escrita(sesion, paso)


async def una_sola_vez(
    sesion: AsyncSession,
    paso: Paso,
    rastro: Rastro,
    escribir: Callable[[], Coroutine[Any, Any, Any]],
) -> ResultadoDelPaso:
    """Corre el paso **si y solo si** no hay rastro suyo. El guardia de R-4.

    `escribir` no recibe nada y devuelve lo que el paso devuelva: es una
    corrutina ya compuesta con sus argumentos, de modo que el guardia no tiene
    que conocer ningun paso concreto — y, sobre todo, **no se la llega a llamar**
    cuando el paso ya corrio. Evitar la fila no bastaria: `ESCRIBIENDO` es el
    unico paso caro de repetir (`architecture.md` §3.7) y lo caro es la llamada,
    no el `INSERT`.
    """
    tabla = await donde_ya_escribio(sesion, paso, rastro)
    if tabla is not None:
        return ResultadoDelPaso(paso=paso, repetido=True, valor=None, tabla=tabla)
    return ResultadoDelPaso(paso=paso, repetido=False, valor=await escribir(), tabla=None)
