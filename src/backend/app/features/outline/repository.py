"""Acceso a las tablas de la feature `outline`: `version_obra` y `capitulo`.

**`obra` se lee por nombre de tabla, no importando su modelo.** Una feature solo
importa de `commons/` y del `__init__.py` de otra (`CLAUDE.md` §5.1), y el de
`obra` no exporta sus tablas. Es el mismo trato que la Tarea 2 le dio a las
claves ajenas —`capitulo.obra_id` apunta a `"obra.id"` por nombre, sin que las
dos features se conozcan—, y aqui se extiende a la lectura. La `table()` de
abajo **no es una tabla nueva**: no se declara sobre `Base.metadata`, asi que no
la ve `create_all` ni el `--autogenerate` de Alembic.
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import column, func, select, table
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.outline.modelos import Capitulo, VersionObra
from app.features.outline.schemas import CapituloDelOutline

_obra = table(
    "obra",
    column("id"),
    column("titulo"),
    column("genero"),
    column("tono"),
    column("nivel_de_calor"),
)


@dataclass(frozen=True)
class DatosDeObra:
    """Lo que el Arquitecto necesita saber de la obra para planificarla.

    Es un `dataclass` propio y no la fila cruda: lo que sale del repositorio no
    es un modelo de base de datos de otra feature, y asi el servicio no depende
    de la forma de una tabla que no es suya.
    """

    id: int
    titulo: str
    genero: str
    tono: str
    nivel_de_calor: int

    def como_brief(self) -> dict[str, Any]:
        """El brief que entra al prompt, sin el `id`: no es dato de la historia."""
        return {
            "titulo": self.titulo,
            "genero": self.genero,
            "tono": self.tono,
            "nivel_de_calor": self.nivel_de_calor,
        }


async def leer_obra(sesion: AsyncSession, obra_id: int) -> DatosDeObra | None:
    """`None` si no existe. Quien decide que hacer con eso es el servicio."""
    fila = (
        await sesion.execute(
            select(
                _obra.c.id,
                _obra.c.titulo,
                _obra.c.genero,
                _obra.c.tono,
                _obra.c.nivel_de_calor,
            ).where(_obra.c.id == obra_id)
        )
    ).first()
    if fila is None:
        return None
    return DatosDeObra(
        id=fila.id,
        titulo=fila.titulo,
        genero=fila.genero,
        tono=fila.tono,
        nivel_de_calor=fila.nivel_de_calor,
    )


async def cuenta_capitulos(sesion: AsyncSession, obra_id: int) -> int:
    """Cuantos capitulos tiene ya la obra. Cero significa «sin planificar»."""
    return (
        await sesion.execute(
            select(func.count()).select_from(Capitulo).where(Capitulo.obra_id == obra_id)
        )
    ).scalar_one()


async def siguiente_numero_de_version(sesion: AsyncSession, obra_id: int) -> int:
    """La biblia se versiona, no se edita (RF-PLA-01): la primera es la 1."""
    ultima = (
        await sesion.execute(
            select(func.max(VersionObra.numero)).where(VersionObra.obra_id == obra_id)
        )
    ).scalar_one()
    return 1 if ultima is None else int(ultima) + 1


async def guardar_outline(
    sesion: AsyncSession,
    obra_id: int,
    numero: int,
    biblia: dict[str, Any],
    capitulos: list[CapituloDelOutline],
) -> tuple[VersionObra, list[Capitulo]]:
    """La biblia congelada y sus capitulos, en una sola escritura.

    El `flush` no es de conveniencia: pone en el camino de escritura las
    restricciones de `capitulo` —el numero unico por obra, el rango de
    extension— en vez de dejarlas para el `commit` de quien llame.

    **El plan dramatico se persiste desde el cierre de la ola 2.** Lugar,
    objetivo, obstaculo y giro previsto son columnas de `capitulo` (RF-PLA-04);
    antes no lo eran y el outline se perdia al guardar. El `beat_de_genero`
    sigue viviendo en `escena`, que es de otra feature.
    """
    version = VersionObra(obra_id=obra_id, numero=numero, biblia=biblia)
    sesion.add(version)
    await sesion.flush()

    filas = [
        Capitulo(
            obra_id=obra_id,
            numero=capitulo.numero,
            titulo=capitulo.titulo,
            pov_dominante=capitulo.pov_dominante,
            gancho_de_apertura=capitulo.gancho_de_apertura,
            tipo_de_corte_final=capitulo.tipo_de_corte_final,
            extension_objetivo=capitulo.extension_objetivo,
            lugar=capitulo.lugar,
            objetivo=capitulo.objetivo,
            obstaculo=capitulo.obstaculo,
            # El giro previsto es el par entrada -> salida del Arquitecto.
            giro_de_valor_previsto=f"{capitulo.valor_entrada} -> {capitulo.valor_salida}",
        )
        for capitulo in capitulos
    ]
    sesion.add_all(filas)
    await sesion.flush()
    return version, filas
