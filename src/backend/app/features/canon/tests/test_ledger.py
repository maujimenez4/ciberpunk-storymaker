"""P-29, P-30, P-31, P-34, P-37 y P-38: el ledger y el estado derivado.

RF-CAN-05, RF-CAN-06, RF-CAN-09, RF-CAN-11 y RF-CAN-13.

La idea que sostiene todo el modulo: **el estado en T no se guarda, se deriva**.
Una tabla de estado editable se desincroniza del texto ya escrito y nadie se
entera hasta que una escena contradice a otra diez capitulos despues. Los
*snapshots* son cache, no verdad, y por eso se pueden invalidar y recalcular.
"""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.commons.domain import RelojFijo
from app.features.canon import RepositorioDeCanon, derivar_estado_en_t

N_SNAPSHOT = 5


@pytest.fixture
def reloj() -> RelojFijo:
    return RelojFijo(datetime(2026, 9, 22, tzinfo=UTC))


@pytest.fixture
def repositorio(base_de_datos: Path) -> RepositorioDeCanon:
    return RepositorioDeCanon(base_de_datos)


@pytest.fixture
def obra(base_de_datos: Path) -> str:
    """Una obra con doce escenas: hacen falta mas de N para probar snapshots."""
    conexion = sqlite3.connect(base_de_datos)
    conexion.execute("INSERT INTO serie (serie_id, titulo) VALUES ('s1','S')")
    conexion.execute(
        "INSERT INTO obra (obra_id, serie_id, titulo, genero, subgenero,"
        " extension_objetivo, persona, tiempo_verbal, esquema_de_pov, nivel_de_calor)"
        " VALUES ('o1','s1','O','romance','contemporaneo',90000,'tercera','pasado',"
        "'dual','sensual')"
    )
    conexion.execute(
        "INSERT INTO parte (parte_id, obra_id, numero, funcion_estructural)"
        " VALUES ('pa1','o1',1,'planteamiento')"
    )
    conexion.execute(
        "INSERT INTO capitulo (capitulo_id, parte_id, numero) VALUES ('ca1','pa1',1)"
    )
    for i in range(1, 13):
        conexion.execute(
            "INSERT INTO escena (escena_id, capitulo_id, orden_discurso, pov)"
            " VALUES (?,?,?,'pj-ada')",
            (f"es{i}", "ca1", i),
        )
    conexion.commit()
    conexion.close()
    return "o1"


# --- P-29: el ledger es append-only ------------------------------------------


def test_ninguna_ruta_actualiza_ni_borra_un_evento(
    repositorio: RepositorioDeCanon, obra: str
) -> None:
    """RF-CAN-05. Lo impone el disparador de la migracion, no el repositorio."""
    repositorio.registrar_evento(
        "s1", "es1", "Ada ve la grieta", testigos=["pj-ada"], participantes=["pj-ada"]
    )

    assert not hasattr(repositorio, "actualizar_evento")
    assert not hasattr(repositorio, "borrar_evento")
    with pytest.raises(sqlite3.IntegrityError):
        repositorio.ejecutar_sql_crudo("UPDATE evento SET descripcion = 'otra'")


def test_el_repositorio_no_contiene_update_ni_delete_sobre_evento() -> None:
    """La prohibicion se lee en el codigo, no solo en la base."""
    from app.features.canon import repository

    fuente = Path(repository.__file__).read_text(encoding="utf-8").lower()
    for prohibido in ("update evento", "delete from evento"):
        assert prohibido not in fuente


# --- P-38: el conocimiento sale de los testigos -------------------------------


def test_el_conocimiento_se_deriva_de_los_testigos(
    repositorio: RepositorioDeCanon, obra: str
) -> None:
    """RF-CAN-11. Es lo que alimenta RF-CAL-05: sin `testigos[]` no hay forma de
    saber quien puede usar un dato y el defecto CON-03 se vuelve indetectable."""
    repositorio.registrar_evento(
        "s1",
        "es1",
        "el incendio",
        testigos=["pj-ada"],
        participantes=["pj-ada", "pj-noe"],
    )

    estado = derivar_estado_en_t(repositorio, "es2")

    assert "el incendio" in estado.sabe("pj-ada")
    assert "el incendio" not in estado.sabe("pj-noe")


