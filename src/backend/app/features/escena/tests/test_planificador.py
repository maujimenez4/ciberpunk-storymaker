"""El Planificador de escena: la ficha, y la regla de dominio 1 antes de escribir.

La ficha es el contrato de generacion. Lo que aqui se comprueba no es que el
modelo escriba bien, sino que **lo que devuelve se cree solo si cumple su
esquema** (RF-ORQ-09) y que lo que no puede faltar no falta: objetivo,
obstaculo, giro de valor y un POV.

Ninguna prueba llama al proveedor (CA-4): el cliente es `DobleDeterminista`.
"""

import json
from typing import Any

import pytest
from sqlalchemy import select

from app.commons.llm.doble import DobleDeterminista
from app.features.escena.agents import (
    MARCA_DE_PLANTILLA,
    PLANTILLA_V1,
    Planificador,
    SalidaMalFormada,
    render_planificador,
)
from app.features.escena.modelos import Escena
from app.features.escena.repository import obtener_escena_de_capitulo
from app.features.escena.schemas import (
    DiscursoNoDeclarado,
    RestriccionesDeDiscurso,
    SalidaPlanificador,
)
from app.features.escena.service import planificar_escena

BIBLIA = {
    "protagonista": "Nadia",
    "persona": "3ª limitada",
    "tiempo_verbal": "pasado",
}

CAPITULO = {
    "numero": 2,
    "titulo": "Capitulo 2",
    "pov_dominante": "Nadia",
    "gancho_de_apertura": "La puerta estaba abierta",
    "tipo_de_corte_final": "pregunta",
    "extension_objetivo": 1200,
}

ESTADO_EN_T = {"hilos_abiertos": ["la carta sin abrir"], "presentes": ["Nadia", "Teo"]}


def _salida(**cambios: Any) -> str:
    """Lo que el modelo devuelve, en JSON, con lo que el test quiera cambiado."""
    campos: dict[str, Any] = {
        "tiempo_historia": "dia 2, tarde",
        "elapsed_desde_anterior": "un dia",
        "pov": "Nadia",
        "lugar": "El invernadero",
        "presentes": ["Nadia", "Teo"],
        "mencionados": ["la madre de Teo"],
        "objetivo_del_pov": "Que Teo confiese",
        "obstaculo": "Teo no habla de su madre",
        "resultado": "si-pero",
        "valor_entrada": "confianza",
        "valor_salida": "sospecha",
        "extension_objetivo": 1200,
        "densidad_de_dialogo_objetivo": 0.4,
        "distancia_psiquica": 3,
        "beat_de_genero": "Encuentro",
        "planta": ["la carta sin abrir"],
        "paga": [],
        "revela": [],
    }
    campos.update(cambios)
    return json.dumps(campos)


def _planificador(crudo: str, semilla: int = 0) -> Planificador:
    return Planificador(DobleDeterminista({MARCA_DE_PLANTILLA: crudo}), semilla=semilla)


async def _planificar(sesion, obra_con_outline, crudo: str, biblia: dict[str, Any] | None = None):
    return await planificar_escena(
        sesion,
        _planificador(crudo),
        capitulo_id=obra_con_outline.capitulos[1].id,
        version_obra_id=obra_con_outline.version_obra.id,
        orden_discurso=2,
        capitulo=CAPITULO,
        estado_en_t=ESTADO_EN_T,
        biblia=BIBLIA if biblia is None else biblia,
        nivel_de_calor=obra_con_outline.obra.nivel_de_calor,
    )


async def test_la_ficha_lleva_objetivo_obstaculo_y_giro_de_valor(sesion, obra_con_outline):
    """Regla de dominio 1 y RF-PLA-04: es lo que distingue una escena de un relleno."""
    ficha = await _planificar(sesion, obra_con_outline, _salida())

    assert ficha.objetivo_del_pov == "Que Teo confiese"
    assert ficha.obstaculo == "Teo no habla de su madre"
    assert (ficha.valor_entrada, ficha.valor_salida) == ("confianza", "sospecha")


async def test_una_ficha_sin_giro_de_valor_no_se_acepta(sesion, obra_con_outline):
    """Regla de dominio 1: «una escena sin giro de valor es relleno» (`definitions.md` §4.1).

    Es la validacion que CA-6 vigila: quitarla tiene que hacer caer **este**
    test y ningun otro.
    """
    crudo = _salida(valor_entrada="confianza", valor_salida="  Confianza ")
    with pytest.raises(SalidaMalFormada):
        await _planificar(sesion, obra_con_outline, crudo)


async def test_una_ficha_sin_giro_de_valor_no_deja_escena_escrita(sesion, obra_con_outline):
    """Lo que no se cree no se guarda: la ficha rechazada no deja fila."""
    with pytest.raises(SalidaMalFormada):
        await _planificar(sesion, obra_con_outline, _salida(valor_salida="confianza"))

    assert await obtener_escena_de_capitulo(sesion, obra_con_outline.capitulos[1].id) is None


