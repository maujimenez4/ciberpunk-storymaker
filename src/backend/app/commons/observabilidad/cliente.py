"""Por donde el prompt de cada rol llega a su span, **sin tocar ningun agente**.

`CLAUDE.md` §4.3 pide que suban el prompt renderizado y la salida de cada rol.
Los diez roles renderizan su prompt dentro y llaman a `cliente.completar`; lo
unico que todos comparten es el cliente. Asi que se observa ahi: el orquestador
abre el span del rol, `ClienteObservado` sabe cual es el span en curso y le
deja lo que paso por la llamada. Ningun agente cambia, y un rol nuevo queda
observado el dia que se construye con este cliente.

**El span en curso vive en una `ContextVar` de la instancia**, no en un atributo:
dos tareas que compartan cliente -- el Continuista y el Critico en paralelo, que
`CLAUDE.md` §4.1 permite -- veria cada una el suyo. Y es de la instancia, no del
modulo: no hay estado global que un test tenga que limpiar.

Lo que **no** hace: blindar. Eso es de `blindar`, y el observador que llega aqui
ya viene blindado (`obtener_observador`). Duplicarlo daria dos contadores de
fallos para lo mismo.
"""

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from app.commons.llm.cliente import ClienteModelo, Vectorizacion
from app.commons.observabilidad.dobles import _TrazaNula as TrazaNula
from app.commons.observabilidad.trazas import Span, Traza


class ClienteObservado(ClienteModelo):
    """El cliente de modelo, con cada llamada anotada en el span en curso."""

    def __init__(self, dentro: ClienteModelo) -> None:
        self._dentro = dentro
        self._span: ContextVar[Span | None] = ContextVar(f"span-de-{id(self)}", default=None)

    @property
    def ultimo_consumo(self) -> Any | None:
        """El del cliente de dentro, tal cual. `escritura` lo pregunta para
        cerrar la fila de `ejecucion`, y envolver no puede quitarle el dato."""
        return getattr(self._dentro, "ultimo_consumo", None)

    @contextmanager
    def en(self, span: Span) -> Iterator[None]:
        """Lo que se llame dentro de este bloque se anota en `span`."""
        marca = self._span.set(span)
        try:
            yield
        finally:
            self._span.reset(marca)

    async def completar(self, prompt: str, semilla: int, modelo: str | None = None) -> str:
        span = self._span.get()
        # La entrada sube **antes** de llamar: si el modelo falla, el prompt que
        # lo hizo fallar es justo lo que hace falta ver.
        if span is not None:
            span.entrada(prompt)

        # `modelo` solo se pasa si se pidio: hay dobles con la firma antigua.
        if modelo is None:
            respuesta = await self._dentro.completar(prompt, semilla=semilla)
        else:
            respuesta = await self._dentro.completar(prompt, semilla=semilla, modelo=modelo)

        if span is not None:
            span.salida(respuesta)
            consumo = self.ultimo_consumo
            # Sin consumo declarado no se inventa un cero: un cero se suma en el
            # panel como si la llamada hubiera sido gratis.
            if consumo is not None:
                span.consumo(
                    modelo=str(consumo.modelo),
                    tokens_entrada=int(consumo.tokens_entrada),
                    tokens_salida=int(consumo.tokens_salida),
                    coste_usd=consumo.coste_usd,
                )
        return respuesta

    def vectorizar(self, texto: str) -> Vectorizacion:
        return self._dentro.vectorizar(texto)


@dataclass(frozen=True, slots=True)
class Observacion:
    """Una traza abierta y el cliente que comparten sus roles.

    Es lo que baja por el ciclo en vez de dos parametros sueltos. `cliente` es
    opcional porque un test que monta los roles con un doble a pelo no lo
    envuelve: el span se abre igual, sin prompt. Es menos, no es un error.
    """

    traza: Traza
    cliente: ClienteObservado | None = None

    @staticmethod
    def nula() -> "Observacion":
        """Para quien llama sin observador: el mismo codigo, cero efecto.

        Existe para que el servicio no tenga dos caminos -- con y sin
        observacion --, que es como uno de los dos se queda sin probar.
        """
        return Observacion(traza=TrazaNula())

    @asynccontextmanager
    async def span(self, nombre: str) -> AsyncIterator[Span]:
        """El span del rol `nombre`, con el cliente apuntando a el."""
        async with self.traza.span(nombre) as span:
            if self.cliente is None:
                yield span
            else:
                with self.cliente.en(span):
                    yield span
