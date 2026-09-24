"""Los dos roles que juzgan un capitulo: el **Continuista** y el **Critico**.

Viven juntos porque `CLAUDE.md` §9.3 los pone en la misma feature, y **no
comparten nada mas que el fichero**: contextos distintos, prompts distintos y
criterios de exito distintos. El Continuista contrasta hechos y devuelve
codigos con cita; el Critico puntua contra una rubrica y devuelve numeros con
justificacion. Ninguno de los dos repara, y ninguno decide si el capitulo
pasa.

---

**El Continuista** contrasta el capitulo **contra el grafo y contra el
ledger**.

Es el primer `agents.py` de esta feature, y la Fase 2 la construyo entera sin
ninguno **a proposito**. La decision **P-B** de aquel plan lo dejo fuera con este
motivo exacto: «contrasta contra el grafo, y un capitulo solo no tiene contra
que chocar». Con diez capitulos, si: el problema real del producto es que el
siete contradiga al cuatro, y este fichero es quien lo mira.

**Contrastar no es opinar** (RF-VAL-06), y aqui esa diferencia es mecanica y no
una promesa del prompt:

1. **El grafo y el estado en T entran en el prompt con sus identificadores.**
   Lo que no esta en la lista no existe para el Continuista. Un prompt sin ellos
   pide una opinion.
2. **Lo que vuelve se valida con esquema antes de creerselo** (RF-ORQ-09), con
   `extra="forbid"`: un `BaseModel` por defecto acepta una clave que no conoce,
   la tira y sigue, y eso **pierde datos en silencio**. La Fase 1 lo descubrio
   en el Entrevistador y la Fase 2 lo heredo en el Extractor.
3. **La forma la comprueba la puerta de la Fase 2, no este fichero.**
   `clasificar` de `defectos.py` es quien decide si un `CAN-01` nombra un hecho
   que existe (regla de dominio 9), si la cita es subcadena exacta en su
   desplazamiento (regla de dominio 8) y —desde P-4— si el `evento_id` de un
   `CON-03` esta situado por el ledger **antes** de este capitulo (regla de
   dominio 2). Aqui se **usa**; reescribirla habria dado dos comprobaciones que
   divergen.

**Que P-4 se pagara aqui no amplia el rol: lo completa.** RF-VAL-06 pide canon,
continuidad **y conocimiento** contra el grafo, y hasta hoy solo el primero se
contrastaba: un `CON-03` era una opinion cuya forma se comprobaba y cuyo fondo
no. Lo que sigue siendo probabilistico es la **extraccion** —que el modelo vea
el pasaje— y eso ninguna comprobacion de forma lo alcanza
(`verification.md` §6.3).

**El Continuista no repara** (`CLAUDE.md` §9.1). Devuelve codigos con cita y
nada mas: en `DefectoDelContinuista` no hay ningun campo donde quepa una
reescritura, y el esquema rechaza el que lo intente. La reparacion vuelve al
Escritor con el defecto concreto, y eso ya existe desde la Fase 2
(`features/escritura/agents.py`). Que sean dos roles separados es lo que hace
**atribuible** un defecto: si el que juzga arreglase, nadie sabria si el fallo
vino de quien escribio o de quien juzgo.

**Lo que el Continuista NO hace, y conviene no ampliarlo al leerlo:** no
puntua, no persiste, no cuenta reintentos y no decide si el capitulo pasa.
Devuelve una revision; quien cruza la puerta es `cruzar_g1a`, y quien cuenta los
intentos es el orquestador.

---

**El Critico** puntua contra la rubrica compartida y **no bloquea**. Que no
bloquee no es una fase a medias: `RF-JUZ-06` lo deja fuera de la puerta hasta que
su correlacion con la revision humana este medida y firmada con ese numero
delante. Construir hoy un componente que por regla no puede parar nada y
cablearlo a una puerta seria telemetria llamada defensa.

Y desde la revision de P-02 **corre en el mismo modelo que escribio el
capitulo**, lo que le empuja a aprobar su propio estilo: la distancia de
`RF-JUZ-05` saldra mejor de lo que el sistema merece. No lo arregla este fichero
—queda declarado—, pero si lo empuja en la direccion contraria: los anclajes de
la rubrica van al prompt y describen lo observable, no lo deseable.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from hashlib import sha256
from pathlib import Path

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)

from app.commons.llm.claude_code import MODELO_JUEZ
from app.commons.llm.cliente import ClienteModelo
from app.commons.llm.json_de_modelo import json_de_modelo
from app.features.calidad.defectos import (
    ContrasteDeConocimiento,
    DefectoMalFormado,
    clasificar,
)
from app.features.calidad.rubrica import Rubrica
from app.features.calidad.schemas import ConocimientoEnT, Defecto, TextoNoVacio

__all__ = ["ConocimientoEnT", "ContrasteDeConocimiento"]
"""**No es la superficie publica de este modulo**: los nombres que aqui se
definen se exportan igual. Marca solo los dos que este modulo **no define** y
que el `__init__.py` de la feature necesita sacar por el.

