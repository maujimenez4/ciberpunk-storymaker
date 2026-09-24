"""La UNICA puerta de entrada a la feature `canon` (`CLAUDE.md` §5.1).

Casi vacia: la Tarea 2 trajo las tablas, los disparadores del ledger y las dos
vistas derivadas; el Extractor es de la Tarea 9. Las tablas **no** cruzan la
frontera: las claves ajenas se declaran por nombre.

`Embedding` es la excepcion, y va dicho por que. El indice vectorial lo
**escribe** el Extractor (`architecture.md` §4.3) y por eso la tabla vive aqui,
pero quien lo **lee** es la recuperacion de `contexto` (T7). Leerla por esta
puerta es lo unico que evita que `contexto` importe un fichero interno de otra
feature, que es lo que §5.1 prohibe de verdad.
"""

from app.features.canon.modelos import Embedding

__all__ = ["Embedding"]
