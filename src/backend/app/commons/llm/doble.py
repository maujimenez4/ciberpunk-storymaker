from app.commons.llm.cliente import ClienteModelo


class RespuestaNoPreparada(Exception):
    """El doble no inventa: si no se preparo, el test esta mal escrito."""


class DobleDeterminista(ClienteModelo):
    def __init__(self, respuestas: dict[str, str]) -> None:
        self._respuestas = respuestas
        self.llamadas: list[tuple[str, int]] = []

    async def completar(self, prompt: str, semilla: int) -> str:
        self.llamadas.append((prompt, semilla))
        for clave, valor in self._respuestas.items():
            if clave in prompt:
                return valor
        raise RespuestaNoPreparada(prompt[:120])
