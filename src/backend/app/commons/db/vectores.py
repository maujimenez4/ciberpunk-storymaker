"""Busqueda semantica tras una interfaz (RI-17, RI-20, RI-22, RD-07).

`CLAUDE.md` §4.2 hace una promesa fuerte: **el sistema nunca falla por falta de
extension vectorial**. Se cumple con dos implementaciones de `VectorStore` y una
deteccion en arranque que degrada y avisa.

Los dos almacenes leen y escriben **el mismo BLOB** de la tabla `fragmento`
(RD-07). Esa es la parte que permite que degradar no cueste un reindexado: si
cada uno tuviera su formato, quedarse sin extension obligaria a recalcular todos
los embeddings, que es justo lo que la promesa evita.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Protocol

import numpy as np

_log = logging.getLogger(__name__)


class ProveedorDeEmbeddings(Protocol):
    """RI-20: interfaz propia. Su consumo **no** cuenta contra el presupuesto
    de contexto, porque no viaja en el paquete: solo produce vectores."""

    def incrustar(self, texto: str) -> np.ndarray: ...


class DobleDeEmbeddings:
    """Determinista y sin red: el mismo texto da siempre el mismo vector.

    Existe porque RI-13 prohibe que la suite llame al proveedor real, y porque
    el proveedor de produccion sigue sin decidirse: la API de generacion no
    ofrece embeddings.
    """

    def __init__(self, dimension: int) -> None:
        self.dimension = dimension

    def incrustar(self, texto: str) -> np.ndarray:
        semilla = abs(hash(texto)) % (2**32)
        return np.random.default_rng(semilla).random(self.dimension).astype(np.float32)


class VectorStore(Protocol):
    def guardar(self, fragmento_id: str, vector: np.ndarray) -> None: ...

    def buscar(
        self, vector: np.ndarray, k: int, candidatos: set[str] | None = None
    ) -> list[str]: ...


class _AlmacenBase:
    """Lo comun a los dos: el mismo fichero, la misma tabla, el mismo BLOB."""

    def __init__(self, ruta: Path | str, dimension: int) -> None:
        self.ruta = str(ruta)
        self.dimension = dimension
        with self._conexion() as conexion:
            conexion.execute(
                "CREATE TABLE IF NOT EXISTS fragmento_vector ("
                " fragmento_id TEXT PRIMARY KEY,"
                " embedding BLOB NOT NULL,"
                " dimension INTEGER NOT NULL)"
            )

    def _conexion(self) -> sqlite3.Connection:
        return sqlite3.connect(self.ruta)

    def guardar(self, fragmento_id: str, vector: np.ndarray) -> None:
        if vector.shape != (self.dimension,):
            raise ValueError(
                f"el vector tiene dimension {vector.shape} y el almacen espera "
                f"({self.dimension},): cambiar de proveedor exige reindexar"
            )
        with self._conexion() as conexion:
            conexion.execute(
                "INSERT OR REPLACE INTO fragmento_vector VALUES (?, ?, ?)",
                (fragmento_id, vector.astype(np.float32).tobytes(), self.dimension),
            )

    def _todos(self, candidatos: set[str] | None) -> list[tuple[str, np.ndarray]]:
        with self._conexion() as conexion:
            filas = conexion.execute(
                "SELECT fragmento_id, embedding FROM fragmento_vector"
            ).fetchall()
        return [
            (fid, np.frombuffer(blob, dtype=np.float32))
            for fid, blob in filas
            if candidatos is None or fid in candidatos
        ]


class BruteForceStore(_AlmacenBase):
    """NumPy sobre los BLOB. Utilizable hasta unos 10.000 fragmentos (RNF-REN-04)."""

    def buscar(
        self, vector: np.ndarray, k: int, candidatos: set[str] | None = None
    ) -> list[str]:
        filas = self._todos(candidatos)
        if not filas:
            return []
        matriz = np.vstack([v for _, v in filas])
        normas = np.linalg.norm(matriz, axis=1) * np.linalg.norm(vector)
        similitud = np.where(
            normas > 0, matriz @ vector / np.where(normas > 0, normas, 1), 0.0
        )
        orden = np.argsort(-similitud)[:k]
        return [filas[i][0] for i in orden]


class SqliteVecStore(_AlmacenBase):
    """KNN con `vec0`. Escribe **ademas** el mismo BLOB que el otro almacen.

    Esa duplicacion es deliberada y es lo que cumple RD-07: la tabla `vec0` es un
    indice, no la fuente. Si manana la extension deja de cargar, `BruteForceStore`
    lee los mismos BLOB y el sistema sigue, sin reindexar nada.
    """

    def __init__(self, ruta: Path | str, dimension: int) -> None:
        super().__init__(ruta, dimension)
        with self._conexion() as conexion:
            conexion.execute(
                f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_fragmento USING vec0("
                f" embedding float[{dimension}])"
            )

    def _conexion(self) -> sqlite3.Connection:
        conexion = sqlite3.connect(self.ruta)
        conexion.enable_load_extension(True)
        import sqlite_vec

        sqlite_vec.load(conexion)
        conexion.enable_load_extension(False)
        return conexion

    def guardar(self, fragmento_id: str, vector: np.ndarray) -> None:
        super().guardar(fragmento_id, vector)
        with self._conexion() as conexion:
            fila = conexion.execute(
                "SELECT rowid FROM fragmento_vector WHERE fragmento_id = ?",
                (fragmento_id,),
            ).fetchone()
            conexion.execute("DELETE FROM vec_fragmento WHERE rowid = ?", (fila[0],))
            conexion.execute(
                "INSERT INTO vec_fragmento (rowid, embedding) VALUES (?, ?)",
                (fila[0], vector.astype(np.float32).tobytes()),
            )

    def buscar(
        self, vector: np.ndarray, k: int, candidatos: set[str] | None = None
    ) -> list[str]:
        with self._conexion() as conexion:
            # RF-CTX-07: la similitud opera sobre el conjunto ya filtrado. vec0
            # admite restringir por rowid, asi que el filtro entra en la consulta
            # en vez de aplicarse despues, que daria menos de k resultados.
            if candidatos is not None:
                filas = conexion.execute(
                    "SELECT rowid FROM fragmento_vector WHERE fragmento_id IN "
                    f"({','.join('?' * len(candidatos))})",
                    tuple(candidatos),
                ).fetchall()
                rowids = [f[0] for f in filas]
                if not rowids:
                    return []
                # sqlite-vec 0.1.9 devuelve vacio cuando `rowid IN (...)` lleva
                # un solo elemento, con cualquier orden de clausulas. Con un
                # unico candidato el KNN no ordena nada, asi que se resuelve sin
                # preguntarle a la extension en vez de depender de la rareza.
                if len(rowids) == 1:
                    return [next(iter(candidatos))] if k >= 1 else []
                # El orden de las clausulas importa: vec0 necesita `k` **antes**
                # del filtro por rowid. Al reves aplica el KNN primero y filtra
                # despues, que devuelve menos de k o directamente nada.
                consulta = (
                    "SELECT rowid FROM vec_fragmento WHERE embedding MATCH ? "
                    "AND k = ? "
                    f"AND rowid IN ({','.join('?' * len(rowids))}) ORDER BY distance"
                )
                parametros: tuple[object, ...] = (
                    vector.astype(np.float32).tobytes(),
                    k,
                    *rowids,
                )
            else:
                consulta = (
                    "SELECT rowid FROM vec_fragmento WHERE embedding MATCH ? "
                    "AND k = ? ORDER BY distance"
                )
                parametros = (vector.astype(np.float32).tobytes(), k)

            encontrados = [f[0] for f in conexion.execute(consulta, parametros)]
            if not encontrados:
                return []
            nombres = dict(
                conexion.execute(
                    "SELECT rowid, fragmento_id FROM fragmento_vector WHERE rowid IN "
                    f"({','.join('?' * len(encontrados))})",
                    tuple(encontrados),
                )
            )
        return [nombres[r] for r in encontrados if r in nombres]


def extension_disponible() -> bool:
    """Se comprueba una vez, en arranque (RI-17)."""
    try:
        conexion = sqlite3.connect(":memory:")
        conexion.enable_load_extension(True)
        import sqlite_vec

        sqlite_vec.load(conexion)
        return True
    except Exception:
        return False


def elegir_vector_store(ruta: Path | str, dimension: int) -> VectorStore:
    """RI-22: registra **una vez** que implementacion quedo activa."""
    if extension_disponible():
        _log.info("busqueda semantica: sqlite-vec cargada")
        return SqliteVecStore(ruta, dimension)
    _log.warning(
        "busqueda semantica degradada a fuerza bruta: la extension sqlite-vec "
        "no carga. El sistema funciona igual (CLAUDE.md §4.2)"
    )
    return BruteForceStore(ruta, dimension)