Con `mypy` en modo estricto un import normal no cuenta como reexportacion, y la
forma `X as X` --que seria la idiomatica-- la rechaza `ruff` con `PLC0414`. De
las tres salidas esta es la unica que no obliga a elegir entre los dos
linters."""

_PROMPTS = Path(__file__).parent / "prompts"

PROMPT_ID = "continuista"
PROMPT_VERSION = "v2"


class PlantillaAusente(Exception):
    """Falta el fichero de una plantilla. Es un fallo del despliegue, no del
    modelo, y por eso tiene excepcion propia y mensaje con la ruta."""


@cache
def _leer(nombre: str) -> str:
    """La plantilla, leida **al usarla y no al importar el modulo**.

    Se lee dentro de la funcion por algo que costo caro el dia que se escribio
    la v2: leerla a nivel de modulo convierte «todavia no esta el fichero» en
    «el backend entero no arranca». `calidad/__init__.py` importa este modulo, y
    de el cuelgan `manuscrito`, `obra`, `canon` y `escritura`, asi que un
    `FileNotFoundError` aqui dejaba de coleccionar **la suite entera** para
    todas las sesiones a la vez. `CLAUDE.md` §10 pide crear la version nueva y
    **despues** cambiar la referencia; esto hace que hacerlo al reves cueste un
    fallo local y legible en vez de una tarde.

    El `cache` mantiene lo que habia: se lee una vez por proceso.
    """
    fichero = _PROMPTS / nombre
    if not fichero.is_file():
        raise PlantillaAusente(str(fichero))
    return fichero.read_text(encoding="utf-8")


def plantilla_v1() -> str:
    """La v1 **no se toca y no se retira**. Es la mitad de la iteracion de
    *tuning*: el «antes» contra el que se compara la v2, y un «antes» que se
    edita no mide nada."""
    return _leer("continuista.v1.md")


def plantilla_v2() -> str:
    """La que corre. Anade la seccion de conocimiento —P-4— y es lo unico que la
    separa de la v1: si la v2 emite menos `CON-03` mal formados, es por eso."""
    return _leer("continuista.v2.md")


def hash_de_plantilla(plantilla: str) -> str:
    """Lo que ata la fila de `ejecucion` al fichero sin duplicarlo en cada
    llamada (regla de dominio 7). La plantilla **no se edita en sitio**: una
    version nueva es un fichero nuevo con su propio hash (`CLAUDE.md` §10)."""
    return sha256(plantilla.encode("utf-8")).hexdigest()


MARCA_CAPITULO = "capitulo"
"""La etiqueta con la que el capitulo entra **como dato** (`CLAUDE.md` §11).
Cinco de los diez roles reciben prosa, y ninguno la recibe como instruccion."""

HUECO_DEL_CAPITULO = "{{CAPITULO}}"
HUECO_DEL_CANON = "{{CANON}}"
HUECO_DEL_CONOCIMIENTO = "{{CONOCIMIENTO}}"
HUECO_DEL_ORDEN = "{{ORDEN_DISCURSO}}"

SIN_GRAFO = (
    "No hay ningún hecho de canon. **No puede haber ninguna contradicción de canon**: "
    "no se devuelve ningún `CAN-01`."
)
"""Con el grafo vacio no hay contra que contrastar, y decirlo es mas honesto que
dejar la seccion en blanco: un hueco vacio invita a rellenarlo de memoria."""

SIN_CONOCIMIENTO = (
    "El ledger no sitúa ningún conocimiento antes de este capítulo. "
    "**No puede haber ningún `CON-03`**: no se devuelve ninguno."
)
"""Hermana de `SIN_GRAFO`, y por el mismo motivo. Con la vista vacia no hay
conocimiento establecido que un personaje pueda estar usando antes de tiempo, y
cualquier `CON-03` seria una opinion sobre algo que no esta."""


class SalidaMalFormada(Exception):
    """Un agente que devuelve algo fuera de su esquema es un fallo (RF-ORQ-09).

    Se repite desde `features/canon/agents.py` por el mismo motivo que
    `TextoNoVacio`, y con la misma anotacion en Desviaciones.
    """


class OrigenDeHecho(StrEnum):
    """De donde salio un hecho (`definitions.md` §4.5). Los mismos tres valores
    que el `CheckConstraint` de la tabla, para que la proyeccion no pueda
    representar un hecho que la base no admitiria."""

    ESCENA = "escena"
    BRIEF = "brief"
    EDICION_HUMANA = "edicion_humana"


class HechoDeCanon(BaseModel):
    """Un hecho del grafo, **tal y como el Continuista lo ve**.

    Es una proyeccion, no la tabla: `HechoCanon` vive en `features/obra` y una
    feature solo entra a otra por su `__init__.py` (`CLAUDE.md` §5.1). La misma
    decision que ya tomo `puerta.py`, y por el mismo motivo: asi esta feature se
    prueba sin base de datos.

    Lleva `entidad`, `atributo` y `valor` **separados** y no una frase, porque
    eso es lo que hace comparable un hecho con otro: la regla de arbitraje de
    `definitions.md` §4.5 —si dos hechos sobre el mismo atributo difieren,
    prevalece el de menor `orden_discurso` y el otro es un `CAN-01`— no se puede
    aplicar sobre una cadena libre.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    hecho_canon_id: TextoNoVacio
    entidad: TextoNoVacio
    atributo: TextoNoVacio
    valor: TextoNoVacio
    origen: OrigenDeHecho = OrigenDeHecho.ESCENA
    escena_de_origen: str | None = None

    @model_validator(mode="after")
    def el_origen_es_coherente(self) -> "HechoDeCanon":
        """Regla de dominio 4, axioma 14 de `definitions.md` §11, **entera**.

        Las dos mitades, porque la segunda es la que se olvida: un hecho de
        escena declara la suya —sin ella R-1 puede decir que hay contradiccion
        pero no donde se establecio lo que choca— y **un hecho del brief no la
        inventa**, porque existia antes de que se escribiera una linea.
        """
        de_escena = self.origen is OrigenDeHecho.ESCENA
        if de_escena and not (self.escena_de_origen or "").strip():
            raise ValueError("un hecho de origen `escena` declara su `escena_de_origen`")
        if not de_escena and self.escena_de_origen is not None:
            raise ValueError("un hecho que no viene de una escena no inventa `escena_de_origen`")
        return self

    def como_linea(self) -> str:
        """La linea que ve el modelo. El identificador va **primero** porque es
        lo que tiene que copiar literal en el `CAN-01`."""
        procedencia = self.escena_de_origen or f"origen: {self.origen.value}"
        campos = (self.hecho_canon_id, self.entidad, self.atributo, self.valor, procedencia)
        return "- " + " · ".join(_en_una_linea(campo) for campo in campos)


