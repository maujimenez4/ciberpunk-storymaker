"""La rubrica versionada y sus anclajes (RF-JUZ-01, RF-JUZ-02, mitad de `CA-20`).

El test que abre esta tarea es `test_ningun_criterio_se_queda_sin_anclajes`, y no
es ceremonia: `definitions.md` §8 dice que **una rubrica sin anclajes descritos no
es una rubrica, es una escala**, y aqui esa frase es ejecutable. Se escribe como
test y no como inspeccion porque una inspeccion no vuelve a correr.

Importa mas de lo que parece desde que P-02 se reviso: **el juez corre en el mismo
Haiku 4.5 que escribio el capitulo**. Un juez que comparte modelo y entrenamiento
con el autor tiende a aprobarse, asi que la distancia de `RF-JUZ-05` saldra mejor
de lo que el sistema merece. La rubrica no puede arreglar eso; lo que si puede es
**no empeorarlo**, y por eso los anclajes describen lo que se ve en el texto y no
adjetivos que un modelo se concede solo.
"""

from dataclasses import FrozenInstanceError, replace

import pytest

from app.features.calidad.rubrica import (
    HASH_DE_RUBRICA_V1,
    RUBRICA_V1,
    Criterio,
    hash_de_rubrica,
    rubrica_vigente,
)

# Los que el encargo §5b enumera, con esos nombres. No es una lista libre.
CRITERIOS_DEL_ENCARGO = (
    "continuidad",
    "tono",
    "arco",
    "coherencia_de_personajes",
    "ritmo",
    "naturalidad_de_la_personalizacion",
)


# --- El test que abre la tarea ----------------------------------------------


def test_ningun_criterio_se_queda_sin_anclajes() -> None:
    for criterio in RUBRICA_V1.criterios:
        assert criterio.ancla_minimo.strip(), criterio.nombre
        assert criterio.ancla_maximo.strip(), criterio.nombre


def test_los_criterios_son_los_seis_del_encargo() -> None:
    """Ni uno mas ni uno menos: el juez que puntua un criterio que la rubrica no
    tiene, o que se deja uno, produce una salida que no es comparable con la
    revision humana (R-5 del plan). Eso solo se puede rechazar si la lista es
    cerrada."""
    assert tuple(c.nombre for c in RUBRICA_V1.criterios) == CRITERIOS_DEL_ENCARGO


def test_cada_criterio_tiene_definicion() -> None:
    """El nombre no define nada. Dos jueces que no comparten que mide `ritmo` no
    estan midiendo lo mismo, y `ritmo` es justo el que se presta: aqui es **entre
    capitulos**, no dentro de uno."""
    for criterio in RUBRICA_V1.criterios:
        assert criterio.definicion.strip(), criterio.nombre


def test_los_dos_anclajes_de_un_criterio_no_dicen_lo_mismo() -> None:
    """Un ancla que se limita a negar la otra —«bien» / «mal»— no ancla: deja el
    3 sin describir, que es donde caen casi todos los capitulos."""
    for criterio in RUBRICA_V1.criterios:
        assert criterio.ancla_minimo != criterio.ancla_maximo, criterio.nombre


# --- La escala --------------------------------------------------------------


def test_la_escala_declara_sus_dos_extremos() -> None:
    minimo, maximo = RUBRICA_V1.escala
    assert minimo < maximo
    assert (minimo, maximo) == (1, 5)


# --- El versionado, que es lo que hace comparables dos corridas --------------


def test_el_hash_corresponde_al_contenido() -> None:
    assert HASH_DE_RUBRICA_V1 == hash_de_rubrica(RUBRICA_V1)


def test_cambiar_un_ancla_cambia_el_hash() -> None:
    """`definitions.md` §8: cambiar un criterio invalida la comparacion con
    puntuaciones anteriores. Si el hash no se moviera, eso pasaria en silencio y
    el *tuning* de T11 compararia numeros de dos rubricas distintas creyendo que
    son de la misma."""
    criterios = list(RUBRICA_V1.criterios)
    criterios[0] = replace(criterios[0], ancla_maximo="otra cosa")
    retocada = replace(RUBRICA_V1, criterios=tuple(criterios))

    assert hash_de_rubrica(retocada) != HASH_DE_RUBRICA_V1


def test_cambiar_la_version_cambia_el_hash() -> None:
    assert hash_de_rubrica(replace(RUBRICA_V1, version="v2")) != HASH_DE_RUBRICA_V1


# --- Una rubrica, no dos ----------------------------------------------------


def test_la_rubrica_vigente_es_la_misma_instancia() -> None:
    """`CA-20`: la que usa el juez y la que se le presenta al Autor son **la
    misma**. Si fueran dos objetos iguales pero distintos, bastaria con que una
    se editara para que la comparacion dejara de significar nada."""
    assert rubrica_vigente() is RUBRICA_V1


def test_la_rubrica_no_se_puede_mutar() -> None:
    with pytest.raises(FrozenInstanceError):
        RUBRICA_V1.version = "v2"  # type: ignore[misc]


def test_un_criterio_no_se_puede_mutar() -> None:
    with pytest.raises(FrozenInstanceError):
        RUBRICA_V1.criterios[0].ancla_minimo = "otra cosa"  # type: ignore[misc]


# --- Lo que la rubrica NO es ------------------------------------------------


def test_la_rubrica_no_sabe_puntuar() -> None:
    """El Critico puntua y **no repara** (`CLAUDE.md` §9.1); la rubrica ni
    siquiera puntua. Es un modulo sin base de datos y sin modelo: si aqui
    apareciera un metodo que decide, el instrumento de medida y el que mide
    serian el mismo objeto."""
    publicos = [n for n in dir(RUBRICA_V1) if not n.startswith("_")]

    assert sorted(publicos) == ["criterios", "escala", "version"]


def test_un_criterio_solo_describe() -> None:
    publicos = [n for n in dir(Criterio) if not n.startswith("_")]

    assert sorted(publicos) == ["ancla_maximo", "ancla_minimo", "definicion", "nombre"]
