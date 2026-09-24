from pathlib import Path

PLANTILLA_V1 = (Path(__file__).parent / "prompts" / "entrevistador.v1.md").read_text(
    encoding="utf-8"
)
_MARCA = "texto_aportado"


def _sin_etiquetas(texto: str) -> str:
    """Quita la etiqueta hasta que quitarla ya no cambie nada.

    Una pasada sola no basta: al borrar el cierre de `</texto</texto_aportado>_aportado>`
    se unen los dos trozos que lo rodeaban y la etiqueta se vuelve a formar. Se repite
    hasta punto fijo, y termina siempre porque cada vuelta que cambia algo acorta la
    cadena.
    """
    sano = texto
    while True:
        podado = sano.replace(f"</{_MARCA}>", "").replace(f"<{_MARCA}>", "")
        if podado == sano:
            return sano
        sano = podado


def render_entrevistador(plantilla: str, texto_aportado: str) -> str:
    """El texto del comprador entra SIEMPRE marcado como dato (CLAUDE.md §11)."""
    if not texto_aportado.strip():
        return plantilla.replace("{{TEXTO_APORTADO}}", "")
    bloque = f"<{_MARCA}>\n{_sin_etiquetas(texto_aportado)}\n</{_MARCA}>"
    return plantilla.replace("{{TEXTO_APORTADO}}", bloque)
