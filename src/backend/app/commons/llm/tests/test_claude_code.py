"""El cliente de modelo real, probado **sin llamar al proveedor** (CA-4).

Ni un solo test de este fichero abre el SDK. Lo que se prueba es lo que el
codigo nuestro decide: que modelo viaja, que opciones viajan, como se deriva
el coste y que no se toca nada al importar. La llamada de verdad se hace una
vez, a mano, y esta declarada en el plan (Tarea 1) — no en la suite.
"""

import inspect
import os
import subprocess
import sys
from collections.abc import AsyncIterator
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock

from app.commons.llm.claude_code import (
    MODELO_ESCRITOR,
    MODELO_JUEZ,
    TARIFAS,
    ClienteClaudeCode,
    LlamadaRechazada,
    RespuestaVacia,
    TarifaDesconocida,
    coste_derivado,
)
from app.commons.llm.cliente import ClienteModelo, obtener_cliente_modelo


class ConsultaFalsa:
    """El SDK sustituido. Registra las opciones y devuelve lo preparado.

    Es el mismo principio que `DobleDeterminista`: el doble no inventa y no
    sale de la maquina.
    """

    def __init__(self, textos: list[str], uso: dict[str, Any] | None = None) -> None:
        self._textos = textos
        self._uso = uso if uso is not None else {"input_tokens": 0, "output_tokens": 0}
        self.prompts: list[str] = []
        self.opciones: list[ClaudeAgentOptions] = []

    def __call__(
        self, *, prompt: str, options: ClaudeAgentOptions | None = None, **_: object
    ) -> AsyncIterator[Any]:
        self.prompts.append(prompt)
        assert options is not None
        self.opciones.append(options)
        return self._emitir()

    async def _emitir(self) -> AsyncIterator[Any]:
        yield AssistantMessage(
            content=[TextBlock(text=t) for t in self._textos],
            model=MODELO_ESCRITOR,
        )
        yield ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=False,
            num_turns=1,
            session_id="s-1",
            # El proveedor manda una cifra de coste: se ignora a proposito.
            total_cost_usd=999.0,
            usage=self._uso,
        )


async def test_el_cliente_real_satisface_el_protocolo_y_devuelve_la_prosa():
    """`ClienteModelo` no cambia de forma: si cambiara, rompe `DobleDeterminista`."""
    consulta = ConsultaFalsa(["Dos ", "bloques."])
    cliente: ClienteModelo = ClienteClaudeCode(consulta=consulta)

    assert await cliente.completar("escribe el capitulo", semilla=7) == "Dos bloques."
    assert consulta.prompts == ["escribe el capitulo"]


def test_el_modelo_por_defecto_del_escritor_es_haiku():
    """P-02: Haiku 4.5 escribe, Opus 5 juzga. Y el modelo es **parametro**."""
    assert ClienteClaudeCode().modelo == "claude-haiku-4-5"
    assert MODELO_ESCRITOR == "claude-haiku-4-5"
    assert MODELO_JUEZ == "claude-opus-5"
    assert ClienteClaudeCode(MODELO_JUEZ).modelo == MODELO_JUEZ


async def test_el_modelo_y_las_restricciones_viajan_en_las_opciones():
    """Un capitulo se escribe sin herramientas, sin ajustes del repositorio y
    con el prompt entregado tal cual.

    Lo tercero no es cosmetico: el texto del comprador es contenido no
    confiable (`CLAUDE.md` §11), y sin `verbatim_prompts` el CLI expande
    `@ruta` y despacha barras dentro de ese texto.
    """
    consulta = ConsultaFalsa(["x"])
    await ClienteClaudeCode(MODELO_JUEZ, consulta=consulta).completar("p", semilla=1)

    opciones = consulta.opciones[0]
    assert opciones.model == MODELO_JUEZ
    assert opciones.tools == []
    assert opciones.allowed_tools == []
    assert opciones.setting_sources == []
    assert opciones.max_turns == 1
    assert opciones.verbatim_prompts is True


