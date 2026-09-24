"""Leer el JSON del modelo aunque venga envuelto.

El caso que lo motivo es real y esta fechado: la primera corrida contra el
proveedor, el 2026-09-24, murio en la entrevista porque el modelo devolvio JSON
valido dentro de una valla de markdown.
"""

import json

import pytest

from app.commons.llm.json_de_modelo import json_de_modelo, sin_valla

PELADO = '{"faltantes": [], "contradicciones": []}'


def test_el_json_pelado_se_lee_igual_que_antes() -> None:
    """Lo que ya funcionaba tiene que seguir funcionando sin cambios."""
    assert json_de_modelo(PELADO) == {"faltantes": [], "contradicciones": []}


def test_el_caso_real_que_rompio_la_corrida() -> None:
    """Copiado del log de la corrida, con su etiqueta y sus saltos."""
    crudo = '```json\n{\n  "faltantes": ["extension"],\n  "contradicciones": []\n}\n```'

    assert json_de_modelo(crudo) == {"faltantes": ["extension"], "contradicciones": []}


@pytest.mark.parametrize(
    "crudo",
    [
        "```json\n" + PELADO + "\n```",
        "```JSON\n" + PELADO + "\n```",
        "```\n" + PELADO + "\n```",
        "  ```json\n" + PELADO + "\n```  ",
        "```json\n" + PELADO + "\n```\n",
    ],
)
def test_las_formas_de_valla_que_usa_el_modelo(crudo: str) -> None:
    """Con etiqueta, sin ella, en mayusculas y con espacios alrededor."""
    assert json_de_modelo(crudo) == json.loads(PELADO)


def test_una_llave_dentro_del_texto_no_confunde_al_lector() -> None:
    """El contenido puede llevar comillas triples en un valor y no pasa nada."""
    crudo = '```json\n{"nota": "usa ``` para el codigo"}\n```'

    assert json_de_modelo(crudo) == {"nota": "usa ``` para el codigo"}


def test_el_json_roto_sigue_fallando() -> None:
    """No se repara nada: si dentro de la valla no hay JSON, el error sube.

    Tolerar mas seria adivinar, y entonces un modelo que explica en vez de
    contestar pareceria estar funcionando.
    """
    with pytest.raises(json.JSONDecodeError):
        json_de_modelo("```json\nesto no es json\n```")


def test_el_texto_alrededor_de_la_valla_no_se_tolera() -> None:
    """«Aqui tienes el JSON:» delante **debe** fallar: es el modelo hablando
    cuando se le pidio que contestara, y eso hay que verlo."""
    with pytest.raises(json.JSONDecodeError):
        json_de_modelo("Aqui tienes el JSON:\n```json\n" + PELADO + "\n```")


def test_sin_valla_devuelve_el_texto_intacto_cuando_no_la_hay() -> None:
    assert sin_valla(PELADO) == PELADO


def test_la_valla_sin_cerrar_de_una_respuesta_truncada() -> None:
    """Truncada a mitad: llega la apertura y no el cierre.

    El JSON sigue estando roto -- y debe fallar --, pero el error tiene que
    hablar del **final**, que es donde se corto, y no del primer caracter.
    """
    truncado = '```json\n{"faltantes": ["uno", "do'

    with pytest.raises(json.JSONDecodeError) as fallo:
        json_de_modelo(truncado)

    assert fallo.value.pos > 1, "el error apunta al char 0: la valla no se quito"


def test_la_valla_cerrada_sigue_teniendo_prioridad() -> None:
    """Con cierre se usa el cierre: la forma abierta es el caso degradado."""
    assert json_de_modelo("```json\n" + PELADO + "\n```") == json.loads(PELADO)


def test_el_modelo_que_sigue_escribiendo_tras_cerrar_la_valla() -> None:
    """El segundo bloqueo del Arquitecto, 2026-09-24.

    Devolvio el outline entero, cerro la valla y escribio debajo un resumen de
    lo que acababa de planificar. El JSON estaba completo y bien formado; el
    error era `Extra data: char 9368`, que suena a JSON roto y no lo era.

    Lo de despues se descarta. Lo de antes no -- ese test esta arriba --, porque
    con texto delante no se sabe cual de los dos es la respuesta.
    """
    crudo = "```json\n" + PELADO + "\n```\n\nEspero que te sirva. He estructurado..."

    assert json_de_modelo(crudo) == json.loads(PELADO)


def test_se_toma_el_primer_bloque_y_no_el_ultimo() -> None:
    """Si hay dos, el primero es la respuesta y el resto es comentario."""
    crudo = '```json\n{"a": 1}\n```\ny otro ejemplo:\n```json\n{"a": 2}\n```'

    assert json_de_modelo(crudo) == {"a": 1}
