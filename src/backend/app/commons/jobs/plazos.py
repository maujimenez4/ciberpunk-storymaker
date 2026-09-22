"""Plazos por paso, cerrojo por obra y reintento del proveedor.

`architecture.md` §2.2, §3.6 y §3.8; D-04.

**El plazo depende del tipo de paso, no del paso.** `ENSAMBLANDO` es código puro
y debe terminar en menos de 2 s; `ESCRIBIENDO` es una llamada al modelo que tarda
minutos. Un plazo único que tolerase al segundo no vigilaría al primero, y ahí es
donde un cuelgue pasa desapercibido.

**El cerrojo es por obra, no global.** SQLite con WAL admite lectores concurrentes
y un solo escritor; el orquestador respeta eso serializando por obra en vez de
confiar en `busy_timeout` para resolver colisiones. Varias obras avanzan a la vez;
lo que se serializa entre ellas es la **llamada al modelo**, por el turno único.
"""

import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from app.commons.errors import FalloDeProveedor, TiempoAgotado
from app.commons.jobs.estados import Estado

# D-04. Los que llaman al modelo llevan el plazo largo; el resto, el corto.
PASOS_CON_MODELO = frozenset(
    {Estado.PLANIFICANDO, Estado.ESCRIBIENDO, Estado.EXTRAYENDO}
)
PLAZO_CODIGO_S = 30
PLAZO_MODELO_S = 600

# RNF-FIA-02. Tres intentos y después `FALLIDA`.
INTENTOS_DE_PROVEEDOR = 3


def plazo_de(
    paso: Estado, plazo_codigo: int = PLAZO_CODIGO_S, plazo_modelo: int = PLAZO_MODELO_S
) -> int:
    return plazo_modelo if paso in PASOS_CON_MODELO else plazo_codigo


class CerrojoPorObra:
    """Serializa las escrituras de una misma obra (RF-ORQ-11, §3.8).

    Una escena en vuelo por obra es restricción de **corrección**, no de
    rendimiento: la escena N+1 necesita el estado en T posterior a N.
    Paralelizar escenas de la misma obra no es arriesgado, es incorrecto.
    """

    def __init__(self) -> None:
        self._cerrojos: dict[str, threading.Lock] = {}
        self._guarda = threading.Lock()

    def _para(self, obra_id: str) -> threading.Lock:
        with self._guarda:
            return self._cerrojos.setdefault(obra_id, threading.Lock())

    def tomar(self, obra_id: str, espera_s: float = 0) -> bool:
        cerrojo = self._para(obra_id)
        if espera_s <= 0:
            return cerrojo.acquire(blocking=False)
        return cerrojo.acquire(timeout=espera_s)

    def soltar(self, obra_id: str) -> None:
        self._para(obra_id).release()

    @contextmanager
    def en_uso(self, obra_id: str, espera_s: float = 0) -> Iterator[bool]:
        tomado = self.tomar(obra_id, espera_s)
        try:
            yield tomado
        finally:
            if tomado:
                self.soltar(obra_id)


def ejecutar_con_plazo[T](
    paso: Estado,
    accion: Callable[[], T],
    plazo_s: int | None = None,
    ahora: Callable[[], float] = time.monotonic,
) -> T:
    """Mide lo que tarda y falla con `TiempoAgotado` si se pasa (RNF-FIA-04).

    Se comprueba **después** de ejecutar y no se interrumpe a mitad: matar un
    paso en curso dejaría escrituras parciales, y toda la reanudación se apoya en
    que la salida solo se persiste al completarse (§3.7). Un paso lento se
    detecta y se anota; no se aborta por la fuerza.
    """
    limite = plazo_s if plazo_s is not None else plazo_de(paso)
    empezo = ahora()
    resultado = accion()
    transcurrido = ahora() - empezo
    if transcurrido > limite:
        raise TiempoAgotado(paso=paso.value, relanzable_sin_coste=False)
    return resultado


def con_reintentos[T](
    accion: Callable[[], T],
    intentos: int = INTENTOS_DE_PROVEEDOR,
    esperar: Callable[[float], None] = time.sleep,
) -> T:
    """RNF-FIA-02: espera creciente, hasta tres. Después, `FalloDeProveedor`.

    La espera crece porque un proveedor que acaba de fallar por tasa vuelve a
    fallar si se le insiste de inmediato: reintentar sin esperar convierte un
    fallo transitorio en tres.
    """
    ultimo: Exception | None = None
    for numero in range(intentos):
        try:
            return accion()
        except FalloDeProveedor:
            raise
        except Exception as error:  # noqa: BLE001 - se reintenta y se reenvuelve
            ultimo = error
            if numero < intentos - 1:
                esperar(2**numero)
    raise FalloDeProveedor(intentos=intentos) from ultimo
