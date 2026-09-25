"""Los dos observadores que no salen de la maquina.

`ObservadorEnMemoria` es el de las pruebas: guarda lo que le mandan y permite
afirmar sobre ello. `ObservadorNulo` es el de produccion **sin credenciales**, y
tiene que ser indistinguible de uno bueno para quien lo usa: mismo contrato,
cero efecto. Que el sistema arranque, avise y genere es RF-OBS-07 y R-1.

Ninguno de los dos abre una conexion. `CA-4`: la suite corre sin red.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.commons.observabilidad.trazas import Puntuacion, sesion_de


@dataclass
class SpanEnMemoria:
    """Lo que un span recibio, en orden."""

    nombre: str
    entradas: list[str] = field(default_factory=list)
    salidas: list[str] = field(default_factory=list)
    consumos: list[dict[str, Any]] = field(default_factory=list)
    puntuaciones: list[Puntuacion] = field(default_factory=list)

    def entrada(self, texto: str) -> None:
        self.entradas.append(texto)

    def salida(self, texto: str) -> None:
        self.salidas.append(texto)

    def consumo(
        self,
        *,
        modelo: str,
        tokens_entrada: int,
        tokens_salida: int,
        coste_usd: Decimal,
    ) -> None:
        self.consumos.append(
            {
                "modelo": modelo,
                "tokens_entrada": tokens_entrada,
                "tokens_salida": tokens_salida,
                "coste_usd": coste_usd,
            }
        )

    def puntuar(self, puntuacion: Puntuacion) -> None:
        self.puntuaciones.append(puntuacion)


@dataclass
class TrazaEnMemoria:
    """Una traza con sus spans, para afirmar sobre la forma del arbol."""

    sesion_id: str
    nombre: str
    spans: list[SpanEnMemoria] = field(default_factory=list)

    @asynccontextmanager
    async def span(self, nombre: str) -> AsyncIterator[SpanEnMemoria]:
        registro = SpanEnMemoria(nombre=nombre)
        self.spans.append(registro)
        yield registro


class ObservadorEnMemoria:
    """El observador de las pruebas. No inventa y no sale de la maquina."""

    def __init__(self) -> None:
        self.trazas: list[TrazaEnMemoria] = []
        self.cerrado = False

    @staticmethod
    def sesion_de(obra_id: int) -> str:
        return sesion_de(obra_id)

    def cerrar(self) -> None:
        """Solo lo anota: es lo que el test del *lifespan* mira."""
        self.cerrado = True

    @asynccontextmanager
    async def traza(self, *, obra_id: int, nombre: str) -> AsyncIterator[TrazaEnMemoria]:
        registro = TrazaEnMemoria(sesion_id=sesion_de(obra_id), nombre=nombre)
        self.trazas.append(registro)
        yield registro


class _SpanNulo:
    """Recibe y olvida. Las cuatro operaciones del contrato, sin efecto."""

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


class _TrazaNula:
    @asynccontextmanager
    async def span(self, nombre: str) -> AsyncIterator[_SpanNulo]:
        yield _SpanNulo()


class ObservadorNulo:
    """El de produccion sin credenciales: arranca, no mide y no estorba.

    No cuenta fallos porque no los tiene: no intentar no es fracasar. Lo que
    avisa de que no hay telemetria es el arranque (`ciclo_de_vida`), no un
    contador a cero que nadie sabria interpretar.
    """

    @asynccontextmanager
    async def traza(self, *, obra_id: int, nombre: str) -> AsyncIterator[_TrazaNula]:
        yield _TrazaNula()

    def cerrar(self) -> None:
        """Nada encolado, nada que vaciar."""
