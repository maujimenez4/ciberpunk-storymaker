"""P-03: las claves se leen de entorno y no dejan rastro (RI-15, RNF-SEG-03).

Tres cosas distintas, y las tres han fallado en proyectos reales:
el codigo no trae la clave dentro, los ajustes no la buscan en un fichero,
y el objeto de ajustes no la escupe al registrarse en un log (RNF-OBS-03).
"""

import re
from pathlib import Path

import pytest
from pydantic import SecretStr

from app.commons.config import Ajustes, cargar_ajustes
from app.commons.config.tests.test_ajustes import ENTORNO_COMPLETO

CAMPOS_SECRETOS = ("proveedor_generacion_clave", "proveedor_embeddings_clave")

RAIZ = Path(__file__).resolve().parents[6]  # raiz del repositorio

# Formas habituales de una clave escrita a mano en el codigo.
SOSPECHOSOS = re.compile(
    r"""(sk-[A-Za-z0-9_-]{16,})"""
    r"""|(?:clave|token|secret|api_key|password)\s*[:=]\s*["'][^"']{16,}["']""",
    re.IGNORECASE,
)


def test_las_claves_son_secretas_y_no_aparecen_al_representar_los_ajustes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RNF-OBS-03: registrar los ajustes no puede filtrar la clave."""
    for nombre, valor in ENTORNO_COMPLETO.items():
        monkeypatch.setenv(nombre, valor)

    ajustes = cargar_ajustes()

    for campo in CAMPOS_SECRETOS:
        assert isinstance(getattr(ajustes, campo), SecretStr)
    assert "clave-de-prueba" not in repr(ajustes)
    assert "clave-de-prueba" not in str(ajustes)


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
