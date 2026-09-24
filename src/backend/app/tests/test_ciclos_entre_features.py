"""Las features no forman ciclos: `CLAUDE.md` §5.1, regla 5.

**Por que esto es un test y no un contrato de import-linter.** La forma natural
de expresar «sin ciclos» alli es un contrato `layers`, y no se deja: sigue
cadenas que pasan por `app.main`, que es el raiz de composicion y monta **todas**
las features por diseno (§5.1), asi que cualquier capa acaba «importando» a todas
las demas a traves de el. Ignorar esas cadenas exige ignorar tantas que el
contrato deja de comprobar lo que dice.

**Y por que esto existe.** El 2026-09-24 se midio el grafo a mano, salieron cero
ciclos, y se escribio en `pyproject.toml` que la regla 5 quedaba como
«comprobacion manual declarada». **Duro una hora**: la tarea de publicar
introdujo `manuscrito -> escritura` y con el dos ciclos, y el arbol dejo de
coleccionar para los cinco agentes que trabajaban a la vez.

La medicion era correcta. Lo que no valia era el metodo: **una comprobacion que
se hace una vez no vigila un arbol que cambia cada diez minutos.**

Antes de aquello, alguien ya se habia topado con el mismo ciclo y lo habia
esquivado **difiriendo un import dentro de una funcion**. Eso hace que Python
arranque y deja el ciclo en pie, asi que este test mira el **texto** de los
imports y no el grafo en tiempo de ejecucion: un import diferido cuenta igual.
"""

from __future__ import annotations

import re
from pathlib import Path

FEATURES = Path(__file__).resolve().parents[1] / "features"

# `from app.features.X` e `import app.features.X`, con o sin sangria -- la
# sangria es lo que delata un import diferido dentro de una funcion, y cuenta.
IMPORT = re.compile(r"(?:from|import)\s+app\.features\.([a-z_]+)")


def _grafo() -> dict[str, set[str]]:
    """Que feature importa a que feature, leyendo el texto de los ficheros.

    Los tests quedan fuera: un test entra a otra feature a proposito, para
    fabricar el estado que necesita comprobar, y eso no es deuda de diseno.
    """
    grafo: dict[str, set[str]] = {}
    for fichero in FEATURES.rglob("*.py"):
        if "tests" in fichero.parts:
            continue
        propia = fichero.relative_to(FEATURES).parts[0]
        for linea in fichero.read_text(encoding="utf-8").splitlines():
            encontrado = IMPORT.search(linea)
            if encontrado and encontrado.group(1) != propia:
                grafo.setdefault(propia, set()).add(encontrado.group(1))
    return grafo


def _ciclos(grafo: dict[str, set[str]]) -> list[list[str]]:
    hallados: dict[tuple[str, ...], list[str]] = {}

    def recorrer(nodo: str, camino: list[str]) -> None:
        for siguiente in sorted(grafo.get(nodo, ())):
            if siguiente in camino:
                ciclo = camino[camino.index(siguiente) :] + [siguiente]
                hallados.setdefault(tuple(sorted(set(ciclo))), ciclo)
            else:
                recorrer(siguiente, camino + [siguiente])

    for inicio in sorted(grafo):
        recorrer(inicio, [inicio])
    return list(hallados.values())


def test_las_features_no_forman_ciclos() -> None:
    """Regla 5 de §5.1: un ciclo entre features **es un error de diseno**.

    No se arregla difiriendo el import -- eso solo hace que Python arranque --
    sino extrayendo el concepto a `commons/domain/` o invirtiendo con un evento.
    """
    ciclos = _ciclos(_grafo())
    assert not ciclos, "ciclos entre features:\n" + "\n".join("  " + " -> ".join(c) for c in ciclos)


def test_el_grafo_tiene_aristas_que_mirar() -> None:
    """Sin esto, el test de arriba pasa el dia que el barrido deje de encontrar
    imports -- por un cambio de nombre de carpeta, por ejemplo -- y nadie se
    entera de que ha dejado de comprobar nada.

    Es la misma salvaguarda que `len(manuscrito) > 0` en el test de la
    dedicatoria: afirmar tambien que **hay algo que mirar**.
    """
    grafo = _grafo()
    assert len(grafo) >= 4, f"solo {len(grafo)} features importan a otras: ¿sigue leyendo bien?"
    assert sum(len(v) for v in grafo.values()) >= 6
