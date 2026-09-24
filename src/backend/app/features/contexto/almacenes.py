"""`VectorStore` y sus dos implementaciones (`architecture.md` §5.5).

Las dos leen **la misma tabla**, `embedding`, y devuelven lo mismo. Lo unico
que cambia es donde se calcula el coseno: dentro de SQLite cuando la extension
esta, y en Python cuando no. Por eso no hay «modo completo» y «modo reducido»:
hay un modo rapido y otro que no lo es tanto (RNF-FIA-02, CA-28).

**La tabla vive en `canon`, no aqui**, porque quien la escribe es el Extractor
(`architecture.md` §4.3); quien la lee es esta feature. Se entra por el
`__init__.py` de `canon`, que es la unica puerta (`CLAUDE.md` §5.1).

**Y hay una regla que los dos almacenes cumplen y que sostiene `CA-8`:** el
almacen recibe la lista de candidatos y **no puede ampliarla**. El orden
semantico va sobre el conjunto **ya filtrado**; si el almacen pudiera traer una
escena que el filtro descarto, filtrar antes no serviria de nada.

**Lo que esto no da, y la spec lo dice sin suavizar:** el vector de consulta lo
calcula el mismo proveedor que genera, asi que la ordenacion semantica es una
**senal con varianza**. Dos ensamblados del mismo estado pueden devolver otro
orden en la capa de memoria recuperada. Las otras siete siguen deterministas, y
`ejecucion` guarda los IDs recuperados: una ejecucion concreta es **auditable
aunque no repetible**. Se cambio a proposito, sabiendo lo que costaba.
"""

import sqlite3
import warnings
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import Select, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.db.vectores import (
    AvisoDeDegradacion,
    cargar_extension,
    distancias_coseno,
    empaquetar_vector,
    extension_disponible,
    matriz_de_vectores,
)
from app.features.canon import Embedding


@dataclass(frozen=True, slots=True)
class Vecino:
    """Un fragmento indexado con su distancia a la consulta.

    Lleva `embedding_id` **y** `escena_id`: el primero identifica lo que entro
    en el paquete, el segundo es lo que el filtro estructural y la recencia
    saben mirar.
    """

    escena_id: int
    embedding_id: int
    fragmento: str
    distancia: float


class VectorStore(Protocol):
    """La interfaz. `modo` no es decorativo: sale en el aviso y en los tests."""

    modo: str

    async def vecinos(
        self, consulta: Sequence[float], candidatos: Sequence[int], limite: int
    ) -> list[Vecino]:
        """Los `limite` fragmentos mas cercanos a `consulta` **de entre `candidatos`**."""
        ...


def _dimension_incompatible(esperada: int, encontrada: int) -> ValueError:
    return ValueError(
        f"El vector de consulta tiene dimension {esperada} y el indice {encontrada}: "
        "no son comparables"
    )


def _seleccion(candidatos: Sequence[int]) -> Select[tuple[int, int | None, str, int]]:
    """Las columnas que los dos almacenes necesitan, acotadas a los candidatos."""
    return select(
        Embedding.id,
        Embedding.escena_id,
        Embedding.fragmento,
        Embedding.dimension,
    ).where(Embedding.escena_id.in_(candidatos))


