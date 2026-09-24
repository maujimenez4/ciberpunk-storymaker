"""Leer el JSON que devuelve un modelo, que casi nunca viene pelado.

**Por que existe, y no es una comodidad.** El 2026-09-24, la primera corrida
real contra el proveedor murio dos veces seguidas leyendo respuestas correctas:

1. La entrevista, con JSON impecable **dentro de una valla de markdown**. Los
   cinco agentes -- entrevistador, arquitecto, planificador, extractor y
   continuista -- llamaban a `json.loads(crudo)` a pelo.
2. El Arquitecto, que devolvio el outline entero, **cerro la valla y siguio
   escribiendo** un resumen debajo. El error decia `Extra data: char 9368`
   sobre un JSON que estaba completo.

Ninguno de los dos se ve con dobles: el doble devuelve lo que el test le pone.

**No se arregla en el prompt.** Pedir «devuelve solo JSON» baja la frecuencia y
no la lleva a cero, y una restriccion de formato que depende de que el modelo
obedezca no es una restriccion (`CLAUDE.md` §10).

Lo que **no** hace: no repara JSON roto ni adivina donde empieza la respuesta.
Con texto **delante** de la valla sigue fallando a proposito -- ahi no se sabe
cual de los dos textos es la respuesta, y un modelo que explica en vez de
contestar debe verse.
"""

import json
import re
from typing import Any

# Los tres candidatos, **en orden de preferencia**. Se prueban uno a uno y gana
# el primero que sea JSON valido, porque ninguna expresion sola cubre los tres
# casos sin romper otro:
#
# - Anclada y codiciosa: toma hasta el **ultimo** cierre, asi que un ``` dentro
#   de un valor del JSON no parte el bloque por la mitad.
# - No anclada y perezosa: toma hasta el **primer** cierre, que es lo que hace
#   falta cuando el modelo sigue escribiendo despues.
# - Abierta: sin cierre, que es como llega una respuesta truncada. Quitarla
#   igual hace que el error hable del final -- donde se corto -- y no del primer
#   caracter.
_CANDIDATOS = (
    re.compile(r"^\s*```[a-zA-Z]*\s*\n(?P<dentro>.*)\n?\s*```\s*$", re.DOTALL),
    re.compile(r"^\s*```[a-zA-Z]*\s*\n(?P<dentro>.*?)\n?\s*```", re.DOTALL),
    re.compile(r"^\s*```[a-zA-Z]*\s*\n(?P<dentro>.*)$", re.DOTALL),
)


def _trozos(crudo: str) -> list[str]:
    """Lo que podria ser el JSON, de mas probable a menos, sin repetir."""
    vistos = [crudo]
    for patron in _CANDIDATOS:
        hallada = patron.match(crudo)
        if hallada is not None and hallada.group("dentro") not in vistos:
            vistos.insert(-1, hallada.group("dentro"))
    return vistos


def sin_valla(crudo: str) -> str:
    """El contenido de la valla, o el texto tal cual si no la lleva.

    Devuelve el **primer candidato que parsea**; si ninguno lo hace, el mas
    probable, para que el error que suba sea el suyo y no el del texto entero
    con las comillas delante.
    """
    candidatos = _trozos(crudo)
    for trozo in candidatos:
        try:
            json.loads(trozo)
        except json.JSONDecodeError:
            continue
        return trozo
    return candidatos[0]


def json_de_modelo(crudo: str) -> Any:
    """`json.loads` tolerante a la valla de markdown, y a nada mas."""
    return json.loads(sin_valla(crudo))
