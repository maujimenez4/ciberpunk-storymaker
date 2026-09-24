"""El techo concurrente: se da turno contando tokens, no llamadas.

Cierra RF-ORQ-08, RF-ORQ-10 y CA-36. Aqui no se llama a ningun modelo: se
prueba **el portero**, no lo que pasa al otro lado.

**Como se sincroniza, porque importa mas que en otros tests.** Un test de
concurrencia que pasa por casualidad de temporizacion no prueba nada, asi que
ningun test de este fichero usa `sleep` para ordenar nada. Se usan dos cosas:

1. `asyncio.Event`, que da un orden **causal**: cuando el test vuelve de
   `pidiendo.wait()`, la tarea que lo activo ya ha llegado a su siguiente
   suspension —o sea, ya esta en la cola de turnos—, porque un `set()` no
   devuelve el control al test hasta que quien lo activo se suspende.
2. El **contador en vuelo**, que es observable a proposito: la reserva se hace
   en el instante en que se concede el turno, no cuando la tarea despierta.
   Por eso `tokens_en_vuelo` responde sobre quien tiene turno **sin** depender
   de que ninguna tarea haya llegado a ejecutarse.

`GUARDA` es lo unico que mira el reloj, y no sincroniza: es el plazo tras el
cual un test que se ha colgado se da por fallado en vez de bloquear la suite.
"""

import asyncio

import pytest

from app.commons.domain.errores import ErrorDeDominio, TiempoAgotado
from app.commons.jobs.turnos import TECHO_CONCURRENTE, CerrojoDeEscena, PresupuestoConcurrente

GUARDA = 5.0


async def _ocupar(
    presupuesto: PresupuestoConcurrente,
    tokens: int,
    pidiendo: asyncio.Event,
    dentro: asyncio.Event,
    soltar: asyncio.Event,
) -> None:
    """Pide turno para `tokens` y lo retiene hasta que el test active `soltar`."""
    pidiendo.set()
    async with presupuesto.turno(tokens):
        dentro.set()
        await soltar.wait()


async def _escena(
    cerrojo: CerrojoDeEscena,
    obra_id: int,
    pidiendo: asyncio.Event,
    dentro: asyncio.Event,
    soltar: asyncio.Event,
) -> None:
    pidiendo.set()
    async with cerrojo.por_obra(obra_id):
        dentro.set()
        await soltar.wait()


def _eventos(cuantos: int) -> list[asyncio.Event]:
    return [asyncio.Event() for _ in range(cuantos)]


async def _esperar(*esperas: asyncio.Event) -> None:
    """Espera a que todos los eventos se activen, o falla en vez de colgarse."""
    await asyncio.wait_for(asyncio.gather(*(e.wait() for e in esperas)), GUARDA)


# --- El techo es el del encargo, y la excepcion es de dominio ---------------


def test_el_techo_concurrente_es_el_del_encargo():
    assert TECHO_CONCURRENTE == 100_000


def test_tiempo_agotado_es_un_error_de_dominio():
    assert issubclass(TiempoAgotado, ErrorDeDominio)


# --- El contador en vuelo es observable, no implicito -----------------------


async def test_el_contador_en_vuelo_es_observable():
    presupuesto = PresupuestoConcurrente()
    assert presupuesto.tokens_en_vuelo == 0
    assert presupuesto.llamadas_en_vuelo == 0

    async with presupuesto.turno(30_000):
        assert presupuesto.tokens_en_vuelo == 30_000
        assert presupuesto.llamadas_en_vuelo == 1

    assert presupuesto.tokens_en_vuelo == 0
    assert presupuesto.llamadas_en_vuelo == 0


async def test_el_turno_se_devuelve_aunque_la_llamada_falle():
    presupuesto = PresupuestoConcurrente()

    with pytest.raises(RuntimeError):
        async with presupuesto.turno(30_000):
            raise RuntimeError("el proveedor se cayo a mitad")

    assert presupuesto.tokens_en_vuelo == 0
    assert presupuesto.llamadas_en_vuelo == 0


# --- Se cuentan tokens, no llamadas ----------------------------------------


async def test_tres_paquetes_pequenos_se_solapan_porque_no_se_cuentan_llamadas():
    """Con 30.000 cada uno caben tres a la vez: el turno no es un contador de llamadas.

    Este test y el siguiente son el par que distingue de verdad. Ningun limite
    expresado en numero de llamadas pasa los dos: uno de 1 o 2 falla aqui, y
    uno de 3 o mas falla en el siguiente.
    """
    presupuesto = PresupuestoConcurrente()
    pidiendo, dentro, soltar = _eventos(3), _eventos(3), _eventos(3)
    tareas = [
        asyncio.create_task(_ocupar(presupuesto, 30_000, pidiendo[i], dentro[i], soltar[i]))
        for i in range(3)
    ]

    await _esperar(*dentro)
    assert presupuesto.llamadas_en_vuelo == 3
    assert presupuesto.tokens_en_vuelo == 90_000

    for evento in soltar:
        evento.set()
    await asyncio.wait_for(asyncio.gather(*tareas), GUARDA)
    assert presupuesto.tokens_en_vuelo == 0