class DefectoDelContinuista(BaseModel):
    """Lo que el modelo puede decir de un pasaje, y **nada mas**.

    No hay `version_texto_id`: lo pone el codigo, que sabe que version se juzga.
    Si lo pusiera el modelo seria un dato inventado con aspecto de
    trazabilidad, que es el mismo criterio con el que el Extractor tiene
    prohibido escribir la escena de origen de un hecho.

    Y no hay **ningun** campo donde quepa una reescritura. Con `extra="forbid"`,
    un modelo que devuelva `texto_corregido` no ve su sugerencia ignorada: ve su
    salida rechazada entera. `CLAUDE.md` §9.1, en el esquema y no en el prompt.

    `codigo` es `str` sin restringir por la misma razon que en `Defecto`: si el
    esquema rechazara un codigo fuera de la taxonomia, el defecto mal formado no
    llegaria a existir y no habria nada que contar aparte (CA-17).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    codigo: str
    cita: str
    desplazamiento_inicio: int
    desplazamiento_fin: int
    hecho_canon_id: str | None = None
    evento_id: str | None = None


class InformeDeContinuidad(BaseModel):
    """La salida entera del agente: una clave y ninguna mas."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    defectos: list[DefectoDelContinuista] = Field(default_factory=list)


@dataclass(frozen=True, slots=True)
class CapituloAContrastar:
    """El capitulo y aquello contra lo que se contrasta, juntos.

    `grafo` no es un parametro opcional de conveniencia: sin el no hay contraste
    y lo que salga es una opinion. Va en la misma estructura que el texto para
    que no se pueda llamar al Continuista «solo con la prosa» por descuido.

    **`conocimiento` tampoco lleva valor por defecto**, por lo mismo que
    `HechoUsado.usado_en`: un `()` implicito convertiria el olvido de quien
    construye la proyeccion en «no hay contradiccion posible», y el validador
    mediria el descuido en vez del capitulo. Quien la construye es la consulta
    sobre `estado_en_t` (T6), y esta feature no la hace: recibe filas, no sesion.
    """

    version_texto_id: str
    texto: str
    grafo: tuple[HechoDeCanon, ...]
    conocimiento: tuple[ConocimientoEnT, ...]
    orden_discurso: int

    @property
    def ids_del_grafo(self) -> frozenset[str]:
        """Los identificadores que **existen**: la proyeccion que
        `comprobar_forma` necesita para la regla de dominio 9."""
        return frozenset(hecho.hecho_canon_id for hecho in self.grafo)

    @property
    def contraste(self) -> ContrasteDeConocimiento:
        """La vista y el punto desde el que se mira, que es lo que necesita la
        regla de dominio 2."""
        return ContrasteDeConocimiento(
            conocimiento=self.conocimiento, orden_discurso=self.orden_discurso
        )


