"""Lo que el Arquitecto recibe, y por que se comprueba aparte.

**El hallazgo de la primera corrida real, fijado. 2026-09-24.**

`DatosDeObra.como_brief()` pasaba cuatro campos -- titulo, genero, tono y nivel
de calor -- y el Arquitecto devolvio esto:

    "titulo": "Novela para [DESTINATARIO_PERSONALIZADO]"
    "premisa": "Elena y Carlos se encuentran en un cafe..."

Un marcador de posicion y dos personajes inventados. El modelo no se equivoco:
se le pidio personalizar y no se le dio con que.

**Ningun test lo veia** porque todos los del outline construyen el brief a mano
o usan dobles: el agente recibia lo que el test le ponia, no lo que el
repositorio entrega. Estos tests miran justo esa juntura.

Dos reglas del proyecto dependen de ella:

- `CLAUDE.md` §1: «la novela es correcta y podria ser de cualquiera» es un modo
  de fallo declarado, y con cuatro campos era el resultado garantizado.
- **Regla de dominio 11**: todo elemento obligatorio aparece en al menos un
  capitulo. Si no llega al Arquitecto, no hay outline que lo contenga.
"""

import json
import re

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.outline.agents import PLANTILLA_V2
from app.features.outline.repository import leer_obra

BRIEF = {
    "nombre": "Marta",
    "edad": 34,
    "rasgos": ["terca", "curiosa"],
    "recuerdos": ["el verano en Cadiz"],
    "obligatorios": ["el perro Luna", "la bufanda roja"],
}


@pytest.fixture
async def obra_de_marta(sesion: AsyncSession) -> int:
    """Una obra con destinatario y elementos obligatorios, por SQL.

    Por SQL y no por el modelo porque esto prueba **la lectura**: construirla
    con el ORM de `obra` ataria el test a la forma de una tabla de otra
    feature, que es lo que el repositorio evita a proposito.
    """
    await sesion.execute(
        text(
            "INSERT INTO destinatario (id, nombre, edad, rasgos, recuerdos_aportados) "
            "VALUES (1, :nombre, :edad, :rasgos, :recuerdos)"
        ),
        {
            "nombre": BRIEF["nombre"],
            "edad": BRIEF["edad"],
            "rasgos": json.dumps(BRIEF["rasgos"]),
            "recuerdos": json.dumps(BRIEF["recuerdos"]),
        },
    )
    await sesion.execute(
        text(
            "INSERT INTO obra (id, titulo, genero, tono, nivel_de_calor, "
            "elementos_obligatorios, destinatario_id) "
            "VALUES (99, 'Novela para Marta', 'romance', 'calido', 2, :obligatorios, 1)"
        ),
        {"obligatorios": json.dumps(BRIEF["obligatorios"])},
    )
    await sesion.flush()
    return 99


async def test_el_brief_lleva_al_destinatario(sesion: AsyncSession, obra_de_marta: int) -> None:
    """Sin esto la novela es correcta y podria ser de cualquiera (§1)."""
    brief = (await leer_obra(sesion, obra_de_marta)).como_brief()

    destinatario = brief.get("destinatario")
    assert destinatario is not None, "el Arquitecto no sabe para quien es la novela"
    assert destinatario["nombre"] == "Marta"
    assert destinatario["edad"] == 34
    assert "terca" in destinatario["rasgos"]
    assert "el verano en Cadiz" in destinatario["recuerdos_aportados"]


async def test_el_brief_lleva_los_elementos_obligatorios(
    sesion: AsyncSession, obra_de_marta: int
) -> None:
    """Regla de dominio 11: si no llegan aqui, no hay capitulo que los narre."""
    brief = (await leer_obra(sesion, obra_de_marta)).como_brief()

    assert brief["elementos_obligatorios"] == ["el perro Luna", "la bufanda roja"]


async def test_el_brief_no_lleva_los_vetos(sesion: AsyncSession, obra_de_marta: int) -> None:
    """`CLAUDE.md` §11: los vetos son guardarrailes y se aplican **en codigo**.

    Meterlos en el prompt del Arquitecto los convertiria en una sugerencia, y
    una regla de seguridad que depende de que el modelo obedezca no es una
    regla. Se comprueban despues, sobre el capitulo, en el hook.
    """
    brief = (await leer_obra(sesion, obra_de_marta)).como_brief()

    assert "vetos" not in brief


async def test_una_obra_sin_destinatario_se_puede_planificar(sesion: AsyncSession) -> None:
    """`obra.destinatario_id` es 0..1, asi que la lectura no puede exigirlo.

    Con un `JOIN` en vez de un `LEFT JOIN`, la obra sin destinatario
    desapareceria de la consulta y no se podria planificar -- peor que
    planificarla sin el.
    """
    await sesion.execute(
        text(
            "INSERT INTO obra (id, titulo, genero, tono, nivel_de_calor, elementos_obligatorios) "
            "VALUES (98, 'Sin destinatario', 'romance', 'calido', 1, '[\"un faro\"]')"
        )
    )
    await sesion.flush()

    datos = await leer_obra(sesion, 98)

    assert datos is not None
    # `.get` y no `[...]`: sin destinatario la clave **no esta**, y con
    # corchetes el test moriria de `KeyError` en vez de comprobar lo suyo.
    assert datos.como_brief().get("destinatario") is None


async def test_lo_que_el_prompt_promete_usar_es_lo_que_el_brief_entrega(
    sesion: AsyncSession, obra_de_marta: int
) -> None:
    """**La correspondencia prompt ↔ repositorio**, que es lo que fallaba.

    El prompt del Arquitecto nombra los campos del brief que va a usar. Si
    nombra uno que el repositorio no entrega, el modelo rellena el hueco -- y
    eso fue exactamente `[DESTINATARIO_PERSONALIZADO]`.

    Se comprueba sobre las claves de primer nivel del brief, que son las que el
    prompt interpola. No sobre la prosa: el prompt se reescribe, la
    correspondencia no debe romperse al reescribirlo.
    """
    brief = (await leer_obra(sesion, obra_de_marta)).como_brief()

    # Lo que el prompt nombra entre llaves o como `campo`, en su bloque de brief.
    citados = set(re.findall(r"`([a-z_]+)`", PLANTILLA_V2))
    del_brief = citados & {
        "titulo",
        "genero",
        "tono",
        "nivel_de_calor",
        "elementos_obligatorios",
        "destinatario",
    }

    faltan = del_brief - set(brief)
    assert not faltan, (
        f"el prompt del Arquitecto nombra {sorted(faltan)} y el repositorio no lo entrega. "
        f"El modelo rellenara el hueco: asi salio `[DESTINATARIO_PERSONALIZADO]`."
    )
