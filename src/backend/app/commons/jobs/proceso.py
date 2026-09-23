"""Turno de modelo y ejecutor de trabajos, ambos **del proceso**.

`architecture.md` §2.2 regla 3 y §10: el limite de llamadas simultaneas es por
proceso, y por eso los trabajos corren en el proceso de la API. Repartirlos en
un *worker* aparte daria dos turnos donde el diseno cuenta uno, y duplicaria el
limite **en silencio**: sin error, sin aviso, solo el doble de factura y de
latencia. Es de los fallos mas caros de detectar, porque el sistema parece ir
mejor.

Aqui vive el mecanismo. La maquina de estados que lo usa es la fase 7.
"""

import queue
import threading
import traceback
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager

from fastapi import FastAPI


class TurnoDeModelo:
    """Cuantas llamadas al modelo puede haber en vuelo (RNF-TOK-03).

    Uno por defecto (D-03). Quien no tiene turno **espera**: nunca se recorta el
    paquete para que quepa antes, porque recortar obedece al presupuesto de
    §2.1 y no a la carga del sistema (RNF-TOK-04).
    """

    def __init__(self, simultaneas: int = 1) -> None:
        self.simultaneas = simultaneas
        self._semaforo = threading.BoundedSemaphore(simultaneas)

    def tomar(self, espera_s: float) -> bool:
        """Devuelve False si vence la espera; el llamante decide (RNF-TOK-05).

        `espera_s <= 0` significa **no esperar**, no "esperar sin limite": pasar
        timeout=None a acquire() bloquea para siempre, que es exactamente el
        turno colgado del que avisa RF-ORQ-13.
        """
        if espera_s <= 0:
            return self._semaforo.acquire(blocking=False)
        return self._semaforo.acquire(timeout=espera_s)

    def liberar(self) -> None:
        self._semaforo.release()

    @contextmanager
    def en_uso(self, espera_s: float) -> Iterator[bool]:
        """Libera el turno **pase lo que pase** (RF-ORQ-13).

        Un turno que no se libera no degrada el rendimiento: cuelga el proceso
        entero, porque nadie mas podra llamar al modelo nunca.
        """
        obtenido = self.tomar(espera_s)
        try:
            yield obtenido
        finally:
            if obtenido:
                self.liberar()


_turno: TurnoDeModelo | None = None
_cerrojo = threading.Lock()


def turno_del_proceso(simultaneas: int = 1) -> TurnoDeModelo:
    """El turno es **uno** por proceso, no uno por modulo que lo pida."""
    global _turno
    with _cerrojo:
        if _turno is None:
            _turno = TurnoDeModelo(simultaneas)
    return _turno


class EjecutorDeTrabajos:
    """Corre los trabajos en el mismo proceso que sirve la API.

    **Un solo hilo**, y no un grupo. No es simplicidad: el turno de §2.2 admite
    una llamada al modelo a la vez, asi que varios hilos se pasarian la vida
    esperandolo, y mientras tanto tendrian abiertas varias transacciones sobre
    el mismo SQLite. La concurrencia que el diseno quiere es entre **obras**
    (§3.8), y esa la da el cerrojo por obra, no mas hilos aqui.
    """

    def __init__(self, turno: TurnoDeModelo) -> None:
        self.turno = turno
        self._cola: queue.Queue[Callable[[], None] | None] = queue.Queue()
        self._hilo: threading.Thread | None = None

    def encolar(self, trabajo: Callable[[], None]) -> None:
        self._cola.put(trabajo)

    def arrancar(self) -> None:
        """Hasta P-112 no habia hilo: `drenar()` solo corria al **apagar** la
        aplicacion, asi que el endpoint encolaba y el trabajo esperaba a que
        alguien parase el servidor."""
        if self._hilo is not None:
            return
        self._hilo = threading.Thread(
            target=self._atender, name="trabajos", daemon=True
        )
        self._hilo.start()

    def parar(self) -> None:
        """Termina lo que queda en la cola y cierra el hilo.

        No se descarta lo pendiente: si la API devolvio 202, el trabajo esta
        aceptado. Perderlo al apagar dejaria al cliente con un identificador que
        nunca cambia de estado.
        """
        if self._hilo is None:
            self.drenar()
            return
        self._cola.put(None)  # centinela: «no hay mas»
        self._hilo.join()
        self._hilo = None

    def _atender(self) -> None:
        while True:
            trabajo = self._cola.get()
            if trabajo is None:
                return
            self._ejecutar(trabajo)

    @staticmethod
    def _ejecutar(trabajo: Callable[[], None]) -> None:
        try:
            trabajo()
        except Exception:  # noqa: BLE001 - un fallo no puede matar al hilo
            # Quien encola es el responsable de dejar constancia -el trabajo
            # pasa a FALLIDA-. Aqui solo se impide que el hilo muera: si muriera,
            # la cola quedaria parada para siempre y **sin un solo error
            # visible**, que es el peor de los dos fallos posibles.
            traceback.print_exc()

    def drenar(self) -> None:
        """Ejecuta lo pendiente en el hilo que llama. Es lo que usan los tests
        para no depender de tiempos."""
        while not self._cola.empty():
            trabajo = self._cola.get()
            if trabajo is not None:
                self._ejecutar(trabajo)


def montar_ejecutor_de_trabajos(app: FastAPI) -> EjecutorDeTrabajos:
    """Cuelga el ejecutor de la aplicacion y lo drena al apagarla.

    Se envuelve el `lifespan` existente en vez de usar `on_event`, que FastAPI
    tiene obsoleto, y asi montar el ejecutor no pisa lo que la aplicacion ya
    hiciera al arrancar o al apagarse.
    """
    ejecutor = EjecutorDeTrabajos(turno_del_proceso())
    app.state.ejecutor = ejecutor
    anterior = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(aplicacion: FastAPI) -> AsyncIterator[None]:
        ejecutor.arrancar()
        async with anterior(aplicacion):
            yield
        ejecutor.parar()

    app.router.lifespan_context = lifespan
    return ejecutor
