"""La ficha de escena: lo que el Planificador produce y el Escritor recibe.

Tres modelos y una excepcion, y la frontera entre ellos es lo que importa:

- `SalidaPlanificador` es **lo que dice el modelo**, y por eso es donde vive la
  desconfianza: `extra='forbid'`, conjuntos cerrados y las dos mitades de la
  regla de dominio 1.
- `RestriccionesDeDiscurso` es **lo que no decide el modelo**: persona, tiempo
  verbal y nivel de calor los declara la obra (`definitions.md` §4.1 y §5) y la
  escena los hereda.
- `FichaDeEscena` es la suma de las dos, con el capitulo al que pertenece.

Nunca se expone el modelo de base de datos (`CLAUDE.md` §6): la ficha es la
forma que cruza la frontera de la feature, y `Escena` se queda dentro.
"""

import re
from collections.abc import Mapping
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.commons.domain.normalizacion import normalizar
from app.features.escena.modelos import RESULTADOS

TextoNoVacio = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

# `definitions.md` §5, capa de Discurso. Los dos conjuntos son cerrados y se
# declaran **a nivel de obra**; la escena no elige, hereda.
# Los literales los fija `docs/definitions.md` §5 («Capa de Discurso»), y gana
# el documento (`CLAUDE.md` §2). T4 los escribio sin la indicacion ordinal y
# T3 con ella: los necesitan tres tareas en tres olas -- T3 para escribir la
# biblia, T4 para validar la ficha y T8 para comprobar la regla 10 en el
# texto -- y nadie era dueno del contrato. Se alinean al cerrar la ola 2.
PERSONAS = ("1ª", "3ª limitada", "3ª omnisciente")
TIEMPOS_VERBALES = ("pasado", "presente")

# Un POV es **un** personaje (`definitions.md` §4.1). La columna es escalar, asi
# que el «exactamente uno» lo da la forma; lo que esto caza es el disfraz:
# «Nadia y Teo» en un campo son dos POV escritos en uno, y es la manera de tener
# dos teniendo una columna.
_DOS_POV = re.compile(r"[,;/&+]|\b(?:y|e|and)\b", re.IGNORECASE)

DISTANCIA_PSIQUICA_MINIMA = 1
DISTANCIA_PSIQUICA_MAXIMA = 5


class DiscursoNoDeclarado(Exception):
    """La biblia vigente no dice en que persona ni en que tiempo verbal se escribe.

    No se completa con un defecto: una restriccion dura inventada aqui viaja al
    prompt del Escritor como si la hubiera declarado la obra, y la regla de
    dominio 10 la comprobaria **en el texto** contra un valor que nadie decidio.
    Es un fallo del almacen, igual que una capa vacia del paquete, y se falla
    antes de llamar al modelo.
    """

    def __init__(self, faltantes: list[str]) -> None:
        self.faltantes = list(faltantes)
        super().__init__(
            "La biblia no declara los parametros de discurso: " + ", ".join(self.faltantes)
        )


class RestriccionesDeDiscurso(BaseModel):
    """Lo que la obra impone a todas sus escenas (`definitions.md` §5).

    Viajan **con la ficha** y no se vuelven a leer de la base: el Escritor solo
    ve lo que hay en su paquete (`CLAUDE.md` §9.1), y es lo que hace que un
    defecto de persona o de tiempo verbal sea atribuible al prompt que lo
    produjo y no al estado de hoy.
    """

    model_config = ConfigDict(extra="forbid")

    persona: str
    tiempo_verbal: str
    nivel_de_calor: int = Field(ge=0, le=4)

    @field_validator("persona")
    @classmethod
    def persona_declarada(cls, valor: str) -> str:
        if valor not in PERSONAS:
            raise ValueError(f"persona {valor!r} no es una de {PERSONAS}")
        return valor

    @field_validator("tiempo_verbal")
    @classmethod
    def tiempo_verbal_declarado(cls, valor: str) -> str:
        if valor not in TIEMPOS_VERBALES:
            raise ValueError(f"tiempo_verbal {valor!r} no es uno de {TIEMPOS_VERBALES}")
        return valor

    @classmethod
    def de_la_obra(
        cls, biblia: Mapping[str, Any], nivel_de_calor: int
    ) -> "RestriccionesDeDiscurso":
        """Los hereda de la obra: dos de la biblia vigente y el calor de la obra.

        `persona` y `tiempo_verbal` viven en la biblia y no en una columna de
        `obra` porque la biblia es lo que se congela por version (RF-PLA-01):
        una obra que cambiara de persona a mitad tendria dos versiones, y cada
        escena sabria con cual se escribio. `nivel_de_calor` si es columna,
        porque lo declara el comprador en el brief y no el Arquitecto.
        """
        faltantes = [
            clave
            for clave in ("persona", "tiempo_verbal")
            if not str(biblia.get(clave) or "").strip()
        ]
        if faltantes:
            raise DiscursoNoDeclarado(faltantes)
        return cls(
            persona=str(biblia["persona"]),
            tiempo_verbal=str(biblia["tiempo_verbal"]),
            nivel_de_calor=nivel_de_calor,
        )


