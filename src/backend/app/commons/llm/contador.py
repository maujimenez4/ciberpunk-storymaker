"""Contador de tokens (RNF-TOK-02, D-07).

**Local a proposito.** D-07 lo exige para que RNF-REN-01 se cumpla —ensamblar un
paquete en menos de 2 s no es posible si cada recuento cruza la red— y porque el
sistema debe funcionar sin clave de proveedor.

**Es una aproximacion, y conviene no olvidarlo.** La tokenizacion exacta del
modelo de generacion no es publica, asi que este contador usa un BPE local. El
riesgo esta declarado en el plan: si tokeniza por debajo del proveedor, el
paquete "cabe" segun nosotros y no segun quien factura, y RNF-TOK-01 se
incumple en silencio. El margen que absorbe esa diferencia se aplica en el
ensamblador (fase 5), no aqui: este modulo cuenta, no decide.
"""

from typing import Protocol

import tiktoken

CODIFICACION = "cl100k_base"


class ContadorDeTokens(Protocol):
    """Lo que el ensamblador necesita. Se inyecta; en pruebas va un doble."""

    def contar(self, texto: str) -> int: ...


class ContadorBPE:
    """Cuenta con un BPE local. El vocabulario se carga una vez y se reutiliza."""

    def __init__(self, codificacion: str = CODIFICACION) -> None:
        self._codificador = tiktoken.get_encoding(codificacion)

    def contar(self, texto: str) -> int:
        if not texto:
            return 0
        return len(self._codificador.encode(texto))
