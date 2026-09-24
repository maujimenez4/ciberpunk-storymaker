"""Las restricciones, sobre la base **migrada**.

Son dos esquemas y solo uno existira: el de `Base.metadata.create_all`, que es
el que levantan los tests, y el de `alembic upgrade head`, que es el que tendra
la instalacion. Que una comprobacion muerda en el primero no dice nada del
segundo -- `--autogenerate` no compara restricciones de comprobacion, y los
disparadores y las vistas no salen de `Base.metadata` en absoluto --, asi que
este modulo levanta la base migrada de verdad y le pide lo mismo.

Es el unico modulo que corre Alembic. No usa ningun modelo: habla SQL contra el
fichero, porque comparar los dos esquemas importando uno de ellos seria
comprobar que un lado se parece a si mismo. `Base` si se importa, y solo para
mirar sus nombres.

No es un test asincrono: `alembic/env.py` hace su propio `asyncio.run`, y eso
no cabe dentro de un bucle ya arrancado.
"""

import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from app.commons.db.base import Base

# tests -> canon -> features -> app -> backend -> src -> raiz del repositorio.
RAIZ = Path(__file__).resolve().parents[6]


@pytest.fixture
def base_migrada(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> sqlite3.Connection:
    """`alembic upgrade head` sobre una base vacia del `tmp_path` de pytest.

    La ruta sale de `STORYMAKER_DB` porque `env.py` la lee de `Ajustes` y de
    ningun otro sitio: sin esto, el test migraria la base del desarrollador.
    """
    ruta = tmp_path / "migrada.db"
    monkeypatch.setenv("STORYMAKER_DB", str(ruta))

    config = Config(str(RAIZ / "alembic.ini"))
    config.set_main_option("script_location", str(RAIZ / "src" / "backend" / "alembic"))
    command.upgrade(config, "head")

    con = sqlite3.connect(ruta)
    con.execute("PRAGMA foreign_keys=ON")
    yield con
    con.close()


def _nombres(con: sqlite3.Connection, tipo: str) -> set[str]:
    filas = con.execute(
        "SELECT name FROM sqlite_master WHERE type = ? AND name NOT LIKE 'sqlite_%'", (tipo,)
    )
    # `alembic_version` es de Alembic y no del proyecto: no esta en `Base.metadata`
    # y tampoco deberia, porque nadie la mapea.
    return {fila[0] for fila in filas} - {"alembic_version"}


def test_la_base_migrada_tiene_las_mismas_tablas_que_el_metadata(base_migrada):
    """La migracion y `create_all` describen la misma base, o una de las dos miente."""
    assert _nombres(base_migrada, "table") == set(Base.metadata.tables)


def test_la_base_migrada_trae_las_dos_vistas_derivadas(base_migrada):
    """RF-MEM-03 y RF-MEM-05 sobre el esquema que tendra la instalacion."""
    assert _nombres(base_migrada, "view") == {"estado_en_t", "cronologia"}


def test_la_base_migrada_trae_los_disparadores_que_hacen_de_pared(base_migrada):
    assert _nombres(base_migrada, "trigger") == {
        "trg_evento_sin_update",
        "trg_evento_sin_delete",
        "trg_version_texto_inmutable",
    }


def test_sobre_la_base_migrada_el_ledger_rechaza_update_y_delete(base_migrada):
    """RF-MEM-05 donde de verdad tiene que morder."""
    _sembrar(base_migrada)

    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        base_migrada.execute("UPDATE evento SET descripcion = 'otra' WHERE id = 1")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        base_migrada.execute("DELETE FROM evento WHERE id = 1")


def test_sobre_la_base_migrada_el_texto_de_una_version_es_inmutable(base_migrada):
    """RF-ESC-02: cambiar el texto aborta; marcar la vigente no."""
    _sembrar(base_migrada)

    with pytest.raises(sqlite3.IntegrityError, match="inmutable"):
        base_migrada.execute("UPDATE version_texto SET texto = 'otra cosa' WHERE id = 1")

    base_migrada.execute("UPDATE version_texto SET vigente = 0 WHERE id = 1")


def test_sobre_la_base_migrada_una_escena_sin_giro_de_valor_no_entra(base_migrada):
    """Regla de dominio 1. `--autogenerate` no compara `CheckConstraint`: se mira."""
    _sembrar(base_migrada)

    with pytest.raises(sqlite3.IntegrityError):
        base_migrada.execute("UPDATE escena SET valor_salida = valor_entrada WHERE id = 1")


def test_sobre_la_base_migrada_un_capitulo_fuera_de_rango_no_entra(base_migrada):
    _sembrar(base_migrada)

    with pytest.raises(sqlite3.IntegrityError):
        base_migrada.execute("UPDATE capitulo SET extension_objetivo = 9000 WHERE id = 1")


def test_sobre_la_base_migrada_estado_en_t_se_deriva_del_ledger(base_migrada):
    """La vista existe y responde sobre datos reales, no solo en `sqlite_master`."""
    _sembrar(base_migrada)

    filas = base_migrada.execute("SELECT personaje FROM estado_en_t ORDER BY personaje").fetchall()
    assert filas == [("Nadia",), ("Teo",)]


def _sembrar(con: sqlite3.Connection) -> None:
    """Una obra, una biblia, un capitulo, su escena, su texto y un evento."""
    con.executescript(
        """
        INSERT INTO obra (id, titulo, genero, tono, nivel_de_calor)
          VALUES (1, 'De prueba', 'romance', 'calido', 2);
        INSERT INTO version_obra (id, obra_id, numero, biblia, vigente_desde)
          VALUES (1, 1, 1, '{}', '2026-09-24 00:00:00+00:00');
        INSERT INTO capitulo (id, obra_id, numero, titulo, pov_dominante,
                              gancho_de_apertura, tipo_de_corte_final, extension_objetivo,
                              lugar, objetivo, obstaculo, giro_de_valor_previsto)
          VALUES (1, 1, 1, 'Uno', 'Nadia', 'La puerta', 'pregunta', 1200,
                  'El invernadero', 'Que Teo confiese', 'Teo calla',
                  'confianza -> sospecha');
        INSERT INTO escena (id, capitulo_id, version_obra_id, orden_discurso, tiempo_historia,
                            pov, lugar, presentes, mencionados, objetivo_del_pov, obstaculo,
                            resultado, valor_entrada, valor_salida, extension_objetivo,
                            densidad_de_dialogo_objetivo, distancia_psiquica,
                            planta, paga, revela)
          VALUES (1, 1, 1, 1, 'dia 2', 'Nadia', 'El invernadero', '[]', '[]', 'Que Teo confiese',
                  'Teo calla', 'si-pero', 'confianza', 'sospecha', 1200, 0.4, 3, '[]', '[]', '[]');
        INSERT INTO version_texto (id, escena_id, numero, texto, vigente, run_id, creado_en)
          VALUES (1, 1, 1, 'La puerta estaba abierta.', 1, 'run-1', '2026-09-24 00:00:00+00:00');
        INSERT INTO evento (id, obra_id, escena_id, descripcion, tiempo_historia, lugar,
                            participantes, testigos, causa, consecuencia, excluye)
          VALUES (1, 1, 1, 'Nadia encuentra la carta', 'dia 2', 'El invernadero',
                  '["Nadia"]', '["Nadia","Teo"]', '[]', '[]', '[]');
        """
    )
