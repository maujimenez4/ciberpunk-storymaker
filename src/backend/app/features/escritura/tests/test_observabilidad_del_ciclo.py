"""`CLAUDE.md` §4.3 en el camino que escribe la novela, no en el modulo suelto.

El observador estaba escrito y probado y **no lo llamaba nadie**: ni un router,
ni un servicio, ni `main.py`. Es la familia de fallo de `RELEVO.md` —la pieza
existe, sus tests pasan y en produccion no corre—, y por eso lo que se prueba
aqui es el ciclo **de verdad**: una traza por capitulo en la sesion de la obra,
un span por rol que se llamo, con su prompt, y los *scores* de G1a, de la policy
y del juez en el span del validador que los produjo.

El ultimo bloque va por HTTP, que es lo unico que prueba que el router inyecta
el observador y envuelve el cliente: un test que monta los roles a mano pasaria
aunque el router no hiciera nada.

Sin red y sin modelo (`CA-4`): el cliente es `DobleDeterminista` y el
observador, `ObservadorEnMemoria`.
"""

from typing import Any

import pytest
from sqlalchemy import select

from app.commons.jobs.turnos import CerrojoDeEscena, PresupuestoConcurrente
from app.commons.llm.doble import DobleDeterminista
from app.commons.observabilidad import (
    ClienteObservado,
    ObservadorEnMemoria,
    TrazaEnMemoria,
    blindar,
    sesion_de,
)
from app.features.calidad import Continuista, Critico, rubrica_vigente
from app.features.canon import Extractor
from app.features.escena import Planificador
from app.features.escritura import Escritor
from app.features.escritura.ciclo import Agentes, abrir_trabajo, ejecutar_ciclo
from app.features.escritura.tests.test_ciclo import (
    PROSA_BUENA,
    PROSA_CORTA,
    ContadorDePalabras,
    _respuestas,
    obra_lista,  # noqa: F401  (fixture)
)
from app.features.outline.modelos import Capitulo

ROLES_DE_UN_CAPITULO_LIMPIO = [
    "planificador",
    "ensamblador",
    "escritor",
    "policy",
    "continuista",
    "puerta_g1a",
    "critico",
    "extractor",
]


def _agentes(prosa: str = PROSA_BUENA) -> Agentes:
    """Los cinco roles sobre **un** cliente observado, como los compone el router."""
    observado = ClienteObservado(DobleDeterminista(_respuestas(prosa)))
    return Agentes(
        planificador=Planificador(observado),
        escritor=Escritor(observado),
        extractor=Extractor(observado),
        continuista=Continuista(observado),
        critico=Critico(observado, rubrica_vigente()),
        observado=observado,
    )


async def _ciclo(sesion: Any, capitulo_id: int, observador: Any, prosa: str = PROSA_BUENA) -> Any:
    trabajo = await abrir_trabajo(sesion, capitulo_id=capitulo_id)
    return await ejecutar_ciclo(
        sesion,
        trabajo,
        capitulo_id=capitulo_id,
        agentes=_agentes(prosa),
        contador=ContadorDePalabras(),
        presupuesto=PresupuestoConcurrente(),
        cerrojo=CerrojoDeEscena(),
        observador=observador,
    )


def _span(traza: TrazaEnMemoria, nombre: str) -> Any:
    [span] = [s for s in traza.spans if s.nombre == nombre]
    return span


# --- Una traza por capitulo, en la sesion de la obra --------------------------


async def test_un_capitulo_abre_una_traza_en_la_sesion_de_su_obra(sesion, obra_lista):  # noqa: F811
    observador = ObservadorEnMemoria()

    await _ciclo(sesion, obra_lista.capitulos[0].id, observador)

    [traza] = observador.trazas
    assert traza.sesion_id == sesion_de(obra_lista.obra.id)
    assert traza.nombre.startswith("capitulo 1")


