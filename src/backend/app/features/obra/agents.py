import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from app.commons.llm.cliente import ClienteModelo
from app.commons.llm.json_de_modelo import json_de_modelo

PLANTILLA_V1 = (Path(__file__).parent / "prompts" / "entrevistador.v2.md").read_text(
    encoding="utf-8"
)
_MARCA = "texto_aportado"
_MARCA_RESPUESTAS = "respuestas"


def _sin_etiquetas(texto: str, marca: str = _MARCA) -> str:
    """Quita la etiqueta hasta que quitarla ya no cambie nada.

    Una pasada sola no basta: al borrar el cierre de `</texto</texto_aportado>_aportado>`
    se unen los dos trozos que lo rodeaban y la etiqueta se vuelve a formar. Se repite
    hasta punto fijo, y termina siempre porque cada vuelta que cambia algo acorta la
    cadena.
    """
    sano = texto
    while True:
        podado = sano.replace(f"</{marca}>", "").replace(f"<{marca}>", "")
        if podado == sano:
            return sano
        sano = podado


def render_entrevistador(plantilla: str, texto_aportado: str) -> str:
    """El texto del comprador entra SIEMPRE marcado como dato (CLAUDE.md §11)."""
    if not texto_aportado.strip():
        return plantilla.replace("{{TEXTO_APORTADO}}", "")
    bloque = f"<{_MARCA}>\n{_sin_etiquetas(texto_aportado)}\n</{_MARCA}>"
    return plantilla.replace("{{TEXTO_APORTADO}}", bloque)


class SalidaMalFormada(Exception):
    """Un agente que devuelve algo fuera de su esquema es un fallo (RF-ORQ-09)."""


def _con_motivo(crudo: str, error: Exception) -> str:
    """Lo que devolvio el modelo **y por que no valida**.

    Guardar solo el crudo deja el diagnostico a ciegas: se ve el texto y no lo
    que le sobra o le falta, y con un esquema de veinte campos eso es una hora
    de leer JSON a mano. Paso en la corrida real del 2026-09-24.

    El crudo se recorta y el motivo no: el motivo es la parte corta y util.
    """
    if isinstance(error, ValidationError):
        fallos = "; ".join(
            f"{'.'.join(str(parte) for parte in e['loc'])}: {e['type']}" for e in error.errors()[:6]
        )
        return f"{fallos} | crudo: {crudo[:200]}"
    return f"{type(error).__name__}: {error} | crudo: {crudo[:200]}"


class Contradiccion(BaseModel):
    """`extra=forbid` por lo mismo que `Evaluacion`: lo que sobra es un fallo."""

    model_config = ConfigDict(extra="forbid")

    campos: list[str]
    explicacion: str


class Evaluacion(BaseModel):
    """La salida del Entrevistador, con las dos claves de la plantilla y ninguna mas.

    `extra=forbid` no es celo: sin el, un modelo que pone lo que encontro en una
    clave que se invento deja `faltantes` y `contradicciones` vacias y la
    evaluacion sale `completa`. RF-ORQ-09 dice que una salida fuera de su esquema
    es un fallo, y una clave de mas esta fuera del esquema tanto como la prosa.
    """

    model_config = ConfigDict(extra="forbid")

    faltantes: list[str]
    contradicciones: list[Contradiccion]

    @property
    def completa(self) -> bool:
        return not self.faltantes and not self.contradicciones


class Entrevistador:
    def __init__(self, cliente: ClienteModelo, semilla: int = 0) -> None:
        self._cliente = cliente
        self._semilla = semilla

    async def evaluar(self, respuestas: dict[str, object], texto: str) -> Evaluacion:
        # P-32: las respuestas tambien las escribe el comprador, asi que van
        # marcadas como dato igual que el texto aportado (`CLAUDE.md` §11).
        marca = _MARCA_RESPUESTAS
        cuerpo = _sin_etiquetas(repr(respuestas), marca)
        prompt = (
            render_entrevistador(PLANTILLA_V1, texto)
            + f"\nENTREVISTADOR\n<{marca}>\n{cuerpo}\n</{marca}>"
        )
        crudo = await self._cliente.completar(prompt, semilla=self._semilla)
        try:
            return Evaluacion.model_validate(json_de_modelo(crudo))
        except (json.JSONDecodeError, ValidationError) as error:
            raise SalidaMalFormada(_con_motivo(crudo, error)) from error
