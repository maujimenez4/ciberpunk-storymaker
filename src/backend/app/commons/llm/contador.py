from typing import Protocol


class ContadorDeTokens(Protocol):
    """Cuenta tokens de verdad; `CLAUDE.md` §4.1 prohibe estimar por caracteres."""

    def contar(self, texto: str) -> int: ...