class SalidaPlanificador(BaseModel):
    """Lo que el Planificador devuelve, y nada mas (RF-ORQ-09).

    `extra='forbid'` no es celo: sin el, un modelo que mete el giro de valor en
    una clave que se invento —`giro_de_valor: "de confianza a sospecha"`— deja
    `valor_entrada` y `valor_salida` a lo que le dio la gana y la ficha sale
    «valida». Una clave de mas esta fuera del esquema tanto como la prosa.

    Los campos son los de `definitions.md` §4.1, uno a uno, menos los tres que
    no decide el modelo: `capitulo_id`, `version_obra_id` y `orden_discurso`
    los pone quien planifica, porque son del outline y no de la escena.
    """

    model_config = ConfigDict(extra="forbid")

    tiempo_historia: TextoNoVacio
    elapsed_desde_anterior: str | None = None

    pov: TextoNoVacio
    lugar: TextoNoVacio
    presentes: list[TextoNoVacio] = Field(default_factory=list)
    mencionados: list[TextoNoVacio] = Field(default_factory=list)

    objetivo_del_pov: TextoNoVacio
    obstaculo: TextoNoVacio
    resultado: str

    valor_entrada: TextoNoVacio
    valor_salida: TextoNoVacio

    extension_objetivo: int = Field(gt=0)
    densidad_de_dialogo_objetivo: float = Field(ge=0.0, le=1.0)
    distancia_psiquica: int = Field(ge=DISTANCIA_PSIQUICA_MINIMA, le=DISTANCIA_PSIQUICA_MAXIMA)

    beat_de_genero: str | None = None
    planta: list[TextoNoVacio] = Field(default_factory=list)
    paga: list[TextoNoVacio] = Field(default_factory=list)
    revela: list[TextoNoVacio] = Field(default_factory=list)

    @field_validator("resultado")
    @classmethod
    def resultado_declarado(cls, valor: str) -> str:
        """El conjunto de `definitions.md` §4.1, cerrado, y en un solo sitio.

        Se importa de `modelos.py` en vez de repetirlo: dos copias de un
        conjunto cerrado divergen, y la de la base es la que muerde.
        """
        if valor not in RESULTADOS:
            raise ValueError(f"resultado {valor!r} no es uno de {RESULTADOS}")
        return valor

    @field_validator("pov")
    @classmethod
    def un_pov_y_solo_uno(cls, valor: str) -> str:
        """Regla de dominio 1, primera mitad.

        Rechazar los separadores de lista compra un falso positivo raro —un
        personaje que se llamara «Ana y Sol»— a cambio de cazar el caso que si
        pasa: el modelo que no elige y pone los dos. El intercambio se acepta
        aqui y no en el sentido contrario porque una escena con dos POV es
        *head-hopping* (`definitions.md` §5) y se propaga al texto entero.
        """
        if _DOS_POV.search(valor):
            raise ValueError(f"pov {valor!r} nombra mas de un personaje: una escena tiene uno")
        return valor

    @field_validator("valor_salida")
    @classmethod
    def el_giro_de_valor_no_es_nulo(cls, salida: str, info: Any) -> str:
        """Regla de dominio 1, segunda mitad, y la primera validacion que pide el dominio.

        «Una escena sin giro de valor es relleno» (`definitions.md` §4.1). Se
        compara **normalizado** por lo mismo que los vetos: entrar en
        «Confianza» y salir en «confianza » no es un giro, es la misma palabra
        con otra caja.

        El `CheckConstraint` de la tabla dice lo mismo, y los dos hacen falta:
        aqui se caza **antes de escribir nada**, y alli se caza lo que entrara
        por otra ruta.
        """
        entrada = info.data.get("valor_entrada")
        if entrada is not None and normalizar(entrada) == normalizar(salida):
            raise ValueError(
                f"el giro de valor es nulo: entra y sale en {salida!r}. "
                "Una escena sin giro de valor es relleno"
            )
        return salida


class FichaDeEscena(SalidaPlanificador):
    """La ficha completa: lo que decidio el modelo, mas lo que no decide.

    Hereda de `SalidaPlanificador` —y con ella `extra='forbid'` y las dos
    mitades de la regla de dominio 1— y anade lo que pone quien planifica: de
    que capitulo es, con que version de la biblia se planifico (RF-PLA-01) y en
    que orden va, mas las restricciones heredadas de la obra.
    """

    capitulo_id: int
    version_obra_id: int
    orden_discurso: int
    restricciones: RestriccionesDeDiscurso
