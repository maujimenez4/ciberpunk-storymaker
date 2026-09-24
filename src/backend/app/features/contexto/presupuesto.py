"""El techo de **una** llamada, repartido en ocho capas (`CLAUDE.md` §4.1).

Es la restriccion de diseno mas importante del proyecto, y aqui vive entera:
los topes, el recorte y el fallo. Codigo puro —ni base de datos ni framework—
porque el Ensamblador es codigo y no un modelo (RF-CTX-01): si fuera un modelo
no se podria reproducir un fallo.

**Los topes suman 100.000 exactos**, y eso no es decoracion: hace que respetar
el tope de cada capa sea lo mismo que respetar el techo de la llamada, sin una
segunda comprobacion que pudiera discrepar de la primera. El test
`test_los_topes_son_los_literales_de_claude_md_y_agotan_el_techo` guarda esa
identidad: si alguien sube un tope, cae.

**Este modulo no es el techo concurrente**, que es la suma de las llamadas *en
vuelo* y lo impone el encargo §7 (`architecture.md` §2.2, T10). Que las dos
cifras sean 100.000 es casualidad de numeros: aquel se comprueba al conceder el
turno, este al construir el paquete.

Tres reglas gobiernan el recorte, y las tres estan probadas:

1. **Se recorta la capa que se pasa, no las vecinas** (RF-CTX-03). Recortar a
   prorrata es lo que parece razonable y es justo lo que el requisito prohibe.
2. **Constitucional e Instruccion no se recortan nunca** (RF-CTX-07): lo que la
   obra es y lo que se pide no son material sobrante.
3. **Se quitan piezas enteras, nunca media pieza**, y lo quitado sale nombrado
   en el desglose. `CLAUDE.md` §15: no truncar sin registrar que se ha quitado.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from app.commons.domain.errores import ContextBudgetExceeded
from app.commons.llm.contador import ContadorDeTokens

TECHO_POR_LLAMADA = 100_000
"""Tokens de **una** llamada al modelo. No confundir con el concurrente (T10)."""


class Capa(StrEnum):
    """Las ocho capas del paquete de contexto (`definitions.md` §7).

    El nombre es vocabulario de todo el sistema: el mismo en el esquema, en el
    desglose que se persiste en `ejecucion` y en la interfaz (`CLAUDE.md` §2).
    """

    CONSTITUCIONAL = "constitucional"
    ESTRUCTURAL = "estructural"
    CANON = "canon"
    ESTADO_EN_T = "estado_en_t"
    CONTINUIDAD = "continuidad"
    MEMORIA = "memoria"
    INSTRUCCION = "instruccion"
    RESERVA = "reserva"


TOPES: Mapping[Capa, int] = MappingProxyType(
    {
        Capa.CONSTITUCIONAL: 5_000,
        Capa.ESTRUCTURAL: 10_000,
        Capa.CANON: 20_000,
        Capa.ESTADO_EN_T: 15_000,
        Capa.CONTINUIDAD: 20_000,
        Capa.MEMORIA: 10_000,
        Capa.INSTRUCCION: 10_000,
        Capa.RESERVA: 10_000,
    }
)
"""Copiados de `CLAUDE.md` §4.1 y `architecture.md` §2.1. No se derivan ni se
redondean, y son inmutables: un presupuesto que se puede reescribir en caliente
no es un presupuesto."""

NUNCA_SE_RECORTAN: frozenset[Capa] = frozenset({Capa.CONSTITUCIONAL, Capa.INSTRUCCION})
"""RF-CTX-07. Si una de estas dos se pasa de su tope, no hay recorte: hay fallo."""


@dataclass(frozen=True, slots=True)
class Pieza:
    """Lo mas pequeno que entra o no entra en el paquete.

    El `identificador` es lo que hace auditable el paquete: la capa de canon
    etiqueta cada pieza por su `hc_id` **y no por posicion**, porque la posicion
    cambia con el recorte y el identificador no (RF-CTX-08). Es opcional porque
    no todas las capas tienen de donde sacarlo.
    """

    texto: str
    identificador: str | None = None


@dataclass(frozen=True, slots=True)
class LineaDeCapa:
    """Una capa en el desglose: lo que entro, lo que se quito y lo que cuesta."""

    capa: Capa
    tope: int
    tokens: int
    piezas: tuple[Pieza, ...]
    descartadas: tuple[Pieza, ...]


@dataclass(frozen=True, slots=True)
class Desglose:
    """El desglose por capa que viaja **junto al paquete** (RF-CTX-05).

    Se persiste en `ejecucion`, y de ahi sale CU-07: saber que se envio al
    modelo sin volver a preguntarselo a nadie. Trae siempre las ocho capas,
    tambien las vacias: una capa ausente y una capa vacia no son lo mismo, y
    quien audita no deberia tener que adivinar cual era.
    """

    lineas: Mapping[Capa, LineaDeCapa]

    @property
    def total(self) -> int:
        """Lo que suma el paquete. Suma lo que dice: son las mismas lineas."""
        return sum(linea.tokens for linea in self.lineas.values())

    @property
    def reserva_libre(self) -> int:
        """Lo que queda en la reserva para el reintento con el defecto anadido.

        Tras un ensamblado normal es la reserva entera: nadie la surte
        (`architecture.md` §4.8, su fila no tiene memoria de origen). Es el
        margen que permite volver a pedir la escena con la cita del defecto sin
        tener que recortar nada de lo que ya cabia.
        """
        return TOPES[Capa.RESERVA] - self.lineas[Capa.RESERVA].tokens


def presupuestar(piezas: Mapping[Capa, Sequence[Pieza]], contador: ContadorDeTokens) -> Desglose:
    """Reparte las piezas por capas, recorta lo que sobra y devuelve el desglose.

    El `contador` es **inyectado** (RF-CTX-02): este modulo no sabe contar
    tokens ni lo intenta, que es lo que impide que acabe estimando por
    caracteres.

    Cada capa llega ordenada **de mas a menos importante**: quien la surte sabe
    que se recorta primero (`architecture.md` §2.1, tercera columna), y el
    recorte quita por el final.

    Lanza `ContextBudgetExceeded` —sin llamar a nadie, porque aqui no hay a
    quien llamar— cuando una capa no cabe en su tope y no se puede recortar: o
    porque es de las que no se recortan, o porque ni su pieza mas importante
    cabe ella sola.
    """
    lineas = {capa: _linea(capa, piezas.get(capa, ()), contador) for capa in Capa}
    return Desglose(lineas=MappingProxyType(lineas))


def _linea(capa: Capa, piezas: Sequence[Pieza], contador: ContadorDeTokens) -> LineaDeCapa:
    """Una capa, contada y —si hace falta y se puede— recortada."""
    tope = TOPES[capa]
    contadas = [(pieza, contador.contar(pieza.texto)) for pieza in piezas]
    tokens = sum(coste for _, coste in contadas)

    if tokens <= tope:
        return LineaDeCapa(
            capa=capa,
            tope=tope,
            tokens=tokens,
            piezas=tuple(pieza for pieza, _ in contadas),
            descartadas=(),
        )

    if capa in NUNCA_SE_RECORTAN:
        raise ContextBudgetExceeded(capa=capa, tokens=tokens, tope=tope)

    descartadas: list[Pieza] = []
    # Se quita por el final —lo menos importante— y **nunca la ultima pieza**:
    # vaciar una capa que tenia contenido no es recortarla, es perderla, y el
    # Ensamblador ya no podria distinguirla de una que nunca se surtio
    # (RF-CTX-06). Si lo que queda sigue sin caber, se falla y se dice donde.
    while len(contadas) > 1 and tokens > tope:
        pieza, coste = contadas.pop()
        descartadas.append(pieza)
        tokens -= coste

    if tokens > tope:
        raise ContextBudgetExceeded(capa=capa, tokens=tokens, tope=tope)

    return LineaDeCapa(
        capa=capa,
        tope=tope,
        tokens=tokens,
        piezas=tuple(pieza for pieza, _ in contadas),
        descartadas=tuple(descartadas),
    )
