from typing import Protocol


class ClienteModelo(Protocol):
    async def completar(self, prompt: str, semilla: int) -> str: ...
