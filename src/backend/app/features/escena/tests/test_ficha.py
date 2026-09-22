"""P-25: la ficha de escena declara las restricciones duras.

RF-ESC-01 y RF-ESC-02. La ficha es lo que el Planificador produce y lo que
despues viaja en la capa de instruccion del paquete. Si una restriccion dura no
esta aqui, el Escritor no la recibe y ningun validador tiene contra que
comparar: los defectos dejarian de ser atribuibles.
"""

import json
from datetime import UTC, datetime

import pytest

from app.commons.domain import NivelDeCalor, ParametrosDeDiscurso, RelojFijo
from app.commons.llm import DobleDeModelo
from app.features.escena import FichaInvalida, planificar_escena

PARAMETROS = ParametrosDeDiscurso(
    persona="tercera",
    tiempo_verbal="pasado",
    esquema_de_pov="dual",
    nivel_de_calor=NivelDeCalor.SENSUAL,
)

FICHA_DEL_AGENTE = {
    "pov": "pj-ada",
    "presentes": ["pj-ada", "pj-noe"],
    "lugar": "lug-taller",
    "objetivo_del_pov": "cerrar el trato",
    "obstaculo": "el otro no firma",
    "valor_entrada": "control",
    "valor_salida": "amenaza",
    "distancia_psiquica": "cercana",
    "densidad_de_dialogo_objetivo": 0.4,
    "extension_objetivo": 1800,
}


@pytest.fixture
def reloj() -> RelojFijo:
    return RelojFijo(datetime(2026, 9, 22, tzinfo=UTC))


def test_la_ficha_declara_las_siete_restricciones_duras(reloj: RelojFijo) -> None:
    ficha = planificar_escena(
        "esc-1",
        PARAMETROS,
        DobleDeModelo([json.dumps(FICHA_DEL_AGENTE)]),
        "prompt del planificador",
        reloj,
    )

    assert ficha.pov == "pj-ada"
    assert ficha.presentes == ["pj-ada", "pj-noe"]
    assert ficha.lugar == "lug-taller"
    assert ficha.distancia_psiquica == "cercana"
    assert ficha.densidad_de_dialogo_objetivo == 0.4
    assert ficha.extension_objetivo == 1800
    assert ficha.nivel_de_calor is NivelDeCalor.SENSUAL


def test_el_nivel_de_calor_lo_hereda_de_la_obra_y_el_agente_no_lo_elige(
    reloj: RelojFijo,
) -> None:
    """RF-ESC-02 dice "el `nivel_de_calor` **heredado**", y la palabra importa.

    Es el unico campo de la ficha que el Planificador no decide. Si pudiera
    proponerlo, un agente tendria via para subir el calor por encima de lo
    prometido al lector, y RG-10 dependeria de que el modelo se porte bien.
    """
    intenta_subirlo = {**FICHA_DEL_AGENTE, "nivel_de_calor": "explicito"}

    ficha = planificar_escena(
        "esc-1",
        PARAMETROS,
        DobleDeModelo([json.dumps(intenta_subirlo)]),
        "p",
        reloj,
    )

    assert ficha.nivel_de_calor is NivelDeCalor.SENSUAL


def test_el_pov_tiene_que_estar_entre_los_presentes(reloj: RelojFijo) -> None:
    """Un POV ausente de su propia escena no puede percibir nada."""
    ausente = {**FICHA_DEL_AGENTE, "pov": "pj-otro"}

    with pytest.raises(FichaInvalida):
        planificar_escena(
            "esc-1", PARAMETROS, DobleDeModelo([json.dumps(ausente)]), "p", reloj
        )


def test_una_ficha_sin_giro_de_valor_se_rechaza(reloj: RelojFijo) -> None:
    """RG-08 y RF-CAL-01: se caza en la ficha, antes de gastar una llamada."""
    sin_giro = {**FICHA_DEL_AGENTE, "valor_salida": "control"}

    with pytest.raises(FichaInvalida):
        planificar_escena(
            "esc-1", PARAMETROS, DobleDeModelo([json.dumps(sin_giro)]), "p", reloj
        )


def test_una_densidad_de_dialogo_imposible_se_rechaza(reloj: RelojFijo) -> None:
    """Es una proporcion. Un 4.0 delata una salida mal formada, no una escena
    muy dialogada."""
    imposible = {**FICHA_DEL_AGENTE, "densidad_de_dialogo_objetivo": 4.0}

    with pytest.raises(FichaInvalida):
        planificar_escena(
            "esc-1", PARAMETROS, DobleDeModelo([json.dumps(imposible)]), "p", reloj
        )


def test_una_salida_que_no_es_json_es_fallo_del_paso(reloj: RelojFijo) -> None:
    with pytest.raises(FichaInvalida):
        planificar_escena(
            "esc-1", PARAMETROS, DobleDeModelo(["lo siento, no puedo"]), "p", reloj
        )
