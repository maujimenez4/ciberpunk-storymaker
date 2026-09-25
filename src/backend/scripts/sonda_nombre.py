"""Sonda de P-19 (plan 8, T1): ¿el modelo, con ESTA cuenta, conserva el nombre del destinatario?

Una llamada real al Arquitecto (unos 3 minutos). No se ejecuta en la suite.
Uso, desde la raíz del repositorio:

    uv run python src/backend/scripts/sonda_nombre.py

Imprime una sola línea JSON. No imprime el outline: solo cuenta.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.commons.llm.claude_code import ClienteClaudeCode  # noqa: E402
from app.features.outline.agents import PLANTILLA_V2, render_arquitecto  # noqa: E402

BRIEF = json.loads(Path("ejemplos/brief-marta.json").read_text(encoding="utf-8"))

# Con un argumento, el nombre del destinatario se sustituye por ese: sirve para
# comprobar si la cuenta anonimiza tambien un nombre inventado (el marcador de T2).
if len(sys.argv) > 1:
    BRIEF["destinatario"]["nombre"] = sys.argv[1]
    BRIEF["dedicatoria"] = BRIEF.get("dedicatoria", "").replace("Marta", sys.argv[1])


async def main() -> None:
    nombre = BRIEF["destinatario"]["nombre"]
    prompt = render_arquitecto(PLANTILLA_V2, {"titulo": f"Novela para {nombre}", **BRIEF})
    salida = await ClienteClaudeCode().completar(prompt, semilla=0)
    print(
        json.dumps(
            {
                "nombre": nombre,
                "apariciones_del_nombre": salida.count(nombre),
                "anonimizado": "ANONIMIZADO" in salida.upper(),
                "marcas_de_anonimizado": salida.upper().count("ANONIMIZADO"),
                "longitud_de_la_salida": len(salida),
            },
            ensure_ascii=False,
        )
    )


asyncio.run(main())
