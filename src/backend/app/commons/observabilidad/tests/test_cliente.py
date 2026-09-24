"""`ClienteObservado` y `Observacion`: por donde el prompt de cada rol llega a su span.

Lo que se prueba aqui es la pieza, no el cableado: que un rol que llama al
modelo **dentro** de un span deje en el su prompt renderizado, su salida y su
consumo (`CLAUDE.md` §4.3), y que fuera de un span no deje nada ni estorbe.
Ninguna prueba sale de la maquina (`CA-4`).
"""

from decimal import Decimal

import pytest

from app.commons.llm.doble import DobleDeterminista
from app.commons.observabilidad import (
    ClienteObservado,
    Observacion,
    ObservadorEnMemoria,
    blindar,
)


class _Consumo:
    def __init__(self) -> None:
        self.modelo = "claude-haiku-4-5"
        self.tokens_entrada = 120
        self.tokens_salida = 30
        self.coste_usd = Decimal("0.0003")


class DobleQueCuenta(DobleDeterminista):
    """El doble con el `ultimo_consumo` que el cliente real expone."""

    def __init__(self, respuestas: dict[str, str]) -> None:
        super().__init__(respuestas)
        self.ultimo_consumo: _Consumo | None = None

    async def completar(self, prompt: str, semilla: int, modelo: str | None = None) -> str:
        respuesta = await super().completar(prompt, semilla, modelo)
        self.ultimo_consumo = _Consumo()
        return respuesta


async def test_dentro_de_un_span_sube_el_prompt_la_salida_y_el_consumo() -> None:
    observador = ObservadorEnMemoria()
    cliente = ClienteObservado(DobleQueCuenta({"ESCRITOR": "la prosa"}))

    async with observador.traza(obra_id=3, nombre="capitulo-1") as traza:
        observacion = Observacion(traza=traza, cliente=cliente)
        async with observacion.span("escritor"):
            respuesta = await cliente.completar("# ESCRITOR con su paquete", semilla=0)

    assert respuesta == "la prosa"
    [span] = observador.trazas[0].spans
    assert span.nombre == "escritor"
    assert span.entradas == ["# ESCRITOR con su paquete"]
    assert span.salidas == ["la prosa"]
    assert span.consumos == [
        {
            "modelo": "claude-haiku-4-5",
            "tokens_entrada": 120,
            "tokens_salida": 30,
            "coste_usd": Decimal("0.0003"),
        }
    ]


async def test_fuera_de_un_span_no_sube_nada_y_la_llamada_sale_igual() -> None:
    cliente = ClienteObservado(DobleDeterminista({"X": "y"}))

    assert await cliente.completar("X", semilla=0) == "y"


async def test_cada_span_recibe_solo_lo_de_su_rol() -> None:
    observador = ObservadorEnMemoria()
    cliente = ClienteObservado(DobleDeterminista({"PLAN": "ficha", "ESCRIBE": "prosa"}))

    async with observador.traza(obra_id=1, nombre="t") as traza:
        observacion = Observacion(traza=traza, cliente=cliente)
        async with observacion.span("planificador"):
            await cliente.completar("PLAN", semilla=0)
        async with observacion.span("escritor"):
            await cliente.completar("ESCRIBE", semilla=0)

    planificador, escritor = observador.trazas[0].spans
    assert planificador.salidas == ["ficha"]
    assert escritor.salidas == ["prosa"]


async def test_sin_consumo_declarado_no_se_inventa_un_cero() -> None:
    """El doble no tiene `ultimo_consumo`. Un cero se sumaria en el panel como
    si la llamada hubiera sido gratis; que no haya consumo se tiene que ver."""
    observador = ObservadorEnMemoria()
    cliente = ClienteObservado(DobleDeterminista({"X": "y"}))

    async with (
        observador.traza(obra_id=1, nombre="t") as traza,
        Observacion(traza=traza, cliente=cliente).span("rol"),
    ):
        await cliente.completar("X", semilla=0)

    assert observador.trazas[0].spans[0].consumos == []


async def test_el_modelo_pedido_llega_al_cliente_de_dentro() -> None:
    """P-02: el juez pide su modelo en la llamada. Envolver no puede perderlo."""
    doble = DobleDeterminista({"X": "y"})

    await ClienteObservado(doble).completar("X", semilla=0, modelo="claude-opus")

    assert doble.modelos == ["claude-opus"]


async def test_reenvia_el_ultimo_consumo_y_vectoriza_igual() -> None:
    """`_completar_ejecucion` pregunta `ultimo_consumo` al cliente del Escritor:
    envuelto, tiene que seguir contestando lo mismo."""
    doble = DobleQueCuenta({"X": "y"})
    cliente = ClienteObservado(doble)

    await cliente.completar("X", semilla=0)

    assert cliente.ultimo_consumo is doble.ultimo_consumo
    assert cliente.vectorizar("hola") == doble.vectorizar("hola")


async def test_el_fallo_del_modelo_sale_entero_y_el_prompt_ya_subio() -> None:
    """El blindaje protege del observador, no del modelo: si el modelo falla,
    la excepcion sale. Y el prompt ya esta en el span, que es lo que hace falta
    para entender por que fallo."""
    observador = ObservadorEnMemoria()
    cliente = ClienteObservado(DobleDeterminista({}))

    async with observador.traza(obra_id=1, nombre="t") as traza:
        with pytest.raises(Exception, match="NADA"):
            async with Observacion(traza=traza, cliente=cliente).span("rol"):
                await cliente.completar("NADA preparado", semilla=0)

    assert observador.trazas[0].spans[0].entradas == ["NADA preparado"]


async def test_con_un_observador_que_revienta_la_llamada_sale_igual() -> None:
    """R-1 por el camino del cliente: el span blindado se traga el fallo."""

    class Roto:
        def traza(self, *, obra_id: int, nombre: str):  # type: ignore[no-untyped-def]
            raise RuntimeError("langfuse caido")

    cliente = ClienteObservado(DobleDeterminista({"X": "y"}))

    async with (
        blindar(Roto()).traza(obra_id=1, nombre="t") as traza,  # type: ignore[arg-type]
        Observacion(traza=traza, cliente=cliente).span("rol"),
    ):
        assert await cliente.completar("X", semilla=0) == "y"


async def test_sin_cliente_observado_el_span_se_abre_igual() -> None:
    """Un test del ciclo que monta sus roles a mano no envuelve el cliente: el
    span existe igual, sin prompt. Es menos, no es un error."""
    observador = ObservadorEnMemoria()

    async with (
        observador.traza(obra_id=1, nombre="t") as traza,
        Observacion(traza=traza, cliente=None).span("rol") as span,
    ):
        span.salida("algo")

    assert observador.trazas[0].spans[0].salidas == ["algo"]
