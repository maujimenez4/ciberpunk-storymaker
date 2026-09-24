"""El Ensamblador, en lo que tiene de codigo puro (RF-CTX-01, 06, 08, 09).

Aqui no hay base de datos ni framework a proposito: el paquete lo ensambla
**codigo determinista, nunca un modelo**, y el motivo no es la eficiencia --
es que si fuera un modelo **no se podria reproducir un fallo** (RF-CTX-01,
`CLAUDE.md` §9.1). Un modulo que no puede llamar a nadie es la unica forma de
afirmar eso y que un test pueda caer.

El test que de verdad distingue es
`test_una_capa_vacia_que_deberia_tener_contenido_falla_antes_de_llamar` (R-3):
esta escrito para caer si el Ensamblador se limita a pasar lo que le den. Su
pareja, `test_una_capa_vacia_que_nadie_surtio_no_falla`, guarda que la regla
siga discriminando: una regla que fallara **siempre** que una capa llega vacia
convertiria en error el caso legitimo, y nadie lo notaria hasta el primer
capitulo sin memoria pertinente.
"""

import ast
from pathlib import Path

import pytest

from app.commons.domain.errores import ContextBudgetExceeded, ErrorDeDominio
from app.features.contexto.capas import (
    CAPAS_CON_ORIGEN,
    CapaVacia,
    Paquete,
    Surtido,
    ensamblar,
)
from app.features.contexto.presupuesto import TOPES, Capa, Pieza


class ContadorDePalabras:
    """Doble exacto y reproducible: el test elige los numeros, no el tokenizador."""

    def contar(self, texto: str) -> int:
        return len(texto.split())


class ClienteQueFalla:
    """Si alguien lo llama, el test cae. Es como se prueba «sin haber llamado»."""

    async def completar(self, prompt: str, semilla: int) -> str:
        raise AssertionError("el Ensamblador llamo al modelo, y es codigo")


def pieza(tokens: int, identificador: str | None = None) -> Pieza:
    """Una pieza que `ContadorDePalabras` cuenta como exactamente `tokens`."""
    return Pieza(texto=" ".join(["x"] * tokens), identificador=identificador)


def surtido(*piezas: Pieza, disponibles: int | None = None) -> Surtido:
    """Un surtido cuyo censo, por defecto, es lo que entrega."""
    return Surtido(piezas=piezas, disponibles=len(piezas) if disponibles is None else disponibles)


def surtidos_minimos(**cambios: Surtido) -> dict[Capa, Surtido]:
    """Las siete capas con origen surtidas con una pieza, y las que el test cambie."""
    base = {capa: surtido(pieza(1, f"{capa.value}:1")) for capa in CAPAS_CON_ORIGEN}
    base.update(cambios)
    return base


# ---------------------------------------------------------------------------
# 1. RF-CTX-01 · codigo determinista, nunca un modelo
# ---------------------------------------------------------------------------


def test_dos_ensamblados_del_mismo_surtido_dan_el_mismo_paquete() -> None:
    """Determinismo, que es lo que permite reproducir un fallo (RF-CTX-01)."""
    surtidos = surtidos_minimos()
    contador = ContadorDePalabras()

    primero = ensamblar(surtidos, contador)
    segundo = ensamblar(surtidos, contador)

    assert primero.texto == segundo.texto
    assert primero.ids_por_capa == segundo.ids_por_capa
    assert primero.tokens_por_capa == segundo.tokens_por_capa


def test_el_ensamblador_no_conoce_al_cliente_de_modelo() -> None:
    """RF-CTX-01 se verifica por **analisis**, y la spec lo dice asi.

    Un test que solo comprobara que no se llamo al modelo en un caso concreto
    dejaria vivo el caso siguiente. Lo que hace imposible que el Ensamblador
    sea un modelo es que su feature **no importe al cliente**, y eso se lee del
    arbol de sintaxis. `contexto` es la unica feature de `CLAUDE.md` §9 sin
    `agents.py`, y esta es la afirmacion correspondiente.
    """
    raiz = Path(__file__).resolve().parents[1]
    infracciones: list[str] = []
    for fichero in raiz.rglob("*.py"):
        if "tests" in fichero.relative_to(raiz).parts:
            continue
        arbol = ast.parse(fichero.read_text(encoding="utf-8"), str(fichero))
        for nodo in ast.walk(arbol):
            modulos = []
            if isinstance(nodo, ast.ImportFrom) and nodo.module:
                modulos = [nodo.module]
            elif isinstance(nodo, ast.Import):
                modulos = [alias.name for alias in nodo.names]
            for modulo in modulos:
                if modulo.startswith("app.commons.llm.cliente"):
                    infracciones.append(f"{fichero.name}:{nodo.lineno} -> {modulo}")

    assert not infracciones, (
        "La feature `contexto` importa el cliente de modelo, y el Ensamblador es "
        "codigo (RF-CTX-01):\n  " + "\n  ".join(infracciones)
    )