@dataclass(frozen=True, slots=True)
class RevisionDeContinuidad:
    """Los dos montones, y los dos presentes.

    Que los mal formados vengan en el mismo resultado es lo que hace
    comprobable «se cuenta aparte» (CA-17, RF-VAL-07), y aqui importa mas que en
    ningun otro sitio: el Continuista es **el emisor** para el que se escribio
    esa comprobacion. Los validadores mecanicos citan del texto y no pueden
    equivocarse de cita; un modelo si. La tasa de mal formados es hoy la unica
    senal directa de que quien los emite esta afirmando cosas que no estan.
    """

    defectos: tuple[Defecto, ...]
    mal_formados: tuple[DefectoMalFormado, ...]


def _en_una_linea(texto: str) -> str:
    """Un hecho ocupa una linea. Un valor con saltos partiria la lista y el
    siguiente hecho se leeria como continuacion del anterior."""
    return " ".join(sin_etiquetas(texto, MARCA_CAPITULO).split())


def sin_etiquetas(texto: str, marca: str) -> str:
    """Quita la etiqueta hasta que quitarla ya no cambie nada.

    Una pasada sola no basta: al borrar el cierre de `</cap</capitulo>itulo>` se
    unen los dos trozos que lo rodeaban y la etiqueta se vuelve a formar. Se
    repite hasta punto fijo, y termina siempre porque cada vuelta que cambia
    algo acorta la cadena.

    Se repite desde `features/canon/agents.py` —tercera copia en el
    repositorio— porque esa es interna a otra feature y §5.1 prohibe entrar por
    ella. Anotado en Desviaciones.
    """
    sano = texto
    while True:
        podado = sano.replace(f"</{marca}>", "").replace(f"<{marca}>", "")
        if podado == sano:
            return sano
        sano = podado


