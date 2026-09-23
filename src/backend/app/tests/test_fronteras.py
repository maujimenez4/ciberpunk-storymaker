"""P-16 y P-17: la estructura y sus fronteras (architecture.md §5.1 y §5.2).

Las reglas de frontera las verifica `import-linter` en la build (CA-9). Lo que
se comprueba aqui es lo que `import-linter` **no** puede ver: que las ocho
features existan con los segmentos que §5.1 declara, y que la superficie
importable de cada una sea su `__init__.py` y nada mas.

Sin esto, la primera feature que se escriba inventara su propia disposicion y
las siguientes la copiaran.
"""

from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
FEATURES = (
    "obra",
    "outline",
    "escena",
    "contexto",
    "escritura",
    "calidad",
    "canon",
    "manuscrito",
)
SEGMENTOS = ("router.py", "schemas.py", "service.py", "repository.py", "__init__.py")


@pytest.mark.parametrize("feature", FEATURES)
def test_la_feature_existe_con_sus_segmentos(feature: str) -> None:
    carpeta = RAIZ / "features" / feature
    assert carpeta.is_dir(), f"falta la feature {feature}"
    for segmento in SEGMENTOS:
        assert (carpeta / segmento).is_file(), f"{feature}: falta {segmento}"
    assert (carpeta / "tests").is_dir()
    assert (carpeta / "prompts").is_dir()


def test_auditoria_no_existe_todavia() -> None:
    """Esta fuera de alcance en la v1. Crearla invitaria a llenarla."""
    assert not (RAIZ / "features" / "auditoria").exists()


@pytest.mark.parametrize("feature", FEATURES)
def test_ninguna_feature_importa_de_otra(feature: str) -> None:
    """§5.2 regla 1. import-linter lo verifica en la build; esto lo localiza.

    El valor de tenerlo tambien aqui es el mensaje: import-linter dice que un
    contrato se rompio, este test dice en que fichero y con que linea.
    """
    otras = [f for f in FEATURES if f != feature]
    for fichero in (RAIZ / "features" / feature).rglob("*.py"):
        texto = fichero.read_text(encoding="utf-8")
        for otra in otras:
            prohibido = f"app.features.{otra}."
            assert prohibido not in texto, (
                f"{fichero.relative_to(RAIZ)} entra en las tripas de {otra}: "
                f"solo se entra por su __init__.py"
            )


def test_commons_no_importa_de_ninguna_feature() -> None:
    """§5.2 regla 2: commons es el nivel mas bajo y el mas caro de cambiar."""
    for fichero in (RAIZ / "commons").rglob("*.py"):
        assert "app.features" not in fichero.read_text(encoding="utf-8"), (
            f"{fichero.relative_to(RAIZ)} importa de una feature"
        )


def test_solo_agents_habla_con_el_modelo() -> None:
    """`CLAUDE.md` §9.3: el codigo de cada agente vive en el `agents.py` de su
    feature.

    Se comprueba como regla y no como lista de ficheros, a proposito. Exigir un
    `agents.py` en las ocho obligaria a crear cascarones vacios en las features
    cuyo agente todavia no existe -el Escritor, el Continuista-, y un fichero
    vacio que cumple un test es justo lo que hace que el test deje de significar
    algo. Esto en cambio crece solo: el dia que `escritura` invoque al modelo,
    tendra que hacerlo desde su `agents.py` o este test se pone rojo.
    """
    infractores = []
    for feature in FEATURES:
        for fichero in (RAIZ / "features" / feature).glob("*.py"):
            if fichero.name == "agents.py":
                continue
            if ".generar(" in fichero.read_text():
                infractores.append(f"{feature}/{fichero.name}")

    assert not infractores, (
        f"invocan al modelo fuera de agents.py: {', '.join(infractores)}"
    )


def test_los_agentes_declarados_existen() -> None:
    """Guardia del anterior: si `agents.py` desapareciera, aquel pasaria en
    vacio y nadie se enteraria. Las cuatro son las que hoy tienen agente."""
    for feature in ("obra", "outline", "escena", "canon"):
        assert (RAIZ / "features" / feature / "agents.py").is_file()
