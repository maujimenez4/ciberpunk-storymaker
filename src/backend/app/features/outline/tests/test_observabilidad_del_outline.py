"""`CLAUDE.md` §4.3 en el Arquitecto: el outline abre su traza y el rol su span.

Va por HTTP, que es lo unico que prueba que la ruta inyecta el observador y que
el Arquitecto se construye sobre el cliente observado: sin lo segundo, el span
se abre y sale **sin prompt**, que es justo lo que el *tuning* necesita ver.
"""

from typing import Any

import pytest

from app.commons.llm.doble import DobleDeterminista
from app.commons.observabilidad import (
    ClienteObservado,
    ObservadorEnMemoria,
    blindar,
    sesion_de,
)
from app.features.escritura.tests.test_ciclo import _respuestas
from app.features.escritura.tests.test_observabilidad_del_ciclo import prompt_del_fichero
from app.features.outline.agents import Arquitecto
from app.features.outline.service import planificar_obra


@pytest.fixture
def respuestas_del_modelo() -> dict[str, str]:
    return _respuestas()


async def test_el_outline_por_http_deja_su_traza_con_el_prompt_del_arquitecto(
    cliente: Any, obra: Any, observador: ObservadorEnMemoria
) -> None:
    assert cliente.post(f"/obras/{obra.id}/outline").status_code == 201

    [traza] = observador.trazas
    assert traza.nombre == "outline"
    assert traza.sesion_id == sesion_de(obra.id)
    [span] = traza.spans
    assert span.nombre == "arquitecto"
    assert "# Arquitecto" in span.entradas[0]
    assert '"capitulos"' in span.salidas[0]
    # P-22.3 (plan 8 T7): la plantilla que produjo el outline, sacada del
    # fichero y no de la constante del agente.
    assert span.prompts == [prompt_del_fichero("outline", "arquitecto.v2.md")]


async def test_una_obra_que_no_existe_no_abre_traza(
    cliente: Any, observador: ObservadorEnMemoria
) -> None:
    """Una traza con una sesion de una obra que no existe es ruido en el panel,
    y el 404 sale antes de llamar al modelo."""
    assert cliente.post("/obras/9999/outline").status_code == 404

    assert observador.trazas == []


async def test_con_el_observador_caido_el_outline_se_planifica_igual(
    sesion: Any, obra: Any
) -> None:
    class Roto:
        def traza(self, *, obra_id: int, nombre: str) -> Any:
            raise RuntimeError("langfuse caido")

    observado = ClienteObservado(DobleDeterminista(_respuestas()))
    observador = blindar(Roto())  # type: ignore[arg-type]

    plan = await planificar_obra(
        sesion, Arquitecto(observado), obra.id, observador=observador, cliente=observado
    )

    assert len(plan.outline.capitulos) == 10
    assert observador.fallos > 0
