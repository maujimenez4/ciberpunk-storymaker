"""El Ensamblador, y **es codigo, no un modelo** (RF-CTX-01, `CLAUDE.md` §9.1).

`contexto` es la unica feature de `CLAUDE.md` §9 sin `agents.py`, y este modulo
es el motivo: el paquete se ensambla con una funcion pura. **El motivo no es la
eficiencia — es que si fuera un modelo no se podria reproducir un fallo.** Un
test lo afirma por analisis del arbol de sintaxis: ningun modulo de produccion
de esta feature importa el cliente de modelo, asi que no hay forma de que el
ensamblado dependa de una llamada.

Este modulo hace tres cosas, y ninguna mas:

1. **Comprueba que no falte una capa que deberia estar surtida** (RF-CTX-06,
   R-3), y falla **antes** de que nadie llame a nadie.
2. Delega el reparto y el recorte en `presupuestar` (T5), que es quien sabe de
   topes.
3. Devuelve el **paquete junto a su desglose** (RF-CTX-05) y los
   **identificadores por capa de lo que sobrevivio al recorte** (RF-CTX-09).

**El censo es la pieza de diseno que hace ejecutable R-3.** Un `Surtido` no trae
solo lo que entrega: trae tambien cuanto tenia el almacen que lo surtio. Sin ese
segundo numero, «una capa vacia cuando **deberia** tener contenido» no es
comprobable — una capa vacia es una capa vacia, y el Ensamblador no puede
distinguir el capitulo sin memoria pertinente, que es normal, del almacen que
no respondio, que es un fallo. Con el, la distincion es una comparacion y tiene
test por los dos lados.

**La reserva queda fuera de la comprobacion**, y no por excepcion: en la tabla
de `architecture.md` §4.8 su fila **no tiene memoria de origen**. Exigirle
contenido seria exigir que alguien la surtiera, y existe para lo contrario.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from app.commons.domain.errores import ErrorDeDominio
from app.commons.llm.contador import ContadorDeTokens
from app.features.contexto.presupuesto import Capa, Desglose, Pieza, presupuestar

CAPAS_CON_ORIGEN: frozenset[Capa] = frozenset(Capa) - {Capa.RESERVA}
"""Las siete capas que `architecture.md` §4.8 hace salir de un almacen.

