"""Fixtures compartidas por toda la suite del backend.

La base de datos se crea **aplicando la migracion**, no con `create_all`: asi lo
que prueban los tests es el esquema que se desplegara, y una migracion rota se
detecta aqui y no en el arranque.
"""

import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session")
def esquema_migrado(tmp_path_factory: pytest.TempPathFactory) -> Path:
    plantilla = tmp_path_factory.mktemp("esquema") / "plantilla.db"
    resultado = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-x",
            f"url=sqlite:///{plantilla}",
            "upgrade",
            "head",
        ],
        cwd=RAIZ,
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    return plantilla


@pytest.fixture
def base_de_datos(esquema_migrado: Path, tmp_path: Path) -> Iterator[Path]:
    """Copia de la plantilla por test: migrar en cada uno cuesta segundos."""
    import shutil

    destino = tmp_path / "obra.db"
    shutil.copy(esquema_migrado, destino)
    yield destino
