"""P-108b: la ficha persistida se lee entera (§4.8, capa de instruccion).

`planificar_escena` produce una `FichaDeEscena` y la fila de `escena` guarda sus
campos, pero **no habia forma de leerlos de vuelta**: `EscenaPersistida` solo
expone seis. La capa de instruccion del paquete es precisamente esa ficha, asi
que sin esta lectura el Ensamblador no tiene de donde sacarla, y por eso
`corrida.py` la fabricaba a mano.
"""

import json
import sqlite3
from pathlib import Path

import pytest

from app.features.escena import RepositorioDeEscenas


@pytest.fixture
def escena_con_ficha(base_de_datos: Path) -> Path:
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
        "INSERT INTO capitulo (capitulo_id, parte_id, numero, titulo)"
        " VALUES ('ca1','pa1',1,'La tregua')"
    )
    conexion.execute(
        "INSERT INTO escena (escena_id, capitulo_id, orden_discurso, tiempo_historia,"
        " pov, lugar, presentes, mencionados, objetivo_del_pov, obstaculo,"
        " valor_entrada, valor_salida, extension_objetivo, distancia_psiquica,"
        " beat_de_genero) VALUES ('es1','ca1',1,'dia-1','pj-ada','el taller',?,?,"
        "'recuperar el contrato','la puerta esta sellada','esperanza','miedo',"
        "1800,'cercana','encuentro')",
        (json.dumps(["pj-ada", "pj-noe"]), json.dumps(["pj-vera"])),
    )
    conexion.commit()
    conexion.close()
    return base_de_datos


def test_la_ficha_persistida_se_lee_entera(escena_con_ficha: Path) -> None:
    ficha = RepositorioDeEscenas(escena_con_ficha).ficha_de("es1")

    assert ficha.lugar == "el taller"
    assert ficha.presentes == ["pj-ada", "pj-noe"]
    assert ficha.mencionados == ["pj-vera"]
    assert ficha.objetivo_del_pov == "recuperar el contrato"
    assert ficha.obstaculo == "la puerta esta sellada"
    assert ficha.valor_entrada == "esperanza"
    assert ficha.valor_salida == "miedo"
    assert ficha.beat_de_genero == "encuentro"
    assert ficha.pov == "pj-ada"


def test_presentes_y_mencionados_vacios_son_listas_y_no_none(
    base_de_datos: Path, escena_con_ficha: Path
) -> None:
    """Un `None` aqui se propaga a la capa de canon, donde se itera para separar
    presentes de mencionados. Mejor una lista vacia que un `if` en cada uso."""
    conexion = sqlite3.connect(escena_con_ficha)
    conexion.execute(
        "INSERT INTO escena (escena_id, capitulo_id, orden_discurso, pov)"
        " VALUES ('es2','ca1',2,'pj-noe')"
    )
    conexion.commit()
    conexion.close()

    ficha = RepositorioDeEscenas(escena_con_ficha).ficha_de("es2")

    assert ficha.presentes == []
    assert ficha.mencionados == []


def test_la_ficha_del_planificador_se_guarda_y_se_vuelve_a_leer(
    escena_con_ficha: Path,
) -> None:
    """P-111b, RF-ESC-01.

    `planificar_escena` producia la ficha y **nadie la escribia**: `corrida.py`
    la usaba en memoria y la tiraba. La fila de `escena` conservaba solo lo que
    el outline habia puesto, sin presentes, sin distancia psiquica y sin
    extension objetivo.

    Se nota al montar el paquete: la capa de instruccion sale de la ficha en
    disco, asi que sin esta escritura el Escritor recibe la ficha del outline
    -la propuesta gruesa- en vez de la del Planificador.
    """
    from app.commons.domain import NivelDeCalor
    from app.features.escena import FichaDeEscena

    repositorio = RepositorioDeEscenas(escena_con_ficha)
    ficha = FichaDeEscena(
        escena_id="es1",
        pov="pj-noe",
        presentes=["pj-noe", "pj-vera"],
        lugar="el muelle",
        objetivo_del_pov="entregar el paquete",
        obstaculo="la inspectora lo espera",
        valor_entrada="confianza",
        valor_salida="sospecha",
        distancia_psiquica="cercana",
        densidad_de_dialogo_objetivo=0.4,
        extension_objetivo=1600,
        persona="tercera",
        tiempo_verbal="pasado",
        nivel_de_calor=NivelDeCalor.SENSUAL,
    )

    repositorio.guardar_ficha(ficha)
    leida = repositorio.ficha_de("es1")

    assert leida.pov == "pj-noe"
    assert leida.lugar == "el muelle"
    assert leida.presentes == ["pj-noe", "pj-vera"]
    assert leida.objetivo_del_pov == "entregar el paquete"
    assert leida.distancia_psiquica == "cercana"
    assert leida.extension_objetivo == 1600
    assert leida.densidad_de_dialogo_objetivo == 0.4
    # Lo que el Planificador no propone no se pisa (RF-ESC-02).
    assert leida.mencionados == ["pj-vera"]
