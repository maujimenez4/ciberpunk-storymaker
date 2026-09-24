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

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Persona(StrEnum):
    """`definitions.md` §5. Se declara en la `Obra` y se hereda a cada escena."""

    PRIMERA = "primera"
    TERCERA_LIMITADA = "tercera_limitada"
    TERCERA_OMNISCIENTE = "tercera_omnisciente"


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
    """

    model_config = ConfigDict(frozen=True)

    codigo: str
    version_texto_id: str
    cita: str
    desplazamiento_inicio: int
    desplazamiento_fin: int
    hecho_canon_id: str | None = None
    defecto_id: str | None = None
