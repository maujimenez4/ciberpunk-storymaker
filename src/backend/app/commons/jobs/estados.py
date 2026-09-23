"""Los diez estados del trabajo y sus transiciones (`architecture.md` §3.3).

**La máquina es explícita a propósito.** Si el orden de los pasos lo decidiera un
modelo, un fallo no se podría reproducir ni atribuir (decisión 10). Aquí el orden
es una tabla, y la traza de una ejecución es una lista de transiciones, no una
conversación.

Lo que esta tabla protege por encima de todo: **ningún estado se salta**.
`VALIDANDO` no puede llegar a `INTEGRADA` sin pasar por `EXTRAYENDO`, porque es
el Extractor quien deja rastro en la memoria de largo plazo (§4.4). Saltarse ese
paso daría una escena en el manuscrito de la que el canon no sabe nada, y el
síntoma aparecería capítulos después.
"""

from enum import StrEnum


class Estado(StrEnum):
    PLANIFICANDO = "PLANIFICANDO"
    ENSAMBLANDO = "ENSAMBLANDO"
    ESCRIBIENDO = "ESCRIBIENDO"
    VALIDANDO = "VALIDANDO"
    REPARANDO = "REPARANDO"
    EXTRAYENDO = "EXTRAYENDO"
    INTEGRADA = "INTEGRADA"
    ESCALADA = "ESCALADA"
    FALLIDA = "FALLIDA"
    CANCELADA = "CANCELADA"


# §3.3. `ESCALADA` es terminal **hasta que el autor actúe**: D-08 le añade dos
# salidas, y por eso no está en TERMINALES_DEFINITIVOS.
TERMINALES = frozenset(
    {Estado.INTEGRADA, Estado.ESCALADA, Estado.FALLIDA, Estado.CANCELADA}
)
TERMINALES_DEFINITIVOS = frozenset({Estado.INTEGRADA, Estado.FALLIDA, Estado.CANCELADA})

# Un paso que supera su plazo, o cuya espera de turno vence, va a FALLIDA desde
# donde esté (§3.6). Se declara aparte para que la tabla lea el flujo normal.
EN_CURSO = frozenset(
    {
        Estado.PLANIFICANDO,
        Estado.ENSAMBLANDO,
        Estado.ESCRIBIENDO,
        Estado.VALIDANDO,
        Estado.REPARANDO,
        Estado.EXTRAYENDO,
    }
)

TRANSICIONES: dict[Estado, frozenset[Estado]] = {
    Estado.PLANIFICANDO: frozenset({Estado.ENSAMBLANDO, Estado.CANCELADA}),
    # ContextBudgetExceeded va a FALLIDA sin llamar al modelo (§3.6).
    Estado.ENSAMBLANDO: frozenset(
        {Estado.ESCRIBIENDO, Estado.FALLIDA, Estado.CANCELADA}
    ),
    Estado.ESCRIBIENDO: frozenset({Estado.VALIDANDO, Estado.CANCELADA}),
    Estado.VALIDANDO: frozenset(
        {Estado.EXTRAYENDO, Estado.REPARANDO, Estado.CANCELADA}
    ),
    # Máximo dos reparaciones dirigidas; después, humano (RF-ORQ-07).
    Estado.REPARANDO: frozenset({Estado.ESCRIBIENDO, Estado.ESCALADA}),
    Estado.EXTRAYENDO: frozenset({Estado.INTEGRADA}),
    Estado.INTEGRADA: frozenset(),
    # D-08: tras la edición humana reentra por VALIDANDO (RF-ORQ-17); si el autor
    # acepta pese al defecto, pasa a EXTRAYENDO con el defecto anulado registrado
    # (RF-ORQ-18). Sin estas dos salidas, CU-04 no podría prometer que una escena
    # nunca se queda indefinidamente en ESCALADA.
    Estado.ESCALADA: frozenset({Estado.VALIDANDO, Estado.EXTRAYENDO, Estado.CANCELADA}),
    Estado.FALLIDA: frozenset(),
    Estado.CANCELADA: frozenset(),
}


# --- No todo trabajo es el ciclo de una escena -------------------------------
#
# Los diez estados de arriba describen **ese** ciclo. Un trabajo de biblia, de
# outline o de ficha no pasa por `EXTRAYENDO` -no deja rastro en la memoria de
# largo plazo- y con una sola tabla no tenia ningun camino a un terminal de
# exito: nacia y solo podia acabar cancelado.
#
# La invariante que la tabla de arriba protege no se toca: sigue rigiendo entera
# para las escenas, que es donde saltarse `EXTRAYENDO` dejaria una escena en el
# manuscrito de la que el canon no sabe nada.

TIPO_ESCENA = "escribir_escena"

TRANSICIONES_SIMPLES: dict[Estado, frozenset[Estado]] = {
    Estado.PLANIFICANDO: frozenset(
        {Estado.INTEGRADA, Estado.FALLIDA, Estado.CANCELADA}
    ),
    Estado.INTEGRADA: frozenset(),
    Estado.FALLIDA: frozenset(),
    Estado.CANCELADA: frozenset(),
}


def transiciones_de(tipo: str) -> dict[Estado, frozenset[Estado]]:
    """Por defecto, la tabla estricta.

    El defecto importa: si un tipo nuevo se olvidara de declararse, se llevaria
    la maquina del ciclo -que como mucho le impedira avanzar y saltara- y no la
    permisiva, que le dejaria marcar exito sin haber hecho nada.
    """
    return TRANSICIONES if tipo == TIPO_ESCENA else TRANSICIONES_SIMPLES


class TransicionInvalida(ValueError):
    """Se intentó un salto que la máquina no declara."""

    def __init__(self, desde: Estado, hasta: Estado) -> None:
        super().__init__(
            f"transicion no declarada: {desde} -> {hasta}. Los estados no se "
            f"saltan (architecture.md §3.3)"
        )
        self.desde = desde
        self.hasta = hasta


def puede_ir(desde: Estado, hasta: Estado, tipo: str = TIPO_ESCENA) -> bool:
    """Incluye la salida a `FALLIDA` por plazo agotado desde cualquier paso."""
    if hasta is Estado.FALLIDA and desde in EN_CURSO:
        return True
    return hasta in transiciones_de(tipo).get(desde, frozenset())


def exigir(desde: Estado, hasta: Estado, tipo: str = TIPO_ESCENA) -> None:
    if not puede_ir(desde, hasta, tipo):
        raise TransicionInvalida(desde, hasta)
