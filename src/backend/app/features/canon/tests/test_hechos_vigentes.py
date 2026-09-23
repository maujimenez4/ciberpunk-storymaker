"""P-108c: los hechos de canon vigentes antes de una escena (§4.8).

La capa de canon del paquete necesita **lo que se sabe hasta aqui**, y hasta hoy
solo habia `hechos_de_escena`, que devuelve los que una escena establecio. Sin
esta lectura el Ensamblador no tenia de donde sacar la capa, y esa es la razon
por la que el canon aportaba 36 tokens de media al paquete: no se leia.

Dos reglas, y la segunda es la que muerde:

- **Estrictamente anteriores**, igual que `eventos_hasta`. El canon de una
  escena es el de justo antes de escribirla, no el de despues.
- **Solo los vigentes** (RF-CAN-07). Corregir no edita: registra un hecho nuevo
  que cita al viejo. Devolver el sustituido metería en el paquete la afirmacion
  que el canon ya desmintio, y el Escritor la trataria como verdad.
"""

import sqlite3
from pathlib import Path

import pytest

from app.features.canon import RepositorioDeCanon


@pytest.fixture
def repositorio(base_de_datos: Path) -> RepositorioDeCanon:
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
        " VALUES ('ca1','pa1',1,'C')"
    )
    for i in (1, 2, 3):
        conexion.execute(
            "INSERT INTO escena (escena_id, capitulo_id, orden_discurso, pov)"
            " VALUES (?,?,?,'pj-ada')",
            (f"es{i}", "ca1", i),
        )
    conexion.commit()
    conexion.close()
    return RepositorioDeCanon(base_de_datos)


def test_los_hechos_hasta_una_escena_excluyen_los_posteriores(
    repositorio: RepositorioDeCanon,
) -> None:
    repositorio.registrar_hecho("s1", "es1", "pj-ada", "oficio", "relojera")
    repositorio.registrar_hecho("s1", "es3", "pj-noe", "oficio", "contrabandista")

    hasta_la_tercera = repositorio.hechos_hasta(3)

    assert [h.entidad for h in hasta_la_tercera] == ["pj-ada"]


def test_un_hecho_sustituido_no_entra_en_el_paquete(
    repositorio: RepositorioDeCanon,
) -> None:
    """RF-CAN-07: el corregido sigue en el grafo, pero no es lo que se sabe."""
    viejo = repositorio.registrar_hecho("s1", "es1", "pj-ada", "oficio", "relojera")
    repositorio.sustituir_hecho("s1", "es2", viejo.hc_id, "pj-ada", "oficio", "forense")

    vigentes = repositorio.hechos_hasta(3)

    assert [(h.entidad, h.valor) for h in vigentes] == [("pj-ada", "forense")]


def test_sin_hechos_anteriores_la_lista_es_vacia_y_no_falla(
    repositorio: RepositorioDeCanon,
) -> None:
    """La primera escena de una obra no tiene canon detras. Que la capa quede
    vacia es problema de RF-CTX-14, no de esta lectura."""
    assert repositorio.hechos_hasta(1) == []