async def test_los_ajustes_del_repositorio_no_se_cargan_nunca():
    """`None` no es «ninguna fuente»: es **todas**, y con ellas el `CLAUDE.md`.

    Lo dice el propio SDK en `ClaudeAgentOptions.setting_sources`: «When
    ``None``, all sources are loaded (matches CLI defaults). Pass ``[]`` to
    disable filesystem settings. Must include ``"project"`` to load CLAUDE.md
    files». Y su transporte solo anade `--setting-sources` al comando cuando el
    valor **no** es `None`, asi que con `None` no se manda el flag y decide el
    defecto del CLI, que carga los ajustes del proyecto.

    Lo que costo: la primera llamada real del Entrevistador devolvio «He
    recibido y procesado el contexto completo del proyecto
    ciberpunk-storymaker». El modelo respondio sobre el repositorio en vez de
    sobre la entrevista, el esquema de salida lo rechazo -que es para lo que
    esta- y el endpoint devolvio 500.

    **Lo que este test no cubre.** Comprueba el valor que pedimos, no lo que el
    CLI hace con el: si el SDK cambiara el significado de `[]`, esto seguiria
    verde. Cubrir eso exige lanzar el binario, y entonces ya no seria un test
    -gastaria cuota y CA-4 pide que la suite corra sin red-.
    """
    consulta = ConsultaFalsa(["x"])
    await ClienteClaudeCode(consulta=consulta).completar("p", semilla=1)

    fuentes = consulta.opciones[0].setting_sources
    assert fuentes == [], f"se cargarian ajustes del repositorio: {fuentes!r}"
    assert fuentes is not None, "`None` significa «todas las fuentes», no «ninguna»"


@pytest.mark.parametrize(
    ("modelo", "entrada", "salida", "esperado"),
    [
        (MODELO_ESCRITOR, 1_000_000, 0, "1.00"),
        (MODELO_ESCRITOR, 0, 1_000_000, "5.00"),
        (MODELO_JUEZ, 1_000_000, 1_000_000, "30.00"),
        (MODELO_ESCRITOR, 0, 0, "0.00"),
    ],
)
def test_el_coste_se_deriva_de_los_tokens_y_la_tarifa(modelo, entrada, salida, esperado):
    """RF-OBS-03: con consumo de cuenta no hay cargo por llamada que leer.

    La cifra es **imputada**, y por eso tiene que salir de una tarifa escrita
    en el repositorio y de los tokens, no de una factura.
    """
    assert coste_derivado(modelo, entrada, salida) == Decimal(esperado)


def test_un_modelo_sin_tarifa_falla_en_vez_de_imputar_cero():
    """Un coste de cero por no tener tarifa es peor que un fallo: se publica."""
    assert "modelo-inventado" not in TARIFAS
    with pytest.raises(TarifaDesconocida):
        coste_derivado("modelo-inventado", 10, 10)


async def test_el_consumo_se_deriva_y_no_se_lee_del_proveedor():
    """`total_cost_usd` llega a 999 en la respuesta y **no** es lo que se guarda."""
    consulta = ConsultaFalsa(["x"], uso={"input_tokens": 2_000_000, "output_tokens": 1_000_000})
    cliente = ClienteClaudeCode(consulta=consulta)
    await cliente.completar("p", semilla=42)

    consumo = cliente.ultimo_consumo
    assert consumo is not None
    assert (consumo.tokens_entrada, consumo.tokens_salida) == (2_000_000, 1_000_000)
    assert consumo.coste_usd == Decimal("7.00")
    assert consumo.modelo == MODELO_ESCRITOR
    assert consumo.semilla == 42


async def test_una_respuesta_sin_texto_falla_en_vez_de_devolver_vacio():
    """Una cadena vacia guardada como capitulo es un fallo que nadie ve."""
    cliente = ClienteClaudeCode(consulta=ConsultaFalsa([]))
    with pytest.raises(RespuestaVacia):
        await cliente.completar("p", semilla=1)


