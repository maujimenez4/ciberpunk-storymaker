"""RF-PLA-04: el plan dramatico de cada capitulo se PERSISTE, no solo se devuelve.

Lo destapo el agente de T3 al cerrar la ola 2. El requisito pide que cada
capitulo lleve POV, lugar, objetivo, obstaculo y giro de valor previsto; la
tabla que T2 creo tenia el POV y ninguno de los otros cuatro. El outline se
producia, se validaba y la API lo devolvia entero -- y se perdia al guardar.

Importa mas de lo que parece: T6 llena la capa Estructural del paquete con
«outline y beats del capitulo», y sin estas columnas no habia de donde leerlos
salvo de `escena`, que escribe T4 leyendo el outline. Circulo.
"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.obra.modelos import Obra
from app.features.outline.modelos import Capitulo


def _capitulo(obra_id: int, **cambios: object) -> Capitulo:
    campos: dict[str, object] = {
        "obra_id": obra_id,
        "numero": 1,
        "pov_dominante": "Nadia",
        "gancho_de_apertura": "Una carta sin remite",
        "tipo_de_corte_final": "pregunta",
        "extension_objetivo": 1200,
        "lugar": "Cadiz, el muelle",
        "objetivo": "Encontrar a quien la escribio",
        "obstaculo": "Nadie recuerda el nombre",
        "giro_de_valor_previsto": "esperanza -> sospecha",
    }
    campos.update(cambios)
    return Capitulo(**campos)  # type: ignore[arg-type]


async def test_el_capitulo_guarda_los_cinco_campos_de_rf_pla_04(sesion: AsyncSession):
    obra = Obra(titulo="X", genero="romance", tono="calido", nivel_de_calor=2)
    sesion.add(obra)
    await sesion.flush()

    sesion.add(_capitulo(obra.id))
    await sesion.flush()

    guardado = (await sesion.get(Capitulo, 1)) if False else None
    del guardado
    fila = (await sesion.execute(Capitulo.__table__.select())).mappings().one()
    assert fila["pov_dominante"] == "Nadia"
    assert fila["lugar"] == "Cadiz, el muelle"
    assert fila["objetivo"] == "Encontrar a quien la escribio"
    assert fila["obstaculo"] == "Nadie recuerda el nombre"
    assert fila["giro_de_valor_previsto"] == "esperanza -> sospecha"


@pytest.mark.parametrize("campo", ["lugar", "objetivo", "obstaculo", "giro_de_valor_previsto"])
async def test_ninguno_de_los_cuatro_admite_quedarse_vacio(sesion: AsyncSession, campo: str):
    """Un capitulo sin obstaculo no es un capitulo con un hueco: es relleno.

    Es el mismo argumento que `definitions.md` §4.1 da para el giro de valor de
    la escena, y la razon por la que R-6 de la Fase 1 rechazaba el elemento
    obligatorio vacio: una cadena vacia pasa cualquier validador posterior.
    """
    obra = Obra(titulo="X", genero="romance", tono="calido", nivel_de_calor=2)
    sesion.add(obra)
    await sesion.flush()

    sesion.add(_capitulo(obra.id, **{campo: ""}))
    with pytest.raises(IntegrityError):
        await sesion.flush()