def render_grafo(grafo: Sequence[HechoDeCanon]) -> str:
    """El grafo, en lineas con su identificador. Es lo que convierte la revision
    en un contraste (RF-VAL-06)."""
    if not grafo:
        return SIN_GRAFO
    return "\n".join(hecho.como_linea() for hecho in grafo)


def render_conocimiento(conocimiento: Sequence[ConocimientoEnT], orden_discurso: int) -> str:
    """El estado en T, en lineas con su identificador de evento.

    Solo entran las filas **anteriores** a este capitulo, y esa es la decision
    que hace la seccion util: las posteriores no son conocimiento del capitulo
    que se juzga, y ensenarselas al modelo seria invitarle a emitir `CON-03` que
    el contraste descarta despues. Es «lo que no esta en la lista no existe»
    aplicado tambien al tiempo, y deja al prompt y a `comprobar_forma` mirando
    exactamente las mismas filas.
    """
    anteriores = [
        fila
        for fila in conocimiento
        if fila.sabe_desde is not None and fila.sabe_desde < orden_discurso
    ]
    if not anteriores:
        return SIN_CONOCIMIENTO
    return "\n".join(_linea_de_conocimiento(fila) for fila in anteriores)


def _linea_de_conocimiento(fila: ConocimientoEnT) -> str:
    """El `evento_id` va **primero**: es lo que hay que copiar literal en el
    `CON-03`, igual que el `hecho_canon_id` en el `CAN-01`."""
    campos = (
        fila.evento_id,
        fila.personaje,
        fila.tiempo_historia,
        f"lo sabe desde la escena {fila.sabe_desde}",
    )
    return "- " + " · ".join(_en_una_linea(campo) for campo in campos)


def render_continuista(
    plantilla: str,
    texto: str,
    grafo: Sequence[HechoDeCanon],
    conocimiento: Sequence[ConocimientoEnT],
    orden_discurso: int,
) -> str:
    """El capitulo entra SIEMPRE marcado como dato (`CLAUDE.md` §11).

    Dos propiedades, y la segunda es la que importa: que el capitulo no pueda
    cerrar su etiqueta, y que **lo que rodea a la etiqueta no dependa del
    capitulo**. La segunda es la que hace que un ataque no cambie el prompt, y
    por tanto que un capitulo no pueda desactivar al que lo revisa.
    """
    con_canon = plantilla.replace(HUECO_DEL_CANON, render_grafo(grafo)).replace(
        HUECO_DEL_CONOCIMIENTO, render_conocimiento(conocimiento, orden_discurso)
    )
    con_canon = con_canon.replace(HUECO_DEL_ORDEN, str(orden_discurso))
    if not texto.strip():
        return con_canon.replace(HUECO_DEL_CAPITULO, "")
    bloque = f"<{MARCA_CAPITULO}>\n{sin_etiquetas(texto, MARCA_CAPITULO)}\n</{MARCA_CAPITULO}>"
    return con_canon.replace(HUECO_DEL_CAPITULO, bloque)


