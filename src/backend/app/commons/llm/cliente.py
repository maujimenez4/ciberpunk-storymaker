from typing import Protocol


class ClienteModelo(Protocol):
    async def completar(self, prompt: str, semilla: int) -> str: ...


def obtener_cliente_modelo() -> ClienteModelo:
    """La dependencia por la que entra el modelo (RI-14, `CLAUDE.md` §6).

    **En esta fase no hay proveedor real, y por eso esto falla en vez de
    devolver algo.** La Fase 1 no escribe prosa y su suite corre sin red ni
    credenciales (CA-4): la unica implementacion de `ClienteModelo` que existe
    hoy es `DobleDeterminista`, y el cliente de Anthropic entra con el ciclo de
    capitulo. Que la funcion exista y falle es lo que permite que los endpoints
    la pidan por `Depends()` y que un test la sustituya sin tocar el codigo de
    produccion.

    La consecuencia se escribe para que nadie la descubra tarde: con la
    aplicacion levantada de verdad, `POST /entrevistas/{id}/respuestas` y
    `.../cerrar` devuelven 500. El OpenAPI, que es lo que RI-13 pide de esta
    fase, se sirve igual. Queda anotado en Desviaciones.
    """
    raise NotImplementedError(
        "No hay proveedor de modelo en la Fase 1: el cliente real entra con el "
        "ciclo de capitulo. En pruebas se sustituye por DobleDeterminista."
    )
