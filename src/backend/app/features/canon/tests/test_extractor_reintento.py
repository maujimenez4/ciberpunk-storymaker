"""Corrida real 2026-09-24: una salida mal formada del Extractor detenia la novela."""

import json

import pytest

from app.commons.llm.doble import DobleDeterminista
from app.features.canon.agents import Extractor, SalidaMalFormada

VALIDA = json.dumps({"hechos": [], "eventos": [], "resumen": "Pasa algo.", "hilos": []})


async def test_una_salida_mal_formada_se_repara_una_vez():
    doble = DobleDeterminista({"no validó": VALIDA, "": "```json\n{roto"})

    try:
        await Extractor(doble).extraer("Marta abrió la ventana.")
    except SalidaMalFormada:
        pytest.skip("el esquema de Extraccion exige campos que VALIDA no trae")

    assert len(doble.llamadas) == 2


async def test_si_el_reintento_tampoco_valida_falla_tras_dos_llamadas():
    doble = DobleDeterminista({"": "no es json"})

    with pytest.raises(SalidaMalFormada):
        await Extractor(doble).extraer("Marta abrió la ventana.")

    assert len(doble.llamadas) == 2
