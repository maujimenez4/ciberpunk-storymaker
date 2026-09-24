"""La maquina de estados del ciclo de escena. **RF-ORQ-01, RF-ORQ-02 y R-6.**

`architecture.md` §3 lo dice en una frase: «el orquestador es **codigo
determinista**, una maquina de estados explicita. No hay ningun agente que
decida cual es el siguiente paso». Este fichero es esa frase.

**Por que importa que sea codigo y no un modelo.** Si quien decide el orden es
un agente, un fallo no se puede reproducir ni atribuir: la traza es una
conversacion y no una tabla, y a la pregunta «por que este trabajo acabo
escalado» solo se puede contestar leyendo prosa. Aqui la respuesta es una fila
de `_TRANSICIONES` y el contador de la fila `trabajo`.

Tres decisiones, y las tres se prueban:

| Decision | Consecuencia |
| --- | --- |
| La senal es un **miembro de un alfabeto cerrado**, nunca una cadena | Lo que un agente devuelve es prosa; el orquestador la traduce a senal **en codigo**, y esa traduccion es lo auditable |
| Lo que no esta en la tabla **se lanza** | Un `else` que traga convierte un fallo de logica en un estado plausible: el trabajo acaba donde nadie pidio y la traza dice que todo fue bien |
| El destino se **persiste antes de devolverse** | RF-ORQ-02: al arrancar, el orquestador lee los trabajos vivos de SQLite (§3.7). Un estado en memoria del proceso no sobrevive a la caida que justifica que exista |

**El unico destino que no sale de la tabla es el de `REPARANDO`**, porque
depende del contador de reparaciones y no solo del par estado-senal. Es la
diferencia entre `ESCRIBIENDO` y `ESCALADA`, y el contador vive en la fila, no
en el argumento de quien llama.

**Lo que este fichero NO hace, y no es un olvido:** no decide cual es el
capitulo siguiente ni guarda checkpoint —eso es la Tarea 5— y no toca el
`run_id` —Tarea 3—. De la maquina de la novela (§3.9) aqui solo esta el freno
de R-6: un capitulo escalado detiene la obra.
"""

from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.domain.errores import ErrorDeDominio
from app.features.escritura.modelos import INTENTOS_MAXIMOS, Trabajo


class Estado(StrEnum):
    """Los diez de `architecture.md` §3.3, en su orden.

    Son los mismos que `ESTADOS_DE_TRABAJO` admite en la columna, y el test lo
    comprueba: dos listas que pueden divergir son dos verdades.
    """

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


class Senal(StrEnum):
    """Lo que hace avanzar la maquina: **un alfabeto cerrado**.

    `PASO_COMPLETADO` es «el paso termino sin incidencia». `APROBADA` y
    `DEFECTO_BLOQUEANTE` son el veredicto de las puertas de §8.3 —y por eso
    `VALIDANDO` no sale con `PASO_COMPLETADO`: de validar no se sale «porque
    termino», se sale con un veredicto—. Las cuatro restantes son, una a una,
    las causas de fallo de §3.6.

    Ninguna de ellas la escribe un modelo. Quien orqueste recibe la salida del
    agente y **elige** la senal; esa eleccion es codigo y se revisa como codigo.
    """

    PASO_COMPLETADO = "paso_completado"
    APROBADA = "aprobada"
    DEFECTO_BLOQUEANTE = "defecto_bloqueante"
    CONTEXTO_EXCEDIDO = "contexto_excedido"
    FALLO_DE_PROVEEDOR = "fallo_de_proveedor"
    TIEMPO_AGOTADO = "tiempo_agotado"
    PROCESO_INTERRUMPIDO = "proceso_interrumpido"
    """El proceso murio: no termino, no fallo el proveedor y no vencio el plazo.

    Existe porque `reanudacion.py` cerraba el trabajo muerto con
    `TIEMPO_AGOTADO` **por descarte** —era la unica averia con flecha desde
    cualquier estado vivo— y con Langfuse esa traza es lo que alguien va a abrir:
    una novela que se cayo aparecia como una que agoto su plazo. Son dos averias
    que se arreglan de forma distinta, asi que confundirlas manda a quien la lea
    a mirar donde no es.

    `CANCELACION` no valia: no tiene flecha desde `REPARANDO` ni `EXTRAYENDO`, y
    una caida no elige en que estado te pilla (P-12)."""
    CANCELACION = "cancelacion"


ESTADOS_TERMINALES: frozenset[Estado] = frozenset(
    {Estado.INTEGRADA, Estado.ESCALADA, Estado.FALLIDA, Estado.CANCELADA}
)
"""De aqui no se sale. `FALLIDA` se relanza como **trabajo nuevo** (§3.6), no
reviviendo este: un trabajo que resucita pierde la cuenta de sus reparaciones."""

