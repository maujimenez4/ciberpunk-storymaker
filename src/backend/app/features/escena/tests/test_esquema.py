"""El esquema de `escena`: la ficha, y la regla de dominio 1 escrita en la base."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.features.escena.modelos import Escena


async def test_una_escena_cuelga_de_su_capitulo_y_de_la_biblia_vigente(sesion, obra_con_outline):
    """RF-PLA-01: cada escena apunta a la `version_obra` vigente cuando se escribio."""
    escena = (await sesion.execute(select(Escena))).scalars().one()
    assert escena.capitulo_id == obra_con_outline.capitulos[0].id
    assert escena.version_obra_id == obra_con_outline.version_obra.id


async def test_una_escena_sin_giro_de_valor_no_entra(sesion, obra_con_outline):
    """Regla de dominio 1: el giro de valor no es nulo. Una escena sin el es relleno."""
    sesion.add(
        _escena(obra_con_outline, capitulo=1, valor_entrada="esperanza", valor_salida="esperanza")
    )
    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_una_escena_sin_pov_no_entra(sesion, obra_con_outline):
    """La otra mitad de la regla de dominio 1: exactamente un POV, y no en blanco."""
    sesion.add(_escena(obra_con_outline, capitulo=1, pov="   "))
    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_un_capitulo_no_puede_tener_dos_escenas(sesion, obra_con_outline):
    """P-C: hoy la cardinalidad es 1:1, y lo dice el esquema, no un convenio."""
    sesion.add(_escena(obra_con_outline, capitulo=0))
    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_un_resultado_que_no_existe_no_entra(sesion, obra_con_outline):
    """`definitions.md` §4.1 declara el conjunto, y es cerrado."""
    sesion.add(_escena(obra_con_outline, capitulo=1, resultado="quiza"))
    with pytest.raises(IntegrityError):
        await sesion.flush()


@pytest.mark.parametrize("distancia", [0, 6])
async def test_una_distancia_psiquica_fuera_de_uno_a_cinco_no_entra(
    sesion, obra_con_outline, distancia: int
):
    """`definitions.md` §5: de 1 (lejana) a 5 (flujo interior)."""
    sesion.add(_escena(obra_con_outline, capitulo=1, distancia_psiquica=distancia))
    with pytest.raises(IntegrityError):
        await sesion.flush()


def _escena(obra_con_outline, capitulo: int, **cambios) -> Escena:
    campos = {
        "capitulo_id": obra_con_outline.capitulos[capitulo].id,
        "version_obra_id": obra_con_outline.version_obra.id,
        "orden_discurso": capitulo + 1,
        "tiempo_historia": "dia 2, tarde",
        "pov": "Nadia",
        "lugar": "El invernadero",
        "presentes": ["Nadia", "Teo"],
        "objetivo_del_pov": "Que Teo confiese",
        "obstaculo": "Teo no habla de su madre",
        "resultado": "si-pero",
        "valor_entrada": "confianza",
        "valor_salida": "sospecha",
        "extension_objetivo": 1200,
        "densidad_de_dialogo_objetivo": 0.4,
        "distancia_psiquica": 3,
    }
    campos.update(cambios)
    return Escena(**campos)
