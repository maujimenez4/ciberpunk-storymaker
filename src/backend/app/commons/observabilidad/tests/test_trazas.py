"""El contrato: `Puntuacion`, los tres protocolos y de donde sale el observador.

Lo que se prueba aqui es la **forma** por la que van a salir todos los numeros
de la Fase 6. Si el contrato se tuerce, se tuerce once tareas a la vez.
"""

import os
from decimal import Decimal

import pytest

from app.commons.config.ajustes import Ajustes
from app.commons.observabilidad import (
    ObservadorEnMemoria,
    ObservadorLangfuse,
    ObservadorNulo,
    Puntuacion,
    obtener_observador,
)


def test_una_puntuacion_lleva_nombre_y_valor_y_es_inmutable() -> None:
    """Se llama como en `verification.md` §8.1, **sin traducir**.

    El nombre es la llave por la que se cruza el *score* con la tabla de
    validadores; traducirlo aqui rompe el cruce sin que nada falle.
    """
    puntuacion = Puntuacion(nombre="extension_de_capitulo", valor=0.8)

    assert (puntuacion.nombre, puntuacion.valor) == ("extension_de_capitulo", 0.8)
    assert puntuacion.justificacion is None
    assert puntuacion.criterio is None
    with pytest.raises(AttributeError):
        puntuacion.valor = 1.0  # type: ignore[misc]


def test_una_puntuacion_del_juez_lleva_criterio_y_justificacion() -> None:
    """R-4: una puntuacion sin justificacion se rechaza. Aqui **cabe**; que sea
    obligatoria para el juez es de T4, que tiene su propio esquema."""
    puntuacion = Puntuacion(
        nombre="voz", valor=3.0, justificacion="La voz se sostiene", criterio="voz"
    )

    assert puntuacion.justificacion == "La voz se sostiene"
    assert puntuacion.criterio == "voz"


async def test_el_observador_nulo_no_guarda_nada_y_no_se_queja() -> None:
    """Es el que corre sin credenciales, y tiene que ser indistinguible de uno
    bueno **para quien lo usa**: mismo contrato, cero efecto."""
    observador = ObservadorNulo()

    async with (
        observador.traza(obra_id=1, nombre="generacion") as traza,
        traza.span("escritor") as span,
    ):
        span.entrada("x")
        span.salida("y")
        span.consumo(modelo="m", tokens_entrada=1, tokens_salida=2, coste_usd=Decimal("0.1"))
        span.puntuar(Puntuacion(nombre="n", valor=1.0))


async def test_el_de_memoria_guarda_el_consumo_para_que_t7_lo_lea() -> None:
    """T7 saca de aqui tokens, coste y latencia. Si no se guardan, no hay nada
    que agregar despues."""
    observador = ObservadorEnMemoria()

    async with (
        observador.traza(obra_id=2, nombre="generacion") as traza,
        traza.span("escritor") as span,
    ):
        span.consumo(
            modelo="claude-haiku-4-5",
            tokens_entrada=100,
            tokens_salida=200,
            coste_usd=Decimal("0.0015"),
        )

    (consumo,) = observador.trazas[0].spans[0].consumos
    assert consumo["modelo"] == "claude-haiku-4-5"
    assert consumo["tokens_entrada"] == 100
    assert consumo["coste_usd"] == Decimal("0.0015")


_LAS_TRES = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST")


def test_sin_credenciales_se_devuelve_el_nulo_y_el_sistema_arranca(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Arrancar, avisar y generar. **No lanzar.**

    Un arranque que falla por no tener telemetria deja al comprador sin novela
    por una credencial de un panel.
    """
    for variable in (*_LAS_TRES, "LANGFUSE_BASE_URL"):
        monkeypatch.delenv(variable, raising=False)

    assert isinstance(obtener_observador(), ObservadorNulo)


@pytest.mark.parametrize("falta", ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"])
def test_con_una_credencial_a_medias_tambien_se_degrada(
    monkeypatch: pytest.MonkeyPatch, falta: str
) -> None:
    """Tres variables y **las tres hacen falta**.

    Media configuracion es el caso que se cuela: alguien pone la publica, olvida
    el host, y un cliente construido a medias falla en la primera llamada -- ya
    dentro de la generacion, no al arrancar.
    """
    for variable in _LAS_TRES:
        monkeypatch.setenv(variable, "puesta")
    monkeypatch.delenv(falta)
    # Sin esto, un `LANGFUSE_BASE_URL` en el entorno de quien corre la suite
    # rellenaria el host que falta y el caso dejaria de ser «a medias».
    monkeypatch.delenv("LANGFUSE_BASE_URL", raising=False)

    assert isinstance(obtener_observador(), ObservadorNulo)


def test_con_las_tres_credenciales_se_devuelve_uno_blindado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Y **blindado**, no el cliente a pelo: R-1 no puede depender de que quien
    lo pida se acuerde de envolverlo."""
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-x")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-x")
    monkeypatch.setenv("LANGFUSE_HOST", "https://example.invalid")

    observador = obtener_observador()

    assert not isinstance(observador, ObservadorNulo)
    assert hasattr(observador, "fallos"), "no esta blindado: no cuenta fallos"


def test_los_ajustes_leen_las_tres_del_entorno_y_de_ningun_otro_sitio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RF-OBS-07. Ni del repositorio, ni de la base de datos."""
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-y")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-y")
    monkeypatch.setenv("LANGFUSE_HOST", "https://ejemplo.invalid")

    ajustes = Ajustes.desde_entorno()

    assert ajustes.langfuse_clave_publica == "pk-lf-y"
    assert ajustes.langfuse_clave_secreta == "sk-lf-y"
    assert ajustes.langfuse_host == "https://ejemplo.invalid"
    assert "LANGFUSE_SECRET_KEY" in os.environ


def test_sin_host_el_host_sale_de_langfuse_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """`LANGFUSE_BASE_URL` es el nombre del SDK v3, y es el que trae un `.env`
    copiado del panel de Langfuse. Leyendo solo `LANGFUSE_HOST`, ese `.env`
    dejaba el observador en el nulo **sin error**: arrancaba, avisaba de que
    faltaba el host y no media nada."""
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://base.invalid")

    assert Ajustes.desde_entorno().langfuse_host == "https://base.invalid"


def test_un_host_en_blanco_no_tapa_a_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """`.env.example` trae `LANGFUSE_HOST=` vacio: quien lo copia y rellena solo
    `LANGFUSE_BASE_URL` no puede volver a caer en el nulo."""
    monkeypatch.setenv("LANGFUSE_HOST", "")
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://base.invalid")

    assert Ajustes.desde_entorno().langfuse_host == "https://base.invalid"


def test_con_los_dos_nombres_gana_langfuse_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGFUSE_HOST", "https://host.invalid")
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://base.invalid")

    assert Ajustes.desde_entorno().langfuse_host == "https://host.invalid"


def test_con_base_url_en_vez_de_host_el_observador_no_se_degrada(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """El caso del `.env` del usuario, visto desde quien decide la degradacion."""
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-x")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-x")
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://example.invalid")

    assert not isinstance(obtener_observador(), ObservadorNulo)


def test_el_observador_de_langfuse_traduce_la_obra_a_sesion() -> None:
    """Lo unico que traduce: `obra_id` -> `session_id`. Nada mas.

    Cuanto menos haga este adaptador, menos hay que volver a pensar el dia que
    el proveedor cambie de forma.
    """
    assert ObservadorLangfuse.sesion_de(7) == "obra-7"
    assert ObservadorLangfuse.sesion_de(7) == ObservadorEnMemoria.sesion_de(7)