async def test_un_fallo_de_credenciales_o_de_cuota_se_propaga_con_su_nombre():
    """Sin esto, una sesion caducada llega al manuscrito como prosa a medias."""

    class ConsultaRechazada(ConsultaFalsa):
        async def _emitir(self) -> AsyncIterator[Any]:
            yield AssistantMessage(
                content=[TextBlock(text="a medias")],
                model=MODELO_ESCRITOR,
                error="authentication_failed",
            )

    with pytest.raises(LlamadaRechazada, match="authentication_failed"):
        await ClienteClaudeCode(consulta=ConsultaRechazada(["a medias"])).completar("p", semilla=1)


# --------------------------------------------------------------------------
# P-02 · El juez no comparte modelo con quien escribio
# --------------------------------------------------------------------------


def test_el_protocolo_deja_pedir_el_modelo_en_cada_llamada():
    """`CLAUDE.md` §4 y la decision **P-02**: Haiku 4.5 escribe, Opus 5 juzga,
    «porque un juez que comparte modelo con quien escribio tiende a aprobar su
    propio estilo».

    Hasta la Fase 3 esa separacion **no se podia ni pedir**: `completar` tomaba
    prompt y semilla, el modelo lo fijaba el constructor, y ningun test podia
    caer por incumplirla. Es el patron que este proyecto lleva cazado seis
    veces -- una restriccion sobre la que nada puede fallar --, y esta vez
    estaba en una decision firmada.
    """
    assert "modelo" in inspect.signature(ClienteModelo.completar).parameters


@pytest.mark.parametrize("modelo", [MODELO_ESCRITOR, MODELO_JUEZ])
async def test_el_modelo_que_pide_quien_llama_es_el_que_viaja(modelo):
    """Y este es el test que cae si alguien vuelve a fijarlo dentro del cliente."""
    consulta = ConsultaFalsa(["x"])

    await ClienteClaudeCode(consulta=consulta).completar("p", semilla=1, modelo=modelo)

    assert consulta.opciones[0].model == modelo


async def test_sin_modelo_se_usa_el_que_declaro_el_cliente():
    """Quien ya llamaba no tiene que cambiar: el Escritor sigue por defecto."""
    consulta = ConsultaFalsa(["x"])

    await ClienteClaudeCode(consulta=consulta).completar("p", semilla=1)

    assert consulta.opciones[0].model == MODELO_ESCRITOR


async def test_el_coste_se_imputa_a_la_tarifa_del_modelo_que_de_verdad_se_uso():
    """Opus cuesta cinco veces mas que Haiku. Derivar el coste del modelo del
    constructor mientras se llama a otro imputa la cifra al modelo equivocado,
    y RF-OBS-03 la usa para comparar plantillas."""
    consulta = ConsultaFalsa(["x"], uso={"input_tokens": 1_000_000, "output_tokens": 1_000_000})
    cliente = ClienteClaudeCode(consulta=consulta)

    await cliente.completar("p", semilla=1, modelo=MODELO_JUEZ)

    consumo = cliente.ultimo_consumo
    assert consumo is not None
    assert consumo.modelo == MODELO_JUEZ
    assert consumo.coste_usd == Decimal("30.00")