DETIENEN_LA_NOVELA: frozenset[Estado] = frozenset({Estado.ESCALADA})
"""R-6. **Solo `ESCALADA`**, y el «solo» esta razonado.

`ESCALADA` espera decision humana (§3.3) y es lo que el punto de revision
nombra. `FALLIDA` no entra porque §3.6 dice que se relanza como trabajo nuevo:
es una averia tecnica con remedio automatico, no un juicio de calidad que
alguien tenga que emitir. Decidir si un `FALLIDA` sin relanzar tambien frena la
novela es de la Tarea 5, que es la que sabe cual es el capitulo siguiente.
"""


class TransicionInexistente(ErrorDeDominio):
    """Se pidio un paso que la maquina no tiene. **Es un error de dominio.**

    No un `else` que devuelve algo plausible: si el codigo pide `VALIDANDO` →
    `INTEGRADA`, lo que hay es un fallo de logica, y tragarselo produciria una
    escena en el manuscrito que el Extractor nunca vio.
    """

    def __init__(self, estado: Estado, senal: Senal, intento: int) -> None:
        self.estado = estado
        self.senal = senal
        self.intento = intento
        super().__init__(
            f"La maquina no tiene transicion desde {estado.value} con la senal "
            f"{senal.value} (intento {intento})"
        )


class SenalDesconocida(ErrorDeDominio):
    """Lo que llego no es una `Senal`. **RF-ORQ-01, y es la puerta que la sostiene.**

    Se comprueba por tipo y no por valor a proposito: `Senal` es un `StrEnum`,
    asi que la cadena `"aprobada"` casaria por igualdad con el miembro. Si la
    comparacion fuera por contenido, bastaria con que un modelo devolviera esa
    palabra para mover la maquina, y el siguiente paso lo estaria decidiendo el
    agente.
    """

    def __init__(self, recibido: object) -> None:
        self.recibido = recibido
        super().__init__(
            f"{type(recibido).__name__} no es una senal de la maquina: la salida de "
            "un agente se traduce a `Senal` en codigo, no se pasa como texto"
        )


class EstadoDesconocido(ErrorDeDominio):
    """La columna guarda algo que no es un estado de §3.3.

    Con el `CheckConstraint` puesto no deberia ocurrir nunca desde la base; si
    ocurre, es que alguien asigno una cadena a mano antes de escribir, y es
    mejor enterarse aqui que dentro de tres pasos.
    """

    def __init__(self, recibido: object) -> None:
        self.recibido = recibido
        super().__init__(f"{recibido!r} no es un estado de la maquina")


class NovelaDetenida(ErrorDeDominio):
    """R-6. Hay un capitulo escalado: **la novela se detiene y se informa.**

    No se salta al siguiente. El capitulo N+1 se construiria sobre un estado en
    T que el escalado nunca llego a producir, y lo que falta no se nota al
    escribirlo: se nota tres capitulos despues, cuando ya no se sabe de donde
    viene el agujero.
    """

    def __init__(self, obra_id: int, trabajo_id: int, causa: str | None) -> None:
        self.obra_id = obra_id
        self.trabajo_id = trabajo_id
        self.causa = causa
        detalle = f": {causa}" if causa else ""
        super().__init__(
            f"La obra {obra_id} tiene el trabajo {trabajo_id} escalado y espera "
            f"decision humana{detalle}"
        )


# `architecture.md` §3.3, flecha a flecha. **`REPARANDO` no esta aqui** porque
# su destino no es funcion del par: lo decide el contador, y eso se resuelve en
# `transitar`. Las causas de §3.6 que acaban en `FALLIDA` tampoco, por el mismo
# motivo: dependen de si el estado es terminal.
_TRANSICIONES: dict[tuple[Estado, Senal], Estado] = {
    (Estado.PLANIFICANDO, Senal.PASO_COMPLETADO): Estado.ENSAMBLANDO,
    (Estado.ENSAMBLANDO, Senal.PASO_COMPLETADO): Estado.ESCRIBIENDO,
    (Estado.ESCRIBIENDO, Senal.PASO_COMPLETADO): Estado.VALIDANDO,
    (Estado.EXTRAYENDO, Senal.PASO_COMPLETADO): Estado.INTEGRADA,
    (Estado.VALIDANDO, Senal.APROBADA): Estado.EXTRAYENDO,
    (Estado.VALIDANDO, Senal.DEFECTO_BLOQUEANTE): Estado.REPARANDO,
    # El unico sitio del que sale `ContextBudgetExceeded` (§3.6): es un fallo
    # de diseno del ensamblado, y llega **antes** de llamar al modelo.
    (Estado.ENSAMBLANDO, Senal.CONTEXTO_EXCEDIDO): Estado.FALLIDA,
    # «`CANCELADA` en el primer punto seguro» (§3.6). El documento dibuja
    # cuatro; `REPARANDO` y `EXTRAYENDO` no estan, y no se anaden por comodidad:
    # cancelar a mitad de la extraccion dejaria el grafo de canon a medias.
    (Estado.PLANIFICANDO, Senal.CANCELACION): Estado.CANCELADA,
    (Estado.ENSAMBLANDO, Senal.CANCELACION): Estado.CANCELADA,
    (Estado.ESCRIBIENDO, Senal.CANCELACION): Estado.CANCELADA,
    (Estado.VALIDANDO, Senal.CANCELACION): Estado.CANCELADA,
}

