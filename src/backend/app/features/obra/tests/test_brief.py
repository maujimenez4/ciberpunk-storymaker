import pytest
from pydantic import ValidationError

from app.features.obra import BriefEntrada


def _brief(**cambios: object) -> dict[str, object]:
    base: dict[str, object] = {
        "destinatario": {
            "nombre": "Marta",
            "edad": 34,
            "rasgos": ["terca"],
            "recuerdos_aportados": ["el verano del 98"],
        },
        "genero": "romance",
        "tono": "calido",
        "nivel_de_calor": 2,
        "vetos": [],
        "elementos_obligatorios": ["el perro Luna"],
    }
    base.update(cambios)
    return base


def test_un_brief_completo_valida():
    brief = BriefEntrada.model_validate(_brief())
    assert brief.destinatario.nombre == "Marta"
    assert brief.elementos_obligatorios == ["el perro Luna"]


def test_menor_de_edad_con_calor_se_rechaza_en_el_esquema():
    """Regla de dominio 6. En el esquema, nunca en el prompt."""
    with pytest.raises(ValidationError, match="menor"):
        BriefEntrada.model_validate(
            _brief(
                destinatario={"nombre": "Ana", "edad": 15, "rasgos": [], "recuerdos_aportados": []},
                nivel_de_calor=3,
            )
        )


def test_dieciocho_anos_no_es_menor_de_edad():
    """R-1. La regla dice 'menores de 18'; 18 no es menor.

    Una frontera mal puesta aqui prohibe novelas legitimas, y nadie lo
    notaria hasta que un comprador se quejara.
    """
    brief = BriefEntrada.model_validate(
        _brief(
            destinatario={"nombre": "Ana", "edad": 18, "rasgos": [], "recuerdos_aportados": []},
            nivel_de_calor=3,
        )
    )
    assert brief.destinatario.edad == 18


@pytest.mark.parametrize("nombre", ["Begoña", "Müller", "García-Ortiz", "O'Shea"])
def test_el_nombre_se_guarda_tal_cual(nombre: str):
    """R-4. La normalizacion de vetos no toca los nombres del canon."""
    brief = BriefEntrada.model_validate(
        _brief(destinatario={"nombre": nombre, "edad": 30, "rasgos": [], "recuerdos_aportados": []})
    )
    assert brief.destinatario.nombre == nombre


@pytest.mark.parametrize("vacio", [[""], ["   "], ["el perro Luna", ""]])
def test_un_elemento_obligatorio_vacio_no_valida(vacio: list[str]):
    """R-6. `min_length=1` sobre la lista exige UN elemento, no que tenga texto.

    Con `[""]` el brief valida, y despues el validador de cobertura de G4 da
    100 % — porque la cadena vacia es subcadena de cualquier capitulo. Un
    validador que siempre pasa es peor que no tenerlo: ocupa su sitio.
    El fallo no esta en el esquema ni en el validador: esta en la juntura.
    """
    with pytest.raises(ValidationError):
        BriefEntrada.model_validate(_brief(elementos_obligatorios=vacio))


def test_edad_que_no_concuerda_con_la_fecha_de_nacimiento_no_valida():
    """R-7. Regla 13, cazada aqui y no en la puerta mas cara."""
    with pytest.raises(ValidationError, match="no concuerda"):
        BriefEntrada.model_validate(
            _brief(
                destinatario={
                    "nombre": "Marta",
                    "edad": 34,
                    "rasgos": [],
                    "recuerdos_aportados": [],
                    "fecha_de_nacimiento": "1950-04-02",
                }
            )
        )


def test_sin_elementos_obligatorios_no_valida():
    """RF-ENT-08: un brief sin ellos no permite comprobar nada despues."""
    with pytest.raises(ValidationError):
        BriefEntrada.model_validate(_brief(elementos_obligatorios=[]))


# --- R-8: ningun veto puede chocar con el nombre del destinatario ----------
#
# `contiene_veto` compara por palabra y `\w+` parte "Garcia-Ortiz" en dos, asi
# que el veto "Ortiz" saltaria sobre el nombre de la persona a quien va el
# regalo, en cada capitulo. El tokenizador NO se afloja (Desviaciones,
# 2026-09-24): aflojarlo compra este falso positivo a cambio de falsos
# negativos, y un veto que deja de saltar es peor que uno que salta de mas.
# La garantia se da aqui, que es el unico sitio donde estan los dos datos.


@pytest.mark.parametrize(
    ("veto", "nombre"),
    [
        ("Ortiz", "García-Ortiz"),
        ("ortiz", "García-Ortiz"),
        ("garcias", "García-Ortiz"),
        ("Marta", "Marta"),
    ],
)
def test_un_veto_que_choca_con_el_nombre_del_destinatario_no_valida(veto: str, nombre: str):
    """R-8. Se rechaza en la entrevista, como R-7, y no en G4."""
    with pytest.raises(ValidationError, match="veto"):
        BriefEntrada.model_validate(
            _brief(
                destinatario={
                    "nombre": nombre,
                    "edad": 30,
                    "rasgos": [],
                    "recuerdos_aportados": [],
                },
                vetos=[veto],
            )
        )


def test_el_choque_dice_que_veto_y_con_que_nombre():
    """R-8: 'hay un choque' no sirve; el comprador tiene que poder corregirlo."""
    with pytest.raises(ValidationError) as fallo:
        BriefEntrada.model_validate(
            _brief(
                destinatario={
                    "nombre": "García-Ortiz",
                    "edad": 30,
                    "rasgos": [],
                    "recuerdos_aportados": [],
                },
                vetos=["sangre", "Ortiz"],
            )
        )
    mensaje = str(fallo.value)
    assert "Ortiz" in mensaje
    assert "García-Ortiz" in mensaje


@pytest.mark.parametrize("veto", ["sangre", "orti", "arcia"])
def test_un_veto_que_no_es_el_nombre_del_destinatario_si_valida(veto: str):
    """R-8 no puede tragarse R-3: un trozo de palabra no es un choque.

    "orti" y "arcia" son subcadenas de "Garcia-Ortiz" y NO deben rechazar el
    brief; si lo hicieran, R-8 habria reintroducido por la puerta de atras el
    falso positivo que R-3 existe para impedir.
    """
    brief = BriefEntrada.model_validate(
        _brief(
            destinatario={
                "nombre": "García-Ortiz",
                "edad": 30,
                "rasgos": [],
                "recuerdos_aportados": [],
            },
            vetos=[veto],
        )
    )
    assert brief.vetos == [veto]
