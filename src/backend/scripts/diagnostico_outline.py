"""Diagnostico de un outline que falla con 500: corre `planificar_obra` sobre una
obra existente con el cliente real y muestra la excepcion (tipo y mensaje, sin el
outline). No escribe nada: la sesion se revierte al final.

Uso: uv run python src/backend/scripts/diagnostico_outline.py <obra_id>
"""

import asyncio
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.commons.db.sesion import obtener_motor
from app.commons.llm.claude_code import ClienteClaudeCode
from app.features.outline.agents import Arquitecto
from app.features.outline.service import planificar_obra
from sqlalchemy.ext.asyncio import AsyncSession


async def main(obra_id: int) -> None:
    async with AsyncSession(obtener_motor(), expire_on_commit=False) as sesion:
        try:
            await planificar_obra(sesion, Arquitecto(ClienteClaudeCode()), obra_id)
            print("OK: el outline valido")
        except Exception as error:  # noqa: BLE001 — diagnostico: cualquier fallo se muestra
            print(f"{type(error).__module__}.{type(error).__name__}: {str(error)[:1500]}")
            for linea in traceback.format_exc().splitlines():
                if "app\\" in linea or "app/" in linea:
                    print("  ", linea.strip())
        finally:
            await sesion.rollback()


asyncio.run(main(int(sys.argv[1])))
