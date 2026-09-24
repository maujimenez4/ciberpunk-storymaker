"""El Planificador de escena (`CLAUDE.md` §9): del outline y el estado en T, la ficha.

No escribe prosa. Su criterio de exito es que la ficha tenga objetivo,
obstaculo y giro de valor, y aqui eso no se pide en el prompt y ya esta: lo que
devuelve se valida con esquema antes de creerselo (RF-ORQ-09), porque ninguna
regla de seguridad ni de dominio depende solo del prompt (`CLAUDE.md` §10).
"""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.commons.llm.cliente import ClienteModelo
from app.commons.llm.json_de_modelo import json_de_modelo
from app.features.escena.schemas import RestriccionesDeDiscurso, SalidaPlanificador

PLANTILLA_V1 = (Path(__file__).parent / "prompts" / "planificador.v1.md").read_text(
    encoding="utf-8"
)

# El titulo de la plantilla. Los dobles de test eligen respuesta por subcadena
# del prompt, y una constante evita que el test se apoye en una frase de la
# plantilla que la v2 puede reescribir.
MARCA_DE_PLANTILLA = "PLANIFICADOR DE ESCENA"


class SalidaMalFormada(Exception):
    """Un agente que devuelve algo fuera de su esquema es un fallo (RF-ORQ-09).

    Misma clase y mismo nombre que la de `features/obra/agents.py`, y duplicada
    a proposito: una feature no importa de los ficheros internos de otra
    (`CLAUDE.md` §5.1), y lo repetido sube a `commons/` **al tercer uso**, no al
    segundo (regla 4). Este es el segundo.
    """


def _con_motivo(crudo: str, error: Exception) -> str:
    """Lo que devolvio el modelo **y por que no valida**.

    Guardar solo el crudo deja el diagnostico a ciegas: se ve el texto y no lo
    que le sobra o le falta, y con un esquema de veinte campos eso es una hora
    de leer JSON a mano. Paso en la corrida real del 2026-09-24.

    El crudo se recorta y el motivo no: el motivo es la parte corta y util.
    """
    if isinstance(error, ValidationError):
        fallos = "; ".join(
            f"{'.'.join(str(parte) for parte in e['loc'])}: {e['type']}"
            for e in error.errors()[:6]
        )
        return f"{fallos} | crudo: {crudo[:200]}"
    return f"{type(error).__name__}: {error} | crudo: {crudo[:200]}"


def _como_texto(datos: Mapping[str, Any]) -> str:
    """Lo que el agente recibe como contexto, legible y estable.

    JSON con las claves ordenadas y no el `repr` del diccionario: el orden fija
    el prompt, y un prompt que cambia de orden entre dos ejecuciones rompe el
    determinismo que `CLAUDE.md` §3 pide.
    """
    return json.dumps(dict(datos), ensure_ascii=False, indent=2, sort_keys=True)


def render_planificador(
    plantilla: str,
    capitulo: Mapping[str, Any],
    estado_en_t: Mapping[str, Any],
    restricciones: RestriccionesDeDiscurso,
) -> str:
    """Rellena la plantilla. Las restricciones duras salen dos veces, y es la plantilla
    quien lo decide: van al principio y al final porque el centro del prompt es donde
    mas informacion se pierde (`CLAUDE.md` §10).
    """
    sustituciones = {
        "{{PERSONA}}": restricciones.persona,
        "{{TIEMPO_VERBAL}}": restricciones.tiempo_verbal,
        "{{NIVEL_DE_CALOR}}": str(restricciones.nivel_de_calor),
        "{{CAPITULO}}": _como_texto(capitulo),
        "{{ESTADO_EN_T}}": _como_texto(estado_en_t),
    }
    prompt = plantilla
    for marcador, valor in sustituciones.items():
        prompt = prompt.replace(marcador, valor)
    return prompt


class Planificador:
    """El rol. Una llamada, una ficha, y nada que no pase por el esquema."""

    def __init__(self, cliente: ClienteModelo, semilla: int = 0) -> None:
        self._cliente = cliente
        self._semilla = semilla

    async def planificar(
        self,
        capitulo: Mapping[str, Any],
        estado_en_t: Mapping[str, Any],
        restricciones: RestriccionesDeDiscurso,
    ) -> SalidaPlanificador:
        """Devuelve lo que el modelo dijo **solo si cumple su esquema**.

        Las dos excepciones que se traducen a `SalidaMalFormada` son la misma
        cosa vista dos veces: lo que no es un objeto JSON, y lo que lo es pero
        no es una ficha. Ninguna de las dos es una respuesta.
        """
        prompt = render_planificador(PLANTILLA_V1, capitulo, estado_en_t, restricciones)
        crudo = await self._cliente.completar(prompt, semilla=self._semilla)
        try:
            return SalidaPlanificador.model_validate(json_de_modelo(crudo))
        except (json.JSONDecodeError, ValidationError) as error:
            raise SalidaMalFormada(_con_motivo(crudo, error)) from error