def test_ensamblar_no_recibe_ni_puede_usar_un_cliente() -> None:
    """Y el contrato tampoco deja colarlo: se le pasa el contador, nada mas."""
    with pytest.raises(TypeError):
        ensamblar(surtidos_minimos(), ContadorDePalabras(), ClienteQueFalla())  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# 2. R-3 · RF-CTX-06 · la capa vacia que deberia tener contenido
# ---------------------------------------------------------------------------


def test_una_capa_vacia_que_deberia_tener_contenido_falla_antes_de_llamar() -> None:
    """R-3, y es el test central de esta tarea.

    Un capitulo cuyo grafo de canon tiene hechos y cuya capa de canon sale
    vacia produce prosa que contradice lo ya escrito, y el defecto se
    atribuiria al Escritor, **que no lo cometio**. Es fallo del almacen y se
    falla antes de llamar.
    """
    surtidos = surtidos_minimos(canon=Surtido(piezas=(), disponibles=3))

    with pytest.raises(CapaVacia) as caida:
        ensamblar(surtidos, ContadorDePalabras())

    assert caida.value.capa == Capa.CANON.value
    assert caida.value.disponibles == 3


def test_una_capa_vacia_que_nadie_surtio_no_falla() -> None:
    """La pareja del anterior: censo 0 es una capa legitimamente vacia.

    Sin este test la regla podria endurecerse hasta fallar siempre que una capa
    llega vacia, y eso convertiria en error el caso normal de un capitulo sin
    memoria pertinente. Lo que distingue no es que este vacia: es **que tenia**.
    """
    surtidos = surtidos_minimos(memoria=Surtido(piezas=(), disponibles=0))

    paquete = ensamblar(surtidos, ContadorDePalabras())

    assert paquete.ids_por_capa[Capa.MEMORIA] == ()


def test_la_reserva_vacia_nunca_falla_porque_no_tiene_almacen_de_origen() -> None:
    """`architecture.md` §4.8: la fila de la reserva **no tiene** memoria de origen.

    Exigirle contenido seria exigir que la surtiera alguien, y la reserva existe
    justo para lo contrario: quedar libre para el reintento con el defecto.
    """
    assert Capa.RESERVA not in CAPAS_CON_ORIGEN

    paquete = ensamblar(surtidos_minimos(), ContadorDePalabras())

    assert paquete.desglose.reserva_libre == TOPES[Capa.RESERVA]


def test_las_siete_capas_con_origen_son_las_de_architecture_4_8() -> None:
    """La tabla de §4.8, literal: siete capas con almacen y la reserva sin el."""
    assert CAPAS_CON_ORIGEN == frozenset(
        {
            Capa.CONSTITUCIONAL,
            Capa.ESTRUCTURAL,
            Capa.CANON,
            Capa.ESTADO_EN_T,
            Capa.CONTINUIDAD,
            Capa.MEMORIA,
            Capa.INSTRUCCION,
        }
    )


def test_capa_vacia_es_error_de_dominio_y_no_se_confunde_con_el_presupuesto() -> None:
    """Hereda de `ErrorDeDominio` —el manejador central la traduce sin darla de
    alta— y **no** de `ContextBudgetExceeded`: un almacen que no surte y un
    paquete que no cabe son dos fallos distintos con dos arreglos distintos."""
    error = CapaVacia(capa=Capa.CANON, disponibles=2)

    assert isinstance(error, ErrorDeDominio)
    assert not isinstance(error, ContextBudgetExceeded)


# ---------------------------------------------------------------------------
# 3. RF-CTX-08 · la capa de canon etiqueta por `hc_id`, no por posicion
# ---------------------------------------------------------------------------


