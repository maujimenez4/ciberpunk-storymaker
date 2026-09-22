"""P-18: la obra fija los parametros de discurso y sus escenas los heredan.

RF-OBR-01. Los cuatro -persona, tiempo verbal, esquema de POV y nivel de calor-
se declaran **una vez** a nivel de obra y se imponen en cada escena como
restriccion dura (`definitions.md` §5). Heredarlos no es comodidad: es lo que
permite que RF-CAL-12 compruebe despues si la prosa los cumplio.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.commons.domain import NivelDeCalor, RelojFijo
from app.features.obra import Brief, RepositorioDeObras, crear_obra

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


@pytest.fixture
def repositorio(base_de_datos: Path) -> RepositorioDeObras:
    return RepositorioDeObras(base_de_datos)


def test_crear_obra_fija_los_cuatro_parametros_de_discurso(
    repositorio: RepositorioDeObras,
) -> None:
    obra = crear_obra(BRIEF, repositorio, RelojFijo(datetime(2026, 9, 22, tzinfo=UTC)))

    guardada = repositorio.leer(obra.obra_id)
    assert guardada.persona == "tercera"
    assert guardada.tiempo_verbal == "pasado"
    assert guardada.esquema_de_pov == "dual"
    assert guardada.nivel_de_calor is NivelDeCalor.SENSUAL


def test_las_escenas_heredan_los_parametros_de_la_obra(
    repositorio: RepositorioDeObras,
) -> None:
    """Sin herencia, cada escena podria declarar su propio nivel de calor y la
    promesa al lector dejaria de ser una promesa (`domain-knowledge.md` §8.5)."""
    obra = crear_obra(BRIEF, repositorio, RelojFijo(datetime(2026, 9, 22, tzinfo=UTC)))

    heredados = obra.parametros_para_una_escena()

    assert heredados.nivel_de_calor is NivelDeCalor.SENSUAL
    assert heredados.persona == "tercera"


def test_la_obra_cuelga_de_una_serie_desde_el_principio(
    repositorio: RepositorioDeObras,
) -> None:
    """RD-11: aunque la v1 maneje una sola obra y una serie implicita."""
    obra = crear_obra(BRIEF, repositorio, RelojFijo(datetime(2026, 9, 22, tzinfo=UTC)))

    assert repositorio.leer(obra.obra_id).serie_id


def test_el_brief_exige_los_cuatro_parametros() -> None:
    """Un brief sin ellos dejaria la obra sin restricciones duras que imponer."""
    with pytest.raises(ValidationError):
        Brief(  # type: ignore[call-arg]
            titulo="Sin parametros",
            genero="romance",
            subgenero="contemporaneo",
            extension_objetivo=90_000,
        )
