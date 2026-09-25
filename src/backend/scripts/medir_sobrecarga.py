"""Medida de P-21 (plan 8, T5): ¿cuántos tokens añade el CLI a cada llamada?

El paquete que contamos con `ContadorTiktoken` no es todo lo que llega al
modelo: el CLI del Claude Agent SDK envuelve el prompt con lo suyo. Esa
diferencia es la que el techo concurrente tiene que reservar por llamada
(`commons/jobs/turnos.py`, `SOBRECARGA_POR_LLAMADA`).

Tres tamaños de prompt (~50, ~2.000 y ~8.000 tokens contados) y dos rondas
seguidas, para ver el efecto de la caché. Salidas cortas: se pide «ok».
Seis llamadas reales; no se ejecuta en la suite. Uso, desde la raíz:

    uv run python src/backend/scripts/medir_sobrecarga.py

Imprime una tabla y una línea JSON con el máximo. **No imprime los prompts.**
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.commons.llm.claude_code import ClienteClaudeCode
from app.commons.llm.contador import ContadorTiktoken

OBJETIVOS = (50, 2_000, 8_000)
RONDAS = 2

_INSTRUCCION = "Responde solo con la palabra ok.\n\n"
_RELLENO = (
    "La marea subia despacio sobre la arena de la playa mientras el faro "
    "encendia su luz y las gaviotas volvian a los acantilados del norte. "
)


def _prompt_de(objetivo: int, contador: ContadorTiktoken) -> str:
    """Un prompt de unos `objetivo` tokens contados, que termina pidiendo «ok»."""
    texto = _INSTRUCCION
    while contador.contar(texto) < objetivo:
        texto += _RELLENO
    return texto + "\nResponde solo: ok"


async def main() -> None:
    contador = ContadorTiktoken()
    cliente = ClienteClaudeCode()
    prompts = {objetivo: _prompt_de(objetivo, contador) for objetivo in OBJETIVOS}
    filas: list[dict[str, int]] = []

    for ronda in range(1, RONDAS + 1):
        for objetivo, prompt in prompts.items():
            await cliente.completar(prompt, semilla=0)
            consumo = cliente.ultimo_consumo
            assert consumo is not None
            contados = contador.contar(prompt)
            total = (
                consumo.tokens_entrada
                + consumo.cache_read_input_tokens
                + consumo.cache_creation_input_tokens
            )
            filas.append(
                {
                    "ronda": ronda,
                    "objetivo": objetivo,
                    "contados": contados,
                    "input_tokens": consumo.tokens_entrada,
                    "cache_read": consumo.cache_read_input_tokens,
                    "cache_creation": consumo.cache_creation_input_tokens,
                    "output_tokens": consumo.tokens_salida,
                    "sobrecarga": total - contados,
                }
            )

    columnas = list(filas[0])
    print(" | ".join(columnas))
    for fila in filas:
        print(" | ".join(str(fila[c]) for c in columnas))
    print(
        json.dumps(
            {
                "modelo": cliente.modelo,
                "sobrecarga_maxima": max(f["sobrecarga"] for f in filas),
                "sobrecarga_minima": min(f["sobrecarga"] for f in filas),
            }
        )
    )


asyncio.run(main())
