"""Contar tokens **antes** de llamar, que es lo que evita gastar de balde.

P-A dejo dicho que hay **dos** contadores y son dos momentos distintos:

| Momento | Requisito | Quien lo da |
| --- | --- | --- |
| Antes de llamar | RF-CTX-02 — decidir si el paquete cabe, y fallar sin gastar | esto |
| Despues de llamar | RF-OBS-03 — tokens y coste reales | el proveedor, en `ejecucion` |

Este fichero es el primero. RF-CTX-02 prohibe, con esas palabras, «una
estimacion **por caracteres**», y un BPE de verdad no es eso: `tiktoken`
tokeniza igual que un modelo, aunque **no sea el vocabulario de Anthropic**.
Esa diferencia es una deriva declarada, no una comodidad, y esta acotada por
dos cosas que ya existian: la capa de **reserva** de 10.000 tokens
(`CLAUDE.md` §4.1) y que `ejecucion` guarda el recuento previsto junto al
real, de modo que la deriva se **mide** en vez de suponerse.
"""

from collections.abc import Callable
from typing import Protocol

import tiktoken

CODIFICACION_POR_DEFECTO = "cl100k_base"
"""El vocabulario que se usa para el conteo previo.

`tiktoken` lo descarga la primera vez y lo cachea. Por eso `ContadorTiktoken`
no lo carga al construirse: el arranque decide cuando se paga esa vez, y la
suite no la paga nunca porque inyecta su propia codificacion.
"""


class ContadorDeTokens(Protocol):
    """Cuenta tokens de verdad; `CLAUDE.md` §4.1 prohibe estimar por caracteres."""

    def contar(self, texto: str) -> int: ...


class ContadorTiktoken(ContadorDeTokens):
    """El contador de produccion: un BPE local, sin red en el camino caliente.

    La codificacion se carga **la primera vez que se cuenta**, no al
    construirse, y se conserva. `cargar` existe para que las pruebas pongan un
    vocabulario propio: sin ese hueco, el primer test tendria que descargar el
    de `cl100k_base` y la suite dejaria de correr sin red (RNF-FIA-01, CA-4).
    """

    def __init__(
        self,
        codificacion: str = CODIFICACION_POR_DEFECTO,
        *,
        cargar: Callable[[str], tiktoken.Encoding] = tiktoken.get_encoding,
    ) -> None:
        self._codificacion = codificacion
        self._cargar = cargar
        self._bpe: tiktoken.Encoding | None = None

    @property
    def codificacion(self) -> str:
        return self._codificacion

    def contar(self, texto: str) -> int:
        if self._bpe is None:
            self._bpe = self._cargar(self._codificacion)
        return len(self._bpe.encode(texto))
