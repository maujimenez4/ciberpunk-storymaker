import json

import pytest

from app.commons.llm.doble import DobleDeterminista
from app.features.obra.agents import Entrevistador, SalidaMalFormada
from app.features.obra.service import evaluar_entrevista


def _doble(carga: dict[str, object]) -> DobleDeterminista:
    return DobleDeterminista({"ENTREVISTADOR": json.dumps(carga)})


async def test_devuelve_los_faltantes_nombrados_y_no_un_error_generico():
    """RF-ENT-03: 'falta algo' no sirve; hay que poder volver a preguntar."""
    agente = Entrevistador(
        _doble({"faltantes": ["edad", "recuerdos_aportados"], "contradicciones": []})
    )
    evaluacion = await agente.evaluar({"nombre": "Marta"}, "")
    assert evaluacion.faltantes == ["edad", "recuerdos_aportados"]
    assert not evaluacion.completa


async def test_detecta_una_contradiccion_y_la_explica():
    """RF-ENT-04: el esquema NO la ve. Edad 8 y tono erotico validan los tipos."""
    agente = Entrevistador(
        _doble(
            {
                "faltantes": [],
                "contradicciones": [
                    {
                        "campos": ["destinatario.edad", "tono"],
                        "explicacion": "8 anos y tono erotico",
                    }
                ],
            }
        )
    )
    evaluacion = await agente.evaluar({"edad": 8, "tono": "erotico"}, "")
    assert not evaluacion.completa
    assert evaluacion.contradicciones[0].campos == ["destinatario.edad", "tono"]
    assert "8 anos" in evaluacion.contradicciones[0].explicacion


async def test_sin_faltantes_ni_contradicciones_esta_completa():
    agente = Entrevistador(_doble({"faltantes": [], "contradicciones": []}))
    assert (await agente.evaluar({"nombre": "Marta"}, "")).completa


async def test_una_salida_fuera_de_esquema_es_un_fallo_no_una_respuesta():
    """RF-ORQ-09. Sin esto, un modelo que devuelve prosa pasa por 'sin faltantes'."""
    agente = Entrevistador(DobleDeterminista({"ENTREVISTADOR": "claro, ahi va: ..."}))
    with pytest.raises(SalidaMalFormada):
        await agente.evaluar({"nombre": "Marta"}, "")


async def test_una_clave_de_mas_tambien_es_una_salida_fuera_de_esquema():
    """RF-ORQ-09 por la puerta que el test anterior no mira.

    La plantilla pide el objeto JSON `con estas dos claves y ninguna mas`. Si el
    modelo pone lo que encontro en una clave que se invento, las dos que si mira
    el esquema llegan vacias y la evaluacion sale `completa`: el dato que falta
    se pierde en silencio, que es el mismo fallo que el test anterior evita para
    la prosa. Sin `extra=forbid` esto valida.
    """
    agente = Entrevistador(
        _doble({"faltantes": [], "contradicciones": [], "faltan": ["edad", "recuerdos_aportados"]})
    )
    with pytest.raises(SalidaMalFormada):
        await agente.evaluar({"nombre": "Marta"}, "")


async def test_el_texto_del_comprador_llega_al_prompt_marcado_como_dato():
    """RF-ENT-05: nunca se concatena a un prompt sin esa marca.

    La Tarea 6 comprueba que `render_entrevistador` marca el texto. Lo que aqui
    se comprueba es lo otro: que `evaluar` pasa de verdad por ese render y no
    pega el texto del comprador por su cuenta.
    """
    doble = _doble({"faltantes": [], "contradicciones": []})
    await Entrevistador(doble).evaluar({"nombre": "Marta"}, "Le gusta el mar.")
    prompt, _ = doble.llamadas[0]
    assert "<texto_aportado>" in prompt
    assert prompt.index("Le gusta el mar.") > prompt.index("<texto_aportado>")


async def test_el_caso_de_uso_devuelve_la_evaluacion_y_no_decide_por_su_cuenta():
    """CA-2: el agente informa y la decision ocurre en codigo, sobre `completa`."""
    faltan = await evaluar_entrevista(
        Entrevistador(_doble({"faltantes": ["edad"], "contradicciones": []})),
        {"nombre": "Marta"},
    )
    assert faltan.faltantes == ["edad"]
    assert not faltan.completa

    completa = await evaluar_entrevista(
        Entrevistador(_doble({"faltantes": [], "contradicciones": []})),
        {"nombre": "Marta"},
    )
    assert completa.completa
