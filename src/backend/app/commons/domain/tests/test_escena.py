"""P-14 y P-15: las dos reglas de dominio que se validan por esquema.

RG-08 (un POV y un giro de valor no nulo) y RG-09 (ningun contenido romantico o
sexual con menores de 18). La segunda es la razon por la que este modulo existe
sin framework: una regla de seguridad que solo viviera en el prompt no seria una
regla, seria una peticion (`CLAUDE.md` §10, RNF-SEG-02).
"""

import pytest
from pydantic import ValidationError

from app.commons.domain import (
    EscenaPlanificada,
    NivelDeCalor,
    PersonajeEnEscena,
    RolNarrativo,
)


def _personaje(edad: int = 30) -> PersonajeEnEscena:
    return PersonajeEnEscena(
        pj_id="pj1",
        nombre="Alguien",
        edad=edad,
        rol_narrativo=RolNarrativo.PROTAGONISTA,
    )


def test_una_escena_exige_un_pov() -> None:
    with pytest.raises(ValidationError):
        EscenaPlanificada(
            escena_id="e1",
            pov="",
            valor_entrada="esperanza",
            valor_salida="miedo",
            presentes=[_personaje()],
        )


def test_el_giro_de_valor_no_puede_ser_nulo() -> None:
    """RG-08: valor_entrada = valor_salida es una escena sin giro, o sea relleno."""
    with pytest.raises(ValidationError) as error:
        EscenaPlanificada(
            escena_id="e1",
            pov="pj1",
            valor_entrada="esperanza",
            valor_salida="esperanza",
            presentes=[_personaje()],
        )
    assert "giro" in str(error.value).lower()


def test_una_escena_con_giro_es_valida() -> None:
    escena = EscenaPlanificada(
        escena_id="e1",
        pov="pj1",
        valor_entrada="esperanza",
        valor_salida="miedo",
        presentes=[_personaje()],
    )
    assert escena.tiene_giro_de_valor()


@pytest.mark.parametrize("edad", [0, 12, 17])
def test_el_esquema_rechaza_calor_con_un_menor(edad: int) -> None:
    """RG-09, RNF-SEG-01: bloquea por construccion, sin excepcion narrativa.

    Se comprueba con varias edades por debajo del umbral porque el fallo tipico
    no es aceptar a un nino: es un off-by-one en los 17.
    """
    with pytest.raises(ValidationError) as error:
        EscenaPlanificada(
            escena_id="e1",
            pov="pj1",
            valor_entrada="a",
            valor_salida="b",
            presentes=[_personaje(edad)],
            nivel_de_calor=NivelDeCalor.SENSUAL,
        )
    assert "18" in str(error.value)


def test_puerta_cerrada_con_un_menor_si_es_valida() -> None:
    """La regla es sobre contenido romantico o sexual, no sobre aparecer."""
    escena = EscenaPlanificada(
        escena_id="e1",
        pov="pj1",
        valor_entrada="a",
        valor_salida="b",
        presentes=[_personaje(12)],
        nivel_de_calor=NivelDeCalor.PUERTA_CERRADA,
    )
    assert escena.nivel_de_calor is NivelDeCalor.PUERTA_CERRADA


def test_el_dominio_no_importa_framework() -> None:
    """§5.2 regla 3: commons/domain se prueba sin base de datos."""
    import sys

    from app.commons import domain

    modulos = {m for m in sys.modules if m.startswith(("fastapi", "sqlalchemy"))}
    assert domain.__name__ == "app.commons.domain"
    for fichero in ("reloj", "escena"):
        fuente = (
            __import__("pathlib").Path(domain.__file__).parent / f"{fichero}.py"
        ).read_text(encoding="utf-8")
        for prohibido in (
            "import fastapi",
            "from fastapi",
            "import sqlalchemy",
            "from sqlalchemy",
        ):
            assert prohibido not in fuente, f"{fichero}.py importa {prohibido}"
    assert modulos is not None