def test_un_personaje_no_sabe_lo_de_una_escena_posterior(
    repositorio: RepositorioDeCanon, obra: str
) -> None:
    """El estado en T es "justo antes de" la escena, no "al final de la obra"."""
    repositorio.registrar_evento("s1", "es5", "la carta", testigos=["pj-ada"])

    assert "la carta" not in derivar_estado_en_t(repositorio, "es3").sabe("pj-ada")
    assert "la carta" in derivar_estado_en_t(repositorio, "es6").sabe("pj-ada")


# --- P-30 y P-31: derivado, con snapshots cada N ------------------------------


def test_el_estado_se_deriva_y_no_hay_forma_de_escribirlo(
    repositorio: RepositorioDeCanon,
) -> None:
    """RF-CAN-06: `EstadoEnT` no es una tabla editable."""
    assert not hasattr(repositorio, "guardar_estado_en_t")
    assert not hasattr(repositorio, "actualizar_estado_en_t")


def test_se_crea_un_snapshot_cada_cinco_escenas(
    repositorio: RepositorioDeCanon, obra: str, reloj: RelojFijo
) -> None:
    """D-01: N = 5."""
    creados = [
        repositorio.crear_snapshot_si_toca(f"es{i}", N_SNAPSHOT, reloj)
        for i in range(1, 13)
    ]

    assert [i for i, creado in enumerate(creados, 1) if creado] == [5, 10]


def test_el_snapshot_acelera_pero_no_cambia_el_resultado(
    repositorio: RepositorioDeCanon, obra: str, reloj: RelojFijo
) -> None:
    """Un cache que da otra respuesta que la derivacion completa no es un cache,
    es un segundo origen de verdad."""
    repositorio.registrar_evento("s1", "es1", "el pacto", testigos=["pj-ada"])
    repositorio.registrar_evento("s1", "es6", "la traicion", testigos=["pj-ada"])

    sin_cache = derivar_estado_en_t(repositorio, "es12")
    repositorio.crear_snapshot_si_toca("es10", N_SNAPSHOT, reloj)
    con_cache = derivar_estado_en_t(repositorio, "es12")

    assert sin_cache.conocimientos == con_cache.conocimientos


# --- P-34: un hecho sustituido invalida los snapshots posteriores -------------


def test_un_hecho_sustituido_invalida_los_snapshots_posteriores(
    repositorio: RepositorioDeCanon, obra: str, reloj: RelojFijo
) -> None:
    """RF-CAN-13. Sin esto, una correccion deja el estado derivado mintiendo
    hasta el siguiente snapshot: el fallo silencioso que el ledger evita."""
    repositorio.crear_snapshot_si_toca("es5", N_SNAPSHOT, reloj)
    repositorio.crear_snapshot_si_toca("es10", N_SNAPSHOT, reloj)
    viejo = repositorio.registrar_hecho("s1", "es7", "Ada", "ojos", "verdes")

    repositorio.sustituir_hecho("s1", "es9", viejo.hc_id, "Ada", "ojos", "grises")

    assert repositorio.snapshot_valido_en("es5") is True
    assert repositorio.snapshot_valido_en("es10") is False


def test_los_snapshots_anteriores_al_hecho_siguen_validos(
    repositorio: RepositorioDeCanon, obra: str, reloj: RelojFijo
) -> None:
    """Se recalcula **desde el ultimo valido**, no desde cero: invalidar de mas
    convierte cada correccion en una reconstruccion completa."""
    repositorio.crear_snapshot_si_toca("es5", N_SNAPSHOT, reloj)
    viejo = repositorio.registrar_hecho("s1", "es7", "Ada", "ojos", "verdes")

    repositorio.sustituir_hecho("s1", "es9", viejo.hc_id, "Ada", "ojos", "grises")

    assert repositorio.snapshot_valido_en("es5") is True


# --- P-37: lo que nunca se compacta ------------------------------------------


def test_no_hay_forma_de_compactar_canon_ni_ledger(
    repositorio: RepositorioDeCanon,
) -> None:
    """RF-CAN-09. El olvido de este sistema es de seleccion, no de destruccion:
    un hecho puede dejar de ser relevante para una escena y no entrar en el
    paquete, pero no se borra ni se resume."""
    for prohibido in ("compactar", "purgar", "resumir_canon", "resumir_ledger"):
        assert not hasattr(repositorio, prohibido)
