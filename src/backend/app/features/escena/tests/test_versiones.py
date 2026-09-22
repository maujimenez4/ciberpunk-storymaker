"""P-26, P-27 y P-28: versiones inmutables, dos relojes y la version de obra.

RF-ESC-03 a RF-ESC-06, RD-04. La inmutabilidad no es purismo: es lo que permite
que la `cita` de un defecto se ancle por desplazamiento y siga siendo valida
(axioma 11), y lo que hace comparables dos estrategias de contexto sobre la
misma escena.
"""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.commons.domain import RelojFijo
from app.features.escena import RepositorioDeEscenas


@pytest.fixture
def repositorio(base_de_datos: Path) -> RepositorioDeEscenas:
    return RepositorioDeEscenas(base_de_datos)


@pytest.fixture
def escena_id(base_de_datos: Path) -> str:
    conexion = sqlite3.connect(base_de_datos)
    conexion.execute("INSERT INTO serie (serie_id, titulo) VALUES ('s1','S')")
    conexion.execute(
        "INSERT INTO obra (obra_id, serie_id, titulo, genero, subgenero,"
        " extension_objetivo, persona, tiempo_verbal, esquema_de_pov, nivel_de_calor)"
        " VALUES ('o1','s1','O','romance','contemporaneo',90000,'tercera','pasado',"
        "'dual','sensual')"
    )
    conexion.execute(
        "INSERT INTO version_obra (version_obra_id, obra_id, numero, biblia, creada_en)"
        " VALUES ('vo1','o1',1,'{}','2026-09-22')"
    )
    conexion.execute(
        "INSERT INTO parte (parte_id, obra_id, numero, funcion_estructural)"
        " VALUES ('pa1','o1',1,'planteamiento')"
    )
    conexion.execute(
        "INSERT INTO capitulo (capitulo_id, parte_id, numero) VALUES ('ca1','pa1',1)"
    )
    conexion.execute(
        "INSERT INTO escena (escena_id, capitulo_id, version_obra_id, orden_discurso,"
        " tiempo_historia, pov) VALUES ('es1','ca1','vo1',1,'dia-3','pj-ada')"
    )
    conexion.commit()
    conexion.close()
    return "es1"


@pytest.fixture
def reloj() -> RelojFijo:
    return RelojFijo(datetime(2026, 9, 22, tzinfo=UTC))


def test_guardar_una_version_la_marca_vigente(
    repositorio: RepositorioDeEscenas, escena_id: str, reloj: RelojFijo
) -> None:
    version = repositorio.guardar_version(
        escena_id, "La lluvia cortaba la red.", run_id="run-1", reloj=reloj
    )

    assert version.vigente is True
    assert (
        repositorio.vigente_de(escena_id).version_texto_id == version.version_texto_id
    )


def test_editar_crea_version_nueva_y_desplaza_la_vigente(
    repositorio: RepositorioDeEscenas, escena_id: str, reloj: RelojFijo
) -> None:
    """RF-ESC-04: ninguna ruta modifica texto en sitio."""
    primera = repositorio.guardar_version(escena_id, "Primera.", "run-1", reloj)
    segunda = repositorio.guardar_version(escena_id, "Segunda.", "run-2", reloj)

    historial = repositorio.versiones_de(escena_id)

    assert len(historial) == 2
    assert (
        repositorio.vigente_de(escena_id).version_texto_id == segunda.version_texto_id
    )
    assert repositorio.leer_version(primera.version_texto_id).texto == "Primera."


def test_el_texto_anterior_sobrevive_intacto(
    repositorio: RepositorioDeEscenas, escena_id: str, reloj: RelojFijo
) -> None:
    """Es lo que sostiene el anclaje de la cita (axioma 11): un defecto apunta a
    una version concreta por desplazamiento, y si ese texto cambiara, la cita
    dejaria de ser subcadena exacta sin que nadie lo notara."""
    primera = repositorio.guardar_version(escena_id, "Habia una vez.", "run-1", reloj)
    repositorio.guardar_version(escena_id, "Otra cosa.", "run-2", reloj)

    recuperada = repositorio.leer_version(primera.version_texto_id)

    assert recuperada.texto == "Habia una vez."
    assert recuperada.vigente is False