Se deriva de `Capa` en vez de escribirse a mano para que una capa nueva entre
con origen por defecto: olvidarse de anadirla aqui la dejaria sin la
comprobacion de RF-CTX-06 y nada fallaria.
"""

ENCABEZADOS: Mapping[Capa, str] = MappingProxyType(
    {
        Capa.CONSTITUCIONAL: "constitucional: la obra y su discurso",
        Capa.ESTRUCTURAL: "estructural: outline y beats del capitulo",
        Capa.CANON: "canon relevante: hechos establecidos",
        Capa.ESTADO_EN_T: "estado_en_t: quien sabe que, derivado del ledger",
        Capa.CONTINUIDAD: "continuidad local: las escenas anteriores",
        Capa.MEMORIA: "memoria recuperada: fragmentos pertinentes",
        Capa.INSTRUCCION: "instruccion: la ficha de escena y lo que se pide",
        Capa.RESERVA: "reserva",
    }
)
"""El rotulo de cada capa en el texto. Empieza por el valor de la capa a
proposito: el paquete que llega al Escritor dice de donde sale cada cosa, con
el mismo vocabulario del desglose y del esquema (`CLAUDE.md` §2)."""


class CapaVacia(ErrorDeDominio):
    """Una capa llego vacia y su almacen tenia con que surtirla (RF-CTX-06, R-3).

    **Es un fallo del almacen, no del Escritor**, y por eso se lanza antes de
    llamar: un paquete al que le falta el canon produce prosa que contradice lo
    ya escrito, y la auditoria acusaria a quien escribio de ignorar un hecho
    que nunca vio. Que el fallo salga aqui es lo que hace **atribuible** el
    defecto (`CLAUDE.md` §9.1).

    Hereda de `ErrorDeDominio` —el manejador central la traduce sin darla de
    alta— y **no** de `ContextBudgetExceeded`: un almacen que no surte y un
    paquete que no cabe son dos averias distintas con dos arreglos distintos.

    Vive aqui y no en `commons/domain/errores.py` por el mismo motivo que las
    cinco de T3 viven en `outline/service.py`: ese fichero tiene dueno en el
    reparto de la fase y no es esta tarea (ver Desviaciones).
    """

    def __init__(self, capa: str, disponibles: int) -> None:
        self.capa = str(capa)
        self.disponibles = disponibles
        super().__init__(
            f"La capa {self.capa} llego vacia y su almacen tenia {disponibles} "
            "pieza(s) con que surtirla: es un fallo del almacen, no del Escritor"
        )


@dataclass(frozen=True, slots=True)
class Surtido:
    """Lo que un almacen entrega para una capa, **con el censo de lo que tenia**.

    Los dos numeros no son el mismo dato dicho dos veces, y ahi esta todo:
    `piezas` es lo que entra en el paquete y `disponibles` es lo que el almacen
    encontro **y era pertinente**. Coinciden en el caso normal; cuando no
    coinciden, es que algo se surtio mal, y eso es RF-CTX-06.

    Quien surte es responsable de que `disponibles` sea honesto. Contar ahi lo
    que el almacen tiene *en total* —sin filtrar por pertinencia— convertiria
    en error cualquier capa legitimamente vacia; contar `len(piezas)` haria la
    regla inalcanzable. Las dos trampas tienen test.
    """

    piezas: tuple[Pieza, ...] = ()
    disponibles: int = 0


@dataclass(frozen=True, slots=True)
class Paquete:
    """Lo que se envia al modelo para escribir una escena (`definitions.md` §7).

    Viaja **con su desglose** (RF-CTX-05) y con los identificadores por capa de
    lo que sobrevivio al recorte (RF-CTX-09). Los tres campos son lo que
    `ejecucion` necesita para que CU-07 pueda responderse sin volver a
    preguntarle a nadie.
    """

    texto: str
    desglose: Desglose
    ids_por_capa: Mapping[Capa, tuple[str, ...]]

    @property
    def tokens_por_capa(self) -> dict[str, int]:
        """Tal y como se persiste en `ejecucion.tokens_por_capa`: por nombre de capa."""
        return {capa.value: linea.tokens for capa, linea in self.desglose.lineas.items()}

    @property
    def tokens_previstos(self) -> int:
        """El recuento **previo** de P-A: lo que decide si se llama (RF-CTX-02)."""
        return self.desglose.total


def ensamblar(surtidos: Mapping[Capa, Surtido], contador: ContadorDeTokens) -> Paquete:
    """Las ocho capas, en su orden, contadas y recortadas. Sin llamar a nadie.

    El orden de los pasos importa y es este:

    1. **Primero la comprobacion de capas** (RF-CTX-06). Se hace antes de
       contar porque un paquete al que le falta el canon no mejora por caber:
       fallar por el motivo correcto vale mas que fallar despues por otro.
    2. Despues `presupuestar`, que es de T5 y sabe de topes y de recorte.
    3. Y solo al final el texto y los identificadores, que se leen de lo que
       **sobrevivio**.

    Es una funcion pura: mismos surtidos, mismo paquete. Es lo que permite
    reproducir un fallo, y lo que hace que un defecto se pueda atribuir.
    """
    for capa in sorted(CAPAS_CON_ORIGEN):
        surtido = surtidos.get(capa, Surtido())
        if surtido.disponibles > 0 and not surtido.piezas:
            raise CapaVacia(capa=capa, disponibles=surtido.disponibles)

    desglose = presupuestar({capa: surtidos.get(capa, Surtido()).piezas for capa in Capa}, contador)

    return Paquete(
        texto=_texto(desglose),
        desglose=desglose,
        ids_por_capa=MappingProxyType(
            {
                capa: tuple(
                    pieza.identificador
                    for pieza in desglose.lineas[capa].piezas
                    if pieza.identificador is not None
                )
                for capa in CAPAS_CON_ORIGEN
            }
        ),
    )


def _texto(desglose: Desglose) -> str:
    """El paquete, rotulado por capas y **siempre en el mismo orden**.

    Se recorre `Capa` y no el diccionario: un paquete cuyo orden dependiera del
    orden de insercion cambiaria con quien lo surte, y dos ensamblados del mismo
    estado dejarian de dar el mismo texto.

    Se escriben las piezas **que quedaron**, nunca las descartadas: lo recortado
    sale nombrado en el desglose y no en el prompt (`CLAUDE.md` §15, no truncar
    sin registrar que se ha quitado).
    """
    bloques: list[str] = []
    for capa in Capa:
        piezas = desglose.lineas[capa].piezas
        if not piezas:
            continue
        cuerpo = "\n\n".join(pieza.texto for pieza in piezas)
        bloques.append(f"## {ENCABEZADOS[capa]}\n\n{cuerpo}")
    return "\n\n".join(bloques)
