"""Recuperacion hibrida, y **el orden no es negociable** (`CLAUDE.md` §4.2).

1. **Filtro estructural** -- presentes, lugar, hilos abiertos, rango de capitulos.
2. **Orden semantico** sobre el conjunto **ya filtrado**.
3. **Fusion con recencia.**

Por que en ese orden y no al reves, que es lo que sale solo: la busqueda
puramente vectorial trae escenas **parecidas**, no escenas **pertinentes**. Una
escena de hace veinte capitulos con un beso puede parecerse muchisimo a la
actual y no tener nada que ver con ella (`architecture.md` §4.6).

**Esto es `CA-8`, y tiene historia.** La version anterior de la spec no tuvo ese
criterio, y por eso el filtro estructural quedo sin implementar detras de un
requisito que decia estar probado. Un criterio que solo comprueba el tope se
cumple sin filtrar. El test que guarda esto -- R-5 -- corre sobre un corpus donde
lo parecido y lo pertinente **difieren** a proposito, y su pareja
(`test_ordenar_sin_filtrar_traeria_lo_parecido`) comprueba que el corpus siga
discriminando.

**El vector de consulta llega de fuera.** Lo calcula el mismo proveedor que
genera (spec, `CLAUDE.md` §4.2), y esta feature no le llama: quien ensambla
trae el vector, y aqui se ordena con el. Es lo que mantiene el filtro y la
fusion probables sin red (RNF-FIA-01, CA-4) -- y lo que deja la varianza del
proveedor en un solo sitio, declarado (ver `almacenes.py`).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.contexto.almacenes import Vecino, VectorStore

LIMITE_POR_DEFECTO = 8
PESO_RECENCIA_POR_DEFECTO = 0.3
"""Cuanto pesa «hace poco» frente a «se parece», entre 0 y 1.

