"""P-03 y P-107: la aplicacion no guarda ninguna credencial (RI-15, RNF-SEG-03).

Tras la decision (a) de 2026-09-22, RI-15 cambia de significado. Antes decia
«las claves se leen de entorno, nunca del repositorio»; ahora dice algo mas
fuerte: **no hay claves**. El proveedor es el CLI de Claude Code y autentica con
la sesion de la cuenta, fuera del proceso.

Los tres casos de aqui siguen valiendo, y el primero gana: el que comprobaba que
la clave no se filtrara al representar los ajustes se sustituye por el que
comprueba que no hay clave que filtrar.
"""

import re
from pathlib import Path

import pytest
from pydantic import SecretStr

from app.commons.config import Ajustes, cargar_ajustes
from app.commons.config.tests.test_ajustes import ENTORNO_COMPLETO

RAIZ = Path(__file__).resolve().parents[6]  # raiz del repositorio

# Formas habituales de una clave escrita a mano en el codigo.
SOSPECHOSOS = re.compile(
    r"""(sk-[A-Za-z0-9_-]{16,})"""
    r"""|(?:clave|token|secret|api_key|password)\s*[:=]\s*["'][^"']{16,}["']""",
    re.IGNORECASE,
)


def test_los_ajustes_no_declaran_ninguna_credencial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RI-15 y RNF-SEG-03: no se protege un secreto, no se tiene.

    Un `SecretStr` aqui significaria que el proceso vuelve a custodiar una
    credencial, y con ella vuelven las tres formas de perderla: el log, el repr
    y el volcado de configuracion.
    """
    for nombre, valor in ENTORNO_COMPLETO.items():
        monkeypatch.setenv(nombre, valor)

    ajustes = cargar_ajustes()

    secretos = [
        nombre
        for nombre, campo in Ajustes.model_fields.items()
        if campo.annotation is SecretStr
    ]
    assert not secretos, f"vuelve a haber credenciales en los ajustes: {secretos}"
    assert "SecretStr" not in repr(ajustes)


def test_los_ajustes_no_leen_ningun_fichero_de_entorno() -> None:
    """RI-15: de entorno, nunca del repositorio. Un .env es el repositorio."""
    assert Ajustes.model_config.get("env_file") is None
    assert Ajustes.model_config.get("secrets_dir") is None


def test_el_codigo_no_contiene_literales_con_pinta_de_clave() -> None:
    """RNF-SEG-04: el repositorio no contiene claves."""
    culpables = []
    for fichero in (RAIZ / "src" / "backend" / "app").rglob("*.py"):
        if "tests" in fichero.parts:
            continue
        for numero, linea in enumerate(
            fichero.read_text(encoding="utf-8").splitlines(), 1
        ):
            if SOSPECHOSOS.search(linea):
                culpables.append(f"{fichero.relative_to(RAIZ)}:{numero}")
    assert not culpables, f"literales con pinta de clave: {culpables}"
