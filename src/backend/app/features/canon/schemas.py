"""Lo que el Extractor devuelve, con forma comprobable antes de tocar la base.

**Todos los modelos llevan `extra="forbid"`, y no es celo.** Un `BaseModel` por
defecto acepta una clave que no conoce, la tira, y sigue. Aplicado a una
extraccion eso significa que un modelo que decide llamar `facts` a lo que aqui
es `hechos` devuelve una `Extraccion` **valida y vacia**: el canon deja de
crecer y ninguna puerta se entera. La Fase 1 lo descubrio en el Entrevistador
(`features/obra/agents.py`) y aqui se hereda la leccion.

`TextoNoVacio` se repite desde `features/obra/schemas.py` a proposito:
`CLAUDE.md` §5.1 regla 4 dice que se duplica primero y se sube a `commons/` al
tercer uso real. Este es el segundo.
"""

from dataclasses import dataclass
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

TextoNoVacio = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class HechoExtraido(BaseModel):
    """Un hecho con la forma de `definitions.md` §4.5: entidad, atributo, valor.

    No es una frase, y eso tiene consecuencia: la regla de arbitraje del mismo
    §4.5 —si dos hechos sobre el mismo `atributo` difieren, prevalece el de
    menor `orden_discurso`— y el defecto `CAN-01` comparan **atributos**. Sobre
    una cadena libre no hay nada que comparar.

    Los tres campos son `TextoNoVacio` por R-2: un valor vacio es subcadena de
    cualquier capitulo, asi que el validador de cobertura lo daria por cubierto
    siempre, en todas las novelas.
    """

    model_config = ConfigDict(extra="forbid")

    entidad: TextoNoVacio
    atributo: TextoNoVacio
    valor: TextoNoVacio
    confianza: float = Field(default=1.0, ge=0.0, le=1.0)


class EventoExtraido(BaseModel):
    """Un evento del ledger, con los campos de `definitions.md` §4.5.

    `testigos[]` no es opcional por comodidad: de el se deriva quien puede
    saber el hecho despues, que es el mecanismo que impide que un personaje use
    informacion que no deberia tener (regla de dominio 2). `excluye[]` es lo
    que hace comprobable «que nadie reaparezca despues de morir».
    """

    model_config = ConfigDict(extra="forbid")

    descripcion: TextoNoVacio
    tiempo_historia: TextoNoVacio
    lugar: str | None = None
    participantes: list[str] = Field(default_factory=list)
    testigos: list[str] = Field(default_factory=list)
    causa: list[str] = Field(default_factory=list)
    consecuencia: list[str] = Field(default_factory=list)
    excluye: list[str] = Field(default_factory=list)


class HiloExtraido(BaseModel):
    """Una pregunta abierta que el lector se lleva de la escena.

    Solo la pregunta: el estado nace `abierto` y la escena de apertura la pone
    quien consolida, que es el unico que sabe de que escena viene. Dejar que el
    modelo declarara un hilo ya `pagado` seria dejarle cerrar una promesa sin
    cumplirla.
    """

    model_config = ConfigDict(extra="forbid")

    pregunta: TextoNoVacio


class Extraccion(BaseModel):
    """Lo que el Extractor saca de una escena aprobada.

    Las cuatro claves son las cuatro salidas que `CLAUDE.md` §9 le atribuye:
    hechos, estado —los eventos del ledger, de los que el estado en T se
    deriva—, resumen e hilos.
    """

    model_config = ConfigDict(extra="forbid")

    hechos: list[HechoExtraido] = Field(default_factory=list)
    eventos: list[EventoExtraido] = Field(default_factory=list)
    resumen: str = ""
    hilos: list[HiloExtraido] = Field(default_factory=list)


class ExtraccionDelBrief(BaseModel):
    """Lo que el Extractor saca del `TextoAportado`, y **solo** eso.

    Tiene esquema propio en vez de reusar `Extraccion`, y esa es su unica
    razon de ser: del brief no sale ledger ni salen hilos, porque **no hay
    escena**. Los hechos del brief existian antes de que se escribiera una
    linea (axioma 14 de `definitions.md` §11), asi que un evento aqui seria un
    evento sin escena de origen que nadie podria situar en la cronologia.

    Con `extra="forbid"`, esa imposibilidad es estructural y no una promesa del
    prompt.
    """

    model_config = ConfigDict(extra="forbid")

    hechos: list[HechoExtraido] = Field(default_factory=list)


@dataclass(frozen=True)
class Vector:
    """Un fragmento ya vectorizado, tal y como lo guarda la tabla `embedding`.

    Quien lo calcula **no es esta feature**: el indice vectorial vive detras de
    la interfaz `VectorStore` (`architecture.md` §5.5) y su implementacion es de
    la Tarea 7. Aqui se recibe ya hecho, para que consolidar una escena no
    dependa de que la extension vectorial cargue (R-6, RNF-FIA-02).
    """

    datos: bytes
    dimension: int
    modelo: str
