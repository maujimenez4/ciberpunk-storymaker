"""El techo de la llamada, capa a capa (RF-CTX-02, 03, 05, 07 · CA-7).

Los topes son los literales de `CLAUDE.md` §4.1 y `architecture.md` §2.1. Aqui
no se redondean ni se derivan: se copian, y el primer test los compara.

**Ninguna prueba de este modulo llama al modelo**, y una lo comprueba de la
unica forma que lo comprueba de verdad: pasando un cliente que revienta si
alguien lo llama.
"""

import pytest

from app.commons.domain.errores import ContextBudgetExceeded, ErrorDeDominio
from app.commons.llm.cliente import ClienteModelo
from app.features.contexto.presupuesto import (
    TECHO_POR_LLAMADA,
    TOPES,
    Capa,
    Pieza,
    presupuestar,
)


class ContadorDePalabras:
    """Doble del contador: cuenta palabras y apunta lo que le dieron a contar.

    **No es el contador de produccion** —`CLAUDE.md` §4.1 prohibe estimar—, pero
    es exacto y reproducible, que es lo que un test del reparto necesita: el
    presupuesto se prueba contra numeros que el test elige, no contra los que
    un tokenizador decida.
    """

    def __init__(self) -> None:
        self.textos: list[str] = []

    def contar(self, texto: str) -> int:
        self.textos.append(texto)
        return len(texto.split())


class ContadorQueDiceTres:
    """Devuelve 3 para cualquier texto, largo o corto.

    Sirve a un solo test: si el presupuesto hiciera su propia cuenta por
    caracteres, un texto enorme no cabria y aqui cabe.
    """

    def contar(self, texto: str) -> int:
        return 3


class ClienteQueFalla:
    """Si alguien lo llama, el test cae. Es como se prueba «sin haber llamado»."""

    async def completar(self, prompt: str, semilla: int) -> str:
        raise AssertionError("se llamo al modelo con un paquete que no cabia")


def pieza(tokens: int, identificador: str | None = None) -> Pieza:
    """Una pieza que el `ContadorDePalabras` cuenta como exactamente `tokens`."""
    return Pieza(texto=" ".join(["x"] * tokens), identificador=identificador)


def test_los_topes_son_los_literales_de_claude_md_y_agotan_el_techo() -> None:
    """`CLAUDE.md` §4.1, fila a fila. Y su suma **es** el techo, no menos.

    Que sumen 100.000 exactos no es una casualidad bonita: es lo que hace que
    respetar los topes sea lo mismo que respetar el techo de la llamada. Si
    alguien sube un tope, este test cae, y debe caer: el techo ya no saldria de
    la suma de las capas.
    """
    assert TOPES == {
        Capa.CONSTITUCIONAL: 5_000,
        Capa.ESTRUCTURAL: 10_000,
        Capa.CANON: 20_000,
        Capa.ESTADO_EN_T: 15_000,
        Capa.CONTINUIDAD: 20_000,
        Capa.MEMORIA: 10_000,
        Capa.INSTRUCCION: 10_000,
        Capa.RESERVA: 10_000,
    }
    assert sum(TOPES.values()) == TECHO_POR_LLAMADA == 100_000


def test_el_desglose_suma_lo_que_dice() -> None:
    """Un desglose que no cuadra hace inutil la auditoria de CU-07."""
    desglose = presupuestar(
        {
            Capa.CONSTITUCIONAL: [pieza(1_000)],
            Capa.CANON: [pieza(2_000, "hc-1"), pieza(500, "hc-2")],
            Capa.INSTRUCCION: [pieza(300)],
        },
        ContadorDePalabras(),
    )

    assert desglose.lineas[Capa.CONSTITUCIONAL].tokens == 1_000
    assert desglose.lineas[Capa.CANON].tokens == 2_500
    assert desglose.lineas[Capa.INSTRUCCION].tokens == 300
    assert desglose.total == 3_800
    assert desglose.total == sum(linea.tokens for linea in desglose.lineas.values())


def test_el_desglose_trae_las_ocho_capas_aunque_lleguen_vacias() -> None:
    """El desglose se persiste en `ejecucion` (RF-CTX-05): una capa ausente del
    desglose y una capa vacia no son lo mismo, y quien audite tiene que poder
    distinguirlas sin adivinar."""
    desglose = presupuestar({Capa.INSTRUCCION: [pieza(10)]}, ContadorDePalabras())

    assert set(desglose.lineas) == set(Capa)
    assert desglose.lineas[Capa.CANON].tokens == 0
    assert desglose.lineas[Capa.CANON].piezas == ()
    assert desglose.lineas[Capa.CANON].tope == 20_000


