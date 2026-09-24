"""Acceso a la tabla `escena`: escribir la ficha y volver a leerla.

Nada mas cruza por aqui. El capitulo y la obra son de otras features, y una
feature solo importa de `commons/` y del `__init__.py` de otra (`CLAUDE.md`
§5.1): los ids llegan como datos, no como filas.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.escena.modelos import Escena
from app.features.escena.schemas import FichaDeEscena


async def obtener_escena_de_capitulo(sesion: AsyncSession, capitulo_id: int) -> Escena | None:
    """La escena del capitulo, o `None`. Hoy es una o ninguna (P-C)."""
    return (
        await sesion.execute(select(Escena).where(Escena.capitulo_id == capitulo_id))
    ).scalar_one_or_none()


async def guardar_ficha(sesion: AsyncSession, ficha: FichaDeEscena) -> Escena:
    """La ficha, como fila.

    No se guarda `restricciones`: `persona` y `tiempo_verbal` son de la biblia
    con la que se planifico —y `version_obra_id` dice cual— y `nivel_de_calor`
    es de la obra. Copiarlos aqui crearia una tercera copia que puede divergir
    de las otras dos.

    El `flush` no es de conveniencia: es lo que pone los `CheckConstraint` de la
    tabla —el POV unico y el giro de valor— en el camino de escritura, en vez de
    dejarlos para el `commit` de quien llame.
    """
    escena = Escena(
        capitulo_id=ficha.capitulo_id,
        version_obra_id=ficha.version_obra_id,
        orden_discurso=ficha.orden_discurso,
        tiempo_historia=ficha.tiempo_historia,
        elapsed_desde_anterior=ficha.elapsed_desde_anterior,
        pov=ficha.pov,
        lugar=ficha.lugar,
        presentes=list(ficha.presentes),
        mencionados=list(ficha.mencionados),
        objetivo_del_pov=ficha.objetivo_del_pov,
        obstaculo=ficha.obstaculo,
        resultado=ficha.resultado,
        valor_entrada=ficha.valor_entrada,
        valor_salida=ficha.valor_salida,
        extension_objetivo=ficha.extension_objetivo,
        densidad_de_dialogo_objetivo=ficha.densidad_de_dialogo_objetivo,
        distancia_psiquica=ficha.distancia_psiquica,
        beat_de_genero=ficha.beat_de_genero,
        planta=list(ficha.planta),
        paga=list(ficha.paga),
        revela=list(ficha.revela),
    )
    sesion.add(escena)
    await sesion.flush()
    return escena