def test_el_canon_etiqueta_por_hc_id_y_el_recorte_no_le_cambia_la_etiqueta() -> None:
    """RF-CTX-08. **La posicion cambia con el recorte y el identificador no.**

    Se surte la capa de canon por encima de su tope para que el recorte muerda,
    y se comprueba que lo que sobrevive sigue nombrado por su `hc_id`: si el
    paquete identificara por indice, quitar la pieza del final renumeraria a
    todas y `ejecucion` diria que se envio un hecho que no se envio.
    """
    tope = TOPES[Capa.CANON]
    surtidos = surtidos_minimos(
        canon=surtido(
            pieza(tope - 1, "hc:7"),
            pieza(tope - 1, "hc:41"),
            pieza(tope - 1, "hc:99"),
        )
    )

    paquete = ensamblar(surtidos, ContadorDePalabras())

    assert paquete.ids_por_capa[Capa.CANON] == ("hc:7",)


# ---------------------------------------------------------------------------
# 4. RF-CTX-09 · los IDs, con su capa, y solo los que sobrevivieron
# ---------------------------------------------------------------------------


def test_los_ids_persistidos_son_solo_los_de_las_piezas_que_sobrevivieron() -> None:
    """RF-CTX-09, la mitad que se olvida: lo descartado **no** se persiste.

    Guardar el id de una pieza que se recorto es peor que no guardar ninguno:
    CU-07 diria que un hecho de canon se envio al modelo cuando el modelo nunca
    lo vio, y la auditoria acusaria al Escritor de ignorarlo.
    """
    tope = TOPES[Capa.MEMORIA]
    surtidos = surtidos_minimos(memoria=surtido(pieza(tope, "emb:1"), pieza(tope, "emb:2")))

    paquete = ensamblar(surtidos, ContadorDePalabras())

    assert paquete.ids_por_capa[Capa.MEMORIA] == ("emb:1",)
    assert paquete.desglose.lineas[Capa.MEMORIA].descartadas[0].identificador == "emb:2"


def test_los_ids_van_con_su_capa_y_de_todas_las_capas_que_los_tienen() -> None:
    """RF-CTX-09: **todas** las capas que tienen identificadores, con su capa.

    Guardar solo los de memoria y canon —que son las dos columnas que hay en
    `ejecucion`— dejaria sin auditar de que version de biblia y de que ficha
    salio el paquete, que es justo lo que hace reconstruible CA-12.
    """
    paquete = ensamblar(surtidos_minimos(), ContadorDePalabras())

    assert set(paquete.ids_por_capa) == CAPAS_CON_ORIGEN
    for capa in CAPAS_CON_ORIGEN:
        assert paquete.ids_por_capa[capa] == (f"{capa.value}:1",)


def test_una_pieza_sin_identificador_no_inventa_uno() -> None:
    """No todas las capas tienen de donde sacarlo, y un id inventado no audita nada."""
    surtidos = surtidos_minimos(estado_en_t=surtido(pieza(1), pieza(1, "ev:4")))

    paquete = ensamblar(surtidos, ContadorDePalabras())

    assert paquete.ids_por_capa[Capa.ESTADO_EN_T] == ("ev:4",)


# ---------------------------------------------------------------------------
# 5. El paquete y su desglose viajan juntos (RF-CTX-05)
# ---------------------------------------------------------------------------


def test_el_paquete_trae_el_desglose_y_el_texto_de_lo_que_sobrevivio() -> None:
    """El texto es el de las piezas que quedaron, no el de las que llegaron."""
    tope = TOPES[Capa.CONTINUIDAD]
    surtidos = surtidos_minimos(
        continuidad=surtido(
            Pieza(texto=" ".join(["cabe"] * tope)),
            Pieza(texto="se recorta"),
        )
    )

    paquete: Paquete = ensamblar(surtidos, ContadorDePalabras())

    assert "se recorta" not in paquete.texto
    assert "cabe" in paquete.texto
    assert paquete.tokens_previstos == paquete.desglose.total


def test_el_texto_nombra_cada_capa_y_las_ordena_siempre_igual() -> None:
    """Un paquete cuyo orden dependiera del diccionario no seria reproducible."""
    paquete = ensamblar(surtidos_minimos(), ContadorDePalabras())

    posiciones = [paquete.texto.find(capa.value) for capa in Capa if capa in CAPAS_CON_ORIGEN]
    assert all(p >= 0 for p in posiciones)
    assert posiciones == sorted(posiciones)


def test_una_capa_que_no_cabe_ni_recortando_sigue_lanzando_lo_del_presupuesto() -> None:
    """El Ensamblador no se come el fallo de T5: `ContextBudgetExceeded` sale."""
    surtidos = surtidos_minimos(instruccion=surtido(pieza(TOPES[Capa.INSTRUCCION] + 1, "ficha:1")))

    with pytest.raises(ContextBudgetExceeded):
        ensamblar(surtidos, ContadorDePalabras())
