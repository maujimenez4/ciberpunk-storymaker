"""P-12: la traza dejaba de decir la verdad sobre una caida.

`reanudacion.py` cerraba el trabajo muerto con `TIEMPO_AGOTADO` **por descarte**:
era la unica senal de averia que daba flecha desde cualquier estado vivo. Mientras
nadie mirara, daba igual. Con Langfuse deja de dar igual: **esa traza es lo que
alguien va a abrir**, y una novela que se cayo aparece como una que agoto su
plazo. Son dos averias distintas y se arreglan de forma distinta —una es el
proveedor tardando, la otra el proceso muriendo—, asi que confundirlas manda a
quien la lea a buscar donde no es.

`CANCELACION` no servia y por eso se eligio mal: no tiene flecha desde
`REPARANDO` ni desde `EXTRAYENDO`, y una caida puede ocurrir en cualquiera de los
diez estados.
"""

import pytest

from app.features.escritura.maquina import (
    ESTADOS_TERMINALES,
    Estado,
    Senal,
    transitar,
)

VIVOS = tuple(estado for estado in Estado if estado not in ESTADOS_TERMINALES)


def test_existe_una_senal_para_el_proceso_que_murio() -> None:
    """Sin ella, `reanudacion.py` tiene que mentir o callar."""
    assert Senal.PROCESO_INTERRUMPIDO.value == "proceso_interrumpido"


@pytest.mark.parametrize("estado", VIVOS)
def test_la_caida_tiene_flecha_desde_cualquier_estado_vivo(estado: Estado) -> None:
    """Es lo que `CANCELACION` no tenia, y por lo que se acabo usando
    `TIEMPO_AGOTADO`: una caida no elige en que estado te pilla."""
    assert transitar(estado, Senal.PROCESO_INTERRUMPIDO, intento=0) is Estado.FALLIDA


def test_la_caida_no_se_confunde_con_el_plazo_agotado() -> None:
    """Las dos llevan a `FALLIDA`, y aun asi no son la misma: lo que las separa
    es lo que la traza le dice a quien la abre."""
    assert Senal.PROCESO_INTERRUMPIDO is not Senal.TIEMPO_AGOTADO


def test_el_alfabeto_sigue_cerrado() -> None:
    """RF-ORQ-01. Una senal nueva no puede abrir la puerta a senales libres: lo
    que no este en el alfabeto sigue siendo `SenalDesconocida`."""
    from app.features.escritura.maquina import SenalDesconocida

    with pytest.raises(SenalDesconocida):
        transitar(Estado.ESCRIBIENDO, "se_cayo_el_ordenador", intento=0)
