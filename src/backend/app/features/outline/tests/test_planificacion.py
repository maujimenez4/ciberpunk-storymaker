"""CU-02: de un brief salen una biblia versionada y un outline de diez capitulos.

Aqui viven las reglas de dominio del Arquitecto, que no son del esquema del
agente sino del outline entero: cuantos capitulos hay, que cada beat obligatorio
este en **exactamente un** capitulo (CA-32) y que ningun capitulo se quede sin
giro de valor.
"""

import json
from typing import Any

import pytest
from sqlalchemy import select

from app.commons.llm.doble import DobleDeterminista
from app.features.outline.agents import Arquitecto
from app.features.outline.modelos import Capitulo, VersionObra
from app.features.outline.schemas import BeatDeGenero, Persona, TiempoVerbal
from app.features.outline.service import (
    BeatsMalAsignados,
    DiscursoNoDeclarado,
    GiroDeValorAusente,
    ObraDesconocida,
    ObraYaPlanificada,
    OutlineIncompleto,
    planificar_obra,
)

# Los parametros de discurso que la biblia declara (`definitions.md` §5). Van
# con sus literales: no es la grafia de este fichero, es la del documento.
DISCURSO: dict[str, Any] = {
    "persona": "3ª limitada",
    "tiempo_verbal": "pasado",
    "nivel_de_calor": 2,
}


def _outline(capitulos: list[dict[str, Any]], **biblia: Any) -> str:
    documento = {"protagonista": "Nadia", **DISCURSO, **biblia}
    return json.dumps({"biblia": documento, "capitulos": capitulos})


def _diez_capitulos() -> list[dict[str, Any]]:
    """Diez capitulos validos, con el beat i en el capitulo i.

    No es el reparto que `domain-knowledge.md` §8.1 recomienda —alli el primer
    capitulo carga dos hitos—, y no hace falta que lo sea: lo que la regla exige
    es que cada beat este en **exactamente un** capitulo, no en cual.
    """
    return [
        {
            "numero": n,
            "titulo": f"Capitulo {n}",
            "pov_dominante": "Nadia",
            "lugar": "El invernadero",
            "objetivo": "Que Teo confiese",
            "obstaculo": "Teo no habla de su madre",
            "valor_entrada": "confianza",
            "valor_salida": "sospecha",
            "gancho_de_apertura": "La puerta estaba abierta",
            "tipo_de_corte_final": "pregunta",
            "extension_objetivo": 1200,
            "beat_de_genero": beat.value,
        }
        for n, beat in enumerate(BeatDeGenero, start=1)
    ]


def _arquitecto(crudo: str) -> Arquitecto:
    return Arquitecto(DobleDeterminista({"# Arquitecto": crudo}))


async def test_la_biblia_sale_del_brief_y_queda_versionada(sesion, obra):
    """RF-PLA-01. Una biblia sin version no se puede citar desde una escena."""
    await planificar_obra(sesion, _arquitecto(_outline(_diez_capitulos())), obra.id)

    versiones = (await sesion.execute(select(VersionObra))).scalars().all()
    assert [v.numero for v in versiones] == [1]
    assert versiones[0].biblia["protagonista"] == "Nadia"


async def test_la_biblia_declara_los_parametros_de_discurso(sesion, obra):
    """`definitions.md` §5: se declaran una vez en la obra y se imponen en cada
    escena como restriccion dura.

    Hoy `persona` y `tiempo_verbal` **no son columnas de `obra`** —`modelos.py`
    no es de esta tarea—, asi que la biblia es el unico sitio donde viven: el
    Planificador de escena las lee de aqui para construir la ficha, y el Escritor
    las necesita para la regla de dominio 10. Si no estan, no hay ficha.
    """
    await planificar_obra(sesion, _arquitecto(_outline(_diez_capitulos())), obra.id)

    biblia = (await sesion.execute(select(VersionObra))).scalars().one().biblia
    assert biblia["persona"] == Persona.TERCERA_LIMITADA.value == "3ª limitada"
    assert biblia["tiempo_verbal"] == TiempoVerbal.PASADO.value == "pasado"
    assert biblia["nivel_de_calor"] == obra.nivel_de_calor


async def test_una_biblia_sin_parametros_de_discurso_es_error_de_dominio(sesion, obra):
    """Una biblia sin ellos deja al Planificador sin poder construir la ficha."""
    crudo = json.dumps({"biblia": {"protagonista": "Nadia"}, "capitulos": _diez_capitulos()})

    with pytest.raises(DiscursoNoDeclarado):
        await planificar_obra(sesion, _arquitecto(crudo), obra.id)


async def test_una_persona_narrativa_que_no_esta_en_el_documento_es_error_de_dominio(sesion, obra):
    """El conjunto de `definitions.md` §5 es cerrado, y la grafia es la suya:
    «tercera persona limitada» no es `3ª limitada`, y quien la lea despues no
    sabria compararla."""
    crudo = _outline(_diez_capitulos(), persona="tercera persona limitada")

    with pytest.raises(DiscursoNoDeclarado):
        await planificar_obra(sesion, _arquitecto(crudo), obra.id)


async def test_el_nivel_de_calor_lo_pone_la_obra_y_no_el_arquitecto(sesion, obra):
    """Regla de dominio 5, y `CLAUDE.md` §10: ninguna restriccion dura depende
    solo del prompt.

    El nivel de calor no es del Arquitecto: lo declaro el comprador y es columna
    de `obra`. Si el modelo devuelve otro, el que se guarda es el de la obra.
    """
    crudo = _outline(_diez_capitulos(), nivel_de_calor=4)

    await planificar_obra(sesion, _arquitecto(crudo), obra.id)

    biblia = (await sesion.execute(select(VersionObra))).scalars().one().biblia
    assert biblia["nivel_de_calor"] == obra.nivel_de_calor == 2