def test_se_recorta_la_capa_que_se_pasa_y_las_vecinas_quedan_intactas() -> None:
    """R-2 · RF-CTX-03. Recortar a prorrata es lo que *parece* razonable."""
    contador = ContadorDePalabras()
    canon_holgado = pieza(15_000, "hc-1")
    canon_de_mas = pieza(9_000, "hc-2")
    desglose = presupuestar(
        {
            Capa.CANON: [canon_holgado, canon_de_mas],
            Capa.ESTRUCTURAL: [pieza(9_000)],
            Capa.MEMORIA: [pieza(8_000)],
        },
        contador,
    )

    assert desglose.lineas[Capa.CANON].piezas == (canon_holgado,)
    assert desglose.lineas[Capa.CANON].tokens == 15_000
    # Las vecinas no pagan el exceso de canon: siguen enteras.
    assert desglose.lineas[Capa.ESTRUCTURAL].tokens == 9_000
    assert desglose.lineas[Capa.MEMORIA].tokens == 8_000


def test_el_recorte_quita_por_el_final_y_deja_dicho_que_quito() -> None:
    """`CLAUDE.md` §15: no truncar sin registrar que se ha quitado.

    Se quita por el final porque quien surte la capa la entrega ordenada de mas
    a menos importante (`architecture.md` §2.1, columna «que se recorta
    primero»). Y lo quitado sale nombrado en el desglose: sin eso, un paquete
    al que le falta un hecho de canon es indistinguible de uno que nunca lo
    tuvo.
    """
    contador = ContadorDePalabras()
    primera = pieza(8_000, "hc-1")
    segunda = pieza(8_000, "hc-2")
    tercera = pieza(8_000, "hc-3")
    desglose = presupuestar({Capa.CANON: [primera, segunda, tercera]}, contador)

    linea = desglose.lineas[Capa.CANON]
    assert linea.piezas == (primera, segunda)
    assert linea.descartadas == (tercera,)
    assert [p.identificador for p in linea.descartadas] == ["hc-3"]
    assert linea.tokens == 16_000


def test_la_capa_constitucional_no_se_recorta_aunque_sea_la_salida_facil() -> None:
    """RF-CTX-07. El caso esta elegido para que recortarla fuera comodo.

    Sobran 1.000 tokens en constitucional y el resto del paquete va practicamente
    vacio: quitar una pieza constitucional haria que todo cupiera y nadie se
    quejaria. No se hace. Lo constitucional es lo que la novela **es**; un
    paquete sin su parte constitucional produce prosa que no se parece a la obra,
    y el defecto se le atribuiria al Escritor, que no lo cometio.
    """
    contador = ContadorDePalabras()

    with pytest.raises(ContextBudgetExceeded) as excepcion:
        presupuestar(
            {
                Capa.CONSTITUCIONAL: [pieza(4_000, "biblia"), pieza(2_000, "discurso")],
                Capa.ESTRUCTURAL: [pieza(100)],
            },
            contador,
        )

    assert excepcion.value.capa == Capa.CONSTITUCIONAL
    assert excepcion.value.tokens == 6_000
    assert excepcion.value.tope == 5_000


def test_la_capa_de_instruccion_tampoco_se_recorta() -> None:
    """RF-CTX-07, la otra mitad. La instruccion es lo que se pide: recortarla es
    cambiar el encargo sin decirlo."""
    with pytest.raises(ContextBudgetExceeded) as excepcion:
        presupuestar(
            {Capa.INSTRUCCION: [pieza(6_000, "ficha"), pieza(5_000, "prompt")]},
            ContadorDePalabras(),
        )

    assert excepcion.value.capa == Capa.INSTRUCCION


