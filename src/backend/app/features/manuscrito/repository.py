"""Acceso a las tablas de la publicacion.

T1 deja aqui las dos lecturas que las demas tareas dan por hechas: por token,
que es como entra la lectura (T9), y por obra, que es como se sabe cual fue la
ultima tirada para encadenar la siguiente (T6, T7).

Escribir es de T6 -- publicar es atomico y se decide alli --, y por eso este
modulo no expone ningun `guardar`: media publicacion escrita desde dos sitios
distintos es exactamente lo que T6 existe para impedir.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.manuscrito.modelos import (
    CapituloPublicado,
    Dedicatoria,
    VersionPublicada,
)


async def version_por_token(
    sesion: AsyncSession, identificador_publico: str
) -> VersionPublicada | None:
    """La tirada a la que apunta un enlace repartido.

    Devuelve `None` en vez de lanzar: un token que no existe y un token que
    expiro son lo mismo para quien lee, y quien llama decide que responder.
    Lanzar aqui obligaria a distinguirlos en el mensaje, que es justo lo que no
    conviene decirle a quien esta probando tokens.
    """
    resultado = await sesion.execute(
        select(VersionPublicada).where(
            VersionPublicada.identificador_publico == identificador_publico
        )
    )
    return resultado.scalar_one_or_none()


async def ultima_version(sesion: AsyncSession, obra_id: int) -> VersionPublicada | None:
    """La tirada de ordinal mas alto, o `None` si la obra no se ha publicado.

    Es lo que T6 necesita para dar ordinal a la siguiente y rellenar
    `sucede_a_id`, y lo que T7 compara para calcular `cambiado`.
    """
    resultado = await sesion.execute(
        select(VersionPublicada)
        .where(VersionPublicada.obra_id == obra_id)
        .order_by(VersionPublicada.ordinal.desc())
        .limit(1)
    )
    return resultado.scalar_one_or_none()


async def capitulos_de(sesion: AsyncSession, version_id: int) -> list[CapituloPublicado]:
    """Los capitulos de una tirada, en orden de lectura."""
    resultado = await sesion.execute(
        select(CapituloPublicado)
        .where(CapituloPublicado.version_id == version_id)
        .order_by(CapituloPublicado.numero)
    )
    return list(resultado.scalars())


async def dedicatoria_de(sesion: AsyncSession, obra_id: int) -> Dedicatoria | None:
    """La dedicatoria de la obra, que la portada necesita y puede no existir."""
    resultado = await sesion.execute(select(Dedicatoria).where(Dedicatoria.obra_id == obra_id))
    return resultado.scalar_one_or_none()
