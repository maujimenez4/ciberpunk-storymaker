from datetime import UTC, datetime
from typing import Protocol


class Reloj(Protocol):
    def ahora(self) -> datetime: ...


class RelojDelSistema(Reloj):
    def ahora(self) -> datetime:
        return datetime.now(UTC)


class RelojFijo(Reloj):
    def __init__(self, momento: datetime) -> None:
        self._momento = momento

    def ahora(self) -> datetime:
        return self._momento