def test_una_pieza_que_no_cabe_ella_sola_no_se_trocea() -> None:
    """RF-CTX-03: «nunca se trunca por el final en silencio».

    El recorte quita piezas enteras. Una capa cuya pieza mas importante ya no
    cabe en su tope no se arregla cortandole el final a esa pieza —media ficha de
    canon es peor que ninguna, porque miente sin avisar— ni vaciando la capa, que
    dejaria al Ensamblador sin nada que detectar. Se lanza.
    """
    with pytest.raises(ContextBudgetExceeded) as excepcion:
        presupuestar({Capa.MEMORIA: [pieza(11_000, "res-1")]}, ContadorDePalabras())

    assert excepcion.value.capa == Capa.MEMORIA
    assert excepcion.value.tope == 10_000


async def test_si_no_cabe_se_lanza_sin_haber_llamado_al_modelo() -> None:
    """RF-CTX-02 · CA-7. El cliente revienta si lo tocan; el test pasa porque
    nadie lo toca. Contar es lo primero, y si no cabe no hay llamada que gastar."""
    cliente: ClienteModelo = ClienteQueFalla()

    async def escribir() -> str:
        presupuestar(
            {Capa.CONSTITUCIONAL: [pieza(9_000, "biblia")]},
            ContadorDePalabras(),
        )
        return await cliente.completar("prompt", 7)

    with pytest.raises(ContextBudgetExceeded):
        await escribir()


def test_cien_mil_exactos_caben() -> None:
    """R-1. El techo es «no mas de», no «menos de».

    Cada capa en su tope justo, reserva incluida: es el paquete de un reintento
    que ha consumido la reserva entera y sigue siendo legitimo. Una frontera mal
    puesta —un `>=` donde va un `>`— lo rechazaria, y el capitulo fallaria sin
    motivo que nadie sabria explicar.
    """
    desglose = presupuestar(
        {capa: [pieza(tope, capa.value)] for capa, tope in TOPES.items()},
        ContadorDePalabras(),
    )

    assert desglose.total == 100_000
    assert all(linea.descartadas == () for linea in desglose.lineas.values())


def test_la_reserva_queda_libre_tras_un_ensamblado_normal() -> None:
    """Es lo que permite que el reintento con el defecto anadido quepa
    (`CLAUDE.md` §4.1). Un ensamblado normal no la toca: nadie la surte
    (`architecture.md` §4.8, su fila no tiene origen)."""
    desglose = presupuestar(
        {
            Capa.CONSTITUCIONAL: [pieza(5_000)],
            Capa.ESTRUCTURAL: [pieza(10_000)],
            Capa.CANON: [pieza(20_000)],
            Capa.ESTADO_EN_T: [pieza(15_000)],
            Capa.CONTINUIDAD: [pieza(20_000)],
            Capa.MEMORIA: [pieza(10_000)],
            Capa.INSTRUCCION: [pieza(10_000)],
        },
        ContadorDePalabras(),
    )

    assert desglose.lineas[Capa.RESERVA].tokens == 0
    assert desglose.reserva_libre == 10_000
    assert desglose.total + desglose.reserva_libre == TECHO_POR_LLAMADA


def test_el_contador_es_el_inyectado_y_no_una_estimacion_propia() -> None:
    """RF-CTX-02: el contador se inyecta. Se comprueba por los dos lados.

    Con un contador que dice 3 para todo, un texto larguisimo cabe; si el
    presupuesto contara por su cuenta —por caracteres, por ejemplo—, no cabria.
    Y el otro lado: el contador ve **todas** las piezas, no una muestra.
    """
    contador = ContadorDePalabras()
    presupuestar(
        {Capa.CANON: [pieza(10, "hc-1"), pieza(20, "hc-2")]},
        contador,
    )
    assert len(contador.textos) == 2

    enorme = Pieza(texto="palabra " * 50_000)
    desglose = presupuestar({Capa.CANON: [enorme]}, ContadorQueDiceTres())
    assert desglose.lineas[Capa.CANON].tokens == 3


def test_context_budget_exceeded_es_un_error_de_dominio_y_nombra_la_capa() -> None:
    """Cuelga de `ErrorDeDominio` para que el handler central la traduzca con la
    regla que ya existe (`CLAUDE.md` §6). Y dice **que** capa no cabe: «no cabe»
    a secas no deja arreglar nada."""
    error = ContextBudgetExceeded(capa=Capa.CANON, tokens=21_000, tope=20_000)

    assert isinstance(error, ErrorDeDominio)
    assert error.capa == "canon"
    assert "canon" in str(error)
    assert "21000" in str(error) or "21.000" in str(error)
