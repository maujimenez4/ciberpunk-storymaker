"""RF-MEM-06, que la spec marca como **Analisis** y no como Test.

«Solo el Extractor escribe memoria de largo plazo.» No es una propiedad que se
pueda observar ejecutando una escena: haria falta ejecutar *todas*. Lo que si
se puede es mirar el codigo de produccion entero y comprobar que **ninguna otra
ruta construye** una fila de los almacenes de `architecture.md` §4.3. Ese es el
analisis, y esta escrito como test para que corra en cada commit en vez de
depender de que alguien se acuerde.

**Leer esta permitido y escribir no**, y esa asimetria es el contenido: la
Tarea 7 tiene que leer el indice para recuperar, y la Tarea 6 tiene que leer el
canon para surtir su capa. Por eso no vale un test de imports —marcaria a los
lectores— y hace falta mirar quien **instancia** un modelo o lo pasa a un
`insert`/`update`/`delete`.

**Lo que este analisis no alcanza**, dicho para que nadie lo lea como mas de lo
que es: SQL en texto plano (`exec_driver_sql`, `text(...)`) escribe sin nombrar
la clase y se escapa de aqui. Contra eso protege otra cosa —los disparadores
del ledger, que viven en la base— y no este fichero.
"""

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]

# Los almacenes de largo plazo de `architecture.md` §4.3 que hoy son tablas.
MODELOS_DE_LARGO_PLAZO = frozenset(
    {
        "Embedding",
        "Evento",
        "HechoCanon",
        "HechoUsadoEn",
        "HiloNarrativo",
        "Plantado",
        "ResumenCapitulo",
        # Las variantes de un nombre son canon: dicen como se puede llamar a
        # alguien, y el validador de `calidad` decide con ellas. Si otra ruta
        # las escribiera, `CA-16` aceptaria grafias que el canon no declara.
        "VarianteDeNombre",
    }
)

# `canon/repository.py` es el Extractor. `obra/repository.py` es la unica
# excepcion y esta en la spec: RF-ENT-06 hace entrar al canon los hechos del
# brief, que existen **antes** del texto y por tanto antes de que haya
# Extractor que los extraiga de una escena.
ESCRITORES_PERMITIDOS = frozenset(
    {
        "features/canon/repository.py",
        "features/obra/repository.py",
    }
)

_MUTACIONES = frozenset({"insert", "update", "delete"})


def _ficheros_de_produccion() -> list[Path]:
    return [
        fichero
        for fichero in sorted(RAIZ.rglob("*.py"))
        if "tests" not in fichero.parts and fichero.name != "conftest.py"
    ]


def _nombre(nodo: ast.expr) -> str | None:
    if isinstance(nodo, ast.Name):
        return nodo.id
    if isinstance(nodo, ast.Attribute):
        return nodo.attr
    return None


def _escribe_memoria_de_largo_plazo(arbol: ast.AST) -> bool:
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        llamado = _nombre(nodo.func)
        if llamado in MODELOS_DE_LARGO_PLAZO:
            return True
        if llamado in _MUTACIONES and nodo.args and _nombre(nodo.args[0]) in MODELOS_DE_LARGO_PLAZO:
            return True
    return False


def test_ninguna_ruta_fuera_del_extractor_escribe_en_canon_ledger_ni_indice():
    escritores = {
        fichero.relative_to(RAIZ).as_posix()
        for fichero in _ficheros_de_produccion()
        if _escribe_memoria_de_largo_plazo(ast.parse(fichero.read_text(encoding="utf-8")))
    }
    assert escritores <= ESCRITORES_PERMITIDOS, (
        f"escriben memoria de largo plazo y no deberian: {sorted(escritores - ESCRITORES_PERMITIDOS)}"
    )


def test_el_analisis_mira_de_verdad_el_arbol_de_produccion():
    """Sin esto, un `rglob` que no encuentre nada dejaria el test en verde.

    Es la misma trampa de siempre: una comprobacion cuyo conjunto vacio pasa.
    """
    ficheros = _ficheros_de_produccion()
    assert len(ficheros) > 20
    assert any(f.as_posix().endswith("features/canon/repository.py") for f in ficheros)


def test_el_extractor_si_escribe():
    """Y el contraste: si `canon/repository.py` dejara de escribir, algo va mal."""
    fichero = RAIZ / "features" / "canon" / "repository.py"
    assert _escribe_memoria_de_largo_plazo(ast.parse(fichero.read_text(encoding="utf-8")))
