"""El techo concurrente: se da turno contando tokens, no llamadas.

**Hay dos techos de tokens y este es el segundo** (`architecture.md` §2.2). El
de *una* llamada —100.000 repartidos en ocho capas— lo comprueba el Ensamblador
al construir el paquete, y si no cabe lanza `ContextBudgetExceeded` sin llegar
a llamar. El de aqui es el **presupuesto concurrente**: la suma de los tokens
de las llamadas **en vuelo** de un proceso, que es lo que el encargo §7 pide
literalmente. Que las dos cifras sean 100.000 es **casualidad de numeros, no
el mismo limite** (`definitions.md` §9), y confundirlos es exactamente lo que
dejo el §7 sin cumplir hasta el 2026-09-23: con la concurrencia en 1 la suma
*era* esa unica llamada, asi que el sistema cumplia por consecuencia y no por
regla, y subirla a dos habria incumplido el encargo sin que fallara un test.

Dos piezas, y no una, porque acotan cosas distintas:

| Pieza | Que acota | Requisito |
| --- | --- | --- |
| `PresupuestoConcurrente` | La **suma de tokens** en vuelo del proceso | RF-ORQ-10 |
| `CerrojoDeEscena` | Una **escena** en vuelo **por obra** | RF-ORQ-08 |

Tres invariantes que conviene leer antes de tocar nada:

1. **El techo se hace cumplir esperando, nunca recortando.** Si admitir una
   llamada haria pasar la suma del techo, esa llamada espera. Recortar el
   paquete obedece a §2.1 y a lo que pide la escena, no a la carga del
   proceso: un paquete que se recorta por congestion produce prosa peor sin
   que nadie se entere.
2. **Se cuenta en tokens y no en llamadas.** Un semaforo de N llamadas no
   sirve: con N=1 se cumple el techo serializando todo, que es justo lo que
   P-06 decidio dejar de hacer; con N>1 se incumple en cuanto dos paquetes
   grandes coinciden.
3. **El contador en vuelo es observable y la reserva se hace al conceder el
   turno**, no cuando la tarea admitida despierta. Un contador implicito no se
   puede probar, y una reserva diferida deja una ventana en la que dos
   llamadas se creen dentro del techo.

**El reparto es FIFO estricto**: si el primero de la cola no cabe, nadie de
detras se cuela aunque quepa. Deja turno sin usar en algun instante y a cambio
no hay inanicion — un paquete grande no se queda esperando indefinidamente
mientras pasan pequenos. Con diez capitulos secuenciales por obra la perdida es
teorica; la inanicion, en cambio, se manifestaria como un capitulo que nunca
termina.

**Los dos techos son por proceso** (§2.2, regla 3): por eso en modo servidor
los trabajos corren en el proceso de la API. Repartirlos en un *worker* aparte
duplicaria los dos en silencio.
"""

import asyncio
from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from app.commons.domain.errores import TiempoAgotado

TECHO_CONCURRENTE = 100_000
"""Suma maxima de tokens en vuelo. Del encargo §7, literal: «concurrentes»."""


@dataclass
class _EnEspera:
    """Una llamada en la cola: cuanto pide, y por donde se la avisa."""

    tokens: int
    paso: str
    plazo: float | None
    espera: asyncio.Future[None]
    temporizador: asyncio.TimerHandle | None = field(default=None)


