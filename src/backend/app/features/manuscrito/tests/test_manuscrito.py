"""P-90 y P-94: el manuscrito y el registro de ejecución.

RF-MAN-01, RF-MAN-02, RI-14 y RD-06.
"""

import sqlite3
from datetime import UTC, datetime
from itertools import count
from pathlib import Path

import pytest

from app.commons.db import RegistroDeEjecucion, RepositorioDeEjecuciones
from app.commons.domain import RelojFijo
from app.features.manuscrito import RepositorioDeManuscrito


@pytest.fixture
def reloj() -> RelojFijo:
    return RelojFijo(datetime(2026, 9, 22, tzinfo=UTC))


@pytest.fixture
def obra(base_de_datos: Path) -> str:
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
    # La escena 2 ocurre **antes** en la historia: una analepsis.
    for escena, orden, historia in (("es1", 1, "dia-9"), ("es2", 2, "dia-1")):
        conexion.execute(
            "INSERT INTO escena (escena_id, capitulo_id, orden_discurso,"
            " tiempo_historia, pov) VALUES (?,?,?,?,'pj-ada')",
            (escena, "ca1", orden, historia),
        )
    conexion.commit()
    conexion.close()
    return "o1"


_contador = count()


def _version(
    base: Path, escena: str, texto: str, autoria: str, vigente: int = 1
) -> None:
    conexion = sqlite3.connect(base)
    if vigente:
        conexion.execute(
            "UPDATE version_texto SET vigente = 0 WHERE escena_id = ?", (escena,)
        )
    conexion.execute(
        "INSERT INTO version_texto (version_texto_id, escena_id, texto, vigente,"
        " run_id, autoria, creada_en) VALUES (?,?,?,?,?,?,'2026-09-22')",
        (f"vt-{next(_contador)}", escena, texto, vigente, "run-1", autoria),
    )
    conexion.commit()
    conexion.close()


# --- P-90: el manuscrito -----------------------------------------------------


def test_se_ensambla_en_orden_de_discurso_no_de_historia(
    base_de_datos: Path, obra: str
) -> None:
    """RF-MAN-01. El manuscrito es lo que el lector lee: una analepsis se lee
    donde el autor la puso, no donde ocurrió. Los dos relojes se separaron
    precisamente para poder decir esto sin ambigüedad."""
    _version(base_de_datos, "es1", "Primera en el discurso.", "generado")
    _version(base_de_datos, "es2", "Segunda, pero ocurre antes.", "generado")

    manuscrito = RepositorioDeManuscrito(base_de_datos).ensamblar(obra)

    assert [f.escena_id for f in manuscrito.fragmentos] == ["es1", "es2"]


def test_solo_entran_las_versiones_vigentes(base_de_datos: Path, obra: str) -> None:
    """RF-ESC-03. Si entrara el historial, el manuscrito tendría cada escena
    tantas veces como intentos costó escribirla."""
    _version(base_de_datos, "es1", "Version vieja.", "generado")
    _version(base_de_datos, "es1", "Version buena.", "editado")

    manuscrito = RepositorioDeManuscrito(base_de_datos).ensamblar(obra)

    assert manuscrito.texto == "Version buena."


def test_una_escena_sin_version_vigente_no_aparece(
    base_de_datos: Path, obra: str
) -> None:
    """Está planificada pero no escrita. Meterla vacía daría un manuscrito con
    huecos que parecen texto perdido."""
    _version(base_de_datos, "es1", "La unica escrita.", "generado")

    manuscrito = RepositorioDeManuscrito(base_de_datos).ensamblar(obra)

    assert [f.escena_id for f in manuscrito.fragmentos] == ["es1"]


def test_se_registra_la_autoria_de_cada_fragmento(
    base_de_datos: Path, obra: str
) -> None:
    """RF-MAN-02. Sin esto no se puede responder a qué parte la escribió una
    persona, y reconstruirlo después es imposible: el texto no lo dice."""
    _version(base_de_datos, "es1", "Generada por el modelo.", "generado")
    _version(base_de_datos, "es2", "Escrita a mano.", "humano")

    autorias = RepositorioDeManuscrito(base_de_datos).ensamblar(obra).autorias()

    assert autorias == {"generado": 1, "humano": 1}


# --- P-94: el registro de ejecución ------------------------------------------


REGISTRO = RegistroDeEjecucion(
    run_id="run-1",
    escena_id="es1",
    prompt_id="escritor",
    prompt_version="v1",
    prompt_hash="abc123",
    version_obra_id="vo1",
    ids_recuperados=["frag-1", "frag-2"],
    modelo="modelo-de-prueba",
    parametros={"temperatura": 0.8},
    semilla=42,
    tokens_por_capa={"constitucional": 400, "canon_relevante": 2100},
    coste=0.031,
    veredicto="aprobada",
)


def test_la_ejecucion_guarda_el_conjunto_completo(
    base_de_datos: Path, obra: str, reloj: RelojFijo
) -> None:
    """RI-14 y RD-06, campo a campo."""
    repositorio = RepositorioDeEjecuciones(base_de_datos)

    ejecucion_id = repositorio.registrar(REGISTRO, reloj)
    leido = repositorio.leer(ejecucion_id)

    assert leido == REGISTRO


def test_el_hash_del_prompt_viaja_con_su_version(
    base_de_datos: Path, obra: str, reloj: RelojFijo
) -> None:
    """RD-01: `Prompt` no es tabla. Con id, versión y hash se sabe exactamente
    qué texto se envió, sin un segundo sistema de versionado."""
    repositorio = RepositorioDeEjecuciones(base_de_datos)

    leido = repositorio.leer(repositorio.registrar(REGISTRO, reloj))

    assert (leido.prompt_id, leido.prompt_version, leido.prompt_hash) == (
        "escritor",
        "v1",
        "abc123",
    )


def test_los_ids_recuperados_permiten_auditar_aunque_no_reproducir(
    base_de_datos: Path, obra: str, reloj: RelojFijo
) -> None:
    """RF-CTX-13 tras D-02. Ya no se puede prometer reproducir el paquete —la
    ordenación semántica tiene varianza—, pero sí saber exactamente qué se
    envió. Por eso `ids_recuperados` no es opcional."""
    repositorio = RepositorioDeEjecuciones(base_de_datos)

    leido = repositorio.leer(repositorio.registrar(REGISTRO, reloj))

    assert leido.ids_recuperados == ["frag-1", "frag-2"]
    assert sum(leido.tokens_por_capa.values()) == 2500


def test_el_run_id_correlaciona_las_llamadas_de_un_trabajo(
    base_de_datos: Path, obra: str, reloj: RelojFijo
) -> None:
    """§3.2: es la clave que junta las tres o cuatro llamadas de una escena."""
    repositorio = RepositorioDeEjecuciones(base_de_datos)
    repositorio.registrar(REGISTRO, reloj)
    repositorio.registrar(REGISTRO.model_copy(update={"prompt_id": "extractor"}), reloj)
    repositorio.registrar(REGISTRO.model_copy(update={"run_id": "run-2"}), reloj)

    assert len(repositorio.de_run("run-1")) == 2
