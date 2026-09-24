"""La UNICA puerta de entrada a la feature `outline` (`CLAUDE.md` §5.1).

Lo que no esta aqui no se importa desde fuera: ni `modelos.py`, ni el
`service.py` y el `router.py` que traera la Tarea 3 con el Arquitecto.

Hoy no exporta nada, y no es un olvido: la Tarea 2 solo trae el esquema, y las
tablas **no se importan entre features**. Las claves ajenas se declaran por
nombre de tabla, que es lo que permite que `escena` cuelgue de `capitulo` sin
que las dos features se conozcan.
"""

__all__: list[str] = []
