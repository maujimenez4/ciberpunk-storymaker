"""Lo que entra y sale de la puerta mecanica. Ni base de datos ni framework.

**No hay tabla `defecto` en esta fase** (T2 no la trae), y por eso `Defecto` es
un modelo de Pydantic y no una fila: la puerta de este capitulo clasifica y
devuelve, no persiste. Cuando exista la tabla, este modelo sigue siendo el de
entrada y salida, que es la separacion que `CLAUDE.md` §6 pide de todas formas.

**Lo que esta feature NO importa, y es deliberado:** `HechoCanon` vive en
`features/obra/modelos.py` y una feature solo entra a otra por su `__init__.py`
(`CLAUDE.md` §5.1). La comprobacion de forma recibe por parametro los
identificadores de los hechos que existen —una proyeccion del grafo de canon—,
no la tabla. Ademas de respetar la frontera, deja el validador probable sin
base de datos, que es lo que hace que la puerta corra en el *hook* y no al
final de una transaccion.
"""

from enum import StrEnum
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

TextoNoVacio = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
"""Vivia en `agents.py` de esta misma feature y se baja aqui al necesitarlo
`ConocimientoEnT`. No sube a `commons/` —`CLAUDE.md` §5.1 regla 4 lo pide al
tercer uso real y este seria el cuarto del repositorio— porque `commons/` es
de otra tarea de esta ola: queda anotado en Desviaciones."""


class Persona(StrEnum):
    """`definitions.md` §5. Se declara en la `Obra` y se hereda a cada escena.

    Los valores son los **literales del documento**, no una version en ASCII.
    `CLAUDE.md` §2: el mismo concepto se llama igual en el esquema de datos, en
    los prompts y en la interfaz. Esta feature nacio con `primera` y
    `tercera_limitada` mientras `outline` y `escena` usaban los del documento;
    convivieron una ola entera y lo destapo T8 al tener que traducir entre las
    dos. Se alinean al cerrar la ola 4.
    """

    PRIMERA = "1ª"
    TERCERA_LIMITADA = "3ª limitada"
    TERCERA_OMNISCIENTE = "3ª omnisciente"


class TiempoVerbal(StrEnum):
    """`definitions.md` §5. Dos valores, y mezclarlos dentro del parrafo es el
    defecto que la propia tabla nombra."""

    PASADO = "pasado"
    PRESENTE = "presente"


class ParametrosDeDiscurso(BaseModel):
    """Las dos restricciones duras del axioma 13, juntas porque se comprueban
    juntas: el validador `discurso` mira el mismo texto para las dos."""

    model_config = ConfigDict(frozen=True)

    persona: Persona
    tiempo_verbal: TiempoVerbal


class RangoDeExtension(BaseModel):
    """En palabras. `definitions.md` §4.1 da 1.000-1.500 para un `Capitulo`,
    pero el rango llega declarado y no se clava aqui: quien lo declara es la
    obra, y el `CheckConstraint` de `capitulo.extension_objetivo` ya lo guarda
    en el esquema (Desviaciones, T2)."""

    model_config = ConfigDict(frozen=True)

    minimo: int = Field(ge=0)
    maximo: int = Field(ge=0)

    @model_validator(mode="after")
    def el_minimo_no_supera_al_maximo(self) -> "RangoDeExtension":
        if self.minimo > self.maximo:
            raise ValueError("el minimo del rango de extension supera al maximo")
        return self


class NombreDeCanon(BaseModel):
    """Un nombre **tal y como el canon lo declara**: su forma canonica y sus
    variantes (RF-VAL-03).

    `variantes` no es una comodidad: es donde vive la diferencia entre un error
    de grafia y un apodo. Sin ella, el validador tendria que adivinar, y un
    validador que adivina prohibe por escrito que a Maria la llamen Mari
    (spec, nota sobre CA-16).
    """

    model_config = ConfigDict(frozen=True)

    forma_canonica: str = Field(min_length=1)
    variantes: tuple[str, ...] = ()


class ConocimientoEnT(BaseModel):
    """Una fila de la vista `estado_en_t`, tal y como el Continuista la ve.

    Es una proyeccion, no la vista: `estado_en_t` se deriva del ledger en
    `features/canon` y una feature solo entra a otra por su `__init__.py`
    (`CLAUDE.md` §5.1). La misma decision que ya tomaron `Defecto` y
    `HechoDeCanon`, y por el mismo motivo: asi el contraste se prueba sin
    levantar SQLite.

    **`sabe_desde` es el `orden_discurso` de la escena del evento**, y es nulo
    cuando el evento no tiene escena. Nulo no es cero: significa que el ledger
    **no situa** ese conocimiento en el discurso, y de algo que no esta situado
    no se puede decir que sea anterior a nada.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    personaje: TextoNoVacio
    evento_id: TextoNoVacio
    tiempo_historia: str
    sabe_desde: int | None = None


class Defecto(BaseModel):
    """Un defecto no es una frase: es un registro con forma comprobable
    (`definitions.md` §8).

    **`codigo` es `str` sin restringir, y es la decision que hace posible
    CA-17.** Si el esquema rechazara un codigo fuera de la taxonomia, el defecto
    mal formado no llegaria a existir y no habria nada que contar aparte: el
    fallo se convertiria en una excepcion de validacion en el borde, que es
    justo lo que RF-VAL-07 no pide. La taxonomia la comprueba `defectos.py`,
    en codigo y sin volver a llamar al modelo.

    `defecto_id` es opcional porque en esta fase nadie lo asigna: no hay tabla.
    `definitions.md` §8 lo da con cardinalidad 1 sobre el defecto **persistido**.

    **`evento_id` es a `CON-03` lo que `hecho_canon_id` es a `CAN-01`**: el
    identificador contra el que se contrasta. Sin el, «este personaje sabe lo
    que no deberia» es una frase que no senala nada y que ninguna comprobacion
    puede confirmar ni desmentir — que es P-4 dicho en una linea.
    """

    model_config = ConfigDict(frozen=True)

    codigo: str
    version_texto_id: str
    cita: str
    desplazamiento_inicio: int
    desplazamiento_fin: int
    hecho_canon_id: str | None = None
    evento_id: str | None = None
    defecto_id: str | None = None