_AVERIAS: frozenset[Senal] = frozenset(
    {Senal.FALLO_DE_PROVEEDOR, Senal.TIEMPO_AGOTADO, Senal.PROCESO_INTERRUMPIDO}
)
"""Las dos causas de §3.6 que pueden aparecer en cualquier paso vivo.

El diagrama de §3.3 solo dibuja la flecha de `ContextBudgetExceeded`, pero la
tabla de §3.6 nombra tres causas que acaban en `FALLIDA` y dos de ellas no son
de ningun estado en particular: el proveedor puede caerse en cualquier llamada
y el plazo puede vencer en cualquier paso. Queda anotado en Desviaciones.
"""


def estado_de(valor: object) -> Estado:
    """Lo que guarda la columna, como estado de la maquina.

    Es la frontera entre la cadena que vive en SQLite y el tipo con el que se
    razona. Lo que no case, se lanza: `EstadoDesconocido` y no un `Estado` por
    defecto, porque un defecto aqui seria inventarse en que punto va un trabajo.
    """
    if isinstance(valor, Estado):
        return valor
    if isinstance(valor, str):
        try:
            return Estado(valor)
        except ValueError as fallo:
            raise EstadoDesconocido(valor) from fallo
    raise EstadoDesconocido(valor)


def transitar(estado: object, senal: object, *, intento: int) -> Estado:
    """El siguiente estado. **Funcion del estado, del veredicto y del contador.**

    No recibe texto, y esa ausencia es la garantia de RF-ORQ-01: no existe una
    entrada por donde la salida de un modelo pueda influir en el orden de los
    pasos. Lo que devuelve un agente lo traduce a `Senal` quien orqueste, y esa
    traduccion es una linea de codigo que se lee en una revision.

    `intento` es la cuenta de reparaciones ya gastadas, y solo pesa saliendo de
    `REPARANDO`: con reparaciones libres se vuelve a escribir; agotadas, se
    escala a revision humana (`CLAUDE.md` §9.1).
    """
    if not isinstance(estado, Estado):
        estado = estado_de(estado)
    if not isinstance(senal, Senal):
        raise SenalDesconocida(senal)

    if estado in ESTADOS_TERMINALES:
        raise TransicionInexistente(estado, senal, intento)

    if senal in _AVERIAS:
        return Estado.FALLIDA

    if estado is Estado.REPARANDO and senal is Senal.PASO_COMPLETADO:
        # `>=` y no `==`: un contador que se pasara del tope volveria a escribir
        # para siempre, y el limite de dos reparaciones dejaria de ser un limite.
        return Estado.ESCALADA if intento >= INTENTOS_MAXIMOS else Estado.ESCRIBIENDO

    destino = _TRANSICIONES.get((estado, senal))
    if destino is None:
        raise TransicionInexistente(estado, senal, intento)
    return destino


async def avanzar(
    sesion: AsyncSession, trabajo: Trabajo, senal: Senal, *, causa: str | None = None
) -> Estado:
    """Transita **y persiste**. RF-ORQ-02: el estado vive en SQLite.

    El `commit` no es ceremonia. Sin el, `GET /trabajos/{id}` no veria avanzar
    nada hasta el final y el orquestador que arranca tras una caida no sabria
    desde donde repetir (§3.7) — que es justo para lo que existe la unidad de
    trabajo.

    El contador sale de la fila y no del argumento: dos sitios del orquestador
    contando reparaciones de dos maneras es como se llega a un capitulo que
    escala en la primera vuelta.
    """
    destino = transitar(estado_de(trabajo.estado), senal, intento=trabajo.intento)
    trabajo.estado = destino.value
    if causa is not None:
        trabajo.causa_fallo = causa
    await sesion.commit()
    return destino


def detiene_la_novela(estado: Estado) -> bool:
    """R-6, en una linea: ¿este final de capitulo frena la obra entera?"""
    return estado in DETIENEN_LA_NOVELA


async def exigir_que_la_novela_siga(sesion: AsyncSession, *, obra_id: int) -> None:
    """R-6. Antes de empezar un capitulo, que no haya otro escalado.

    Se pregunta a la base y no a la memoria del proceso por lo mismo de siempre:
    el capitulo anterior pudo escalarse en otra corrida, y un freno que solo
    funciona si nadie reinicio el servidor no es un freno.

    Es **por obra** (§3.8): varias obras pueden estar en curso a la vez, y que
    una se detenga no para a las demas.
    """
    detenido = (
        await sesion.execute(
            select(Trabajo)
            .where(
                Trabajo.obra_id == obra_id,
                Trabajo.estado.in_([e.value for e in Estado if detiene_la_novela(e)]),
            )
            .order_by(Trabajo.id)
            .limit(1)
        )
    ).scalar_one_or_none()
    if detenido is not None:
        raise NovelaDetenida(obra_id, detenido.id, detenido.causa_fallo)
