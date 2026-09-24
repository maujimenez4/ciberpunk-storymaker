from typing import Protocol


class ClienteModelo(Protocol):
    async def completar(self, prompt: str, semilla: int) -> str: ...


def obtener_cliente_modelo() -> ClienteModelo:
    """La dependencia por la que entra el modelo (RI-14, `CLAUDE.md` §6).

    Devuelve el cliente real: el **Claude Agent SDK** ya autenticado contra la
    cuenta (P-08). Con esto se cierra el hueco que la Fase 1 dejo declarado —
    `POST /entrevistas/{id}/respuestas` y `.../cerrar` respondian 500 contra la
    aplicacion levantada, porque la unica implementacion de `ClienteModelo`
    que existia era `DobleDeterminista`.

    **Construirlo no llama a nadie ni lee credenciales**, y eso importa: es
    una dependencia de FastAPI, asi que se resuelve en cada peticion. Lo que
    abre el proceso del proveedor es `completar`, y solo `completar`.

    En pruebas se sustituye por `DobleDeterminista` con
    `dependency_overrides`: la suite corre sin red y sin credenciales
    (RNF-FIA-01, CA-4). Que el cliente exista no cambia eso.

    El import va dentro de la funcion a proposito: `claude_code` importa
    `ClienteModelo` de aqui, y al reves seria un ciclo. De paso, importar este
    modulo —que es lo que hace `features/obra/router.py`— no arrastra el SDK.
    """
    from app.commons.llm.claude_code import ClienteClaudeCode

    return ClienteClaudeCode()