@pytest.mark.parametrize("pov", ["Nadia y Teo", "Nadia, Teo", "   "])
async def test_un_pov_y_solo_uno(sesion, obra_con_outline, pov: str):
    """La otra mitad de la regla de dominio 1. Dos nombres en un campo son dos POV."""
    with pytest.raises(SalidaMalFormada):
        await _planificar(sesion, obra_con_outline, _salida(pov=pov))


async def test_la_ficha_hereda_de_la_obra_persona_tiempo_verbal_y_nivel_de_calor(
    sesion, obra_con_outline
):
    """Son las restricciones duras del prompt del Escritor, y la regla de dominio 10.

    El Escritor las comprobara **en el texto**, asi que tienen que viajar con la
    ficha: si las volviera a leer de la base, el defecto dejaria de ser
    atribuible (`CLAUDE.md` §9.1).
    """
    ficha = await _planificar(sesion, obra_con_outline, _salida())

    assert ficha.restricciones.persona == "3ª limitada"
    assert ficha.restricciones.tiempo_verbal == "pasado"
    assert ficha.restricciones.nivel_de_calor == obra_con_outline.obra.nivel_de_calor


async def test_una_biblia_que_no_declara_el_discurso_no_se_completa_con_un_defecto(
    sesion, obra_con_outline
):
    """Un `persona` por defecto es una restriccion dura inventada: falla antes."""
    with pytest.raises(DiscursoNoDeclarado):
        await _planificar(sesion, obra_con_outline, _salida(), biblia={"protagonista": "Nadia"})


async def test_una_clave_de_mas_es_un_fallo_y_no_una_respuesta(sesion, obra_con_outline):
    """RF-ORQ-09 con `extra='forbid'`: sin el, lo que sobra se pierde en silencio."""
    crudo = _salida(giro_de_valor="de confianza a sospecha")
    with pytest.raises(SalidaMalFormada):
        await _planificar(sesion, obra_con_outline, crudo)


async def test_lo_que_no_es_json_es_salida_mal_formada(sesion, obra_con_outline):
    """Un agente que devuelve prosa donde se pidio un objeto es un fallo."""
    with pytest.raises(SalidaMalFormada):
        await _planificar(sesion, obra_con_outline, "Aqui tienes la ficha de la escena:")


async def test_un_resultado_que_no_existe_no_entra_en_la_ficha(sesion, obra_con_outline):
    """`definitions.md` §4.1 declara el conjunto, y es cerrado."""
    with pytest.raises(SalidaMalFormada):
        await _planificar(sesion, obra_con_outline, _salida(resultado="quiza"))


async def test_la_ficha_se_guarda_como_la_escena_de_su_capitulo(sesion, obra_con_outline):
    """P-C: hacia dentro la unidad es la escena, y hoy hay una por capitulo."""
    ficha = await _planificar(sesion, obra_con_outline, _salida())

    escena = (
        (await sesion.execute(select(Escena).where(Escena.capitulo_id == ficha.capitulo_id)))
        .scalars()
        .one()
    )
    assert escena.pov == "Nadia"
    assert escena.version_obra_id == obra_con_outline.version_obra.id
    assert escena.orden_discurso == 2
    assert (escena.valor_entrada, escena.valor_salida) == ("confianza", "sospecha")


async def test_se_llama_al_modelo_una_vez_y_con_semilla(sesion, obra_con_outline):
    """Determinismo (`CLAUDE.md` §3 punto 6): la semilla viaja con la llamada."""
    doble = DobleDeterminista({MARCA_DE_PLANTILLA: _salida()})
    await planificar_escena(
        sesion,
        Planificador(doble, semilla=7),
        capitulo_id=obra_con_outline.capitulos[1].id,
        version_obra_id=obra_con_outline.version_obra.id,
        orden_discurso=2,
        capitulo=CAPITULO,
        estado_en_t=ESTADO_EN_T,
        biblia=BIBLIA,
        nivel_de_calor=obra_con_outline.obra.nivel_de_calor,
    )

    assert [semilla for _, semilla in doble.llamadas] == [7]


def test_las_restricciones_duras_se_repiten_al_principio_y_al_final():
    """`CLAUDE.md` §10: el centro del prompt es donde mas informacion se pierde."""
    restricciones = RestriccionesDeDiscurso(
        persona="3ª limitada", tiempo_verbal="pasado", nivel_de_calor=2
    )
    prompt = render_planificador(PLANTILLA_V1, CAPITULO, ESTADO_EN_T, restricciones)

    mitad = len(prompt) // 2
    assert "3ª limitada" in prompt[:mitad]
    assert "3ª limitada" in prompt[mitad:]
    assert "{{" not in prompt


def test_la_salida_del_planificador_no_admite_lo_que_no_pidio():
    """El esquema, probado sin base de datos: es dominio, no persistencia."""
    with pytest.raises(ValueError):
        SalidaPlanificador.model_validate(json.loads(_salida(distancia_psiquica=6)))
