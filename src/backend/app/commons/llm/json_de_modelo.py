"""Extrae el JSON de una respuesta de modelo (RF-ORQ-15).

Los prompts piden «solo JSON, sin texto alrededor» y aun asi el modelo lo
envuelve en vallas de markdown la mayoria de las veces. Eso no es un fallo del
paso: el contenido es correcto y el envoltorio es una convencion de formato tan
arraigada que pelearla en el prompt cuesta mas de lo que vale.

**Lo que esto no hace es reparar.** Recorta el envoltorio y nada mas: si lo de
dentro no valida contra el esquema, sigue siendo fallo del paso. La diferencia
importa, porque un extractor que «arreglara» JSON medio escrito convertiria una
salida rota en una silenciosamente incompleta.
"""

import re

_VALLA = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def extraer_json(texto: str) -> str:
    """Devuelve el cuerpo JSON, sin vallas ni texto alrededor."""
    valla = _VALLA.search(texto)
    if valla:
        return valla.group(1).strip()

    limpio = texto.strip()
    # Sin valla: se recorta al primer objeto o array de nivel superior. Un
    # modelo que antepone «Aqui tienes:» sigue siendo utilizable; uno que
    # devuelve prosa no, y entonces no hay corchetes y se devuelve tal cual
    # para que el esquema lo rechace con un mensaje que se entienda.
    for abre, cierra in (("{", "}"), ("[", "]")):
        inicio = limpio.find(abre)
        final = limpio.rfind(cierra)
        if 0 <= inicio < final:
            return limpio[inicio : final + 1]
    return limpio
