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


def test_sobre_la_base_migrada_un_beat_de_genero_inventado_no_entra(base_migrada):
    """`--autogenerate` **no** compara `CheckConstraint` sobre una tabla que ya
    existe -- `capitulo` existia --, asi que esta restriccion se escribio a mano
    en la migracion. Sin este test, la base de `create_all` la tendria y la que
    tendra la instalacion no, y nada lo diria."""
    _sembrar(base_migrada)

    with pytest.raises(sqlite3.IntegrityError):
        base_migrada.execute("UPDATE capitulo SET beat_de_genero = 'persecucion' WHERE id = 1")

    base_migrada.execute("UPDATE capitulo SET beat_de_genero = 'encuentro' WHERE id = 1")


def test_sobre_la_base_migrada_un_hecho_no_se_sustituye_a_si_mismo(base_migrada):
    """La otra restriccion escrita a mano, por el mismo motivo: `hecho_canon`
    tambien existia."""
    _sembrar(base_migrada)

    with pytest.raises(sqlite3.IntegrityError):
        base_migrada.execute("UPDATE hecho_canon SET sustituye_a = id WHERE id = 1")


def test_sobre_la_base_migrada_una_variante_en_blanco_no_entra(base_migrada):
    """`variante_de_nombre` es tabla **nueva**, asi que aqui el
    `CheckConstraint` si lo emitio `--autogenerate`. Se mira igual: lo que
    importa es que muerda, no quien escribio la linea."""
    _sembrar(base_migrada)

    with pytest.raises(sqlite3.IntegrityError):
        base_migrada.execute(
            "INSERT INTO variante_de_nombre (obra_id, forma_canonica, variante) "
            "VALUES (1, 'Nadia', '  ')"
        )

    base_migrada.execute(
        "INSERT INTO variante_de_nombre (obra_id, forma_canonica, variante) "
        "VALUES (1, 'Nadia', 'Nadi')"
    )


def test_sobre_la_base_migrada_una_variante_no_se_repite(base_migrada):
    _sembrar(base_migrada)
    sentencia = (
        "INSERT INTO variante_de_nombre (obra_id, forma_canonica, variante) "
        "VALUES (1, 'Nadia', 'Nadi')"
    )
    base_migrada.execute(sentencia)

    with pytest.raises(sqlite3.IntegrityError):
        base_migrada.execute(sentencia)


def test_sobre_la_base_migrada_una_ejecucion_anterior_no_tiene_ids_por_capa_nulos(base_migrada):
    """`ids_por_capa` es `NOT NULL` y se anadio a una tabla que puede tener
    filas. Sin `server_default`, el modo batch recrea la tabla y las viejas
    entran con `NULL` -- que es lo que este test destaparia."""
    _sembrar(base_migrada)

    fila = base_migrada.execute("SELECT ids_por_capa FROM ejecucion WHERE id = 1").fetchone()
    assert fila == ("{}",)


def test_sobre_la_base_migrada_estado_en_t_se_deriva_del_ledger(base_migrada):
    """La vista existe y responde sobre datos reales, no solo en `sqlite_master`."""
    _sembrar(base_migrada)

    filas = base_migrada.execute("SELECT personaje FROM estado_en_t ORDER BY personaje").fetchall()
    assert filas == [("Nadia",), ("Teo",)]


def _sembrar(con: sqlite3.Connection) -> None:
    """Una obra, una biblia, un capitulo, su escena, su texto, un evento,
    un hecho de canon y una ejecucion **sin** `ids_por_capa`."""
    con.executescript(
        """
        -- `elementos_obligatorios` desde P-2: la columna es obligatoria y no
        -- admite lista vacia. Este fichero siembra por SQL crudo a proposito
        -- —comprueba el esquema **migrado**, no el que construyen los modelos—
        -- y por eso el arreglo del modelo no lo alcanzo.
        INSERT INTO obra (id, titulo, genero, tono, nivel_de_calor, elementos_obligatorios)
          VALUES (1, 'De prueba', 'romance', 'calido', 2, '["el perro Luna"]');
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
        INSERT INTO hecho_canon (id, obra_id, entidad, atributo, valor, confianza,
                                 origen, escena_de_origen, sustituye_a)
          VALUES (1, 1, 'Nadia', 'ojos', 'verdes', 1.0, 'brief', NULL, NULL);
        -- Sin `ids_por_capa` a proposito: es lo que ejerce el `server_default`
        -- de la migracion, que es lo que salva a las filas anteriores.
        INSERT INTO ejecucion (id, run_id, obra_id, escena_id, version_obra_id,
                               prompt_id, prompt_version, prompt_hash, modelo, semilla,
                               parametros, tokens_por_capa, tokens_previstos,
                               ids_recuperados, ids_canon, creado_en)
          VALUES (1, 'run-1', 1, 1, 1, 'escritor', 'v1', 'a', 'doble', 0,
                  '{}', '{}', 10, '[]', '[]', '2026-09-24 00:00:00+00:00');
        """
    )


def test_sobre_la_base_migrada_un_evento_sustituido_sale_de_las_vistas(base_migrada):
    """Corregir no edita (`CLAUDE.md` §4.2), tambien en el ledger. Corrida
    real, obra 3: el Extractor anoto «cruza el salon hacia la salida» como una
    partida definitiva, y Lean vio a las dos protagonistas reaparecer. El
    evento corregido cita al original, y las vistas solo ven el vigente."""
    _sembrar(base_migrada)
    base_migrada.execute(
        """INSERT INTO evento (id, obra_id, escena_id, descripcion, tiempo_historia, lugar,
                               participantes, testigos, causa, consecuencia, excluye, sustituye_a)
           VALUES (2, 1, 1, 'Nadia encuentra la carta', 'dia 2', 'La cocina',
                   '["Nadia"]', '["Nadia"]', '[]', '[]', '[]', 1)"""
    )

    assert base_migrada.execute("SELECT evento_id, lugar FROM cronologia").fetchall() == [
        (2, "La cocina")
    ]
    assert base_migrada.execute("SELECT DISTINCT evento_id FROM estado_en_t").fetchall() == [(2,)]
