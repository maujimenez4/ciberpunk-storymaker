"""Acceso a las tablas de la feature `obra`.

Hoy solo los hechos de canon que nacen del brief. Lo demas —la obra, el
destinatario, los vetos— lo escribe el cierre de la entrevista, que es de la
Tarea 9 y necesita errores de dominio que aun no existen.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.obra.modelos import HechoCanon


async def guardar_hechos_del_brief(
    sesion: AsyncSession,
    obra_id: int,
    enunciados: list[str],
    origen: str = "brief",
) -> list[HechoCanon]:
    """Un `HechoCanon` por enunciado, en el mismo orden, y sin escena de origen.

    `origen` es parametro y no constante porque la Fase 2 escribira por aqui los
    hechos que si nacen de una escena. **No se valida aqui:** de la coherencia
    entre `origen` y `escena_de_origen` responde el `CheckConstraint` de la
    Tarea 4 (regla de dominio 4), y repetir la regla en Python es tener dos
    sitios donde puede divergir. El `flush` no es de conveniencia: es lo que
    pone esa restriccion en el camino de escritura en vez de dejarla para el
    `commit` de quien llame.

    Un enunciado en blanco no es un hecho: no se escribe (R-2). Lo que si tiene
    texto entra tal cual, sin recortar, porque es la palabra del comprador.
    """
    hechos = [
        HechoCanon(
            obra_id=obra_id,
            enunciado=enunciado,
            origen=origen,
            escena_de_origen=None,
        )
        for enunciado in enunciados
        if enunciado.strip()
    ]
    if not hechos:
        return []
    sesion.add_all(hechos)
    await sesion.flush()
    return hechos
