"""Plan 8, T6: el Critico arranca a la vez que el Continuista, **contado**.

P-21 midio ~8 minutos por capitulo con los dos jueces en serie, y el Critico no
usa lo que dice el Continuista ni decide nada (`RF-JUZ-06`). Asi que se solapan
dentro del techo concurrente (`CLAUDE.md` §4.1), con sus tokens pedidos al
portero y nunca por fuera.

**Como se sincroniza.** Igual que `commons/jobs/tests/test_turnos.py`: con
`asyncio.Event` y sin `sleep`. El Continuista de estos tests **no termina hasta
que el Critico ha empezado**, asi que en serie el ciclo se cuelga; `GUARDA`
convierte ese cuelgue en un `TimeoutError` en vez de bloquear la suite.

Y lo que cubre Review Focus 4: con el techo lleno, el Critico **no espera turno
reteniendo el suyo** --eso es el interbloqueo de dos obras-- sino que se juzga
despues, en serie, como hasta hoy.
"""

import asyncio
from typing import Any

import pytest

from app.commons.jobs.turnos import SOBRECARGA_POR_LLAMADA, PresupuestoConcurrente
from app.commons.llm.doble import DobleDeterminista
from app.commons.observabilidad import Observacion, TrazaEnMemoria
from app.features.calidad import (
    CapituloAContrastar,
    CapituloAJuzgar,
    Juicio,
    PuntuacionDelCritico,
    RangoDeExtension,
    RevisionDeContinuidad,
    SalidaMalFormada,
    rubrica_vigente,
)
from app.features.contexto import ContextoDelCapitulo, ensamblar_capitulo
from app.features.escena import RestriccionesDeDiscurso
from app.features.escritura.agents import Escritor
from app.features.escritura.service import Escritura, escribir_capitulo
from app.features.escritura.tests.test_ciclo import obra_lista  # noqa: F401  (fixture)
from app.features.obra.modelos import HechoCanon

GUARDA = 2.0

PROSA = (
    "Marta cerró la puerta del taller y se quedó quieta un momento. "
    "Estaba cansada y no dijo nada más aquella tarde de octubre, "
    "cuando la lluvia empezaba a golpear los cristales del puerto."
)


class _ContadorDePalabras:
    def contar(self, texto: str) -> int:
        return len(texto.split())


class _Continuista:
    """Anota cuando empieza y cuando acaba. Con `esperar_al_critico`, no acaba
    hasta que el Critico ha empezado: es lo que hace del solape un hecho
    comprobable y no una casualidad de temporizacion."""

    def __init__(self, registro: list[str], critico_empezo: asyncio.Event, *, esperar: bool):
        self._registro = registro
        self._critico_empezo = critico_empezo
        self._esperar = esperar

    async def revisar(self, capitulo: CapituloAContrastar) -> RevisionDeContinuidad:
        self._registro.append("continuista:inicio")
        if self._esperar:
            await self._critico_empezo.wait()
        self._registro.append("continuista:fin")
        return RevisionDeContinuidad(defectos=(), mal_formados=())


class _Critico:
    """Anota, avisa de que ha empezado y mira el portero mientras juzga."""

    def __init__(
        self,
        registro: list[str],
        empezo: asyncio.Event,
        presupuesto: PresupuestoConcurrente | None = None,
        *,
        fallar: bool = False,
    ):
        self._registro = registro
        self._empezo = empezo
        self._presupuesto = presupuesto
        self._fallar = fallar
        self.tokens_en_vuelo_al_juzgar: int | None = None

    @property
    def rubrica(self) -> Any:
        return rubrica_vigente()

    async def juzgar(self, capitulo: CapituloAJuzgar) -> Juicio:
        self._registro.append("critico:inicio")
        self._empezo.set()
        if self._presupuesto is not None:
            self.tokens_en_vuelo_al_juzgar = self._presupuesto.tokens_en_vuelo
        # Cede el turno una vez: un juez de verdad espera al modelo, y sin esto
        # el doble acabaria antes de que nadie pudiera solaparse con el.
        await asyncio.sleep(0)
        self._registro.append("critico:fin")
        if self._fallar:
            raise SalidaMalFormada("no es JSON")
        return Juicio(
            puntuaciones=[
                PuntuacionDelCritico(criterio=c.nombre, valor=3, justificacion="se sostiene")
                for c in rubrica_vigente().criterios
            ]
        )


async def _contexto(sesion: Any, obra_con_outline: Any) -> ContextoDelCapitulo:
    # Sin un hecho, la capa de canon llega vacia y el ensamblado falla con
    # `CapaVacia`: es la misma preparacion que `test_continuista_en_el_ciclo.py`.
    sesion.add(
        HechoCanon(
            obra_id=obra_con_outline.obra.id,
            entidad="Nadia",
            atributo="oficio",
            valor="botanica",
            origen="escena",
            escena_de_origen=str(obra_con_outline.escena.id),
        )
    )
    await sesion.flush()
    return await ensamblar_capitulo(sesion, obra_con_outline.capitulos[0].id, _ContadorDePalabras())


