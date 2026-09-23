"""P-108a: de una escena a su obra (§4.8).

El protocolo `Almacenes` del Ensamblador recibe **solo** `escena_id`, y la capa
constitucional sale de la obra. Sin este camino de vuelta, el ensamblador no
puede saber de que obra es la escena que esta montando, y esa es la razon por la
que `features/contexto/repository.py` seguia vacio.

Vive en `outline` porque `parte` y `capitulo` son suyos: los escribe su
`guardar()`. Ponerlo en `escena` obligaria a que `escena` consultase tablas de
otra feature, que es la frontera que §5.2 regla 1 protege.
"""

import sqlite3
from pathlib import Path

import pytest

from app.features.outline import RepositorioDeOutline


@pytest.fixture
def jerarquia(base_de_datos: Path) -> Path:
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
        "INSERT INTO capitulo (capitulo_id, parte_id, numero, titulo, pov_dominante)"
        " VALUES ('ca1','pa1',3,'La tregua','pj-ada')"
    )
    conexion.execute(
        "INSERT INTO escena (escena_id, capitulo_id, orden_discurso, pov)"
        " VALUES ('es1','ca1',7,'pj-ada')"
    )
    conexion.commit()
    conexion.close()
    return base_de_datos


def test_la_ubicacion_de_una_escena_llega_hasta_la_obra(jerarquia: Path) -> None:
    ubicacion = RepositorioDeOutline(jerarquia).ubicacion_de("es1")

    assert ubicacion.obra_id == "o1"
    assert ubicacion.capitulo_id == "ca1"
    assert ubicacion.capitulo_numero == 3
    assert ubicacion.capitulo_titulo == "La tregua"
    assert ubicacion.funcion_estructural == "planteamiento"


def test_una_escena_que_no_existe_no_devuelve_una_ubicacion_a_medias(
    jerarquia: Path,
) -> None:
    """Devolver campos vacios haria que el paquete se montara con una capa
    constitucional en blanco, y RF-CTX-14 lo detectaria mucho mas tarde y en
    otro sitio. Falla aqui, donde se sabe la causa."""
    from app.commons.errors import RecursoNoEncontrado

    with pytest.raises(RecursoNoEncontrado):
        RepositorioDeOutline(jerarquia).ubicacion_de("no-existe")