class AlmacenFuerzaBruta:
    """BLOB mas **NumPy**: lee los vectores de los candidatos y ordena en memoria.

    Es el que hace que el sistema arranque en una maquina sin la extension.

    **Y usa NumPy, invirtiendo lo que decia aqui hasta la Fase 3.** El
    argumento anterior era que «una dependencia binaria mas en el unico camino
    que existe para no depender de una dependencia binaria es cambiar de amo»,
    y confundia dos cosas: `sqlite-vec` es una **extension de SQLite** que puede
    no cargar en la maquina de destino, y NumPy es una dependencia de Python
    como las otras trece que P-01 aprobo en bloque. Depender de NumPy no
    reintroduce el problema del que esta clase escapa.

    Lo que decide, sin embargo, no es eso: `architecture.md` §5.5 y §2 dicen
    «BLOB + NumPy» desde antes de que esta clase existiera, y `CLAUDE.md` §3.3
    dice que **el codigo nunca gana a un documento**. Decidido en el plan 3, no
    aqui dentro.
    """

    modo = "fuerza bruta"

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def vecinos(
        self, consulta: Sequence[float], candidatos: Sequence[int], limite: int
    ) -> list[Vecino]:
        if not candidatos:
            return []

        filas = [
            fila
            for fila in (
                await self._sesion.execute(_seleccion(candidatos).add_columns(Embedding.vector))
            ).all()
            if fila[1] is not None
        ]
        if not filas:
            return []

        for _id, _escena_id, _fragmento, dimension, _blob in filas:
            if dimension != len(consulta):
                raise _dimension_incompatible(len(consulta), dimension)

        # Una operacion y no un bucle: el conjunto ya filtrado entra entero.
        distancias = distancias_coseno(
            consulta, matriz_de_vectores([fila[4] for fila in filas], len(consulta))
        )

        vecinos = [
            Vecino(
                escena_id=escena_id,
                embedding_id=id_,
                fragmento=fragmento,
                distancia=float(distancia),
            )
            for (id_, escena_id, fragmento, _dimension, _blob), distancia in zip(
                filas, distancias, strict=True
            )
        ]

        # El desempate por `embedding_id` no es cosmetico: sin el, dos
        # fragmentos a la misma distancia saldrian en el orden que diera la
        # base, y el modo de fuerza bruta dejaria de coincidir con el otro.
        vecinos.sort(key=lambda vecino: (vecino.distancia, vecino.embedding_id))
        return vecinos[:limite]


class AlmacenSqliteVec:
    """El coseno lo calcula SQLite con `vec_distance_cosine`, sobre la misma columna.

    **No hay tabla `vec0` ni indice aparte**, y es deliberado: lo que se usa de
    la extension son sus funciones escalares sobre el BLOB que `embedding` ya
    guarda. Asi el esquema es uno solo -- con extension y sin ella --, no hay
    migracion que dependa de un binario opcional, y el indice no se puede
    desincronizar de la tabla porque **es** la tabla.
    """

    modo = "sqlite-vec"

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def vecinos(
        self, consulta: Sequence[float], candidatos: Sequence[int], limite: int
    ) -> list[Vecino]:
        if not candidatos:
            return []

        await cargar_extension(self._sesion)

        dimensiones = (
            await self._sesion.execute(
                _seleccion(candidatos).with_only_columns(Embedding.dimension)
            )
        ).scalars()
        for dimension in set(dimensiones):
            if dimension != len(consulta):
                raise _dimension_incompatible(len(consulta), dimension)

        distancia = func.vec_distance_cosine(Embedding.vector, empaquetar_vector(consulta))
        filas = (
            await self._sesion.execute(
                _seleccion(candidatos)
                .add_columns(distancia.label("distancia"))
                .order_by(distancia, Embedding.id)
                .limit(limite)
            )
        ).all()

        return [
            Vecino(
                escena_id=escena_id,
                embedding_id=id_,
                fragmento=fragmento,
                distancia=float(medida),
            )
            for id_, escena_id, fragmento, _dimension, medida in filas
            if escena_id is not None
        ]


async def crear_almacen(sesion: AsyncSession) -> VectorStore:
    """El almacen que toca, con aviso si no es el que se esperaba (R-6).

    La deteccion de `extension_disponible()` se hace sobre una base propia, asi
    que puede acertar y fallar la carga sobre **esta** conexion. Ese caso
    tambien degrada en vez de reventar, y tambien avisa: el sistema arranca.
    """
    if not extension_disponible():
        return AlmacenFuerzaBruta(sesion)

    try:
        await cargar_extension(sesion)
    # Las cuatro formas en que una extension no llega a cargar: el modulo que
    # falta, el binario que no abre, el interprete sin carga de extensiones y
    # el fallo que SQLAlchemy envuelve. Un `except Exception` aqui taparia
    # ademas los errores de programa, que **no** deben degradar en silencio.
    except (
        AttributeError,
        ImportError,
        OSError,
        sqlite3.Error,
        SQLAlchemyError,
    ) as exc:  # pragma: no cover
        warnings.warn(
            f"sqlite-vec se detecto pero no carga en esta conexion ({exc}). "
            "Se sigue con el almacen de fuerza bruta.",
            AvisoDeDegradacion,
            stacklevel=2,
        )
        return AlmacenFuerzaBruta(sesion)

    return AlmacenSqliteVec(sesion)