No se deriva de nada: es una decision, y por eso es un parametro con test en
los dos extremos en vez de una constante escondida en una formula.
"""


@dataclass(frozen=True, slots=True)
class FiltroEstructural:
    """Lo que hace **pertinente** a una escena para la que se esta escribiendo.

    Los cuatro campos son los de `architecture.md` §4.6, y funcionan asi: el
    rango de capitulos **acota** -- es una condicion necesaria --, y lugar,
    presentes e hilos abiertos **admiten**: basta con uno.

    Que sean tres puertas de entrada y no tres condiciones a la vez importa:
    exigirlas todas dejaria fuera la escena que abre el hilo que hay que pagar
    solo por transcurrir en otro sitio, que es justo la que hace falta.
    """

    obra_id: int
    presentes: tuple[str, ...]
    lugar: str | None
    hilos_abiertos: tuple[int, ...]
    desde_capitulo: int
    hasta_capitulo: int


@dataclass(frozen=True, slots=True)
class Candidato:
    """Una escena que paso el filtro, con lo unico que la fusion necesita de ella."""

    escena_id: int
    orden_discurso: int


@dataclass(frozen=True, slots=True)
class Recuperado:
    """Un fragmento que entra en la capa de memoria recuperada, con sus tres cifras.

    `distancia`, `afinidad` y `recencia` viajan junto a la `puntuacion` a
    proposito: una lista ordenada por un numero que no se ve no se puede
    auditar, y `ejecucion` guarda los IDs recuperados para poder rehacer el
    razonamiento (RF-CTX-09).
    """

    escena_id: int
    embedding_id: int
    fragmento: str
    distancia: float
    afinidad: float
    recencia: float
    puntuacion: float


# `escena` no tiene `obra_id`: cuelga de `capitulo`, y de ahi el JOIN -- que
# ademas es el que da el `numero` con el que se acota el rango.
#
# Va en SQL y no por el ORM porque **las tablas no cruzan la frontera entre
# features** (`CLAUDE.md` §5.1): `escena` es de su feature y `hilo_narrativo` de
# `canon`, y las claves ajenas de este proyecto ya se declaran por nombre de
# tabla por el mismo motivo. `embedding` si se importa, por la puerta de
# `canon`, porque el almacen necesita la columna tipada (ver Desviaciones).
_SQL_FILTRO = text(
    """
    SELECT e.id AS escena_id, e.orden_discurso AS orden_discurso
    FROM escena AS e
    JOIN capitulo AS c ON c.id = e.capitulo_id
    WHERE c.obra_id = :obra_id
      AND c.numero BETWEEN :desde_capitulo AND :hasta_capitulo
      AND (
            (:lugar IS NOT NULL AND e.lugar = :lugar)
         OR EXISTS (
                SELECT 1 FROM json_each(e.presentes) AS p
                WHERE p.value IN :presentes
            )
         OR EXISTS (
                SELECT 1 FROM hilo_narrativo AS h
                WHERE h.id IN :hilos_abiertos
                  AND h.estado = 'abierto'
                  AND h.escena_de_apertura = e.id
            )
      )
    ORDER BY e.orden_discurso
    """
).bindparams(
    bindparam("presentes", expanding=True),
    bindparam("hilos_abiertos", expanding=True),
)


async def filtrar_estructuralmente(
    sesion: AsyncSession, filtro: FiltroEstructural
) -> list[Candidato]:
    """Paso 1. Las escenas **pertinentes**, sin mirar ni un vector.

    `h.estado = 'abierto'` no sobra aunque el filtro traiga los ids: un hilo ya
    pagado no vuelve a traer su escena, o el filtro creceria con la obra en vez
    de acotarla.
    """
    filas = await sesion.execute(
        _SQL_FILTRO,
        {
            "obra_id": filtro.obra_id,
            "desde_capitulo": filtro.desde_capitulo,
            "hasta_capitulo": filtro.hasta_capitulo,
            "lugar": filtro.lugar,
            "presentes": list(filtro.presentes),
            "hilos_abiertos": list(filtro.hilos_abiertos),
        },
    )
    return [
        Candidato(escena_id=fila.escena_id, orden_discurso=fila.orden_discurso) for fila in filas
    ]


def fusionar_con_recencia(
    vecinos: Sequence[Vecino],
    ordenes: Mapping[int, int],
    *,
    orden_actual: int,
    peso_recencia: float,
) -> list[Recuperado]:
    """Paso 3. Mezcla parecido y cercania en el tiempo del discurso.

    `recencia = 1 / (1 + escenas de distancia)`: cae rapido al principio y se
    aplana despues, que es como envejece de verdad la continuidad local. Se
    calcula **por escena** y no normalizando sobre el conjunto para que el
    resultado no dependa de que mas entro en la lista.

    `afinidad` se acota a [0, 1]: el coseno llega a 2 para vectores opuestos, y
    una afinidad negativa haria que un fragmento restara.
    """
    if not 0.0 <= peso_recencia <= 1.0:
        raise ValueError(f"El peso de la recencia va de 0 a 1, y llego {peso_recencia}")

    recuperados: list[Recuperado] = []
    for vecino in vecinos:
        afinidad = min(1.0, max(0.0, 1.0 - vecino.distancia))
        recencia = 1.0 / (1.0 + max(0, orden_actual - ordenes[vecino.escena_id]))
        recuperados.append(
            Recuperado(
                escena_id=vecino.escena_id,
                embedding_id=vecino.embedding_id,
                fragmento=vecino.fragmento,
                distancia=vecino.distancia,
                afinidad=afinidad,
                recencia=recencia,
                puntuacion=(1.0 - peso_recencia) * afinidad + peso_recencia * recencia,
            )
        )

    recuperados.sort(key=lambda r: (-r.puntuacion, r.distancia, r.embedding_id))
    return recuperados


async def recuperar(
    sesion: AsyncSession,
    *,
    filtro: FiltroEstructural,
    consulta: Sequence[float],
    almacen: VectorStore,
    orden_actual: int,
    limite: int = LIMITE_POR_DEFECTO,
    peso_recencia: float = PESO_RECENCIA_POR_DEFECTO,
) -> list[Recuperado]:
    """Los tres pasos, en su orden, y el recorte **al final**.

    El `limite` se aplica sobre la **puntuacion** y no sobre la distancia: pedir
    al almacen solo `limite` vecinos tiraria por distancia lo que la recencia
    iba a rescatar, y la fusion quedaria de adorno. Por eso al almacen se le
    piden todos los candidatos.

    Si el filtro no deja nada, **no se pregunta al almacen**: una capa vacia es
    un resultado, no una consulta a ciegas. Quien ensambla distingue esa capa
    vacia de una que nunca se surtio (RF-CTX-06, R-3), y esa distincion es suya.
    """
    if not 0.0 <= peso_recencia <= 1.0:
        raise ValueError(f"El peso de la recencia va de 0 a 1, y llego {peso_recencia}")

    candidatos = await filtrar_estructuralmente(sesion, filtro)
    if not candidatos:
        return []

    ordenes = {candidato.escena_id: candidato.orden_discurso for candidato in candidatos}
    vecinos = await almacen.vecinos(consulta, list(ordenes), limite=max(limite, len(ordenes)))

    fusionados = fusionar_con_recencia(
        vecinos, ordenes, orden_actual=orden_actual, peso_recencia=peso_recencia
    )
    return fusionados[:limite]
