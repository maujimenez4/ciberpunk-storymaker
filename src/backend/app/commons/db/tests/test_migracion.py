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

# P-06b - biblia y mundo. RD-03: parte fija y parte movil del Personaje en
# estructuras separadas; aqui solo vive la fija. La movil se deriva del ledger.
BIBLIA_Y_MUNDO: dict[str, set[str]] = {
    "personaje": {
        "pj_id",
        "obra_id",
        "nombre",
        "edad",
        "fisico_invariable",
        "herida_original",
        "mentira_que_se_cree",
        "deseo_consciente",
        "necesidad_inconsciente",
        "miedo_central",
        "rol_narrativo",
    },
    "perfil_de_voz": {"perfil_de_voz_id", "pj_id", "registro", "muletillas"},
    "relacion": {
        "rel_id",
        "personaje_a",
        "personaje_b",
        "tipo",
        "conflicto_central",
    },
    "lugar": {"lug_id", "obra_id", "nombre", "sensorialidad_fija"},
    "distancia_entre_lugares": {"origen_id", "destino_id", "tiempo_de_viaje"},
    "objeto": {"obj_id", "obra_id", "nombre", "carga_simbolica"},
    "regla_de_mundo": {
        "regla_id",
        "obra_id",
        "enunciado",
        "alcance",
        "escena_en_que_se_establece",
    },
}

# P-06c - canon, ledger, estado derivado e indice.
CANON: dict[str, set[str]] = {
    "entidad": {"entidad_id", "obra_id", "tipo", "nombre"},
    "hecho_canon": {
        "hc_id",
        "serie_id",
        "entidad",
        "atributo",
        "valor",
        "escena_de_origen",
        "confianza",
        "sustituye_a",
    },
    "evento": {
        "evt_id",
        "serie_id",
        "descripcion",
        "tiempo_historia",
        "lugar",
        "participantes",
        "testigos",
        "escena_de_origen",
    },
    "plantado": {
        "plantado_id",
        "escena_de_origen",
        "importancia",
        "escena_de_pago_prevista",
        "escena_de_pago",
    },
    "hilo_narrativo": {
        "hilo_id",
        "pregunta",
        "escena_de_apertura",
        "escena_de_cierre",
        "estado",
    },
    "resumen": {"resumen_id", "nivel", "referencia_id", "texto"},
    "snapshot_estado_en_t": {
        "snapshot_id",
        "escena_id",
        "estado",
        "valido",
        "creado_en",
    },
    "fragmento": {
        "fragmento_id",
        "version_texto_id",
        "texto",
        "embedding",
        "dimension",
    },
}

TABLAS = {**OBRA_Y_MANUSCRITO, **BIBLIA_Y_MUNDO, **CANON}


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


@pytest.mark.parametrize("tabla", sorted(TABLAS))
def test_la_migracion_crea_la_tabla(tabla: str, esquema: dict[str, set[str]]) -> None:
    assert tabla in esquema, f"falta la tabla {tabla}"


@pytest.mark.parametrize("tabla", sorted(TABLAS))
def test_las_columnas_llevan_los_nombres_de_definitions(
    tabla: str, esquema: dict[str, set[str]]
) -> None:
    """RD-02: no se traducen, no se abrevian, no se inventan sinonimos."""
    faltan = TABLAS[tabla] - esquema.get(tabla, set())
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


def test_el_ledger_rechaza_actualizar_y_borrar_por_construccion(
    tmp_path: Path,
) -> None:
    """RF-CAN-05: append-only no es una convencion, es el motor.

    Si solo lo impidiera el repositorio, cualquier consulta suelta o una
    migracion futura podria romperlo sin que nada avisara.
    """
    import sqlite3
    import subprocess
    import sys as _sys

    fichero = tmp_path / "obra.db"
    assert (
        subprocess.run(
            [
                _sys.executable,
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
        ).returncode
        == 0
    )
    conexion = sqlite3.connect(fichero)
    conexion.execute("INSERT INTO serie (serie_id, titulo) VALUES ('s1', 'S')")
    conexion.execute(
        "INSERT INTO evento (evt_id, serie_id, descripcion) VALUES ('e1', 's1', 'x')"
    )
    conexion.commit()
    for sentencia in (
        "UPDATE evento SET descripcion = 'y' WHERE evt_id = 'e1'",
        "DELETE FROM evento WHERE evt_id = 'e1'",
    ):
        try:
            conexion.execute(sentencia)
        except sqlite3.IntegrityError:
            continue
        raise AssertionError(f"el ledger acepto: {sentencia}")
    conexion.close()
