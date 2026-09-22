"""Cliente de modelo: interfaz, doble y el hueco del proveedor real (RI-13).

El proveedor se conecta en la fase 7. Hasta entonces `ClienteNoConfigurado`
ocupa su sitio y **falla en voz alta**: un cliente que devolviera texto vacio se
confundiria con una escena que el modelo no supo escribir, y ese es el tipo de
fallo que cuesta dias encontrar.
"""

from dataclasses import dataclass, field
from typing import Protocol


class ProveedorSinConectar(RuntimeError):
    """No hay proveedor conectado todavia."""


@dataclass(frozen=True)
class RespuestaDeModelo:
    """Lo que un paso necesita devolver para que `ejecucion` quede completa."""

    texto: str
    tokens_entrada: int = 0
    tokens_salida: int = 0
    modelo: str = ""
    parametros: dict[str, object] = field(default_factory=dict)


class ClienteDeModelo(Protocol):
    def generar(self, prompt: str) -> RespuestaDeModelo: ...


class ClienteNoConfigurado:
    """Sitio reservado del proveedor real."""

    def generar(self, prompt: str) -> RespuestaDeModelo:
        raise ProveedorSinConectar(
            "no hay proveedor de modelo conectado: se conecta en la fase 7"
        )


class DobleDeModelo:
    """Respuestas fijas y registro de lo pedido. Nunca sale del proceso."""

    def __init__(self, respuestas: list[str]) -> None:
        self._respuestas = list(respuestas)
        self.llamadas: list[str] = []

    def generar(self, prompt: str) -> RespuestaDeModelo:
        self.llamadas.append(prompt)
        assert self._respuestas, (
            f"el doble se quedo sin respuestas en la llamada "
            f"{len(self.llamadas)}: el codigo llamo mas veces de las previstas"
        )
        return RespuestaDeModelo(texto=self._respuestas.pop(0), modelo="doble")
