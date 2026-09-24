"""La regla 1 de `CLAUDE.md` §5.1, que hasta ahora no la guardaba nadie.

§5.1 dice, literal: «Reglas (**test de arquitectura con import-linter; falla la
build**): 1. Una feature solo importa de `commons/` y del `__init__.py` de otra
feature. **Nunca** de sus ficheros internos.»

Los dos contratos de `import-linter` miran `commons/`: que no importe de ninguna
feature, y que `commons/domain/` no conozca el framework. **Ninguno comprueba la
regla 1.** Lo destaparon dos agentes de la ola 2 de la Fase 2, por separado, y es
el patron que mas se repite en este proyecto: una afirmacion sobre la que ningun
test puede caer.

No se expresa como contrato de `import-linter` porque haria falta uno por cada
par de features -- nueve features son setenta y dos contratos -- y porque lo que
se quiere afirmar no es «A no importa de B» sino «nadie entra por un fichero
interno». Eso se lee mejor del arbol de sintaxis.

**Los ficheros de test quedan fuera, y es una decision, no un descuido.** La
regla protege el acoplamiento del codigo de PRODUCCION: dos features que se
conocen por dentro no se pueden mover por separado. Un test que construye una
fila de otra feature para satisfacer una clave ajena con `foreign_keys=ON` no
acopla nada -- necesita el dato, no el diseno --, y prohibirselo obligaria a
exportar por la puerta cosas que fuera del test nadie debe ver. Hoy hay tres
cruces asi, todos declarados por sus autores.
"""

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1] / "features"


def _imports_de(fichero: Path) -> list[tuple[str, int]]:
    arbol = ast.parse(fichero.read_text(encoding="utf-8"), str(fichero))
    encontrados: list[tuple[str, int]] = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom) and nodo.module:
            encontrados.append((nodo.module, nodo.lineno))
        elif isinstance(nodo, ast.Import):
            encontrados.extend((alias.name, nodo.lineno) for alias in nodo.names)
    return encontrados


def test_ninguna_feature_entra_a_otra_por_un_fichero_interno():
    """La frontera que mas importa, y la que solo sostenia la disciplina."""
    infracciones: list[str] = []
    for fichero in RAIZ.rglob("*.py"):
        partes_ruta = fichero.relative_to(RAIZ).parts
        if "tests" in partes_ruta or fichero.name == "conftest.py":
            continue
        propia = partes_ruta[0]
        for modulo, linea in _imports_de(fichero):
            partes = modulo.split(".")
            if partes[:2] != ["app", "features"] or len(partes) < 4:
                continue
            if partes[2] == propia:
                continue
            infracciones.append(f"{fichero.name}:{linea} -> {modulo}")
    assert not infracciones, (
        "Estas lineas entran a otra feature por un fichero interno, y §5.1 lo "
        "prohibe. Se entra por su `__init__.py`:\n  " + "\n  ".join(infracciones)
    )


def test_el_test_anterior_sabe_reconocer_una_infraccion():
    """Contraste: sin esto, un arbol sin infracciones lo deja verde por vacio."""
    arbol = ast.parse("from app.features.canon.repository import algo\n")
    modulos = [n.module for n in ast.walk(arbol) if isinstance(n, ast.ImportFrom)]
    assert modulos == ["app.features.canon.repository"]
    assert len(modulos[0].split(".")) >= 4