async def test_los_tokens_de_cache_se_guardan_aunque_hoy_no_se_imputen():
    """P-18. El CLI **usa** cache de prompt, y `usage` trae dos campos mas que
    nadie leia: lo que el modelo lee de cache y lo que escribe en ella.

    Las cifras son las de la medicion contra el proveedor: un prompt de 5.012
    tokens devolvio `input_tokens=10` y `cache_read_input_tokens=6835`. Imputar
    solo el primero deja el coste corto por un factor de ~680.

    **Este test no arregla la imputacion y no debe.** Comprueba lo unico que no
    se puede recuperar despues: que el dato quede guardado. A que precio se
    cobra la cache es una tarifa declarada, y esa decision se toma con el dato
    ya en la tabla en vez de perder cada corrida mientras se decide.
    """
    consulta = ConsultaFalsa(
        ["x"],
        uso={
            "input_tokens": 10,
            "output_tokens": 842,
            "cache_read_input_tokens": 6835,
            "cache_creation_input_tokens": 0,
        },
    )
    cliente = ClienteClaudeCode(consulta=consulta)

    await cliente.completar("p", semilla=1)

    consumo = cliente.ultimo_consumo
    assert consumo is not None
    assert consumo.cache_read_input_tokens == 6835
    assert consumo.cache_creation_input_tokens == 0
    assert consumo.tokens_entrada == 10, "lo que ya guardaba no cambia"


async def test_sin_cache_los_campos_valen_cero_y_no_son_none():
    """El proveedor omite las claves cuando no hubo cache. Cero es una medicion
    —no hubo lectura de cache—; `None` seria «no se sabe», y la diferencia
    importa el dia que alguien sume una columna para rehacer un coste."""
    consulta = ConsultaFalsa(["x"], uso={"input_tokens": 500, "output_tokens": 100})
    cliente = ClienteClaudeCode(consulta=consulta)

    await cliente.completar("p", semilla=1)

    consumo = cliente.ultimo_consumo
    assert consumo is not None
    assert consumo.cache_read_input_tokens == 0
    assert consumo.cache_creation_input_tokens == 0


def test_obtener_cliente_modelo_ya_no_lanza_y_devuelve_el_cliente_real():
    """El hueco declarado de la Fase 1: `/respuestas` y `/cerrar` daban 500."""
    cliente = obtener_cliente_modelo()
    assert isinstance(cliente, ClienteClaudeCode)
    assert cliente.modelo == MODELO_ESCRITOR


AUDITOR = """
import os.path
import sys

violaciones = []
HOGAR = os.path.expanduser("~")
# Donde el SDK ya autenticado guarda la sesion de la cuenta. Se comparan como
# **prefijos desde el hogar**: un `.claude` en cualquier punto de la ruta casa
# tambien con el propio repositorio, que no es una credencial.
CREDENCIALES = (
    os.path.join(HOGAR, ".claude"),
    os.path.join(HOGAR, ".config", "anthropic"),
    os.path.join(HOGAR, ".anthropic"),
)


def auditor(evento, args):
    if evento in ("subprocess.Popen", "os.exec", "os.posix_spawn", "os.fork", "os.spawn"):
        violaciones.append(evento)
    elif evento in ("socket.connect", "urllib.Request"):
        violaciones.append(evento)
    elif evento == "open":
        ruta = str(args[0])
        if ruta.startswith(CREDENCIALES) or ".credentials" in os.path.basename(ruta):
            violaciones.append("open:" + ruta)


sys.addaudithook(auditor)

import app.main
from app.commons.llm.cliente import obtener_cliente_modelo

app.main.crear_app()
obtener_cliente_modelo()

print(",".join(violaciones))
"""


def test_importar_la_app_no_abre_proceso_ni_lee_credenciales():
    """El cliente real **no se instancia al importar**, y obtenerlo tampoco gasta.

    Se comprueba en un interprete aparte con un *audit hook*, porque dentro de
    la suite los modulos ya estan importados y el test no veria nada. Lo que
    abre el proceso del proveedor es `completar`, y solo `completar`.
    """
    entorno = dict(os.environ)
    entorno.pop("ANTHROPIC_API_KEY", None)
    entorno["PYTHONPATH"] = str(Path(__file__).resolve().parents[4])

    salida = subprocess.run(
        [sys.executable, "-c", AUDITOR],
        capture_output=True,
        check=False,
        text=True,
        env=entorno,
        timeout=120,
    )

    assert salida.returncode == 0, salida.stderr
    assert salida.stdout.strip() == "", salida.stdout
