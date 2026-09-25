"""El adaptador de Langfuse, contra un `Langfuse` **falso** inyectado.

Sin red y sin la dependencia (`CA-4`): lo que se comprueba es lo que el
adaptador le pide al cliente, que es lo unico que este modulo decide. Si el
proveedor cambia de forma, cambia el falso y cambia este fichero; el resto del
paquete no se entera.
"""

from contextlib import contextmanager
from typing import Any

from app.commons.observabilidad import ObservadorLangfuse, Puntuacion


class SpanFalso:
    """Lo que el cliente real devuelve de `start_as_current_span`, reducido a lo
    que el adaptador usa: `update`, `update_trace`, `score` y abrir hijos."""

    def __init__(self, nombre: str) -> None:
        self.nombre = nombre
        self.actualizaciones: list[dict[str, Any]] = []
        self.scores: list[dict[str, Any]] = []
        self.hijos: list[SpanFalso] = []

    def update(self, **campos: Any) -> None:
        self.actualizaciones.append(campos)

    def update_trace(self, **campos: Any) -> None:
        self.actualizaciones.append({"trace": campos})

    def score(self, **campos: Any) -> None:
        self.scores.append(campos)

    @contextmanager
    def start_as_current_span(self, *, name: str) -> Any:
        hijo = SpanFalso(name)
        self.hijos.append(hijo)
        yield hijo


class LangfuseFalso:
    """El cliente, con `flush` contado."""

    def __init__(self) -> None:
        self.trazas: list[SpanFalso] = []
        self.flushes = 0

    @contextmanager
    def start_as_current_span(self, *, name: str) -> Any:
        traza = SpanFalso(name)
        self.trazas.append(traza)
        yield traza

    def flush(self) -> None:
        self.flushes += 1


def _observador(cliente: Any) -> ObservadorLangfuse:
    return ObservadorLangfuse(
        clave_publica="pk-lf-x",
        clave_secreta="sk-lf-x",
        host="https://example.invalid",
        cliente=cliente,
    )


# --- P-22.1: el criterio llega al nombre del score -----------------------------


async def test_una_puntuacion_con_criterio_sube_con_el_criterio_en_el_nombre() -> None:
    """P-22.1. Los seis criterios del juez se llaman todos `juez_con_rubrica`, y
    sin el criterio en el nombre el panel los mezcla en una sola serie: no se
    puede ver que la voz sube mientras el ritmo baja, que es lo que el *tuning*
    mira."""
    langfuse = LangfuseFalso()
    observador = _observador(langfuse)

    async with (
        observador.traza(obra_id=1, nombre="capitulo 1") as traza,
        traza.span("critico") as span,
    ):
        span.puntuar(
            Puntuacion(
                nombre="juez_con_rubrica", valor=4, justificacion="Se sostiene", criterio="voz"
            )
        )

    [score] = langfuse.trazas[0].hijos[0].scores
    assert score == {"name": "juez_con_rubrica.voz", "value": 4, "comment": "Se sostiene"}


async def test_una_puntuacion_sin_criterio_sube_con_su_nombre_tal_cual() -> None:
    """Los validadores mecanicos no tienen criterio: su nombre es la llave de
    `verification.md` §8.1 y no se le anade nada."""
    langfuse = LangfuseFalso()
    observador = _observador(langfuse)

    async with (
        observador.traza(obra_id=1, nombre="capitulo 1") as traza,
        traza.span("puerta_g1a") as span,
    ):
        span.puntuar(Puntuacion(nombre="extension_de_capitulo", valor=1.0))

    [score] = langfuse.trazas[0].hijos[0].scores
    assert score["name"] == "extension_de_capitulo"
