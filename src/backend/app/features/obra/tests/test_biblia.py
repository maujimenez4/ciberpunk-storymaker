"""P-20: la biblia es versionada y cambiarla no reescribe lo ya escrito.

RF-OBR-02, RF-OBR-03 y RD-12. La razon de fondo esta en RF-ESC-06: cada escena
guarda **con que version de biblia se escribio**. Si cambiar la biblia editara
la vigente en sitio, las escenas anteriores quedarian apoyadas en hechos que ya
no existen, y sin rastro de por que.
"""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.commons.domain import NivelDeCalor, RelojFijo
from app.commons.llm import DobleDeModelo
from app.features.obra import (
    Brief,
    RepositorioDeObras,
    SalidaDeAgenteInvalida,
    crear_obra,
    generar_biblia,
)

BRIEF = Brief(
    titulo="Ceniza y neon",
    genero="romance",
    subgenero="romantasy",
    extension_objetivo=90_000,
    persona="tercera",
    tiempo_verbal="pasado",
    esquema_de_pov="dual",
    nivel_de_calor=NivelDeCalor.SENSUAL,
)

BIBLIA_VALIDA = {
    "tropo": "enemigos a amantes",
    "promesa_de_apertura": "una tregua que ninguno de los dos queria",
    "personajes": [
        {
            "pj_id": "pj-ada",
            "nombre": "Ada",
            "edad": 31,
            "rol_narrativo": "protagonista",
            "herida_original": "la abandonaron en mitad de un proyecto",
            "mentira_que_se_cree": "delegar es perder",
        }
    ],
    "lugares": [
        {"lug_id": "lug-taller", "nombre": "El taller", "sensorialidad_fija": ["ozono"]}
    ],
    "distancias": [
        {"origen_id": "lug-taller", "destino_id": "lug-taller", "tiempo_de_viaje": "0m"}
    ],
    "reglas_de_mundo": [{"regla_id": "rm-1", "enunciado": "La lluvia corta la red"}],
}


@pytest.fixture
def repositorio(base_de_datos: Path) -> RepositorioDeObras:
    return RepositorioDeObras(base_de_datos)


@pytest.fixture
def reloj() -> RelojFijo:
    return RelojFijo(datetime(2026, 9, 22, tzinfo=UTC))


def _obra(repositorio: RepositorioDeObras, reloj: RelojFijo) -> str:
    return crear_obra(BRIEF, repositorio, reloj).obra_id


def test_generar_la_biblia_crea_la_primera_version(
    repositorio: RepositorioDeObras, reloj: RelojFijo
) -> None:
    obra_id = _obra(repositorio, reloj)
    cliente = DobleDeModelo([json.dumps(BIBLIA_VALIDA)])

    version = generar_biblia(
        obra_id, cliente, "prompt del arquitecto", repositorio, reloj
    )

    assert version.numero == 1
    assert version.biblia.tropo == "enemigos a amantes"


def test_cambiar_la_biblia_crea_version_nueva_y_conserva_la_anterior(
    repositorio: RepositorioDeObras, reloj: RelojFijo
) -> None:
    """RF-OBR-03: no se edita en sitio."""
    obra_id = _obra(repositorio, reloj)
    segunda = {**BIBLIA_VALIDA, "tropo": "segunda oportunidad"}

    primera = generar_biblia(
        obra_id, DobleDeModelo([json.dumps(BIBLIA_VALIDA)]), "p", repositorio, reloj
    )
    nueva = generar_biblia(
        obra_id, DobleDeModelo([json.dumps(segunda)]), "p", repositorio, reloj
    )

    assert (primera.numero, nueva.numero) == (1, 2)
    assert repositorio.leer_version(primera.version_obra_id).biblia.tropo == (
        "enemigos a amantes"
    )


def test_una_escena_ya_escrita_sigue_apuntando_a_su_version(
    repositorio: RepositorioDeObras, reloj: RelojFijo, base_de_datos: Path
) -> None:
    """RF-ESC-06 y RF-OBR-03: cambiar la biblia **no reescribe** las escenas."""
    obra_id = _obra(repositorio, reloj)
    primera = generar_biblia(
        obra_id, DobleDeModelo([json.dumps(BIBLIA_VALIDA)]), "p", repositorio, reloj
    )

    conexion = sqlite3.connect(base_de_datos)
    conexion.execute(
        "INSERT INTO parte (parte_id, obra_id, numero, funcion_estructural)"
        " VALUES ('pa1', ?, 1, 'planteamiento')",
        (obra_id,),
    )
    conexion.execute(
        "INSERT INTO capitulo (capitulo_id, parte_id, numero) VALUES ('ca1','pa1',1)"
    )
    conexion.execute(
        "INSERT INTO escena (escena_id, capitulo_id, version_obra_id, orden_discurso,"
        " pov) VALUES ('es1','ca1',?,1,'pj-ada')",
        (primera.version_obra_id,),
    )
    conexion.commit()

    generar_biblia(
        obra_id,
        DobleDeModelo([json.dumps({**BIBLIA_VALIDA, "tropo": "otro"})]),
        "p",
        repositorio,
        reloj,
    )

    apunta_a = conexion.execute(
        "SELECT version_obra_id FROM escena WHERE escena_id = 'es1'"
    ).fetchone()[0]
    conexion.close()
    assert apunta_a == primera.version_obra_id


def test_una_salida_que_no_valida_es_fallo_del_paso(
    repositorio: RepositorioDeObras, reloj: RelojFijo
) -> None:
    """RF-ORQ-15: no es texto que se arrastre al paso siguiente."""
    obra_id = _obra(repositorio, reloj)
    cliente = DobleDeModelo(["esto no es json"])

    with pytest.raises(SalidaDeAgenteInvalida):
        generar_biblia(obra_id, cliente, "p", repositorio, reloj)

    assert repositorio.versiones_de(obra_id) == []


def test_una_biblia_sin_tiempo_de_viaje_se_rechaza(
    repositorio: RepositorioDeObras, reloj: RelojFijo
) -> None:
    """RF-OBR-02 exige `tiempo_de_viaje` en los lugares, y no es un adorno: es
    lo unico que hace detectable el teletransporte de RF-CAL-04."""
    obra_id = _obra(repositorio, reloj)
    sin_distancias = {**BIBLIA_VALIDA, "distancias": []}

    with pytest.raises(SalidaDeAgenteInvalida):
        generar_biblia(
            obra_id,
            DobleDeModelo([json.dumps(sin_distancias)]),
            "p",
            repositorio,
            reloj,
        )
