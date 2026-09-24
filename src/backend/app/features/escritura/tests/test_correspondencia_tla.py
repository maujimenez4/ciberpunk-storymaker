"""RF-FOR-07 mecanizado: la especificacion y el codigo hablan de lo mismo.

`verification.md` §7 declara descubierto el riesgo de que la especificacion
TLA+ deje de corresponder al codigo, porque la correspondencia es una lectura
que nadie repite. Estos tests no la repiten entera —que una accion HAGA lo que
su nombre dice sigue siendo inspeccion— pero si las cuatro mitades que se
rompen solas: que las dos listas de transiciones sigan siendo la misma, que las
acciones esten todas emparejadas, que los simbolos emparejados existan, y que
los PREVISTOS sigan sin existir.

La especificacion abarca tres sitios y no uno: `maquina.py` (el ciclo),
`checkpoint.py` y `reanudacion.py` (la reanudacion), y `features/manuscrito/`
(las versiones publicadas, Fases 4 y 5).

Vive aqui, y no junto al `.tla`, a proposito: lo tiene que romper quien toca el
orquestador, no quien toca el documento.
"""

import importlib
import re
import tomllib
from pathlib import Path

from app.features.escritura.maquina import (
    Estado,
    Senal,
    TransicionInexistente,
    transitar,
)
from app.features.escritura.modelos import INTENTOS_MAXIMOS

RAIZ = Path(__file__).resolve().parents[6]
TLA = RAIZ / "formal" / "tla" / "Harness.tla"
CFG = RAIZ / "formal" / "tla" / "harness.cfg"
TABLA = tomllib.loads((RAIZ / "formal" / "tla" / "correspondencia.toml").read_text("utf-8"))

TERMINALES = {"INTEGRADA", "ESCALADA", "FALLIDA", "CANCELADA"}

ESTADOS_DE_LA_NOVELA = {
    "CONFIGURANDO",
    "PLANIFICADA",
    "ESCRIBIENDO_CAPITULO",
    "VALIDANDO_CAPITULO",
    "VERIFICANDO",
    "PUBLICADA",
    "REGENERANDO",
    "DETENIDA",
}


def acciones_del_next() -> set[str]:
    bloque = re.search(r"^Next ==\n((?:\s*\\/ \w+\n)+)", TLA.read_text("utf-8"), re.MULTILINE)
    assert bloque is not None, "El modulo no tiene un `Next` con un disyunto por linea"
    return set(re.findall(r"\\/ (\w+)", bloque.group(1)))


def resuelve(ruta: str) -> bool:
    modulo, _, simbolo = ruta.rpartition(".")
    try:
        cargado = importlib.import_module(modulo)
    except ModuleNotFoundError:
        return False
    return hasattr(cargado, simbolo)


def test_cada_accion_de_la_especificacion_esta_emparejada():
    assert acciones_del_next() == {a["nombre"] for a in TABLA["accion"]}


def transiciones_reales() -> set[tuple[str, str, str]]:
    """La relacion de transicion **por ejecucion**, no leyendo `_TRANSICIONES`.

    Y la diferencia no es de estilo: `transitar` tiene **dos caminos que
    esquivan la tabla**. Las averias de §3.6 se resuelven antes —`if senal in
    _AVERIAS: return FALLIDA`— y el destino de `REPARANDO` lo decide el
    contador. Un test que compare contra la tabla no ve ninguno de los dos, y
    **se ve verde**: eso fue lo que paso cuando la Fase 6 anadio
    `PROCESO_INTERRUMPIDO` y nada se puso rojo.

    Se prueban los dos lados del contador porque es lo unico que `intento`
    cambia: `>= INTENTOS_MAXIMOS` o por debajo.
    """
    salidas: set[tuple[str, str, str]] = set()
    for estado in Estado:
        for senal in Senal:
            for intento in (0, INTENTOS_MAXIMOS):
                try:
                    destino = transitar(estado, senal, intento=intento)
                except TransicionInexistente:
                    continue
                salidas.add((estado.value, senal.value, destino.value))
    return salidas


def declaradas_sin_accion() -> set[tuple[str, str, str]]:
    """Las sueltas mas las que se declaran **por regla**.

    Las averias no son dieciocho hechos independientes: son una regla —tres
    senales que llevan a `FALLIDA` desde cualquier estado vivo—. Declararlas una
    a una obligaria a anadir filas cada vez que naciera un estado, y el dia que
    alguien se olvidara el test diria que el codigo cambio cuando solo creci— la
    tabla. Se declara la regla y el test la expande.
    """
    sueltas = {tuple(s["transicion"]) for s in TABLA.get("sin_accion", [])}
    vivos = [e.value for e in Estado if e.value not in TERMINALES]
    por_regla = {
        (estado, senal, r["destino"])
        for r in TABLA.get("sin_accion_regla", [])
        for senal in r["senales"]
        for estado in vivos
    }
    return sueltas | por_regla


def test_cada_transicion_del_codigo_esta_reclamada_o_declarada():
    del_codigo = transiciones_reales()
    reclamadas = {tuple(t) for a in TABLA["accion"] for t in a.get("transiciones", [])}
    declaradas = declaradas_sin_accion()
    assert not reclamadas & declaradas, "Una transicion no puede estar en los dos sitios"
    assert del_codigo == reclamadas | declaradas


def test_lo_emparejado_existe_en_el_codigo():
    for accion in TABLA["accion"]:
        for ruta in accion.get("codigo", []):
            assert resuelve(ruta), f"{accion['nombre']} empareja con {ruta}, que no existe"


def test_lo_previsto_sigue_sin_existir():
    """R-5. El dia que la Fase 4 escriba `publicar`, esta fila deja de estar
    pendiente **y el test lo dice**, en vez de esperar a que alguien se acuerde."""
    for accion in TABLA["accion"]:
        for ruta in accion.get("codigo_previsto", []):
            assert not resuelve(ruta), (
                f"{ruta} ya existe: la fila '{accion['nombre']}' dejo de estar pendiente. "
                "Pasala a `codigo` y comprueba que la accion dice lo que hace ese codigo."
            )


def test_lo_pendiente_dice_de_que_fase_es():
    for accion in TABLA["accion"]:
        if not accion.get("codigo"):
            assert accion.get("pendiente"), (
                f"{accion['nombre']} no tiene codigo ni fase que lo traiga"
            )


def test_el_modelo_pequeno_usa_el_limite_del_codigo():
    cfg = CFG.read_text("utf-8")
    assert re.search(r"MaxReintentos\s*=\s*(\d+)", cfg).group(1) == str(INTENTOS_MAXIMOS)
    assert re.search(r"Capitulos\s*=\s*(\d+)", cfg).group(1) == "5"


def test_los_estados_del_modelo_son_los_de_architecture_39():
    bloque = re.search(r"^Estados ==\s*\{(.*?)\}", TLA.read_text("utf-8"), re.MULTILINE | re.DOTALL)
    assert bloque is not None
    assert set(re.findall(r'"(\w+)"', bloque.group(1))) == ESTADOS_DE_LA_NOVELA
