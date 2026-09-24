"""El corte del capitulo es uno de tres, y el Arquitecto tiene un reintento dirigido.

Los destapo la primera corrida real desde el frontend (2026-09-24): el prompt
pedia `tipo_de_corte_final` como «como corta — en tension, en pregunta o en
revelacion», el modelo contesto con una frase, y los diez capitulos murieron en
`max_length=60`. Un intento dio 409, el siguiente 500, y cada uno costo al
comprador tres minutos y un clic. `definitions.md` §4.1 ya decia que el corte
es uno de tres; ni el prompt ni el esquema lo cerraban.
"""

import json
from typing import Any

import pytest

from app.commons.llm.doble import DobleDeterminista
from app.features.outline.agents import (
    MARCA_DE_REPARACION,
    PLANTILLA_V2,
    Arquitecto,
    SalidaMalFormada,
)
from app.features.outline.schemas import TipoDeCorte
from app.features.outline.tests.test_arquitecto import BRIEF, outline_crudo


def _con_corte(corte: str) -> str:
    crudo: dict[str, Any] = json.loads(outline_crudo())
    for capitulo in crudo["capitulos"]:
        capitulo["tipo_de_corte_final"] = corte
    return json.dumps(crudo)


def test_la_plantilla_declara_los_tres_cortes_con_su_literal():
    """`CLAUDE.md` §2: el mismo literal en el prompt y en el esquema."""
    for corte in TipoDeCorte:
        assert f"`{corte.value}`" in PLANTILLA_V2


@pytest.mark.parametrize(
    ("dicho", "esperado"),
    [
        ("pregunta", TipoDeCorte.PREGUNTA),
        ("revelación", TipoDeCorte.REVELACION),
        ("Corta en pregunta: ¿quién escribió la carta que nadie firmó?", TipoDeCorte.PREGUNTA),
        ("Termina en TENSION, con la puerta a medio abrir", TipoDeCorte.TENSION),
    ],
)
async def test_un_corte_que_nombra_uno_solo_de_los_tres_se_normaliza(dicho, esperado):
    """Una frase que nombra exactamente un corte dice cual es; se guarda el literal."""
    outline = await Arquitecto(DobleDeterminista({"# Arquitecto": _con_corte(dicho)})).planificar(
        BRIEF
    )

    assert {c.tipo_de_corte_final for c in outline.capitulos} == {esperado}


@pytest.mark.parametrize(
    "dicho",
    ["tensión y después una revelación", "se queda dormida en el sofá"],
)
async def test_un_corte_ambiguo_o_ajeno_es_un_fallo(dicho):
    """Dos cortes a la vez, o ninguno, no se adivinan: el agente no hizo su trabajo."""
    arquitecto = Arquitecto(DobleDeterminista({"# Arquitecto": _con_corte(dicho)}))

    with pytest.raises(SalidaMalFormada):
        await arquitecto.planificar(BRIEF)


async def test_una_salida_mal_formada_se_repara_una_vez_con_el_motivo_concreto():
    """`CLAUDE.md` §15: el reintento lleva el defecto concreto, no «mejóralo»."""
    mala = json.loads(outline_crudo())
    mala["capitulos"][2]["extension_objetivo"] = 4000
    doble = DobleDeterminista(
        {MARCA_DE_REPARACION: outline_crudo(), "# Arquitecto": json.dumps(mala)}
    )

    outline = await Arquitecto(doble).planificar(BRIEF)

    assert [c.numero for c in outline.capitulos] == list(range(1, 11))
    assert len(doble.llamadas) == 2
    reintento, _ = doble.llamadas[1]
    assert "capitulos.2.extension_objetivo" in reintento


async def test_si_la_reparacion_tampoco_valida_es_un_fallo_tras_dos_llamadas():
    """Un reintento, no un bucle: el coste de CU-02 sigue siendo previsible."""
    doble = DobleDeterminista({"# Arquitecto": "Aqui tienes el outline:"})

    with pytest.raises(SalidaMalFormada):
        await Arquitecto(doble).planificar(BRIEF)

    assert len(doble.llamadas) == 2
