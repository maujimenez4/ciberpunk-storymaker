import re
import unicodedata
from collections.abc import Iterable

_PALABRA = re.compile(r"\w+", re.UNICODE)


def normalizar(texto: str) -> str:
    """Minusculas, sin acentos y sin la -s final del plural simple.

    Solo la -s, y eso es deliberado. La regla de `-es` que llevaba el borrador
    cortaba dos letras: convertia "sangres" en "sangr", con lo que el veto
    "sangre" dejaba de cazar su propio plural. Dos de los cuatro tests de esta
    tarea fallaban contra la implementacion que el propio plan daba.

    Lo que esto NO caza, y se escribe para que nadie lo descubra tarde: el
    plural en `-es` de las palabras que acaban en consonante, "ratones" frente
    a "raton". Distinguir "sangres" (de "sangre", que acaba en vocal y hace el
    plural en -s) de "ratones" (de "raton", que acaba en consonante y lo hace
    en -es) necesita un diccionario, no una regla. RF-GUA-02 pide "plurales y
    variantes simples" y esta es la simple; si hace falta la otra, entra con un
    test que la nombre, no ensanchando esta a ojo.
    """
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn"
    )
    if sin_tildes.endswith("s") and len(sin_tildes) > 3:
        return sin_tildes[:-1]
    return sin_tildes


def contiene_veto(texto: str, vetos: Iterable[str]) -> str | None:
    """Devuelve el veto que coincide, o None. Compara por PALABRA, no por
    subcadena: 'ana' no debe saltar dentro de 'manana' (R-3)."""
    palabras = {normalizar(p.group(0)) for p in _PALABRA.finditer(texto)}
    for veto in vetos:
        if normalizar(veto) in palabras:
            return veto
    return None
