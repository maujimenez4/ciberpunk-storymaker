"""P-22, P-23 y P-24: el outline jerarquico y las dos reglas de genero.

RF-OUT-01 (Parte -> Capitulo -> Escena), RF-OUT-02 con RG-06 (cada beat
obligatorio en **exactamente una** escena) y RF-OUT-05 (orden de los hitos).

Las dos reglas de genero se comprueban **al generar el outline**, no al escribir.
Es la unica fase en la que arreglarlas es barato: mover una escena en el outline
cuesta una linea, y en el manuscrito cuesta reescribir un capitulo
(`domain-knowledge.md` §8.1).
"""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.commons.domain import RelojFijo
from app.commons.llm import DobleDeModelo
from app.features.outline import (
    BEATS_OBLIGATORIOS,
    OutlineInvalido,
    RepositorioDeOutline,
    generar_outline,
)


def _escena(orden: int, beat: str | None) -> dict[str, object]:
    return {
        "orden_discurso": orden,
        "pov": "pj-ada",
        "lugar": "lug-taller",
        "objetivo_del_pov": "cerrar el trato",
        "obstaculo": "el otro no firma",
        "valor_entrada": "control",
        "valor_salida": "amenaza",
        "beat_de_genero": beat,
    }


# Los diez hitos, uno por escena y en orden. `orden_discurso` tiene que crecer:
# con todas las escenas en la posicion 1 el contrato de orden no se puede
# comprobar, y el primer intento de este fichero fallo justo por eso.
OUTLINE_VALIDO: dict[str, object] = {
    "partes": [
        {
            "numero": 1,
            "funcion_estructural": "planteamiento",
            "capitulos": [
                {
                    "numero": 1,
                    "titulo": "La tregua",
                    "pov_dominante": "pj-ada",
                    "escenas": [
                        _escena(i + 1, beat)
                        for i, beat in enumerate(BEATS_OBLIGATORIOS)
                    ],
                }
            ],
        }
    ]
}


def _con_escenas(escenas: list[dict[str, object]]) -> dict[str, object]:
    copia: dict[str, object] = json.loads(json.dumps(OUTLINE_VALIDO))
    partes = copia["partes"]
    assert isinstance(partes, list)
    partes[0]["capitulos"][0]["escenas"] = escenas
    return copia


@pytest.fixture
def repositorio(base_de_datos: Path) -> RepositorioDeOutline:
    return RepositorioDeOutline(base_de_datos)


@pytest.fixture
def reloj() -> RelojFijo:
    return RelojFijo(datetime(2026, 9, 22, tzinfo=UTC))


@pytest.fixture
def obra_id(base_de_datos: Path) -> str:
    """Una obra de verdad: la clave ajena de `parte` la exige, y con un
    identificador inventado los tests de rechazo pasarian por el motivo
    equivocado -no porque no se guarde nada, sino porque no habia donde-."""
    conexion = sqlite3.connect(base_de_datos)
    conexion.execute("INSERT INTO serie (serie_id, titulo) VALUES ('s1','S')")
    conexion.execute(
        "INSERT INTO obra (obra_id, serie_id, titulo, genero, subgenero,"
        " extension_objetivo, persona, tiempo_verbal, esquema_de_pov, nivel_de_calor)"
        " VALUES ('obra-1','s1','O','romance','contemporaneo',90000,'tercera',"
        "'pasado','dual','sensual')"
    )
    conexion.commit()
    conexion.close()
    return "obra-1"


def test_el_outline_produce_la_jerarquia_completa(
    repositorio: RepositorioDeOutline, reloj: RelojFijo, obra_id: str
) -> None:
    """RF-OUT-01."""
    cliente = DobleDeModelo([json.dumps(OUTLINE_VALIDO)])

    outline = generar_outline(obra_id, cliente, "prompt", repositorio, reloj)

    assert len(outline.partes) == 1
    assert len(outline.partes[0].capitulos) == 1
    assert outline.partes[0].capitulos[0].escenas


def test_cada_escena_nace_con_pov_lugar_objetivo_obstaculo_y_giro(
    repositorio: RepositorioDeOutline, reloj: RelojFijo, obra_id: str
) -> None:
    """RF-OUT-03: una escena sin giro es relleno y no deberia llegar a escribirse."""
    outline = generar_outline(
        obra_id, DobleDeModelo([json.dumps(OUTLINE_VALIDO)]), "p", repositorio, reloj
    )
    escena = outline.partes[0].capitulos[0].escenas[0]

    assert escena.pov and escena.lugar and escena.objetivo_del_pov and escena.obstaculo
    assert escena.valor_entrada != escena.valor_salida


def test_un_beat_obligatorio_sin_escena_se_rechaza(
    repositorio: RepositorioDeOutline, reloj: RelojFijo, obra_id: str
) -> None:
    """RF-OUT-02 y RG-06."""
    faltan = _con_escenas(
        [_escena(i + 1, beat) for i, beat in enumerate(BEATS_OBLIGATORIOS[:-1])]
    )

    with pytest.raises(OutlineInvalido) as error:
        generar_outline(
            obra_id, DobleDeModelo([json.dumps(faltan)]), "p", repositorio, reloj
        )

    assert BEATS_OBLIGATORIOS[-1] in str(error.value)


def test_un_beat_obligatorio_repetido_se_rechaza(
    repositorio: RepositorioDeOutline, reloj: RelojFijo, obra_id: str
) -> None:
    """RG-06 dice **exactamente una**. Dos escenas con el mismo hito es un
    outline que promete dos veces lo mismo y cumple a medias las dos."""
    repetido = _con_escenas(
        [_escena(i + 1, beat) for i, beat in enumerate(BEATS_OBLIGATORIOS)]
        + [_escena(len(BEATS_OBLIGATORIOS) + 1, BEATS_OBLIGATORIOS[0])]
    )

    with pytest.raises(OutlineInvalido) as error:
        generar_outline(
            obra_id, DobleDeModelo([json.dumps(repetido)]), "p", repositorio, reloj
        )

    assert "mas de una" in str(error.value) or "repetid" in str(error.value)


def test_un_hito_fuera_de_orden_se_rechaza(
    repositorio: RepositorioDeOutline, reloj: RelojFijo, obra_id: str
) -> None:
    """RF-OUT-05: ninguno se asigna antes que el hito que lo precede.

    El orden del contrato de genero no es decorativo: la ruptura antes del
    reconocimiento deja al lector sin entender que se rompe.
    """
    invertido = list(BEATS_OBLIGATORIOS)
    invertido[0], invertido[-1] = invertido[-1], invertido[0]
    fuera = _con_escenas([_escena(i + 1, beat) for i, beat in enumerate(invertido)])

    with pytest.raises(OutlineInvalido) as error:
        generar_outline(
            obra_id, DobleDeModelo([json.dumps(fuera)]), "p", repositorio, reloj
        )

    assert "orden" in str(error.value).lower()


def test_un_outline_rechazado_no_deja_nada_escrito(
    repositorio: RepositorioDeOutline, reloj: RelojFijo, obra_id: str
) -> None:
    """Mismo motivo que en la biblia: medio outline guardado parece un outline
    pobre en vez de un fallo."""
    faltan = _con_escenas([_escena(1, BEATS_OBLIGATORIOS[0])])

    with pytest.raises(OutlineInvalido):
        generar_outline(
            obra_id, DobleDeModelo([json.dumps(faltan)]), "p", repositorio, reloj
        )

    assert repositorio.partes_de(obra_id) == []
