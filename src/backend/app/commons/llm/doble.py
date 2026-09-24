from app.commons.llm.cliente import ClienteModelo, Vectorizacion, vectorizar_texto


class RespuestaNoPreparada(Exception):
    """El doble no inventa: si no se preparo, el test esta mal escrito."""


class DobleDeterminista(ClienteModelo):
    def __init__(self, respuestas: dict[str, str]) -> None:
        self._respuestas = respuestas
        self.llamadas: list[tuple[str, int]] = []
        self.modelos: list[str | None] = []
        """Que modelo se pidio en cada llamada, **en una lista aparte**.

        Va aparte y no como tercer elemento de `llamadas` porque tres features
        desempaquetan esa lista de dos en dos: ensancharla las rompe sin que
        ninguna gane nada. Es lo unico que hace observable P-02 sin red (CA-4).
        """

    async def completar(self, prompt: str, semilla: int, modelo: str | None = None) -> str:
        self.llamadas.append((prompt, semilla))
        self.modelos.append(modelo)
        for clave, valor in self._respuestas.items():
            if clave in prompt:
                return valor
        raise RespuestaNoPreparada(prompt[:120])

    def vectorizar(self, texto: str) -> Vectorizacion:
        """**El mismo vector que produccion**, y no uno preparado.

        No se pide al test que lo declare —y por eso no lanza
        `RespuestaNoPreparada`— porque vectorizar no es una respuesta del
        modelo: es calculo local y determinista. Compartir la implementacion
        con el cliente real es lo que hace que lo que la suite indexa sea lo
        que se indexara de verdad.
        """
        return vectorizar_texto(texto)
