"""`CLAUDE.md` §4.3 en la publicacion: Lean y G4 emiten su *score*.

`cronologia_lean` es el unico validador formal que corre en una generacion
(`verification.md` §8.3) y G4 es la puerta del manuscrito entero: los dos
corrian en cada publicacion y **ninguno constaba en Langfuse**. Aqui se prueba
que la publicacion abre su traza en la sesion de la obra, con un span por
validador y el *score* dentro.

Lean se sustituye por un doble: lo que se prueba es que su veredicto llegue al
panel, no Lean -- eso es de `test_puerta_lean.py`, con el binario de verdad --.
Y va por HTTP una vez, que es lo unico que prueba que el router inyecta el
observador.
"""

from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.observabilidad import ObservadorEnMemoria, blindar, sesion_de
from app.conftest import ObraConOutline
from app.features.calidad.tests.test_scores import nombres_de_verification
from app.features.manuscrito import CronologiaIncoherente, publicar
from app.features.manuscrito.lean import Resultado
from app.features.manuscrito.tests.test_publicar import _integrar


def _lean_que_dice(ok: bool) -> Any:
    async def correr(_sesion: AsyncSession, _obra_id: int) -> Resultado:
        if ok:
            return Resultado(ok=True, eventos_comprobados=3)
        return Resultado(ok=False, mensaje="La cronologia no es coherente: Marta en dos sitios")

    return correr


@pytest.fixture
def lean_de_acuerdo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.features.manuscrito.service.correr_lean", _lean_que_dice(True))


def _span(traza: Any, nombre: str) -> Any:
    [span] = [s for s in traza.spans if s.nombre == nombre]
    return span


async def test_publicar_abre_una_traza_en_la_sesion_de_la_obra(
    sesion: AsyncSession, obra_con_outline: ObraConOutline, lean_de_acuerdo: None
) -> None:
    await _integrar(sesion, obra_con_outline)
    observador = ObservadorEnMemoria()

    await publicar(sesion, obra_con_outline.obra.id, observador=observador)

    [traza] = observador.trazas
    assert traza.nombre == "publicacion"
    assert traza.sesion_id == sesion_de(obra_con_outline.obra.id)
    assert [s.nombre for s in traza.spans] == ["cronologia_lean", "puerta_g4"]


async def test_lean_puntua_uno_cuando_deja_publicar(
    sesion: AsyncSession, obra_con_outline: ObraConOutline, lean_de_acuerdo: None
) -> None:
    await _integrar(sesion, obra_con_outline)
    observador = ObservadorEnMemoria()

    await publicar(sesion, obra_con_outline.obra.id, observador=observador)

    [puntuacion] = _span(observador.trazas[0], "cronologia_lean").puntuaciones
    assert (puntuacion.nombre, puntuacion.valor) == ("cronologia_lean", 1.0)


async def test_lean_puntua_cero_y_deja_el_motivo_cuando_detiene_la_publicacion(
    sesion: AsyncSession, obra_con_outline: ObraConOutline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El caso que importa: la puerta se cierra **y el panel lo dice**. Un cero
    sin traza seria un numero; con el motivo, es algo que se puede arreglar."""
    await _integrar(sesion, obra_con_outline)
    monkeypatch.setattr("app.features.manuscrito.service.correr_lean", _lean_que_dice(False))
    observador = ObservadorEnMemoria()

    with pytest.raises(CronologiaIncoherente):
        await publicar(sesion, obra_con_outline.obra.id, observador=observador)

    span = _span(observador.trazas[0], "cronologia_lean")
    assert [(p.nombre, p.valor) for p in span.puntuaciones] == [("cronologia_lean", 0.0)]
    assert "Marta" in span.salidas[0]
    assert "puerta_g4" not in [s.nombre for s in observador.trazas[0].spans]


async def test_g4_puntua_cada_validador_del_manuscrito(
    sesion: AsyncSession, obra_con_outline: ObraConOutline, lean_de_acuerdo: None
) -> None:
    await _integrar(sesion, obra_con_outline)
    observador = ObservadorEnMemoria()

    await publicar(sesion, obra_con_outline.obra.id, observador=observador)

    nombres = [p.nombre for p in _span(observador.trazas[0], "puerta_g4").puntuaciones]
    assert nombres == ["cobertura_de_personalizacion"]


def test_cronologia_lean_se_llama_como_en_la_tabla_de_verification() -> None:
    """La llave por la que el *score* se cruza con `verification.md` §8.3."""
    assert "cronologia_lean" in nombres_de_verification()


async def test_con_el_observador_caido_se_publica_igual(
    sesion: AsyncSession, obra_con_outline: ObraConOutline, lean_de_acuerdo: None
) -> None:
    """R-1: un panel caido no puede dejar al comprador sin su enlace."""

    class Roto:
        def traza(self, *, obra_id: int, nombre: str) -> Any:
            raise RuntimeError("langfuse caido")

    await _integrar(sesion, obra_con_outline)
    observador = blindar(Roto())  # type: ignore[arg-type]

    version = await publicar(sesion, obra_con_outline.obra.id, observador=observador)

    assert version.ordinal == 1
    assert observador.fallos > 0


async def test_publicar_por_http_deja_la_traza(
    cliente: Any,
    sesion: AsyncSession,
    obra_con_outline: ObraConOutline,
    observador: ObservadorEnMemoria,
    lean_de_acuerdo: None,
) -> None:
    """Sin el `Depends(obtener_observador)` de la ruta, no hay traza."""
    await _integrar(sesion, obra_con_outline)

    respuesta = cliente.post(f"/obras/{obra_con_outline.obra.id}/publicar")

    assert respuesta.status_code == 200
    [traza] = observador.trazas
    assert traza.nombre == "publicacion"
    assert traza.sesion_id == sesion_de(obra_con_outline.obra.id)
