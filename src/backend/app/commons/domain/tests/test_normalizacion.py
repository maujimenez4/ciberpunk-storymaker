import pytest

from app.commons.domain.normalizacion import contiene_veto, normalizar


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [("Sangre", "sangre"), ("SANGRÉ", "sangre"), ("sangres", "sangre")],
)
def test_normalizar_iguala_mayusculas_acentos_y_plurales(texto: str, esperado: str):
    assert normalizar(texto) == esperado


@pytest.mark.parametrize("variante", ["sangre", "Sangre", "SANGRE", "sangres", "sangré"])
def test_el_veto_caza_sus_variantes(variante: str):
    assert contiene_veto(f"habia mucha {variante} en el suelo", ["sangre"]) == "sangre"


def test_el_veto_no_caza_trozos_de_otra_palabra():
    """R-3. Veto 'ana' contra el texto 'manana'.

    Un veto que da falsos positivos se acaba desactivando, y entonces no
    protege de nada. La comparacion es por palabra, no por subcadena.
    """
    assert contiene_veto("nos vemos manana por la tarde", ["ana"]) is None
    assert contiene_veto("Ana llego tarde", ["ana"]) == "ana"


def test_devuelve_el_termino_y_no_un_booleano():
    """RF-GUA-03 necesita el termino concreto para el reintento dirigido."""
    assert contiene_veto("olia a tabaco", ["humo", "tabaco"]) == "tabaco"
