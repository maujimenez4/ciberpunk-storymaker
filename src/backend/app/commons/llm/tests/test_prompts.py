"""P-21: los prompts son ficheros versionados y su hash se comprueba.

RI-14, `architecture.md` §5.5 y `CLAUDE.md` §10. `Prompt` no es tabla: es un
fichero del que `ejecucion` guarda id, version y hash, y con eso se reconstruye
el paquete de una ejecucion antigua (RF-CTX-13).
"""

from pathlib import Path

import pytest

from app.commons.errors import RecursoNoEncontrado
from app.commons.llm import CargadorDePrompts

RAIZ_REAL = Path(__file__).resolve().parents[4] / "features"


@pytest.fixture
def carpeta(tmp_path: Path) -> Path:
    (tmp_path / "escritor.v1.md").write_text("primera version", encoding="utf-8")
    (tmp_path / "escritor.v3.md").write_text("tercera version", encoding="utf-8")
    (tmp_path / "arquitecto.v1.md").write_text("biblia y outline", encoding="utf-8")
    return tmp_path


def test_carga_la_version_mas_alta_por_defecto(carpeta: Path) -> None:
    cargado = CargadorDePrompts(carpeta).cargar("escritor")

    assert cargado.version == "v3"
    assert cargado.texto == "tercera version"


def test_puede_cargar_una_version_concreta(carpeta: Path) -> None:
    """Reproducir una ejecucion antigua exige la version que se uso, no la
    vigente de hoy (RF-CTX-13)."""
    cargado = CargadorDePrompts(carpeta).cargar("escritor", "v1")

    assert cargado.texto == "primera version"


def test_el_hash_identifica_el_contenido(carpeta: Path) -> None:
    cargador = CargadorDePrompts(carpeta)

    assert cargador.cargar("escritor", "v1").hash != cargador.cargar("escritor").hash
    assert cargador.cargar("escritor").hash == cargador.cargar("escritor").hash


def test_un_prompt_editado_en_sitio_se_detecta(carpeta: Path) -> None:
    """`CLAUDE.md` §10 lo prohibe; esto lo hace comprobable.

    Sin esto la prohibicion es una costumbre: el fichero cambia, `ejecucion`
    sigue guardando el hash viejo y RF-CTX-13 reconstruiria un paquete que nunca
    se envio, sin que nada avisara.
    """
    cargador = CargadorDePrompts(carpeta)
    antes = cargador.cargar("escritor")

    (carpeta / "escritor.v3.md").write_text("editado en sitio", encoding="utf-8")

    assert cargador.coincide_el_hash(antes) is False


def test_un_prompt_que_no_existe_no_se_inventa(carpeta: Path) -> None:
    with pytest.raises(RecursoNoEncontrado):
        CargadorDePrompts(carpeta).cargar("continuista")


def test_los_prompts_del_repositorio_tienen_nombre_versionado() -> None:
    """`CLAUDE.md` §10: uno por rol, versionados como `escritor.v3.md`.

    Un fichero suelto sin version en el nombre es el primer paso hacia editarlo
    en sitio, porque no hay nada que incrementar.
    """
    import re

    patron = re.compile(r"^[a-z_]+\.v\d+\.md$")
    sueltos = [
        p.relative_to(RAIZ_REAL)
        for p in RAIZ_REAL.rglob("prompts/*.md")
        if p.name != "README.md" and not patron.match(p.name)
    ]
    assert not sueltos, f"prompts sin version en el nombre: {sueltos}"
