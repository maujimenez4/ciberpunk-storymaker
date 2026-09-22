"""P-06: la migracion inicial crea el esquema declarado (RD-01, RD-02).

RD-02 es lo que de verdad se comprueba aqui: los nombres son **los de
`definitions.md`**, sin traducir ni abreviar. Un esquema con los nombres
cambiados funciona igual y rompe el vocabulario compartido del proyecto, que es
lo que §2 del manual protege.

Este fichero crece con P-06a, P-06b y P-06c; la revision de Alembic es una sola.
"""

import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

RAIZ = Path(__file__).resolve().parents[6]  # raiz del repositorio

# P-06a - obra y manuscrito. Columnas: solo las que otro requisito cita.
OBRA_Y_MANUSCRITO: dict[str, set[str]] = {
    "serie": {"serie_id", "titulo"},
    "obra": {
        "obra_id",
        "serie_id",
        "titulo",
        "genero",
        "subgenero",
        "extension_objetivo",
        "promesa_de_apertura",
        "persona",
        "tiempo_verbal",
        "esquema_de_pov",
        "nivel_de_calor",
    },
    "version_obra": {"version_obra_id", "obra_id", "numero", "creada_en"},
    "parte": {"parte_id", "obra_id", "numero", "funcion_estructural"},
    "capitulo": {"capitulo_id", "parte_id", "numero", "pov_dominante"},
    "escena": {
        "escena_id",
        "capitulo_id",
        "version_obra_id",
        "orden_discurso",
        "tiempo_historia",
        "pov",
        "lugar",
        "objetivo_del_pov",
        "obstaculo",
        "valor_entrada",
        "valor_salida",
        "extension_objetivo",
        "densidad_de_dialogo_objetivo",
        "distancia_psiquica",
        "beat_de_genero",
    },
    "version_texto": {
        "version_texto_id",
        "escena_id",
        "texto",
        "vigente",
        "run_id",
        "autoria",
        "creada_en",
    },
}


@pytest.fixture(scope="module")
def esquema(tmp_path_factory: pytest.TempPathFactory) -> dict[str, set[str]]:
    """Aplica `alembic upgrade head` sobre un fichero limpio y lee el resultado."""
    fichero = tmp_path_factory.mktemp("migracion") / "obra.db"
    resultado = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-x",
            f"url=sqlite:///{fichero}",
            "upgrade",
            "head",
        ],
        cwd=RAIZ,
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, resultado.stderr
    inspector = inspect(create_engine(f"sqlite:///{fichero}"))
    return {
        tabla: {c["name"] for c in inspector.get_columns(tabla)}
        for tabla in inspector.get_table_names()
    }


@pytest.mark.parametrize("tabla", sorted(OBRA_Y_MANUSCRITO))
def test_la_migracion_crea_la_tabla(tabla: str, esquema: dict[str, set[str]]) -> None:
    assert tabla in esquema, f"falta la tabla {tabla}"


@pytest.mark.parametrize("tabla", sorted(OBRA_Y_MANUSCRITO))
def test_las_columnas_llevan_los_nombres_de_definitions(
    tabla: str, esquema: dict[str, set[str]]
) -> None:
    """RD-02: no se traducen, no se abrevian, no se inventan sinonimos."""
    faltan = OBRA_Y_MANUSCRITO[tabla] - esquema.get(tabla, set())
    assert not faltan, f"{tabla}: faltan columnas {sorted(faltan)}"


def test_el_canon_cuelga_de_la_serie_desde_la_migracion_inicial(
    esquema: dict[str, set[str]],
) -> None:
    """RD-11: `serie_id` existe desde el primer dia aunque la v1 no use series.

    Anadirlo despues obliga a reescribir todas las referencias de canon
    (`definitions.md` §4.1), y por eso no es una decision aplazable.
    """
    assert "serie" in esquema
    assert "serie_id" in esquema["obra"]