async def test_dos_paquetes_que_suman_mas_del_techo_no_se_solapan():
    """R-4, primera mitad: 50.001 + 50.000 no caben, y el segundo **espera**.

    Esperar, no recortar y no lanzarse igualmente: el paquete del segundo sigue
    intacto y sus tokens no entran en vuelo hasta que el primero libera.
    """
    presupuesto = PresupuestoConcurrente()
    pidiendo, dentro, soltar = _eventos(2), _eventos(2), _eventos(2)

    primera = asyncio.create_task(_ocupar(presupuesto, 50_001, pidiendo[0], dentro[0], soltar[0]))
    await _esperar(dentro[0])

    segunda = asyncio.create_task(_ocupar(presupuesto, 50_000, pidiendo[1], dentro[1], soltar[1]))
    await _esperar(pidiendo[1])

    assert not dentro[1].is_set()
    assert presupuesto.llamadas_en_vuelo == 1
    assert presupuesto.tokens_en_vuelo == 50_001

    soltar[0].set()
    await asyncio.wait_for(primera, GUARDA)
    await _esperar(dentro[1])
    assert presupuesto.tokens_en_vuelo == 50_000

    soltar[1].set()
    await asyncio.wait_for(segunda, GUARDA)
    assert presupuesto.tokens_en_vuelo == 0


async def test_dos_paquetes_que_suman_menos_del_techo_si_se_solapan():
    """R-4, segunda mitad: la que de verdad distingue.

    Un sistema que serializa todo cumple el techo y **no** cumple P-06.
    """
    presupuesto = PresupuestoConcurrente()
    pidiendo, dentro, soltar = _eventos(2), _eventos(2), _eventos(2)

    tareas = [
        asyncio.create_task(_ocupar(presupuesto, tokens, pidiendo[i], dentro[i], soltar[i]))
        for i, tokens in enumerate((40_000, 50_000))
    ]

    await _esperar(*dentro)
    assert presupuesto.llamadas_en_vuelo == 2
    assert presupuesto.tokens_en_vuelo == 90_000

    for evento in soltar:
        evento.set()
    await asyncio.wait_for(asyncio.gather(*tareas), GUARDA)


async def test_la_suma_exacta_del_techo_cabe():
    """El techo es «no mas de», no «menos de»: 50.000 + 50.000 se solapan."""
    presupuesto = PresupuestoConcurrente()
    pidiendo, dentro, soltar = _eventos(2), _eventos(2), _eventos(2)

    tareas = [
        asyncio.create_task(_ocupar(presupuesto, 50_000, pidiendo[i], dentro[i], soltar[i]))
        for i in range(2)
    ]

    await _esperar(*dentro)
    assert presupuesto.tokens_en_vuelo == TECHO_CONCURRENTE

    for evento in soltar:
        evento.set()
    await asyncio.wait_for(asyncio.gather(*tareas), GUARDA)


async def test_el_que_espera_arranca_en_cuanto_el_primero_libera():
    """Sin sondeo: al devolver el turno se sirve la cola en el acto.

    La reserva del segundo esta hecha **antes** de que su tarea despierte, que
    es lo que hace observable el traspaso.
    """
    presupuesto = PresupuestoConcurrente()
    pidiendo, dentro, soltar = _eventos(2), _eventos(2), _eventos(2)

    primera = asyncio.create_task(_ocupar(presupuesto, 80_000, pidiendo[0], dentro[0], soltar[0]))
    await _esperar(dentro[0])
    segunda = asyncio.create_task(_ocupar(presupuesto, 80_000, pidiendo[1], dentro[1], soltar[1]))
    await _esperar(pidiendo[1])

    soltar[0].set()
    await asyncio.wait_for(primera, GUARDA)
    assert presupuesto.tokens_en_vuelo == 80_000
    assert presupuesto.llamadas_en_vuelo == 1

    soltar[1].set()
    await asyncio.wait_for(segunda, GUARDA)


# --- Sin turno antes del plazo: TiempoAgotado, y sin coste -----------------


async def test_sin_turno_antes_del_plazo_se_lanza_tiempo_agotado():
    presupuesto = PresupuestoConcurrente()
    pidiendo, dentro, soltar = _eventos(1), _eventos(1), _eventos(1)
    ocupante = asyncio.create_task(
        _ocupar(presupuesto, TECHO_CONCURRENTE, pidiendo[0], dentro[0], soltar[0])
    )
    await _esperar(dentro[0])

    with pytest.raises(TiempoAgotado) as vencido:
        async with presupuesto.turno(1, espera_maxima=0, paso="escritura del capitulo 3"):
            pytest.fail("no debia concederse el turno")

    assert vencido.value.paso == "escritura del capitulo 3"

    # Sin coste: el ocupante sigue siendo el unico en vuelo y nada se reservo
    # para quien no llego a entrar.
    assert presupuesto.llamadas_en_vuelo == 1
    assert presupuesto.tokens_en_vuelo == TECHO_CONCURRENTE

    soltar[0].set()
    await asyncio.wait_for(ocupante, GUARDA)
    assert presupuesto.tokens_en_vuelo == 0
    assert presupuesto.llamadas_en_vuelo == 0


