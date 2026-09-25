"""R-1: **nada de lo que emite el observador puede romper una generacion.**

Es la propiedad que decide el diseno de este paquete. Una novela que se cae
porque el panel de metricas esta caido es peor que una novela sin panel: el
comprador pago por la novela, no por la telemetria.

Y la otra mitad, que es la que suele olvidarse: **la degradacion se ve**. Un
observador que se traga sus propios errores produce un panel vacio, y un panel
vacio no se distingue de un sistema que no genero nada. Por eso se cuentan.
"""

from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Any

import pytest

from app.commons.observabilidad import (
    ObservadorEnMemoria,
    Puntuacion,
    blindar,
)


class ObservadorQueSiempreLanza:
    """El peor caso: falla al abrir la traza, y todo lo de dentro tambien.

    No es un caso de laboratorio. Es exactamente lo que hace un cliente HTTP
    sin red: la primera llamada revienta y las siguientes tambien.
    """

    @asynccontextmanager
    async def traza(self, *, obra_id: int, nombre: str) -> Any:
        raise RuntimeError("Langfuse no responde")
        yield  # pragma: no cover  -- inalcanzable, y lo hace generador


async def test_un_observador_que_revienta_no_rompe_la_generacion() -> None:
    """Las operaciones fallan y **ninguna sale del blindaje**.

    Cinco fallos: abrir la traza, abrir el span, `salida`, `puntuar` y `prompt`.
    Se cuentan uno a uno en vez de marcar «hubo un fallo» porque la tasa es lo
    que dice si el observador esta medio caido o del todo.
    """
    observador = blindar(ObservadorQueSiempreLanza())

    async with (
        observador.traza(obra_id=1, nombre="generacion") as traza,
        traza.span("escritor") as span,
    ):
        span.salida("texto")
        span.puntuar(Puntuacion(nombre="extension_de_capitulo", valor=1.0))
        span.prompt("escritor", "v1", "a" * 64)

    assert observador.fallos == 5


async def test_un_observador_sano_no_cuenta_fallos_y_deja_pasar_todo() -> None:
    """El blindaje no puede ser un agujero: lo que funciona tiene que llegar."""
    dentro = ObservadorEnMemoria()
    observador = blindar(dentro)

    async with (
        observador.traza(obra_id=3, nombre="generacion") as traza,
        traza.span("escritor") as span,
    ):
        span.entrada("el paquete")
        span.salida("la prosa")
        span.consumo(
            modelo="claude-haiku-4-5",
            tokens_entrada=10,
            tokens_salida=20,
            coste_usd=Decimal("0.001"),
        )
        span.puntuar(Puntuacion(nombre="extension_de_capitulo", valor=1.0))
        span.prompt("escritor", "v1", "a" * 64)

    assert observador.fallos == 0
    (registro,) = dentro.trazas
    assert registro.spans[0].prompts == [("escritor", "v1", "a" * 64)]
    assert registro.sesion_id == "obra-3"
    assert registro.spans[0].salidas == ["la prosa"]
    assert registro.spans[0].puntuaciones[0].nombre == "extension_de_capitulo"


async def test_el_cuerpo_de_la_generacion_sigue_corriendo_con_el_observador_roto() -> None:
    """La comprobacion que de verdad importa, y que un contador no da.

    Que `fallos == 4` dice que el blindaje conto; esto dice que **el trabajo se
    hizo**. Sin este test, un `blindar` que se tragara tambien el cuerpo del
    `with` pasaria el anterior.
    """
    observador = blindar(ObservadorQueSiempreLanza())
    escrito: list[str] = []

    async with observador.traza(obra_id=1, nombre="generacion") as traza, traza.span("escritor"):
        escrito.append("el capitulo se escribio igual")

    assert escrito == ["el capitulo se escribio igual"]


async def test_un_fallo_del_cuerpo_si_sale() -> None:
    """El blindaje protege del observador, **no del codigo que envuelve**.

    Tragarse una excepcion de la generacion seria el fallo silencioso mas caro
    posible: el capitulo no se escribe y el ciclo cree que si.
    """
    observador = blindar(ObservadorEnMemoria())

    with pytest.raises(ValueError, match="fallo el escritor"):
        async with (
            observador.traza(obra_id=1, nombre="generacion") as traza,
            traza.span("escritor"),
        ):
            raise ValueError("fallo el escritor")


class _ObservadorQueNoVacia(ObservadorEnMemoria):
    """Abre y traza bien, y revienta al vaciar: Langfuse caido **al apagar**."""

    def cerrar(self) -> None:
        raise RuntimeError("Langfuse no responde al flush")


def test_un_cierre_que_revienta_no_sale_del_blindaje_y_se_cuenta() -> None:
    """Review Focus 5 del plan 8. El `flush` corre al apagar el proceso, y un
    apagado que lanza deja el servidor a medio parar por un panel de metricas."""
    observador = blindar(_ObservadorQueNoVacia())

    observador.cerrar()

    assert observador.fallos == 1


def test_un_cierre_sano_llega_al_de_dentro_y_no_cuenta_fallos() -> None:
    dentro = ObservadorEnMemoria()
    observador = blindar(dentro)

    observador.cerrar()

    assert dentro.cerrado is True
    assert observador.fallos == 0


async def test_las_credenciales_no_aparecen_en_el_repr_ni_en_los_errores() -> None:
    """RF-OBS-07 y `CLAUDE.md` §16, ultima linea.

    Un `repr()` con la clave dentro acaba en un traceback, y un traceback acaba
    en un log. La clave se lee del entorno y **no vuelve a escribirse en ningun
    sitio**.
    """
    from app.commons.observabilidad import ObservadorLangfuse

    secreta = "sk-lf-secretisima-0123456789"
    observador = ObservadorLangfuse(
        clave_publica="pk-lf-publica", clave_secreta=secreta, host="https://example.invalid"
    )

    assert secreta not in repr(observador)
    assert secreta not in str(observador)
    try:
        async with observador.traza(obra_id=1, nombre="generacion"):
            pass
    except Exception as error:  # noqa: BLE001 -- el proveedor no existe: eso es lo esperado
        assert secreta not in str(error)
        assert secreta not in repr(error)
