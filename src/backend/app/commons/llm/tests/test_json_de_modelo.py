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