def test_solo_hay_una_vigente_por_escena(
    repositorio: RepositorioDeEscenas,
    escena_id: str,
    reloj: RelojFijo,
    base_de_datos: Path,
) -> None:
    """Lo impone el indice unico parcial de la migracion, no el servicio."""
    repositorio.guardar_version(escena_id, "Una.", "run-1", reloj)
    repositorio.guardar_version(escena_id, "Dos.", "run-2", reloj)

    conexion = sqlite3.connect(base_de_datos)
    cuantas = conexion.execute(
        "SELECT COUNT(*) FROM version_texto WHERE escena_id = ? AND vigente = 1",
        (escena_id,),
    ).fetchone()[0]
    conexion.close()

    assert cuantas == 1


def test_los_dos_relojes_son_campos_distintos(
    repositorio: RepositorioDeEscenas, escena_id: str
) -> None:
    """RF-ESC-05 y RD-04. Sin separarlos, cualquier analepsis rompe el calculo
    de estado: la escena que se cuenta despues puede ocurrir antes."""
    escena = repositorio.leer_escena(escena_id)

    assert escena.orden_discurso == 1
    assert escena.tiempo_historia == "dia-3"


def test_la_coherencia_se_calcula_por_tiempo_de_historia(
    repositorio: RepositorioDeEscenas, escena_id: str, base_de_datos: Path
) -> None:
    """Una analepsis: la escena 2 del discurso ocurre **antes** en la historia.

    Ordenar por `orden_discurso` daria un estado en T equivocado, y el
    validador de conocimiento (RF-CAL-05) acusaria a un personaje de saber algo
    que en realidad ya habia vivido.
    """
    conexion = sqlite3.connect(base_de_datos)
    conexion.execute(
        "INSERT INTO escena (escena_id, capitulo_id, version_obra_id, orden_discurso,"
        " tiempo_historia, pov) VALUES ('es2','ca1','vo1',2,'dia-1','pj-ada')"
    )
    conexion.commit()
    conexion.close()

    por_discurso = [e.escena_id for e in repositorio.escenas_por_orden_discurso("ca1")]
    por_historia = [e.escena_id for e in repositorio.escenas_por_tiempo_historia("ca1")]

    assert por_discurso == ["es1", "es2"]
    assert por_historia == ["es2", "es1"]


def test_la_escena_recuerda_con_que_version_de_obra_se_escribio(
    repositorio: RepositorioDeEscenas, escena_id: str
) -> None:
    """RF-ESC-06."""
    assert repositorio.leer_escena(escena_id).version_obra_id == "vo1"


def test_el_motor_rechaza_dos_vigentes_aunque_se_salten_el_servicio(
    escena_id: str, base_de_datos: Path
) -> None:
    """RF-ESC-03 impuesta por el indice unico parcial, no por el repositorio.

    El test anterior pasaria igual si la unica garantia fuera el UPDATE del
    servicio. Este inserta con sqlite3 a pelo: si el indice no existiera,
    tendriamos dos versiones vigentes y el manuscrito no sabria cual ensamblar.
    """
    conexion = sqlite3.connect(base_de_datos)
    for i in (1, 2):
        try:
            conexion.execute(
                "INSERT INTO version_texto (version_texto_id, escena_id, texto,"
                " vigente, run_id, autoria, creada_en)"
                " VALUES (?,?,?,1,?,'generado','2026-09-22')",
                (f"vt{i}", escena_id, f"texto {i}", f"run-{i}"),
            )
        except sqlite3.IntegrityError:
            conexion.close()
            return
    conexion.close()
    raise AssertionError("el motor acepto dos versiones vigentes para la misma escena")
