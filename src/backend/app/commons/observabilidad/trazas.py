"""El contrato de la observabilidad: por aqui salen todos los numeros de la fase.

Son **protocolos** y no clases base por la misma razon que el cliente de modelo:
lo que se inyecta en las pruebas es un doble, y un doble que tiene que heredar
de algo arrastra consigo lo que ese algo trajera. `CA-4` pide que la suite corra
sin red y sin credenciales, y eso solo es barato si sustituir al proveedor es
pasar otro objeto.

**Lo que sube y lo que no.** A Langfuse van la plantilla, el prompt renderizado
y la salida -- y con ellos el manuscrito, porque cinco de los diez roles reciben
la prosa como entrada y su prompt renderizado **es** el capitulo. Es decision
declarada de `maujimenez4` (`CLAUDE.md` §4.3). Lo que no puede pasar es que eso
acabe en un log corriente: fuera de Langfuse no sale nada (§16).
"""

from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

PREFIJO_DE_SESION = "obra-"
"""RF-OBS-01. El identificador de sesion **se deriva**, no se pasa.

Si fuera un parametro, una regeneracion de dentro de un mes caeria en la sesion
correcta solo si quien la pide se acuerda del valor. Derivandolo del `obra_id`,
equivocarse es imposible.
"""


def sesion_de(obra_id: int) -> str:
    """El identificador de sesion de una obra. Una funcion, y en un solo sitio."""
    return f"{PREFIJO_DE_SESION}{obra_id}"


@dataclass(frozen=True, slots=True)
class Puntuacion:
    """El *score* de un validador. Se llama como en `verification.md` §8.1.

    `nombre` **sin traducir**: es la llave por la que el *score* se cruza con la
    tabla de validadores, y traducirlo aqui rompe el cruce sin que nada falle.

    `justificacion` y `criterio` son opcionales porque un validador mecanico no
    tiene ninguno de los dos: emite un numero. Los rellena el Critico, y que su
    salida los exija es de T4 -- aqui solo caben.
    """

    nombre: str
    valor: float
    justificacion: str | None = None
    criterio: str | None = None


class Span(Protocol):
    """Un rol o una llamada a tool (RF-OBS-02). El Ensamblador tambien, aunque
    sea codigo: es donde se ve el desglose por capa y lo que se recorto."""

    def entrada(self, texto: str) -> None: ...

    def salida(self, texto: str) -> None: ...

    def consumo(
        self,
        *,
        modelo: str,
        tokens_entrada: int,
        tokens_salida: int,
        coste_usd: Decimal,
    ) -> None: ...

    def puntuar(self, puntuacion: Puntuacion) -> None: ...

    def prompt(self, prompt_id: str, prompt_version: str, prompt_hash: str) -> None:
        """La plantilla que produjo el prompt de este span (P-22.3): los mismos
        tres campos que la fila de `ejecucion` (regla de dominio 7), para que
        el *tuning* diga **que version produjo que resultado**."""
        ...


class Traza(Protocol):
    """Una unidad de trabajo dentro de la sesion de una novela."""

    def span(self, nombre: str) -> AbstractAsyncContextManager[Span]: ...


class Observador(Protocol):
    """Lo que se inyecta. `obra_id` y no `sesion_id`: ver `sesion_de`."""

    def traza(self, *, obra_id: int, nombre: str) -> AbstractAsyncContextManager[Traza]: ...

    def cerrar(self) -> None:
        """Vacia lo encolado. Lo llama el *lifespan* al apagar (P-22.2): el SDK
        manda por lotes, y sin esto se pierden los ultimos spans."""
        ...
