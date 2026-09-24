"""CA-17 · RF-VAL-07 · reglas de dominio 8 y 9 (`architecture.md` §8.3)."""

from app.features.calidad import (
    CODIGOS_DE_LA_TAXONOMIA,
    Defecto,
    MotivoMalFormado,
    clasificar,
    comprobar_forma,
)

TEXTO = "Aquella tarde Marta cerró la puerta y no dijo nada."
HECHOS = frozenset({"hc-1"})


def defecto(**cambios: object) -> Defecto:
    campos: dict[str, object] = {
        "codigo": "CON-01",
        "version_texto_id": "vt-1",
        "cita": "cerró la puerta",
        "desplazamiento_inicio": TEXTO.index("cerró la puerta"),
        "desplazamiento_fin": TEXTO.index("cerró la puerta") + len("cerró la puerta"),
        "hecho_canon_id": None,
    }
    campos.update(cambios)
    return Defecto(**campos)  # type: ignore[arg-type]


def test_un_defecto_bien_formado_pasa():
    assert comprobar_forma(defecto(), TEXTO, HECHOS) is None


def test_un_codigo_fuera_de_la_taxonomia_esta_mal_formado():
    motivo = comprobar_forma(defecto(codigo="XYZ-99"), TEXTO, HECHOS)

    assert motivo is MotivoMalFormado.CODIGO_FUERA_DE_LA_TAXONOMIA


def test_una_cita_inventada_esta_mal_formada():
    """Un pasaje que no esta en el texto no es una imprecision de redaccion: es
    un defecto que no se refiere a nada."""
    motivo = comprobar_forma(defecto(cita="abrió la ventana"), TEXTO, HECHOS)

    assert motivo is MotivoMalFormado.CITA_FUERA_DE_SU_DESPLAZAMIENTO


def test_una_cita_literal_pero_en_otro_desplazamiento_esta_mal_formada():
    """Subcadena exacta NO basta: tiene que estarlo EN el desplazamiento
    declarado (axioma 11). Sin esto, un defecto senala una frase que aparece
    dos veces y nadie sabe cual."""
    motivo = comprobar_forma(defecto(desplazamiento_inicio=0, desplazamiento_fin=15), TEXTO, HECHOS)

    assert motivo is MotivoMalFormado.CITA_FUERA_DE_SU_DESPLAZAMIENTO


def test_un_can_01_sin_hecho_de_canon_esta_mal_formado():
    motivo = comprobar_forma(defecto(codigo="CAN-01"), TEXTO, HECHOS)

    assert motivo is MotivoMalFormado.HECHO_DE_CANON_QUE_NO_EXISTE


def test_un_can_01_con_un_hecho_inventado_esta_mal_formado():
    motivo = comprobar_forma(defecto(codigo="CAN-01", hecho_canon_id="hc-inventado"), TEXTO, HECHOS)

    assert motivo is MotivoMalFormado.HECHO_DE_CANON_QUE_NO_EXISTE


def test_un_can_01_con_un_hecho_que_existe_pasa():
    assert comprobar_forma(defecto(codigo="CAN-01", hecho_canon_id="hc-1"), TEXTO, HECHOS) is None


def test_la_taxonomia_es_la_de_definitions_md():
    assert "EST-02" in CODIGOS_DE_LA_TAXONOMIA
    assert "PER-02" in CODIGOS_DE_LA_TAXONOMIA
    assert "VOZ-03" in CODIGOS_DE_LA_TAXONOMIA
    assert "CAN-01" in CODIGOS_DE_LA_TAXONOMIA
    assert len(CODIGOS_DE_LA_TAXONOMIA) == 21


def test_clasificar_separa_los_dos_montones_conservando_el_motivo():
    bueno = defecto()
    malo = defecto(cita="abrió la ventana")

    clasificados = clasificar([bueno, malo], TEXTO, HECHOS)

    assert clasificados.bien_formados == (bueno,)
    assert [m.defecto for m in clasificados.mal_formados] == [malo]
    assert clasificados.mal_formados[0].motivo is MotivoMalFormado.CITA_FUERA_DE_SU_DESPLAZAMIENTO
