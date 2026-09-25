"""Sonda de Langfuse: abre una traza y un span de prueba con el observador REAL,
sin blindaje, y enseña el error si lo hay. No imprime credenciales.

Uso (con las variables del .env cargadas): uv run python src/backend/scripts/sonda_langfuse.py
"""

import asyncio
import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.commons.config.ajustes import Ajustes
from app.commons.observabilidad.langfuse import ObservadorLangfuse


async def main() -> None:
    for nombre in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST", "LANGFUSE_BASE_URL"):
        print(f"{nombre}: {'definida' if os.environ.get(nombre) else 'NO definida'}")
    ajustes = Ajustes.desde_entorno()
    print("host resuelto:", ajustes.langfuse_host)
    if not (ajustes.langfuse_clave_publica and ajustes.langfuse_clave_secreta and ajustes.langfuse_host):
        print("FALTAN credenciales: el backend usaria ObservadorNulo")
        return
    observador = ObservadorLangfuse(
        clave_publica=ajustes.langfuse_clave_publica,
        clave_secreta=ajustes.langfuse_clave_secreta,
        host=ajustes.langfuse_host,
    )
    try:
        async with observador.traza(obra_id=0, nombre="sonda") as traza:
            async with traza.span("sonda") as span:
                span.entrada("hola")
                span.salida("adios")
                from decimal import Decimal

                span.consumo(
                    modelo="claude-haiku-4-5",
                    tokens_entrada=1000,
                    tokens_salida=200,
                    coste_usd=Decimal("0.002"),
                )
        observador.cerrar()
        print("OK: traza enviada (sesion obra-0, traza 'sonda')")
    except Exception:  # noqa: BLE001 — diagnostico
        traceback.print_exc()


asyncio.run(main())