async def _escribir(
    sesion: Any,
    contexto: ContextoDelCapitulo,
    continuista: _Continuista,
    critico: _Critico,
    presupuesto: PresupuestoConcurrente | None,
    observacion: Observacion | None = None,
) -> Escritura:
    return await escribir_capitulo(
        sesion,
        Escritor(DobleDeterminista({"ESCRITOR · v2": PROSA})),
        contexto=contexto,
        contador=_ContadorDePalabras(),
        run_id="run-t6",
        modelo="doble",
        restricciones=RestriccionesDeDiscurso(
            persona="3ª limitada", tiempo_verbal="pasado", nivel_de_calor=2
        ),
        rango_de_extension=RangoDeExtension(minimo=1, maximo=10_000),
        continuista=continuista,  # type: ignore[arg-type]
        critico=critico,  # type: ignore[arg-type]
        presupuesto=presupuesto,
        observacion=observacion,
    )


# --- Paso 1: el solape ---------------------------------------------------------


async def test_el_critico_empieza_antes_de_que_el_continuista_termine(sesion, obra_con_outline):
    """En serie esto **se cuelga**: el Continuista espera a un Critico que solo
    arrancaria cuando el Continuista acabase."""
    contexto = await _contexto(sesion, obra_con_outline)
    registro: list[str] = []
    empezo = asyncio.Event()
    presupuesto = PresupuestoConcurrente()

    escritura = await asyncio.wait_for(
        _escribir(
            sesion,
            contexto,
            _Continuista(registro, empezo, esperar=True),
            _Critico(registro, empezo),
            presupuesto,
        ),
        GUARDA,
    )

    assert escritura.aprobado
    assert escritura.juicio is not None
    assert registro.index("critico:inicio") < registro.index("continuista:fin")


async def test_el_critico_en_paralelo_pide_sus_tokens_al_portero(sesion, obra_con_outline):
    """«Contados»: mientras juzga, su prompt y la sobrecarga del CLI estan en
    vuelo; al terminar, el portero vuelve a cero. Un paralelo que no pidiera
    turno cumpliria el techo por casualidad, que es lo que §4.1 prohibe."""
    contexto = await _contexto(sesion, obra_con_outline)
    registro: list[str] = []
    empezo = asyncio.Event()
    presupuesto = PresupuestoConcurrente()
    critico = _Critico(registro, empezo, presupuesto)

    await asyncio.wait_for(
        _escribir(
            sesion,
            contexto,
            _Continuista(registro, empezo, esperar=True),
            critico,
            presupuesto,
        ),
        GUARDA,
    )

    assert critico.tokens_en_vuelo_al_juzgar is not None
    assert critico.tokens_en_vuelo_al_juzgar > SOBRECARGA_POR_LLAMADA
    assert presupuesto.tokens_en_vuelo == 0
    assert presupuesto.llamadas_en_vuelo == 0


# --- Paso 2: sin interbloqueo (Review Focus 4) --------------------------------


async def test_si_el_critico_no_cabe_se_juzga_despues_y_sin_esperar_turno(sesion, obra_con_outline):
    """El paquete ya en vuelo deja un token libre: el Critico no cabe. Esperar
    turno aqui, reteniendo el del capitulo, es el interbloqueo de dos obras con
    los jueces en paralelo. Lo correcto es juzgar despues, en serie."""
    contexto = await _contexto(sesion, obra_con_outline)
    registro: list[str] = []
    empezo = asyncio.Event()
    presupuesto = PresupuestoConcurrente(techo=100_000)

    async with presupuesto.turno(presupuesto.techo - 1, paso="el capitulo ya en vuelo"):
        escritura = await asyncio.wait_for(
            _escribir(
                sesion,
                contexto,
                _Continuista(registro, empezo, esperar=False),
                _Critico(registro, empezo, presupuesto),
                presupuesto,
            ),
            GUARDA,
        )
        assert presupuesto.tokens_en_vuelo == presupuesto.techo - 1

    assert escritura.aprobado
    assert registro == ["continuista:inicio", "continuista:fin", "critico:inicio", "critico:fin"]