class PresupuestoConcurrente:
    """Reparte turnos de modo que la suma de tokens en vuelo no pase del techo.

    No sabe nada de modelos ni de proveedores: es un portero. Quien tiene turno
    llama; quien no, espera. Se instancia **uno por proceso** y se inyecta.
    """

    def __init__(self, techo: int = TECHO_CONCURRENTE) -> None:
        self._techo = techo
        self._tokens_en_vuelo = 0
        self._llamadas_en_vuelo = 0
        self._cola: deque[_EnEspera] = deque()

    @property
    def techo(self) -> int:
        return self._techo

    @property
    def tokens_en_vuelo(self) -> int:
        """Suma de los tokens de las llamadas con turno concedido, ahora mismo."""
        return self._tokens_en_vuelo

    @property
    def llamadas_en_vuelo(self) -> int:
        """Cuantas son. Es informativo: el turno **no** se da contando esto."""
        return self._llamadas_en_vuelo

    @asynccontextmanager
    async def turno(
        self,
        tokens: int,
        *,
        espera_maxima: float | None = None,
        paso: str = "espera de turno",
    ) -> AsyncIterator[None]:
        """Espera turno para un paquete de `tokens` y lo devuelve al salir.

        Si `espera_maxima` vence sin turno, lanza `TiempoAgotado` **sin haber
        llamado a nadie**: el trabajo pasa a `FALLIDA` y es relanzable sin coste
        (`architecture.md` §3.6). Sin `espera_maxima`, espera lo que haga falta.
        """
        await self._pedir(tokens, espera_maxima, paso)
        try:
            yield
        finally:
            self._devolver(tokens)

    async def _pedir(self, tokens: int, plazo: float | None, paso: str) -> None:
        if tokens < 0:
            raise ValueError(f"Un paquete no puede pedir {tokens} tokens")
        if tokens > self._techo:
            # No cabria ni con el proceso vacio, asi que esperar seria colgarse.
            # El techo por llamada es cosa del Ensamblador (RF-CTX-03), que ya
            # habria lanzado `ContextBudgetExceeded`: llegar aqui es un fallo de
            # programa, no una regla de negocio incumplida, y por eso no es un
            # `ErrorDeDominio`.
            raise ValueError(
                f"El paquete pide {tokens} tokens y el techo concurrente es {self._techo}: "
                "no cabe ni sin nadie en vuelo"
            )

        if not self._cola and self._cabe(tokens):
            self._admitir(tokens)
            return

        bucle = asyncio.get_running_loop()
        entrada = _EnEspera(tokens=tokens, paso=paso, plazo=plazo, espera=bucle.create_future())
        self._cola.append(entrada)
        if plazo is not None:
            entrada.temporizador = bucle.call_later(plazo, self._vencer, entrada)
        try:
            await entrada.espera
        except asyncio.CancelledError:
            # Puede llegar cuando ya se habia concedido el turno y la reserva
            # esta hecha: se devuelve, o quedaria contada para siempre.
            if entrada.espera.done() and not entrada.espera.cancelled():
                self._devolver(tokens)
            else:
                self._retirar(entrada)
            raise
        finally:
            if entrada.temporizador is not None:
                entrada.temporizador.cancel()

    def _cabe(self, tokens: int) -> bool:
        # «No mas de»: el techo es alcanzable. Rechazar la suma exacta dejaria
        # fuera paquetes legitimos sin que nadie supiera por que.
        return self._tokens_en_vuelo + tokens <= self._techo

    def _admitir(self, tokens: int) -> None:
        self._tokens_en_vuelo += tokens
        self._llamadas_en_vuelo += 1

    def _devolver(self, tokens: int) -> None:
        self._tokens_en_vuelo -= tokens
        self._llamadas_en_vuelo -= 1
        self._servir_cola()

    def _servir_cola(self) -> None:
        """Da turno a los primeros de la cola que quepan. FIFO estricto."""
        while self._cola:
            entrada = self._cola[0]
            if entrada.espera.done():
                self._cola.popleft()
                continue
            if not self._cabe(entrada.tokens):
                return
            self._cola.popleft()
            self._admitir(entrada.tokens)
            entrada.espera.set_result(None)

    def _vencer(self, entrada: _EnEspera) -> None:
        if entrada.espera.done():
            return
        self._retirar(entrada)
        entrada.espera.set_exception(TiempoAgotado(entrada.paso, entrada.plazo))

    def _retirar(self, entrada: _EnEspera) -> None:
        """Saca de la cola a quien ya no espera. La cola vuelve a servirse.

        Sin esto, quien se cansa de esperar sigue bloqueando a los de detras:
        el primero de la cola manda aunque ya no exista.
        """
        try:
            self._cola.remove(entrada)
        except ValueError:
            return
        self._servir_cola()


class CerrojoDeEscena:
    """Una escena en vuelo por obra (RF-ORQ-08, `architecture.md` §3.1, punto 4).

    No es prudencia: la escena N+1 necesita el estado en T posterior a N, asi
    que paralelizar escenas de la misma obra no es arriesgado, es **incorrecto**.
    Obras distintas no comparten canon ni ledger —son ficheros SQLite
    distintos—, asi que se solapan sin mas.

    **El cerrojo es de escena, no de llamada**, y esa distincion es la que deja
    correr al Continuista y al Critico a la vez sobre el mismo capitulo: son dos
    llamadas dentro de la misma escena, y lo unico que las acota es el
    presupuesto concurrente.
    """

    def __init__(self) -> None:
        self._cerrojos: dict[int, asyncio.Lock] = {}
        self._en_vuelo: set[int] = set()

    @property
    def obras_en_vuelo(self) -> frozenset[int]:
        """Que obras tienen una escena en vuelo. Observable, como el contador."""
        return frozenset(self._en_vuelo)

    @asynccontextmanager
    async def por_obra(
        self, obra_id: int, *, espera_maxima: float | None = None
    ) -> AsyncIterator[None]:
        cerrojo = self._cerrojos.setdefault(obra_id, asyncio.Lock())
        if espera_maxima is None:
            await cerrojo.acquire()
        else:
            try:
                await asyncio.wait_for(cerrojo.acquire(), espera_maxima)
            except TimeoutError as vencido:
                raise TiempoAgotado(f"escena de la obra {obra_id}", espera_maxima) from vencido
        self._en_vuelo.add(obra_id)
        try:
            yield
        finally:
            self._en_vuelo.discard(obra_id)
            cerrojo.release()
