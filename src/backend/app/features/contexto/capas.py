"""Las ocho capas del paquete, sus topes y su orden de recorte.

`architecture.md` §2.1 y §4.8. Esto es el corazón de la v1 y el único componente
cuyo fallo es **silencioso**: un paquete mal ensamblado produce prosa que parece
correcta y contradice el capítulo 3.

Tres decisiones estructurales:

**Cada capa es una lista de piezas con prioridad**, no un bloque de texto. Sin
piezas, «recortar» solo podría significar cortar por el final, que es justo lo
que RF-CTX-05 prohíbe. Con piezas, recortar es **descartar las menos
importantes**, y qué es menos importante lo declara §2.1 capa por capa.

**Cada capa declara su almacén de origen** (§4.8). Si llega vacía, es fallo del
almacén que la surte y no del Escritor (RF-CTX-14): un paquete puede estar dentro
de presupuesto, con el desglose cuadrado, y dejar al Escritor sin canon.

**Dos capas no se recortan nunca.** La constitucional lleva las restricciones
duras y la de instrucción lleva la ficha: recortarlas no ahorra tokens, cambia lo
que se pide.
"""

from dataclasses import dataclass, field
from enum import StrEnum


class Capa(StrEnum):
    """En el orden en que se ensamblan y se presentan."""

    CONSTITUCIONAL = "constitucional"
    ESTRUCTURAL = "estructural"
    CANON_RELEVANTE = "canon_relevante"
    ESTADO_EN_T = "estado_en_t"
    CONTINUIDAD_LOCAL = "continuidad_local"
    MEMORIA_RECUPERADA = "memoria_recuperada"
    INSTRUCCION = "instruccion"
    RESERVA = "reserva"


# §2.1. Suman 100.000.
TOPES: dict[Capa, int] = {
    Capa.CONSTITUCIONAL: 5_000,
    Capa.ESTRUCTURAL: 10_000,
    Capa.CANON_RELEVANTE: 20_000,
    Capa.ESTADO_EN_T: 15_000,
    Capa.CONTINUIDAD_LOCAL: 20_000,
    Capa.MEMORIA_RECUPERADA: 10_000,
    Capa.INSTRUCCION: 10_000,
    Capa.RESERVA: 10_000,
}

LIMITE_DURO = 100_000

# RF-CTX-04. Recortarlas no ahorraría tokens: cambiaría lo que se pide.
PROTEGIDAS = frozenset({Capa.CONSTITUCIONAL, Capa.INSTRUCCION})

# RF-CTX-11. No se llena: queda libre para que el reintento con el defecto
# añadido siga cabiendo.
RESERVADA = Capa.RESERVA

# Prefijo de la etiqueta de un fragmento recuperado. Lo que va detras es su
# identificador, y de ahi salen los `ids_recuperados` que `ejecucion` persiste
# (RI-14) y que hacen reconstruible el paquete (CA-10).
ETIQUETA_RECUPERADO = "recuperado:"

# §4.8: de qué almacén sale cada capa. Una capa con origen declarado que llegue
# vacía detiene el ensamblado (RF-CTX-14).
ORIGEN: dict[Capa, str] = {
    Capa.CONSTITUCIONAL: "biblia y parametros de discurso",
    Capa.ESTRUCTURAL: "outline y beats del capitulo",
    Capa.CANON_RELEVANTE: "grafo de canon, filtrado por la ficha",
    Capa.ESTADO_EN_T: "vista derivada del ledger",
    Capa.CONTINUIDAD_LOCAL: "escenas N-1 y N-2",
    Capa.MEMORIA_RECUPERADA: "fragmentos y resumenes, tras §4.6",
    Capa.INSTRUCCION: "ficha de escena y prompt versionado",
}

# §2.1, columna «Qué se recorta primero». Es lo que hace comprobable P-50: no
# basta con que la capa quepa, tiene que haber cedido lo declarado.
QUE_CEDE_PRIMERO: dict[Capa, str] = {
    Capa.ESTRUCTURAL: "detalle de beats lejanos",
    Capa.CANON_RELEVANTE: "personajes mencionados, no presentes",
    Capa.ESTADO_EN_T: "conocimientos antiguos ya usados",
    Capa.CONTINUIDAD_LOCAL: "escena N-2 antes que N-1",
    Capa.MEMORIA_RECUPERADA: "resultados de menor puntuacion",
}


@dataclass(frozen=True)
class Pieza:
    """Un trozo de capa que se puede descartar entero.

    `prioridad` ordena la supervivencia: **la más baja se descarta primero**.
    `etiqueta` no es decorativa — es lo que permite a un test afirmar *qué* se
    recortó, y no solo que la capa quepa.
    """

    texto: str
    prioridad: int
    etiqueta: str = ""


@dataclass
class CapaEnsamblada:
    """Una capa ya construida, antes de contar y recortar."""

    capa: Capa
    piezas: list[Pieza] = field(default_factory=list)
    descartadas: list[Pieza] = field(default_factory=list)

    @property
    def texto(self) -> str:
        return "\n".join(p.texto for p in self.piezas)

    @property
    def esta_vacia(self) -> bool:
        return not any(p.texto.strip() for p in self.piezas)

    def descartar_menos_importante(self) -> Pieza | None:
        """Quita una pieza, la de menor prioridad. Devuelve cuál.

        Recortar es descartar piezas enteras, nunca cortar texto por el final:
        media frase de canon es peor que ninguna, porque el Escritor la lee como
        un hecho completo.
        """
        if not self.piezas:
            return None
        peor = min(self.piezas, key=lambda p: p.prioridad)
        self.piezas.remove(peor)
        self.descartadas.append(peor)
        return peor
