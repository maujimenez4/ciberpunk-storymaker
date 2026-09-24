"""P-2: los elementos obligatorios viven en su columna, no en el brief en bruto.

La regla de dominio 11 dice que todo elemento que el comprador pidio aparece en
al menos un capitulo. Quien lo comprueba es `cobertura_de_personalizacion`, y
hasta hoy leia los elementos de `entrevista.respuestas` —el JSON del brief tal y
como llego— porque **no se persistian en ninguna columna**.

Eso abre la forma de aprobar de balde que P-2 describe: una obra creada por
cualquier camino que no sea la entrevista no tiene elementos que cubrir, y
entonces la cobertura **dice que todo esta bien sin haber comprobado nada**. Es
el mismo modo de fallo que el comentario de `TARIFAS` en P-18: no una respuesta
equivocada, sino una respuesta que nadie calculo.

**El tercer test es el que cierra P-2.** Los dos primeros describen la columna y
caerian igual con la cobertura leyendo del brief; el tercero borra el brief en
bruto y exige que la cobertura siga contando.
"""

import json

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.escritura.novela import elementos_obligatorios_de
from app.features.obra.modelos import Obra


async def test_los_elementos_obligatorios_viven_en_su_columna(sesion: AsyncSession, obra: Obra):
    """Lo que el comprador pidio, en `obra`, sin pasar por la entrevista."""
    obra.elementos_obligatorios = ["el perro Luna", "el verano del 98"]
    await sesion.flush()

    # **Por SQL crudo a proposito.** Un `select(Obra)` devuelve el objeto del
    # mapa de identidad, asi que leeria el atributo que acabamos de poner en
    # memoria y pasaria aunque la columna no existiera. Lo comprobe: la primera
    # version de este test estaba en verde con el modelo sin tocar.
    fila = (
        await sesion.execute(
            text("SELECT elementos_obligatorios FROM obra WHERE id = :o"), {"o": obra.id}
        )
    ).scalar_one()
    assert json.loads(fila) == ["el perro Luna", "el verano del 98"]


async def test_una_obra_sin_elementos_no_puede_existir(sesion: AsyncSession):
    """P-2. Si puede existir, la cobertura aprueba sin comprobar nada.

    La restriccion vive en la base y no solo en el esquema de entrada por el
    mismo motivo que la de `palabra_prohibida.ambito`: una obra escrita por otra
    ruta —una migracion de datos, un script, un test— no tendria quien la parase.
    """
    sesion.add(
        Obra(
            titulo="Sin nada que cubrir",
            genero="romance",
            tono="calido",
            nivel_de_calor=2,
            elementos_obligatorios=[],
        )
    )
    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_la_cobertura_lee_la_columna_y_no_el_brief_en_bruto(sesion: AsyncSession, obra: Obra):
    """**El que cierra P-2.** Sin el brief en bruto, la cobertura sigue contando.

    Se borra la entrevista entera, que es de donde se leian hasta hoy. Si la
    lectura siguiera dependiendo de ella, esto devolveria cero elementos — y
    cero elementos no es «todo cubierto», es «no se comprobo nada», que es
    exactamente la forma de aprobar de balde que P-2 describe.
    """
    obra.elementos_obligatorios = ["el perro Luna", "el verano del 98"]
    await sesion.flush()
    await sesion.execute(text("DELETE FROM entrevista WHERE obra_id = :o"), {"o": obra.id})

    assert await elementos_obligatorios_de(sesion, obra_id=obra.id) == (
        "el perro Luna",
        "el verano del 98",
    )