async def test_el_critico_no_se_cuela_por_delante_de_quien_ya_espera_turno(
    sesion, obra_con_outline
):
    """FIFO estricto (`turnos.py`): con alguien en la cola, el Critico no pasa
    aunque quepa. Se juzga en serie y quien esperaba sigue esperando."""
    contexto = await _contexto(sesion, obra_con_outline)
    registro: list[str] = []
    empezo = asyncio.Event()
    presupuesto = PresupuestoConcurrente(techo=100_000)
    en_cola = asyncio.Event()

    async def _otra_obra() -> None:
        en_cola.set()
        async with presupuesto.turno(60_000, paso="otra obra"):
            pass

    async with presupuesto.turno(50_000, paso="el capitulo ya en vuelo"):
        otra = asyncio.create_task(_otra_obra())
        await asyncio.wait_for(en_cola.wait(), GUARDA)
        await asyncio.sleep(0)
        escritura = await asyncio.wait_for(
            _escribir(
                sesion,
                contexto,
                _Continuista(registro, empezo, esperar=False),
                _Critico(registro, empezo, presupuesto),
                presupuesto,
            ),
            GUARDA,
        )
        assert not otra.done()

    await asyncio.wait_for(otra, GUARDA)
    assert escritura.aprobado
    assert registro.index("continuista:fin") < registro.index("critico:inicio")


async def test_sin_presupuesto_el_orden_es_el_de_siempre(sesion, obra_con_outline):
    """Quien llama a `escribir_capitulo` sin portero no tiene con que contar el
    paralelo, y no se le inventa uno: en serie, como antes del plan 8."""
    contexto = await _contexto(sesion, obra_con_outline)
    registro: list[str] = []
    empezo = asyncio.Event()

    await asyncio.wait_for(
        _escribir(
            sesion,
            contexto,
            _Continuista(registro, empezo, esperar=False),
            _Critico(registro, empezo),
            None,
        ),
        GUARDA,
    )

    assert registro == ["continuista:inicio", "continuista:fin", "critico:inicio", "critico:fin"]


# --- La juntura: el ciclo le pasa el portero ------------------------------------


class _PresupuestoQueAnota(PresupuestoConcurrente):
    """El portero de siempre, que ademas anota para que paso se le pidio turno."""

    def __init__(self) -> None:
        super().__init__()
        self.pasos: list[str] = []

    def turno(self, tokens: int, *, espera_maxima: float | None = None, paso: str = "") -> Any:
        self.pasos.append(paso)
        return super().turno(tokens, espera_maxima=espera_maxima, paso=paso)


async def test_el_ciclo_de_verdad_lanza_al_critico_en_paralelo(sesion, obra_lista):  # noqa: F811
    """Sin esto el paralelo podria estar escrito, probado y sin correr: basta con
    que `ciclo._escribir` no pase el portero, y todo lo de arriba seguiria verde.
    Con el techo real (100.000) y un paquete normal, el turno del Critico cabe."""
    from app.commons.jobs.turnos import CerrojoDeEscena
    from app.commons.observabilidad import ObservadorEnMemoria
    from app.features.escritura.ciclo import abrir_trabajo, ejecutar_ciclo
    from app.features.escritura.tests.test_ciclo import ContadorDePalabras
    from app.features.escritura.tests.test_observabilidad_del_ciclo import _agentes

    capitulo_id = obra_lista.capitulos[1].id
    presupuesto = _PresupuestoQueAnota()
    trabajo = await abrir_trabajo(sesion, capitulo_id=capitulo_id)

    resultado = await ejecutar_ciclo(
        sesion,
        trabajo,
        capitulo_id=capitulo_id,
        agentes=_agentes(),
        contador=ContadorDePalabras(),
        presupuesto=presupuesto,
        cerrojo=CerrojoDeEscena(),
        observador=ObservadorEnMemoria(),
    )

    assert resultado.estado == "INTEGRADA"
    assert "critico en paralelo" in presupuesto.pasos
    assert presupuesto.tokens_en_vuelo == 0


# --- Paso 5: un Critico que falla no tumba el intento --------------------------


@pytest.mark.parametrize("en_paralelo", [True, False])
async def test_un_critico_que_devuelve_basura_no_tumba_el_capitulo(
    sesion, obra_con_outline, en_paralelo: bool
):
    """El juez no decide (`RF-JUZ-06`), asi que su fallo tampoco puede decidir.
    Y vale **igual en serie**: si no, que el capitulo se caiga dependeria de si
    el techo tenia hueco en ese instante, que no es algo que nadie elija."""
    contexto = await _contexto(sesion, obra_con_outline)
    registro: list[str] = []
    empezo = asyncio.Event()
    presupuesto = PresupuestoConcurrente() if en_paralelo else None
    traza = TrazaEnMemoria(sesion_id="obra-1", nombre="capitulo 1")

    escritura = await asyncio.wait_for(
        _escribir(
            sesion,
            contexto,
            _Continuista(registro, empezo, esperar=en_paralelo),
            _Critico(registro, empezo, fallar=True),
            presupuesto,
            Observacion(traza=traza),
        ),
        GUARDA,
    )

    assert escritura.aprobado
    assert escritura.juicio is None
    [span] = [s for s in traza.spans if s.nombre == "critico"]
    assert any("SalidaMalFormada" in salida for salida in span.salidas)
    if presupuesto is not None:
        assert presupuesto.tokens_en_vuelo == 0
