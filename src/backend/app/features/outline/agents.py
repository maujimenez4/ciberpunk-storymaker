"""El **Arquitecto** (`CLAUDE.md` §9): de un brief, una biblia y un outline.

Aqui no hay reglas de dominio, solo el esquema de lo que el agente puede haber
devuelto. Cuantos capitulos son y donde va cada beat lo decide `service.py`: una
salida bien formada puede ser una planificacion invalida, y son dos fallos
distintos —uno del agente, otro de la obra— que merecen dos errores distintos.
"""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from app.commons.llm.cliente import ClienteModelo
from app.commons.llm.json_de_modelo import json_de_modelo
from app.features.outline.schemas import CapituloDelOutline

PLANTILLA_V1 = (Path(__file__).parent / "prompts" / "arquitecto.v1.md").read_text(encoding="utf-8")
_MARCA = "brief"


class SalidaMalFormada(Exception):
    """Un agente que devuelve algo fuera de su esquema es un fallo (RF-ORQ-09).

    No hereda de `ErrorDeDominio` a proposito: no es una regla de negocio
    incumplida sino un agente que no hizo su trabajo, y quien decide si se
    reintenta o se escala es el orquestador, no el manejador de HTTP.

    Es la segunda copia de esta clase —la primera es la del Entrevistador, en
    `features/obra/agents.py`— y se duplica en vez de subir a `commons/`:
    `CLAUDE.md` §5.1 regla 4 dice que se duplica primero y se sube al **tercer**
    uso real. Queda anotado en Desviaciones para que el tercero la mueva.
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


def _sin_etiquetas(texto: str) -> str:
    """Quita la etiqueta hasta que quitarla ya no cambie nada.

    Una pasada sola no basta: al borrar el cierre de `</bri</brief>ef>` se unen
    los dos trozos que lo rodeaban y la etiqueta se vuelve a formar. Se repite
    hasta punto fijo, y termina siempre porque cada vuelta que cambia algo
    acorta la cadena.
    """
    sano = texto
    while True:
        podado = sano.replace(f"</{_MARCA}>", "").replace(f"<{_MARCA}>", "")
        if podado == sano:
            return sano
        sano = podado


def render_arquitecto(plantilla: str, brief: Mapping[str, Any]) -> str:
    """El brief entra SIEMPRE marcado como dato (`CLAUDE.md` §11).

    No es paranoia sobre un diccionario del sistema: sus valores vienen del
    comprador —el titulo se deriva del nombre del destinatario— y RNF-SEG-03
    dice que lo que viene de fuera se lee como dato aunque hoy parezca inocuo.
    """
    cuerpo = "\n".join(f"{clave}: {_sin_etiquetas(str(valor))}" for clave, valor in brief.items())
    return plantilla.replace("{{BRIEF}}", cuerpo)


class OutlineGenerado(BaseModel):
    """La salida del Arquitecto: las dos claves de la plantilla y ninguna mas.

    `biblia` es un objeto abierto y `capitulos` no lo es, y esa asimetria es
    deliberada: la biblia es un documento cuyo contenido decide el Arquitecto
    —premisa, personajes, reglas del mundo—, y el outline es una estructura que
    otras tareas consumen campo a campo. `extra=forbid` protege lo segundo.

    **No se comprueba aqui que sean diez ni que los beats esten repartidos.** Un
    outline de nueve capitulos esta perfectamente bien formado; lo que pasa es
    que no es un outline (RF-PLA-02). Esa es una regla de dominio y vive en el
    servicio, donde puede lanzar un error que el comprador entienda.
    """

    model_config = ConfigDict(extra="forbid")

    biblia: dict[str, Any]
    capitulos: list[CapituloDelOutline]


class Arquitecto:
    """El rol de `CLAUDE.md` §9, con su prompt versionado y su cliente inyectado.

    El cliente entra por el constructor y no se busca aqui: es lo que permite
    que la suite corra sin red y sin credenciales (CA-4), con
    `DobleDeterminista` en su sitio.
    """

    def __init__(self, cliente: ClienteModelo, semilla: int = 0) -> None:
        self._cliente = cliente
        self._semilla = semilla

    async def planificar(self, brief: Mapping[str, Any]) -> OutlineGenerado:
        """Una sola llamada al modelo, y su salida validada antes de creersela.

        Una llamada y no dos —biblia primero, outline despues— porque el outline
        se apoya en la biblia que el propio Arquitecto acaba de decidir: en dos
        llamadas habria que volver a mandarsela entera y el coste de CU-02
        dejaria de ser previsible.
        """
        prompt = render_arquitecto(PLANTILLA_V1, brief)
        crudo = await self._cliente.completar(prompt, semilla=self._semilla)
        try:
            return OutlineGenerado.model_validate(json_de_modelo(crudo))
        except (json.JSONDecodeError, ValidationError) as error:
            raise SalidaMalFormada(_con_motivo(crudo, error)) from error