class Continuista:
    """El rol, con su cliente inyectado (`CLAUDE.md` §6).

    No toca la base de datos y no recibe sesion: recibe el grafo ya proyectado.
    Es la misma frontera que `puerta.py` declaro en la Fase 2, y la que permite
    probar el contraste sin levantar SQLite.
    """

    def __init__(
        self, cliente: ClienteModelo, semilla: int = 0, plantilla: str | None = None
    ) -> None:
        self._cliente = cliente
        self._semilla = semilla
        self._plantilla = plantilla
        """La v2 cuando no se dice otra cosa, y la v1 alcanzable por parametro.
        Es la costura que la iteracion de *tuning* necesita: comparar dos
        plantillas sobre los mismos capitulos exige poder pedir la vieja sin
        editar nada. Se resuelve al revisar y no aqui, para que construir un
        Continuista no dependa de que el fichero exista."""

    async def revisar(self, capitulo: CapituloAContrastar) -> RevisionDeContinuidad:
        """Contrasta el capitulo contra el grafo y devuelve codigos con cita.

        Un capitulo en blanco **no llama al modelo**: no hay texto del que citar,
        asi que cualquier defecto sobre el seria por fuerza una cita inventada.
        Es el mismo criterio con el que el Extractor no paga por un
        `TextoAportado` vacio.
        """
        if not capitulo.texto.strip():
            return RevisionDeContinuidad(defectos=(), mal_formados=())

        crudo = await self._cliente.completar(
            render_continuista(
                self._plantilla if self._plantilla is not None else plantilla_v2(),
                capitulo.texto,
                capitulo.grafo,
                capitulo.conocimiento,
                capitulo.orden_discurso,
            ),
            semilla=self._semilla,
        )
        informe = _validar(crudo)
        clasificados = clasificar(
            (
                Defecto(
                    codigo=defecto.codigo,
                    version_texto_id=capitulo.version_texto_id,
                    cita=defecto.cita,
                    desplazamiento_inicio=defecto.desplazamiento_inicio,
                    desplazamiento_fin=defecto.desplazamiento_fin,
                    hecho_canon_id=defecto.hecho_canon_id,
                    evento_id=defecto.evento_id,
                )
                for defecto in informe.defectos
            ),
            capitulo.texto,
            capitulo.ids_del_grafo,
            capitulo.contraste,
        )
        return RevisionDeContinuidad(
            defectos=clasificados.bien_formados,
            mal_formados=clasificados.mal_formados,
        )


def _validar(crudo: str) -> InformeDeContinuidad:
    """JSON mal formado y esquema incumplido se cuentan igual: fallo del agente.

    Los dos significan lo mismo para quien llama —no hay revision utilizable— y
    distinguirlos obligaria a manejar dos excepciones para tomar la misma
    decision.
    """
    try:
        return InformeDeContinuidad.model_validate(json_de_modelo(crudo))
    except (json.JSONDecodeError, ValidationError) as error:
        raise SalidaMalFormada(crudo[:200]) from error


# ---------------------------------------------------------------------------
# El Critico: puntua contra la rubrica, justifica y **no repara**
# ---------------------------------------------------------------------------

PROMPT_ID_CRITICO = "critico"
PROMPT_VERSION_CRITICO = "v1"

HUECO_DE_LA_RUBRICA = "{{RUBRICA}}"
HUECO_ESCALA_MINIMO = "{{ESCALA_MINIMO}}"
HUECO_ESCALA_MAXIMO = "{{ESCALA_MAXIMO}}"


def plantilla_critico_v1() -> str:
    """La plantilla del juez, leida al usarla por lo mismo que las del
    Continuista: un fichero de datos que falta da un fallo local y legible, no
    un import que tumba medio backend."""
    return _leer("critico.v1.md")


def hash_de_critico_v1() -> str:
    """Es funcion y no constante por lo mismo: una constante obligaria a leer el
    fichero al importar el modulo. Ata la fila de `ejecucion` a la plantilla
    exacta con la que se juzgo (regla de dominio 7)."""
    return hash_de_plantilla(plantilla_critico_v1())


