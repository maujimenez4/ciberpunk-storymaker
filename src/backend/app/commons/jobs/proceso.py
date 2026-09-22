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

    Deliberadamente simple: la unidad de trabajo persistida, los estados y la
    reanudacion son la fase 7. Lo que se fija aqui es **donde** corren.
    """

    def __init__(self, turno: TurnoDeModelo) -> None:
        self.turno = turno
        self._cola: queue.Queue[Callable[[], None]] = queue.Queue()

    def encolar(self, trabajo: Callable[[], None]) -> None:
        self._cola.put(trabajo)

    def drenar(self) -> None:
        while not self._cola.empty():
            self._cola.get()()


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
        async with anterior(aplicacion):
            yield
        ejecutor.drenar()

    app.router.lifespan_context = lifespan
    return ejecutor
