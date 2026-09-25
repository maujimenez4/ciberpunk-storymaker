"""Volver a la version anterior sin destruir la que se deja (plan-5 T6).

RF-PET-08 en dos frases: «revertir devuelve la anterior a vigente y **no borra**
la revertida». La segunda es la que cuesta, porque borrar es mas comodo.

**Revertir no es publicar.** No crea `VersionPublicada`, no pasa por Lean y no
toca el cuadro de defectos: mueve una bandera. Por eso vive en su fichero y no
dentro del que publica.

`version_vigente` vive aqui a proposito: **leer** cual es la vigente y
**cambiar** cual es la vigente son la misma regla vista por sus dos caras.
"""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.domain.errores import ErrorDeDominio, RecursoDesconocido
from app.features.manuscrito.modelos import VersionPublicada


async def version_vigente(sesion: AsyncSession, *, obra_id: int) -> VersionPublicada | None:
    """La version que el lector tiene delante. `None` si la obra no se ha publicado.

    **Se pregunta por la bandera y no por `MAX(ordinal)`:** tras la primera
    reversion dejan de coincidir, porque la revertida conserva su ordinal.
    """
    return (
        await sesion.execute(
            select(VersionPublicada).where(
                VersionPublicada.obra_id == obra_id, VersionPublicada.vigente.is_(True)
            )
        )
    ).scalar_one_or_none()


class VersionDesconocida(RecursoDesconocido):
    def __init__(self, version_publicada_id: int) -> None:
        self.version_publicada_id = version_publicada_id
        super().__init__(f"La version publicada {version_publicada_id} no existe")


class VersionYaVigente(ErrorDeDominio):
    """Se pidio revertir a la version que ya se esta leyendo.

    Se rechaza en vez de no hacer nada: responder 200 sin cambiar nada es
    indistinguible de haber revertido.
    """

    def __init__(self, version_publicada_id: int) -> None:
        self.version_publicada_id = version_publicada_id
        super().__init__(f"La version {version_publicada_id} ya es la vigente")


async def revertir(
    sesion: AsyncSession, *, obra_id: int, version_publicada_id: int
) -> VersionPublicada:
    """RF-PET-08. Apaga la vigente, enciende la pedida, y no borra ninguna.

    No hace `commit`: escribe en la transaccion de quien llama.
    """
    version = await sesion.get(VersionPublicada, version_publicada_id)
    if version is None or version.obra_id != obra_id:
        # La de otra obra es «desconocida» y no «prohibida»: decir que existe
        # pero es de otro ya es contar algo de otra obra.
        raise VersionDesconocida(version_publicada_id)
    if version.vigente:
        raise VersionYaVigente(version_publicada_id)

    # Apagar antes de encender: el indice parcial admite una sola vigente.
    await sesion.execute(
        update(VersionPublicada)
        .where(VersionPublicada.obra_id == obra_id, VersionPublicada.vigente.is_(True))
        .values(vigente=False)
    )
    version.vigente = True
    await sesion.flush()
    return version