class PuntuacionDelCritico(BaseModel):
    """Un numero, su criterio y **por que**.

    `justificacion` es `TextoNoVacio` y no `str`: un numero pelado no se puede
    comparar con el del Autor, y comparar los dos es lo unico para lo que el juez
    existe (`RF-JUZ-05`). La segunda barrera esta en la base —el `CheckConstraint`
    de T2 sobre `trim(justificacion)`—, y las dos hacen falta: esta protege lo
    que devuelve el modelo, aquella lo que entre por cualquier otra via.

    **El rango va clavado a la escala de `RUBRICA_V1`**, que es `(1, 5)`. Una
    rubrica con otra escala exigiria tocar aqui, y hay un test que cae el dia que
    alguien la cambie: si el esquema y la rubrica se separasen, el juez podria
    devolver un numero que la rubrica no define y nadie lo notaria.

    Y **no hay ningun campo donde quepa una reescritura**, exactamente como en
    `DefectoDelContinuista`: con `extra="forbid"`, un modelo que devuelva
    `texto_corregido` no ve su sugerencia ignorada, ve su salida rechazada
    entera. `CLAUDE.md` §9.1, en el esquema y no en el prompt.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    criterio: str
    valor: int = Field(ge=1, le=5)
    justificacion: TextoNoVacio


class Juicio(BaseModel):
    """La salida entera del agente: una clave y ninguna mas.

    No hay veredicto, ni nota global, ni nada que se parezca a una decision. El
    juez **no bloquea** (`RF-JUZ-06`) hasta que su correlacion con la revision
    humana este medida y firmada con ese numero delante, y que no tenga donde
    decirlo es mas fuerte que pedirle que no lo diga.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    puntuaciones: list[PuntuacionDelCritico]


@dataclass(frozen=True, slots=True)
class CapituloAJuzgar:
    """El capitulo y aquello contra lo que se juzga, juntos.

    `rubrica` va dentro y no es parametro suelto por el mismo motivo que el
    `grafo` del Continuista: sin ella lo que sale es una impresion, y no debe
    poder llamarse al Critico «solo con la prosa» por descuido.
    """

    version_texto_id: str
    texto: str
    rubrica: Rubrica


class RubricaDiscordante(Exception):
    """El capitulo llega con una rubrica distinta de la del juez.

    Es un fallo de quien llama, no del modelo, y tiene excepcion propia porque lo
    que estaria pasando es justo lo que `CA-20` prohibe: medir con una regla y
    declarar otra. Dos rubricas parecidas producen numeros que se comparan sin
    protestar y que no significan lo mismo.
    """


def render_rubrica(rubrica: Rubrica) -> str:
    """La rubrica entera, criterio a criterio y **con sus dos anclajes**.

    Sin anclajes en el prompt el modelo puntua contra su propia idea de que es un
    3, y la rubrica deja de ser el instrumento compartido que `CA-20` pide: el
    Autor mediria con las descripciones delante y el juez sin ellas.
    """
    minimo, maximo = rubrica.escala
    bloques = []
    for criterio in rubrica.criterios:
        bloques.append(
            "### "
            + _en_una_linea(criterio.nombre)
            + "\n\n"
            + _en_una_linea(criterio.definicion)
            + "\n\n"
            + f"- Vale **{minimo}** cuando: "
            + _en_una_linea(criterio.ancla_minimo)
            + "\n"
            + f"- Vale **{maximo}** cuando: "
            + _en_una_linea(criterio.ancla_maximo)
        )
    return "\n\n".join(bloques)


def render_critico(plantilla: str, texto: str, rubrica: Rubrica) -> str:
    """El capitulo entra SIEMPRE marcado como dato (`CLAUDE.md` §11).

    Las mismas dos propiedades que en `render_continuista`, y la segunda es la
    que importa: que el capitulo no pueda cerrar su etiqueta, y que **lo que
    rodea a la etiqueta no dependa del capitulo**. Un capitulo no puede
    desactivar al que lo juzga.
    """
    minimo, maximo = rubrica.escala
    con_rubrica = (
        plantilla.replace(HUECO_DE_LA_RUBRICA, render_rubrica(rubrica))
        .replace(HUECO_ESCALA_MINIMO, str(minimo))
        .replace(HUECO_ESCALA_MAXIMO, str(maximo))
    )
    if not texto.strip():
        return con_rubrica.replace(HUECO_DEL_CAPITULO, "")
    bloque = f"<{MARCA_CAPITULO}>\n{sin_etiquetas(texto, MARCA_CAPITULO)}\n</{MARCA_CAPITULO}>"
    return con_rubrica.replace(HUECO_DEL_CAPITULO, bloque)


