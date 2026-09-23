"""El envoltorio de markdown se recorta; lo roto sigue roto."""

from app.commons.llm import extraer_json


def test_quita_la_valla_de_markdown() -> None:
    assert extraer_json('```json\n{"ok": true}\n```') == '{"ok": true}'


def test_quita_la_valla_sin_etiqueta() -> None:
    assert extraer_json("```\n[1, 2]\n```") == "[1, 2]"


def test_quita_un_preambulo() -> None:
    assert extraer_json('Aqui tienes:\n{"ok": true}') == '{"ok": true}'


def test_deja_intacto_el_json_limpio() -> None:
    assert extraer_json('{"ok": true}') == '{"ok": true}'


def test_no_repara_json_roto() -> None:
    """Recorta el envoltorio y nada mas. Un extractor que «arreglara» JSON medio
    escrito convertiria una salida rota en una silenciosamente incompleta."""
    assert extraer_json('```json\n{"ok": tru\n```') == '{"ok": tru'


def test_una_respuesta_en_prosa_se_devuelve_tal_cual() -> None:
    """Para que el esquema la rechace con un mensaje que se entienda."""
    assert extraer_json("Lo siento, no puedo ayudarte con eso.") == (
        "Lo siento, no puedo ayudarte con eso."
    )


# --- P-124: un array de objetos es JSON de nivel superior, y se recortaba ----


def test_un_array_de_objetos_sobrevive_entero() -> None:
    """El Continuista devuelve un array, no un objeto.

    Buscar `{` antes que `[` se comia los corchetes del array y dejaba dentro
    dos objetos sueltos separados por una coma, que no valida contra nada. Se
    devuelve el valor de nivel superior que **empieza antes**, no el que se mire
    primero.
    """
    texto = '[{"cita": "a", "momento": 1}, {"cita": "b", "momento": 2}]'

    assert extraer_json(texto) == texto


def test_un_array_precedido_de_cortesia_tambien() -> None:
    assert extraer_json('Aqui tienes: [{"cita": "a"}]') == '[{"cita": "a"}]'


def test_un_objeto_que_contiene_un_array_sigue_saliendo_entero() -> None:
    """El caso del Extractor: `{` empieza antes, y gana."""
    texto = '{"hechos": [{"entidad": "Ada"}], "resumen": "x"}'

    assert extraer_json(texto) == texto
