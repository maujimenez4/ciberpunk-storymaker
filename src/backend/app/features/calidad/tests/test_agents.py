"""P-124: el Continuista, la frontera con el modelo de la feature `calidad`.

RF-ORQ-15 y `CLAUDE.md` §9.3. Era el unico de los seis agentes de la v1 con su
prompt escrito y sin `agents.py`: los cuatro validadores de continuidad reciben
`Afirmacion` y **nadie las producia**.
"""

import json

import pytest

from app.commons.llm import DobleDeModelo
from app.features.calidad import (
    AfirmacionesInvalidas,
    invocar_continuista,
)

AFIRMACIONES = json.dumps(
    [
        {
            "cita": "Noe la esperaba junto a la mesa",
            "sujeto": "pj-noe",
            "lugar": "lug-taller",
            "momento": 1,
        },
        {
            "cita": "—No voy a firmar eso",
            "sujeto": "pj-noe",
            "atributo": "postura",
            "valor": "se niega a firmar",
            "momento": 2,
        },
    ]
)


def test_el_continuista_devuelve_afirmaciones_con_su_cita() -> None:
    cliente = DobleDeModelo([AFIRMACIONES])

    lectura = invocar_continuista(cliente, "prompt del continuista")

    afirmaciones = lectura.afirmaciones
    assert [a.cita for a in afirmaciones] == [
        "Noe la esperaba junto a la mesa",
        "—No voy a firmar eso",
    ]
    assert afirmaciones[0].lugar == "lug-taller"
    assert afirmaciones[1].valor == "se niega a firmar"
    # Lo que no aplica queda en cadena vacia, como pide el prompt: asi los
    # validadores lo descartan por `if a.sujeto and a.objeto` sin ramas nulas.
    assert afirmaciones[0].atributo == ""
    # La traza de la llamada viaja con las afirmaciones: `ejecucion` la pide
    # (RI-14) y el ciclo no tiene otra forma de saberla.
    assert lectura.modelo == "doble"


def test_el_continuista_ve_la_prosa_y_nada_mas() -> None:
    """§9.1: como el Escritor, recibe un texto. No toca la base de datos."""
    cliente = DobleDeModelo([AFIRMACIONES])

    invocar_continuista(cliente, "la prosa de la escena")

    assert cliente.llamadas == ["la prosa de la escena"]


def test_una_salida_que_no_valida_es_fallo_del_paso() -> None:
    """RF-ORQ-15: lo que no valida no se arrastra al siguiente paso.

    Sin esto, una salida rota se convierte en cero afirmaciones, que es
    indistinguible de una escena limpia: la averia se veria como un verde.
    """
    cliente = DobleDeModelo(["Aqui no hay ningun JSON, solo prosa."])

    with pytest.raises(AfirmacionesInvalidas):
        invocar_continuista(cliente, "prompt")
