"""El reloj como dependencia (RI-13).

Sin inyectarlo, ningun test sobre `creado_en`, plazos por paso o *timeout* de
turno seria reproducible: dependerian de cuando se ejecuta la suite.
"""

from datetime import UTC, datetime
from typing import Protocol


class Reloj(Protocol):
    def ahora(self) -> datetime: ...


class RelojDelSistema:
    """El de produccion. Siempre con zona horaria: un naive no se puede comparar."""

    def ahora(self) -> datetime:
        return datetime.now(UTC)


class RelojFijo:
    """El de pruebas. No avanza salvo que se le diga."""

    def __init__(self, instante: datetime) -> None:
        self._instante = instante

    def ahora(self) -> datetime:
        return self._instante

    def avanzar(self, segundos: float) -> None:
        from datetime import timedelta

        self._instante += timedelta(seconds=segundos)
