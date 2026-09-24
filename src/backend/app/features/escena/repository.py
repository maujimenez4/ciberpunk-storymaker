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


async def ids_de_escenas_de_capitulo(sesion: AsyncSession, capitulo_id: int) -> list[int]:
    """Los identificadores de las escenas de un capitulo, **sin la fila**.

    Existe para que otra feature pueda resolver «que escenas tiene este
    capitulo» **sin importar `Escena`**. `escritura.consumo` lo necesitaba para
    sumar el coste de un capitulo, y lo hacia importando
    `app.features.escena.modelos` desde dentro de una funcion: eso rompe la
    regla 1 de `CLAUDE.md` §5.1 y el import diferido no lo arregla, solo lo
    esconde del arranque.

    **Devuelve `int` y no `Escena` a proposito.** Exportar el modelo por el
    `__init__` habria cerrado el contrato de import y abierto otro peor -§6:
    nunca se expone el modelo de base de datos-. Lo que cruza la frontera es un
    dato, no una fila con su sesion y sus relaciones detras.

    En plural aunque hoy sea una o ninguna (P-C): el que llama suma sobre el
    conjunto, asi que no tiene que enterarse el dia que sean varias.
    """
    return list(
        (await sesion.execute(select(Escena.id).where(Escena.capitulo_id == capitulo_id)))
        .scalars()
        .all()
    )


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