async def test_la_espera_vencida_no_deja_reserva_fantasma():
    """Quien se cansa de esperar sale de la cola: no ocupa sitio ni lo bloquea."""
    presupuesto = PresupuestoConcurrente()
    pidiendo, dentro, soltar = _eventos(1), _eventos(1), _eventos(1)
    ocupante = asyncio.create_task(_ocupar(presupuesto, 90_000, pidiendo[0], dentro[0], soltar[0]))
    await _esperar(dentro[0])

    with pytest.raises(TiempoAgotado):
        async with presupuesto.turno(20_000, espera_maxima=0):
            pytest.fail("no debia concederse el turno")

    soltar[0].set()
    await asyncio.wait_for(ocupante, GUARDA)

    # La cola quedo limpia: un paquete que cabe entra sin esperar a nadie.
    async with presupuesto.turno(20_000, espera_maxima=0):
        assert presupuesto.tokens_en_vuelo == 20_000


async def test_un_paquete_mayor_que_el_techo_no_espera_para_siempre():
    """No cabe ni con el sistema vacio: es un fallo de programa, no una espera.

    El techo **por llamada** lo comprueba el ensamblador (RF-CTX-03) y lanza
    `ContextBudgetExceeded` antes de llegar aqui. Que el portero se quede
    esperando un turno imposible seria colgar el proceso en silencio.
    """
    presupuesto = PresupuestoConcurrente()
    with pytest.raises(ValueError):
        async with presupuesto.turno(TECHO_CONCURRENTE + 1):
            pytest.fail("no debia concederse el turno")
    assert presupuesto.tokens_en_vuelo == 0


# --- RF-ORQ-08: una escena en vuelo por obra -------------------------------


async def test_una_escena_en_vuelo_por_obra():
    cerrojo = CerrojoDeEscena()
    pidiendo, dentro, soltar = _eventos(2), _eventos(2), _eventos(2)

    primera = asyncio.create_task(_escena(cerrojo, 7, pidiendo[0], dentro[0], soltar[0]))
    await _esperar(dentro[0])
    segunda = asyncio.create_task(_escena(cerrojo, 7, pidiendo[1], dentro[1], soltar[1]))
    await _esperar(pidiendo[1])

    assert not dentro[1].is_set()
    assert cerrojo.obras_en_vuelo == frozenset({7})

    soltar[0].set()
    await asyncio.wait_for(primera, GUARDA)
    await _esperar(dentro[1])

    soltar[1].set()
    await asyncio.wait_for(segunda, GUARDA)
    assert cerrojo.obras_en_vuelo == frozenset()


async def test_escenas_de_obras_distintas_si_se_solapan():
    cerrojo = CerrojoDeEscena()
    pidiendo, dentro, soltar = _eventos(2), _eventos(2), _eventos(2)

    tareas = [
        asyncio.create_task(_escena(cerrojo, obra_id, pidiendo[i], dentro[i], soltar[i]))
        for i, obra_id in enumerate((7, 8))
    ]

    await _esperar(*dentro)
    assert cerrojo.obras_en_vuelo == frozenset({7, 8})

    for evento in soltar:
        evento.set()
    await asyncio.wait_for(asyncio.gather(*tareas), GUARDA)


async def test_continuista_y_critico_del_mismo_capitulo_se_solapan():
    """El cerrojo es de **escena**, no de llamada: dentro de una escena caben dos.

    Los dos reciben la misma prosa y no se leen entre si, asi que solaparlos es
    lo que P-06 compra en cada capitulo.
    """
    cerrojo = CerrojoDeEscena()
    presupuesto = PresupuestoConcurrente()
    pidiendo, dentro, soltar = _eventos(2), _eventos(2), _eventos(2)

    async with cerrojo.por_obra(7):
        tareas = [
            asyncio.create_task(_ocupar(presupuesto, 20_000, pidiendo[i], dentro[i], soltar[i]))
            for i in range(2)
        ]
        await _esperar(*dentro)
        assert presupuesto.llamadas_en_vuelo == 2
        assert presupuesto.tokens_en_vuelo == 40_000

        for evento in soltar:
            evento.set()
        await asyncio.wait_for(asyncio.gather(*tareas), GUARDA)


async def test_la_espera_del_cerrojo_tambien_tiene_plazo():
    cerrojo = CerrojoDeEscena()
    pidiendo, dentro, soltar = _eventos(1), _eventos(1), _eventos(1)
    primera = asyncio.create_task(_escena(cerrojo, 7, pidiendo[0], dentro[0], soltar[0]))
    await _esperar(dentro[0])

    with pytest.raises(TiempoAgotado):
        async with cerrojo.por_obra(7, espera_maxima=0):
            pytest.fail("no debia concederse el cerrojo")

    assert cerrojo.obras_en_vuelo == frozenset({7})

    soltar[0].set()
    await asyncio.wait_for(primera, GUARDA)
    assert cerrojo.obras_en_vuelo == frozenset()