async def test_cada_rol_que_se_llama_tiene_su_span_en_orden(sesion, obra_lista):  # noqa: F811
    observador = ObservadorEnMemoria()

    resultado = await _ciclo(sesion, obra_lista.capitulos[1].id, observador)

    assert resultado.estado == "INTEGRADA"
    assert [s.nombre for s in observador.trazas[0].spans] == ROLES_DE_UN_CAPITULO_LIMPIO


async def test_el_span_de_cada_rol_lleva_su_prompt_y_su_salida(sesion, obra_lista):  # noqa: F811
    """El prompt **renderizado**: el de la plantilla con el paquete dentro, no
    un resumen. Es lo que el *tuning* del encargo necesita ver."""
    observador = ObservadorEnMemoria()

    await _ciclo(sesion, obra_lista.capitulos[1].id, observador)

    traza = observador.trazas[0]
    escritor = _span(traza, "escritor")
    assert len(escritor.entradas) == 1
    assert "ESCRITOR · v1" in escritor.entradas[0]
    assert escritor.salidas == [PROSA_BUENA]
    for rol, marca in (
        ("planificador", "PLANIFICADOR DE ESCENA"),
        ("continuista", "# Continuista"),
        ("critico", "# Crítico"),
        ("extractor", "# Extractor"),
    ):
        span = _span(traza, rol)
        assert span.entradas, rol
        assert marca in span.entradas[0], rol
        assert span.salidas, rol


async def test_el_ensamblador_deja_el_desglose_por_capa(sesion, obra_lista):  # noqa: F811
    observador = ObservadorEnMemoria()

    await _ciclo(sesion, obra_lista.capitulos[1].id, observador)

    [salida] = _span(observador.trazas[0], "ensamblador").salidas
    assert "canon" in salida


# --- Los scores, en el span del validador que los produjo --------------------


async def test_la_puerta_g1a_puntua_cada_validador_que_corrio(sesion, obra_lista):  # noqa: F811
    observador = ObservadorEnMemoria()

    await _ciclo(sesion, obra_lista.capitulos[1].id, observador)

    puntuaciones = _span(observador.trazas[0], "puerta_g1a").puntuaciones
    nombres = {p.nombre for p in puntuaciones}
    assert {"extension_de_capitulo", "discurso", "continuidad_y_canon"} <= nombres
    assert all(p.valor == 1.0 for p in puntuaciones)


async def test_un_capitulo_rechazado_puntua_cero_en_el_validador_que_lo_rechazo(
    sesion,
    obra_lista,  # noqa: F811
):
    """Tres vueltas, tres spans del Escritor, y el cero donde fallo. Y **sin
    Extractor**: un capitulo que no entra no escribe memoria (R-7)."""
    observador = ObservadorEnMemoria()

    resultado = await _ciclo(sesion, obra_lista.capitulos[0].id, observador, prosa=PROSA_CORTA)

    assert resultado.estado == "ESCALADA"
    traza = observador.trazas[0]
    assert [s.nombre for s in traza.spans].count("escritor") == 3
    assert "extractor" not in [s.nombre for s in traza.spans]
    ultima_puerta = [s for s in traza.spans if s.nombre == "puerta_g1a"][-1]
    valores = {p.nombre: p.valor for p in ultima_puerta.puntuaciones}
    assert valores["extension_de_capitulo"] == 0.0


async def test_la_policy_puntua_palabras_vetadas(sesion, obra_lista):  # noqa: F811
    observador = ObservadorEnMemoria()

    await _ciclo(sesion, obra_lista.capitulos[1].id, observador)

    [puntuacion] = _span(observador.trazas[0], "policy").puntuaciones
    assert (puntuacion.nombre, puntuacion.valor) == ("palabras_vetadas", 1.0)


