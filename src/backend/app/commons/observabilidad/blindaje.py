"""R-1: que el observador se caiga **no puede** romper una generacion.

Una novela que no se escribe porque el panel de metricas esta caido es peor que
una novela sin panel: el comprador pago por la novela.

**Y la degradacion se ve.** Un observador que se traga sus propios errores
produce un panel vacio, y un panel vacio no se distingue de un sistema que no
genero nada. Por eso cada operacion fallida suma en `fallos`: la tasa es lo que
dice si el observador esta medio caido o del todo.

**Lo que el blindaje NO hace: tragarse el cuerpo.** `blindar` protege del
observador, no del codigo que envuelve. Si el Escritor lanza, esa excepcion sale
entera: tragarsela seria el fallo silencioso mas caro del sistema -- el capitulo
no se escribe y el ciclo cree que si.
"""

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from decimal import Decimal
from typing import Any

from app.commons.observabilidad.trazas import Observador, Puntuacion, Span, Traza


class _Contador:
    """Las operaciones fallidas del observador, compartidas por el arbol entero.

    Es un objeto y no un entero porque los spans lo incrementan desde dentro de
    dos gestores de contexto anidados, y un `int` se copiaria en cada nivel.
    """

    def __init__(self) -> None:
        self.fallos = 0

    def anotar(self) -> None:
        self.fallos += 1


def _a_salvo(contador: _Contador, operacion: Callable[[], Any]) -> None:
    """Ejecuta y, si falla, cuenta. Nunca propaga.

    `BaseException` no se captura a proposito: un `KeyboardInterrupt` o un
    `asyncio.CancelledError` no son un fallo del observador, y tragarselos
    dejaria un proceso que no se puede parar.
    """
    try:
        operacion()
    except Exception:  # noqa: BLE001 -- R-1: del observador no sale nada
        contador.anotar()


class _SpanBlindado:
    """Las cuatro operaciones del contrato, cada una a salvo por separado.

    Por separado y no en bloque: si `salida` falla y `puntuar` no, se pierde una
    y llega la otra. Abortar el span entero al primer fallo perderia datos que
    si se podian mandar.
    """

    def __init__(self, dentro: Span | None, contador: _Contador) -> None:
        self._dentro = dentro
        self._contador = contador

    def entrada(self, texto: str) -> None:
        if self._dentro is None:
            self._contador.anotar()
            return
        _a_salvo(self._contador, lambda: self._dentro.entrada(texto))  # type: ignore[union-attr]

    def salida(self, texto: str) -> None:
        if self._dentro is None:
            self._contador.anotar()
            return
        _a_salvo(self._contador, lambda: self._dentro.salida(texto))  # type: ignore[union-attr]

    def consumo(
        self,
        *,
        modelo: str,
        tokens_entrada: int,
        tokens_salida: int,
        coste_usd: Decimal,
    ) -> None:
        if self._dentro is None:
            self._contador.anotar()
            return
        _a_salvo(
            self._contador,
            lambda: self._dentro.consumo(  # type: ignore[union-attr]
                modelo=modelo,
                tokens_entrada=tokens_entrada,
                tokens_salida=tokens_salida,
                coste_usd=coste_usd,
            ),
        )

    def puntuar(self, puntuacion: Puntuacion) -> None:
        if self._dentro is None:
            self._contador.anotar()
            return
        _a_salvo(self._contador, lambda: self._dentro.puntuar(puntuacion))  # type: ignore[union-attr]


class _TrazaBlindada:
    """Si la traza de dentro no existe -- porque abrirla fallo --, los spans
    siguen abriendose: el cuerpo del `with` tiene que correr igual."""

    def __init__(self, dentro: Traza | None, contador: _Contador) -> None:
        self._dentro = dentro
        self._contador = contador

    @asynccontextmanager
    async def span(self, nombre: str) -> AsyncIterator[_SpanBlindado]:
        interno: Span | None = None
        gestor: AbstractAsyncContextManager[Span] | None = None
        if self._dentro is not None:
            try:
                gestor = self._dentro.span(nombre)
                interno = await gestor.__aenter__()
            except Exception:  # noqa: BLE001 -- R-1
                self._contador.anotar()
                gestor = None
                interno = None
        else:
            self._contador.anotar()

        try:
            yield _SpanBlindado(interno, self._contador)
        finally:
            # El cierre tambien puede fallar, y tampoco puede salir de aqui.
            if gestor is not None:
                try:
                    await gestor.__aexit__(None, None, None)
                except Exception:  # noqa: BLE001 -- R-1
                    self._contador.anotar()


class ObservadorBlindado:
    """El observador envuelto, con su contador de fallos a la vista.

    `fallos` es publico a proposito: T7 lo lee para decir cuanta telemetria se
    perdio, y sin ese numero «no hay datos» y «no hubo trabajo» se parecen
    demasiado.
    """

    def __init__(self, dentro: Observador) -> None:
        self._dentro = dentro
        self._contador = _Contador()

    @property
    def fallos(self) -> int:
        return self._contador.fallos

    def cerrar(self) -> None:
        """El `flush` del apagado, a salvo como todo lo demas (Review Focus 5 del
        plan 8): con Langfuse caido al apagar, el proceso se para igual y el
        fallo se cuenta."""
        _a_salvo(self._contador, self._dentro.cerrar)

    @asynccontextmanager
    async def traza(self, *, obra_id: int, nombre: str) -> AsyncIterator[_TrazaBlindada]:
        interna: Traza | None = None
        gestor: AbstractAsyncContextManager[Traza] | None = None
        try:
            gestor = self._dentro.traza(obra_id=obra_id, nombre=nombre)
            interna = await gestor.__aenter__()
        except Exception:  # noqa: BLE001 -- R-1
            self._contador.anotar()
            gestor = None
            interna = None

        try:
            yield _TrazaBlindada(interna, self._contador)
        finally:
            if gestor is not None:
                try:
                    await gestor.__aexit__(None, None, None)
                except Exception:  # noqa: BLE001 -- R-1
                    self._contador.anotar()


def blindar(observador: Observador) -> ObservadorBlindado:
    """Envuelve un observador para que no pueda romper una generacion."""
    return ObservadorBlindado(observador)
