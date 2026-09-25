"""La peticion de cambio como fila: registrarla, leerla y cerrarla (plan-5 T7).

**Aqui no se orquesta nada.** Atender una peticion compone `canon` (corregir el
hecho), `escritura` (regenerar) y esta feature (clasificar, publicar), y
`escritura -> canon -> obra -> manuscrito` ya existe: si la orquestacion viviera
aqui, `manuscrito -> escritura` cerraria un ciclo entre features (`CLAUDE.md`
§5.1 regla 5). Vive en `escritura/peticion.py`, que ya dependia de las otras
dos, y esta feature conserva lo que es suyo: la tabla y sus estados.

La fila no cruza la frontera: sale `Peticion`, una vista inmutable.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.domain.errores import OperacionNoPermitida, RecursoDesconocido
from app.features.manuscrito.modelos import PeticionDeCambio, VersionPublicada
from app.features.manuscrito.reversion import version_vigente

EN_CURSO = ("registrada", "regenerando")
TERMINADAS = ("atendida", "descartada")


class PeticionDesconocida(RecursoDesconocido):
    def __init__(self, peticion_id: int) -> None:
        self.peticion_id = peticion_id
        super().__init__(f"La peticion {peticion_id} no existe")


@dataclass(frozen=True, slots=True)
class Peticion:
    """Lo que se sabe de una peticion, sin la fila de SQLAlchemy."""

    id: int
    obra_id: int
    version_publicada_id: int
    hecho_canon_id: int
    texto_pedido: str
    estado: str
    resultado: str | None
    hecho_nuevo_id: int | None
    version_producida_id: int | None
    run_id: str | None


def _vista(fila: PeticionDeCambio) -> Peticion:
    return Peticion(
        id=fila.id,
        obra_id=fila.obra_id,
        version_publicada_id=fila.version_publicada_id,
        hecho_canon_id=fila.hecho_canon_id,
        texto_pedido=fila.texto_pedido,
        estado=fila.estado,
        resultado=fila.resultado,
        hecho_nuevo_id=fila.hecho_nuevo_id,
        version_producida_id=fila.version_producida_id,
        run_id=fila.run_id,
    )


async def registrar_peticion(
    sesion: AsyncSession, *, obra_id: int, hecho_canon_id: int, texto_pedido: str
) -> Peticion:
    """RF-PET-01: el hecho, **la version de origen** y el texto pedido.

    La version de origen no la elige quien pide: es la vigente al registrar.
    """
    vigente = await version_vigente(sesion, obra_id=obra_id)
    if vigente is None:
        raise OperacionNoPermitida(
            f"La obra {obra_id} no tiene ninguna version publicada sobre la que pedir un cambio"
        )
    fila = PeticionDeCambio(
        obra_id=obra_id,
        version_publicada_id=vigente.id,
        hecho_canon_id=hecho_canon_id,
        texto_pedido=texto_pedido,
        estado="registrada",
    )
    sesion.add(fila)
    await sesion.flush()
    return _vista(fila)


async def _fila(sesion: AsyncSession, peticion_id: int) -> PeticionDeCambio:
    fila = await sesion.get(PeticionDeCambio, peticion_id, populate_existing=True)
    if fila is None:
        raise PeticionDesconocida(peticion_id)
    return fila


async def leer_peticion(sesion: AsyncSession, peticion_id: int) -> Peticion:
    return _vista(await _fila(sesion, peticion_id))


async def marcar_regenerando(sesion: AsyncSession, peticion_id: int, *, run_id: str) -> Peticion:
    """R-7: `regenerando` **antes** de la primera llamada, con su `run_id`."""
    fila = await _fila(sesion, peticion_id)
    fila.estado = "regenerando"
    fila.run_id = run_id
    await sesion.flush()
    return _vista(fila)


async def anotar_hecho_nuevo(sesion: AsyncSession, peticion_id: int, hecho_nuevo_id: int) -> None:
    fila = await _fila(sesion, peticion_id)
    fila.hecho_nuevo_id = hecho_nuevo_id
    await sesion.flush()


async def cerrar_peticion(
    sesion: AsyncSession,
    peticion_id: int,
    *,
    estado: str,
    resultado: str,
    version_producida_id: int | None = None,
) -> Peticion:
    """RF-PET-07: la peticion se conserva **con su resultado**, prospere o no."""
    if estado not in TERMINADAS:
        raise OperacionNoPermitida(f"«{estado}» no es un estado terminal de una peticion")
    fila = await _fila(sesion, peticion_id)
    fila.estado = estado
    fila.resultado = resultado[:500]
    fila.version_producida_id = version_producida_id
    await sesion.flush()
    return _vista(fila)


async def token_de_la_version(sesion: AsyncSession, version_publicada_id: int) -> str | None:
    """El enlace de una tirada: lo que la lectura necesita para abrir la nueva."""
    return (
        await sesion.execute(
            select(VersionPublicada.identificador_publico).where(
                VersionPublicada.id == version_publicada_id
            )
        )
    ).scalar_one_or_none()


async def peticion_en_curso(sesion: AsyncSession, *, obra_id: int) -> int | None:
    """La peticion viva mas reciente de la obra, o `None` (H-3 de la 002)."""
    return (
        await sesion.execute(
            select(PeticionDeCambio.id)
            .where(PeticionDeCambio.obra_id == obra_id, PeticionDeCambio.estado.in_(EN_CURSO))
            .order_by(PeticionDeCambio.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
