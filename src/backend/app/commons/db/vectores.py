"""Lo de mas abajo del indice vectorial: float32, coseno y la extension.

Aqui no hay ni `Embedding` ni recuperacion, y no es casualidad: `commons/` no
importa de ninguna feature (primer contrato de `import-linter`). Lo que vive
aqui es infraestructura de base de datos, y se prueba sin saber que hay una
obra detras.

**La extension es opcional de verdad, no de boquilla** (`CLAUDE.md` §4, §4.2).
`sqlite-vec` se declara en `pyproject.toml` porque cuando esta acelera la
ordenacion, pero el sistema **arranca y funciona sin ella** con el almacen de
fuerza bruta. Si fuera obligatoria seria una segunda base de datos por la
puerta de atras (RNF-FIA-02, CA-28).

**Y si no carga, se dice.** Degradar en silencio es peor que fallar: quien mide
un corpus lento tiene derecho a saber que esta en el modo lento. El aviso se da
**una vez por proceso** —la deteccion se cachea—, porque un aviso por consulta
es ruido y el ruido se acaba silenciando entero.
"""

import logging
import math
import os
import sqlite3
import struct
import warnings
from collections.abc import Sequence
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession

_log = logging.getLogger(__name__)

VARIABLE_SIN_EXTENSION = "STORYMAKER_SIN_SQLITE_VEC"
"""Puesta a cualquier valor, la extension se da por ausente.

Es el interruptor con el que la suite corre **en los dos modos** sin desinstalar
nada (RNF-FIA-02). No es una opcion de configuracion del producto: es lo que
hace que el modo degradado se pruebe en la misma maquina que el otro.
"""

FORMATO_COMPONENTE = "f"
"""float32, *little-endian* y explicito.

`vec_distance_cosine` lee exactamente esto. Empaquetar en float64 -- que es lo
que sale solo de un `float` de Python -- da un blob del doble de largo que la
extension interpreta como otro vector, y el fallo aparece como distancias
absurdas, no como un error.
"""

BYTES_POR_COMPONENTE = 4


class AvisoDeDegradacion(RuntimeWarning):
    """El indice vectorial funciona, pero no como estaba previsto.

    Es un aviso y no un error a proposito: el sistema arranca igual. Que sea
    una clase propia permite silenciarlo o convertirlo en error sin tocar el
    resto de avisos del proceso.
    """


def empaquetar_vector(vector: Sequence[float]) -> bytes:
    """El vector, en el BLOB que guarda `embedding.vector`."""
    return struct.pack(f"<{len(vector)}{FORMATO_COMPONENTE}", *vector)


def desempaquetar_vector(blob: bytes) -> list[float]:
    """Lo contrario. La longitud sale del blob: la dimension no se adivina."""
    if len(blob) % BYTES_POR_COMPONENTE:
        raise ValueError(f"El blob mide {len(blob)} bytes, que no son float32 enteros")
    componentes = len(blob) // BYTES_POR_COMPONENTE
    return list(struct.unpack(f"<{componentes}{FORMATO_COMPONENTE}", blob))


def distancia_coseno(uno: Sequence[float], otro: Sequence[float]) -> float:
    """`1 - cos(uno, otro)`: 0 es el mismo sentido, 1 perpendicular, 2 opuesto.

    Es la misma metrica que `vec_distance_cosine`, y por eso los dos almacenes
    devuelven lo mismo. Dos decisiones se toman aqui y no en quien llama:

    - **Dimensiones distintas es un error**, no una distancia grande. Un vector
      de otra dimension no es «menos parecido»: es incomparable, y tratarlo como
      lejano lo colaria al final de la lista en vez de destaparlo.
    - **El vector nulo no se parece a nada.** Sin este caso la division daria
      `nan`, y un `nan` no ordena: envenena la lista entera sin fallar.
    """
    if len(uno) != len(otro):
        raise ValueError(f"Dimensiones distintas: {len(uno)} y {len(otro)}")

    producto = math.fsum(a * b for a, b in zip(uno, otro, strict=True))
    norma = math.sqrt(math.fsum(a * a for a in uno)) * math.sqrt(math.fsum(b * b for b in otro))
    if norma == 0.0:
        return 1.0
    return 1.0 - producto / norma


@lru_cache(maxsize=1)
def extension_disponible() -> bool:
    """Si `sqlite-vec` carga en este proceso. Se prueba **una vez** y se avisa una vez.

    La prueba se hace sobre una base **en memoria propia** y no sobre el motor
    de la aplicacion: asi la deteccion es de arranque de verdad -- no necesita
    que haya una obra abierta -- y no deja nada cargado en una conexion que
    luego se devuelve al pool.

    `cache_clear()` existe para los tests, que necesitan mirar los dos modos en
    el mismo proceso.
    """
    motivo = _por_que_no_carga()
    if motivo is None:
        return True

    aviso = (
        f"sqlite-vec no esta disponible ({motivo}). La ordenacion semantica pasa al "
        "almacen de fuerza bruta: el sistema arranca y responde lo mismo, leyendo los "
        "vectores en Python. Sobre corpus grandes sera mas lento."
    )
    warnings.warn(aviso, AvisoDeDegradacion, stacklevel=2)
    _log.warning(aviso)
    return False


def _por_que_no_carga() -> str | None:
    """El motivo, o `None` si carga. Se devuelve el texto porque «no carga» no basta."""
    if os.environ.get(VARIABLE_SIN_EXTENSION):
        return f"{VARIABLE_SIN_EXTENSION} esta puesta"

    try:
        import sqlite_vec
    except ImportError as exc:  # pragma: no cover - depende de la instalacion
        return f"no esta instalada ({exc})"

    conexion = sqlite3.connect(":memory:")
    try:
        conexion.enable_load_extension(True)
        sqlite_vec.load(conexion)
        conexion.execute("SELECT vec_version()").fetchone()
    except (AttributeError, OSError, sqlite3.Error) as exc:  # pragma: no cover
        # `AttributeError` es el interprete compilado sin carga de extensiones,
        # que es el caso real de muchos Python de sistema.
        return f"no carga en este interprete ({exc})"
    finally:
        conexion.close()
    return None


async def cargar_extension(sesion: AsyncSession) -> None:
    """Carga `sqlite-vec` en la conexion que esta usando esta sesion.

    Hace falta **por conexion**: una extension no se hereda del pool, igual que
    `foreign_keys` en `motor.py`. Es idempotente, asi que quien la necesita la
    pide sin comprobar antes si ya estaba.

    No se engancha a `motor.py` a proposito: el motor lo monta la instalacion
    entera y la extension es opcional, asi que cargarla ahi haria que un fallo
    de la extension fuera un fallo de arranque de la base.
    """
    import sqlite_vec

    bruta = (await (await sesion.connection()).get_raw_connection()).driver_connection
    if bruta is None:  # pragma: no cover - la sesion acaba de dar la conexion
        raise RuntimeError("La sesion no tiene conexion viva: no hay donde cargar sqlite-vec")

    # `enable_load_extension` se vuelve a cerrar despues a proposito: dejarlo
    # abierto convierte cualquier SQL posterior en una via para cargar binarios.
    await bruta.enable_load_extension(True)
    await bruta.load_extension(sqlite_vec.loadable_path())
    await bruta.enable_load_extension(False)