class Critico:
    """El juez, con su cliente y su rubrica inyectados (`CLAUDE.md` §6).

    **No repara y no decide.** Devuelve un juicio; quien lo compare con la
    revision humana es T9, y quien decida algun dia si bloquea sera una persona
    con la distancia medida delante (`RF-JUZ-06`).

    No toca la base de datos y no recibe sesion, igual que el Continuista: es lo
    que permite probar el juicio sin levantar SQLite.
    """

    def __init__(self, cliente: ClienteModelo, rubrica: Rubrica, semilla: int = 0) -> None:
        self._cliente = cliente
        self._rubrica = rubrica
        self._semilla = semilla

    @property
    def rubrica(self) -> Rubrica:
        """La rubrica con la que juzga, **para que se pueda pedir**.

        `CA-20` exige que la del juez y la que se le presenta al Autor sean la
        misma. Una propiedad que la devuelve es lo que hace comprobable esa
        frase; sin ella solo se podria prometer.
        """
        return self._rubrica

    async def juzgar(self, capitulo: CapituloAJuzgar) -> Juicio:
        """Puntua el capitulo contra la rubrica y devuelve numeros justificados.

        `modelo=MODELO_JUEZ` va en la llamada y no en el constructor del cliente:
        es P-02 hecho **pedible**, y mientras el modelo lo fijara solo quien
        construye el cliente, la separacion no se podia pedir y ningun test podia
        caer por incumplirla. Hoy `MODELO_JUEZ` y `MODELO_ESCRITOR` valen lo
        mismo —Haiku 4.5 en todos los roles—, y la linea sigue aqui para que
        revertirlo sea cambiar una constante.
        """
        if capitulo.rubrica != self._rubrica:
            raise RubricaDiscordante(
                f"el capitulo trae la rubrica {capitulo.rubrica.version} y el juez "
                f"usa la {self._rubrica.version}"
            )

        crudo = await self._cliente.completar(
            render_critico(plantilla_critico_v1(), capitulo.texto, self._rubrica),
            semilla=self._semilla,
            modelo=MODELO_JUEZ,
        )
        juicio = _validar_juicio(crudo)
        _comprobar_cobertura(juicio, self._rubrica)
        return juicio


def _validar_juicio(crudo: str) -> Juicio:
    """JSON mal formado y esquema incumplido se cuentan igual: fallo del agente.

    El mismo criterio que `_validar` del Continuista, y por el mismo motivo: los
    dos significan lo mismo para quien llama —no hay juicio utilizable— y
    distinguirlos obligaria a manejar dos excepciones para tomar la misma
    decision.

    Y por `json_de_modelo` y no por `json.loads`, que es la leccion del mismo
    dia: la primera corrida real murio porque el modelo devolvio JSON impecable
    **dentro de una valla de markdown**. El Critico habria sido el sexto agente
    en tropezar con ella, y no se habria visto hasta conectar con el proveedor,
    porque el doble devuelve lo que el test le pone.
    """
    try:
        return Juicio.model_validate(json_de_modelo(crudo))
    except (json.JSONDecodeError, ValidationError) as error:
        raise SalidaMalFormada(crudo[:200]) from error


def _comprobar_cobertura(juicio: Juicio, rubrica: Rubrica) -> None:
    """R-5: el juicio cubre **exactamente** la rubrica, una vez cada criterio.

    Esto no lo compra `extra="forbid"`, y ahi esta el motivo de que sea codigo y
    no esquema: un modelo puede devolver una lista corta con las claves
    correctas, y esa salida es valida como esquema y no lo es como juicio. Sin la
    comprobacion, la distancia de `RF-JUZ-05` compararia seis numeros del Autor
    con dos del juez y llamaria a eso una medida.

    Se comparan **multiconjuntos** y no tamanos: un juicio que repite un criterio
    y se deja otro tiene la longitud correcta, y es el fallo que contar cuantas
    vienen no ve.
    """
    esperados = sorted(criterio.nombre for criterio in rubrica.criterios)
    recibidos = sorted(puntuacion.criterio for puntuacion in juicio.puntuaciones)
    if recibidos != esperados:
        raise SalidaMalFormada(
            f"el juicio no cubre la rubrica: esperados {esperados}, recibidos {recibidos}"
        )