async def test_el_outline_tiene_diez_capitulos_con_su_plan(sesion, obra):
    """RF-PLA-02 y RF-PLA-04: los diez, y cada uno con POV, lugar, objetivo,
    obstaculo y giro de valor previsto."""
    plan = await planificar_obra(sesion, _arquitecto(_outline(_diez_capitulos())), obra.id)

    guardados = (await sesion.execute(select(Capitulo).order_by(Capitulo.numero))).scalars().all()
    assert [c.numero for c in guardados] == list(range(1, 11))
    assert all(c.pov_dominante for c in guardados)
    for capitulo in plan.outline.capitulos:
        assert capitulo.lugar
        assert capitulo.objetivo
        assert capitulo.obstaculo
        assert capitulo.valor_entrada != capitulo.valor_salida


async def test_un_beat_obligatorio_sin_asignar_es_error_de_dominio(sesion, obra):
    """CA-32, primer lado: un hito del contrato del genero que no esta en ningun
    capitulo no es un aviso, es que la novela no cumple el genero."""
    capitulos = _diez_capitulos()
    capitulos[7]["beat_de_genero"] = None

    with pytest.raises(BeatsMalAsignados) as fallo:
        await planificar_obra(sesion, _arquitecto(_outline(capitulos)), obra.id)

    assert fallo.value.sin_asignar == [BeatDeGenero.REVELACION_INTERIOR]
    assert fallo.value.duplicados == []


async def test_un_beat_obligatorio_en_dos_capitulos_es_error_de_dominio(sesion, obra):
    """CA-32, segundo lado: «exactamente uno» tambien se incumple por arriba.

    Un beat repetido deja otro fuera, y ademas rompe el orden, que es lo unico
    que `domain-knowledge.md` §8.1 dice que no admite excepcion.
    """
    capitulos = _diez_capitulos()
    capitulos[9]["beat_de_genero"] = BeatDeGenero.GRAN_GESTO.value

    with pytest.raises(BeatsMalAsignados) as fallo:
        await planificar_obra(sesion, _arquitecto(_outline(capitulos)), obra.id)

    assert fallo.value.duplicados == [BeatDeGenero.GRAN_GESTO]
    assert fallo.value.sin_asignar == [BeatDeGenero.HEA_HFN]


async def test_un_outline_rechazado_no_deja_nada_en_la_base(sesion, obra):
    """El outline se valida **antes** de escribir: media planificacion no sirve."""
    capitulos = _diez_capitulos()
    capitulos[7]["beat_de_genero"] = None

    with pytest.raises(BeatsMalAsignados):
        await planificar_obra(sesion, _arquitecto(_outline(capitulos)), obra.id)

    assert (await sesion.execute(select(Capitulo))).scalars().all() == []
    assert (await sesion.execute(select(VersionObra))).scalars().all() == []


async def test_nueve_capitulos_no_son_un_outline(sesion, obra):
    """RF-PLA-02: diez. `domain-knowledge.md` §8.1: «no hay capitulo de sobra»."""
    with pytest.raises(OutlineIncompleto):
        await planificar_obra(sesion, _arquitecto(_outline(_diez_capitulos()[:9])), obra.id)


async def test_dos_capitulos_con_el_mismo_numero_no_son_un_outline(sesion, obra):
    """Diez filas no bastan: «el capitulo 4» tiene que nombrar uno solo."""
    capitulos = _diez_capitulos()
    capitulos[4]["numero"] = 4

    with pytest.raises(OutlineIncompleto):
        await planificar_obra(sesion, _arquitecto(_outline(capitulos)), obra.id)


async def test_un_capitulo_sin_giro_de_valor_es_error_de_dominio(sesion, obra):
    """RF-PLA-04: el giro previsto. Un capitulo que entra y sale del mismo valor
    es relleno (`definitions.md` §4.1)."""
    capitulos = _diez_capitulos()
    capitulos[5]["valor_salida"] = capitulos[5]["valor_entrada"]

    with pytest.raises(GiroDeValorAusente) as fallo:
        await planificar_obra(sesion, _arquitecto(_outline(capitulos)), obra.id)

    assert fallo.value.capitulos == [6]


async def test_planificar_una_obra_que_no_existe_es_error_de_dominio(sesion):
    """Sin esto, un id inventado revienta contra la clave ajena con un 500."""
    with pytest.raises(ObraDesconocida):
        await planificar_obra(sesion, _arquitecto(_outline(_diez_capitulos())), 9999)


async def test_planificar_dos_veces_no_duplica_el_outline(sesion, obra):
    """`uq_capitulo_obra_numero` lo pararia con un `IntegrityError`, que es un
    500: la segunda llamada tiene que ser un error de dominio, no una averia."""
    crudo = _outline(_diez_capitulos())
    await planificar_obra(sesion, _arquitecto(crudo), obra.id)

    with pytest.raises(ObraYaPlanificada):
        await planificar_obra(sesion, _arquitecto(crudo), obra.id)


async def test_planificar_no_llama_al_modelo_si_la_obra_no_existe(sesion):
    """No se gasta cuota para descubrir que el id estaba mal escrito."""
    doble = DobleDeterminista({"# Arquitecto": _outline(_diez_capitulos())})

    with pytest.raises(ObraDesconocida):
        await planificar_obra(sesion, Arquitecto(doble), 9999)

    assert doble.llamadas == []
