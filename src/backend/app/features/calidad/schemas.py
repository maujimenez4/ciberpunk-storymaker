"""Segmento schemas de la feature `calidad` (architecture.md §5.1).

Lo que el Continuista devuelve, y el fallo cuando no lo devuelve. La
`Afirmacion` en si vive en `validadores.py`, junto a las funciones que la
contrastan: es su contrato de entrada, no el de salida de un endpoint.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.features.calidad.validadores import Afirmacion


class AfirmacionesInvalidas(RuntimeError):
    """La salida del Continuista no valida contra `list[Afirmacion]`.

    RF-ORQ-15: es **fallo del paso**, no cero afirmaciones. La distincion
    importa mas de lo que parece: una salida rota tratada como lista vacia es
    indistinguible de una escena sin defectos, y entonces la averia se lee como
    un verde. Es exactamente el modo de fallo que dejo pasar la primera corrida
    real.
    """


class LecturaDelContinuista(BaseModel):
    """Lo que el Continuista deja: sus afirmaciones y la traza de la llamada.

    El modelo y los parametros viajan con las afirmaciones porque `ejecucion`
    los pide (RI-14) y el ciclo no tiene otra forma de saberlos sin volver a
    hablar con el cliente. La corrida real registro diez ejecuciones, todas del
    Escritor: las de los demas agentes no existian, y una llamada sin fila es
    una llamada que no se puede auditar.
    """

    model_config = ConfigDict(frozen=True)

    afirmaciones: list[Afirmacion]
    modelo: str
    parametros: dict[str, object] = Field(default_factory=dict)