async def test_el_juez_puntua_cada_criterio_con_su_justificacion(sesion, obra_lista):  # noqa: F811
    observador = ObservadorEnMemoria()

    await _ciclo(sesion, obra_lista.capitulos[1].id, observador)

    puntuaciones = _span(observador.trazas[0], "critico").puntuaciones
    assert {p.criterio for p in puntuaciones} == {c.nombre for c in rubrica_vigente().criterios}
    assert all(p.nombre == "juez_con_rubrica" and p.justificacion for p in puntuaciones)


# --- R-1: un observador caido no rompe el capitulo ----------------------------


class _ObservadorQueNoAbre:
    def traza(self, *, obra_id: int, nombre: str) -> Any:
        raise RuntimeError("langfuse caido")


class _SpanQueRevienta:
    def entrada(self, texto: str) -> None:
        raise RuntimeError("boom")

    salida = entrada

    def consumo(self, **_: Any) -> None:
        raise RuntimeError("boom")

    def puntuar(self, puntuacion: Any) -> None:
        raise RuntimeError("boom")


class _ObservadorDeSpansQueRevientan(ObservadorEnMemoria):
    """Abre la traza y los spans, y **cada operacion** sobre un span lanza."""

    def traza(self, *, obra_id: int, nombre: str) -> Any:
        from contextlib import asynccontextmanager

        class _Traza:
            @asynccontextmanager
            async def span(self, nombre: str) -> Any:
                yield _SpanQueRevienta()

        @asynccontextmanager
        async def abrir() -> Any:
            yield _Traza()

        return abrir()


@pytest.mark.parametrize("roto", [_ObservadorQueNoAbre, _ObservadorDeSpansQueRevientan])
async def test_con_el_observador_caido_el_capitulo_se_integra_igual(
    sesion,
    obra_lista,  # noqa: F811
    roto: type,
):
    """Es el observador **blindado** el que baja por el ciclo, que es lo que
    `obtener_observador` entrega. Y los fallos se cuentan: un panel vacio no se
    distingue de un sistema que no genero nada."""
    observador = blindar(roto())

    resultado = await _ciclo(sesion, obra_lista.capitulos[1].id, observador)

    assert resultado.estado == "INTEGRADA"
    assert observador.fallos > 0


# --- Por HTTP: el router inyecta el observador y envuelve el cliente ----------


@pytest.fixture
def respuestas_del_modelo() -> dict[str, str]:
    return _respuestas()


async def test_escribir_por_http_deja_la_traza_del_capitulo_con_sus_prompts(
    cliente, sesion, obra, observador
):
    """Sin el `Depends(obtener_observador)` del router no hay traza; sin el
    `ClienteObservado` de `obtener_agentes`, los spans salen sin prompt."""
    assert cliente.post(f"/obras/{obra.id}/outline").status_code == 201
    capitulo_id = (
        await sesion.execute(
            select(Capitulo.id).where(Capitulo.obra_id == obra.id, Capitulo.numero == 1)
        )
    ).scalar_one()

    assert cliente.post(f"/capitulos/{capitulo_id}/escribir").status_code == 202

    [traza] = [t for t in observador.trazas if t.nombre.startswith("capitulo")]
    assert traza.sesion_id == sesion_de(obra.id)
    escritor = _span(traza, "escritor")
    assert "ESCRITOR · v1" in escritor.entradas[0]
    assert {p.nombre for p in _span(traza, "critico").puntuaciones} == {"juez_con_rubrica"}


async def test_la_novela_por_http_deja_una_traza_por_capitulo(cliente, sesion, obra, observador):
    """`POST /obras/{id}/novela` es el camino por el que se escribe la novela
    entera, y el que corre ahora mismo en produccion."""
    assert cliente.post(f"/obras/{obra.id}/outline").status_code == 201

    assert cliente.post(f"/obras/{obra.id}/novela").status_code == 202

    capitulos = [t for t in observador.trazas if t.nombre.startswith("capitulo")]
    assert len(capitulos) == 10
    assert {t.sesion_id for t in capitulos} == {sesion_de(obra.id)}
