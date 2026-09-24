"""La puerta G1a, mecanica (`architecture.md` §8.3).

**Esta feature existe aunque el juez no**, y ese es medio sentido de la tarea.
Sin una puerta que rechace de verdad, **R-7 no se puede probar**: «un capitulo
rechazado no deja rastro en canon, ledger ni indice» necesita algo que rechace;
si nada rechaza nunca, el test pasa sin comprobar nada. Es el modo de fallo que
este proyecto ha encontrado cuatro veces —una restriccion sobre la que ningun
test podia caer— y aqui se evita antes.

**El orden importa y no es intercambiable:** primero se comprueba la forma de
todos los defectos, y solo despues se decide si la puerta bloquea. Un defecto
mal formado no bloquea, **no gasta reintento** y **se cuenta aparte** (CA-17,
RF-VAL-07). Si la forma se comprobara despues del bloqueo, una cita inventada
detendria un capitulo correcto y se llevaria uno de los dos reintentos que
`CLAUDE.md` §9.1 concede.

**Lo que esta puerta NO hace:** no repara, no reintenta y no persiste. Devuelve
un resultado. Quien cuenta los reintentos y quien escribe —o no escribe— en el
ledger es el orquestador (T11), y que sean dos cosas separadas es lo que permite
probar el rechazo sin un ciclo entero alrededor.
"""

from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass

from app.features.calidad.defectos import DefectoMalFormado, clasificar
from app.features.calidad.schemas import Defecto
from app.features.calidad.validadores import CATALOGO, CapituloAValidar, Validador


@dataclass(frozen=True, slots=True)
class ResultadoDePuerta:
    """Lo que la puerta devuelve, con los mal formados **dentro** y no perdidos.

    `validadores_ejecutados` no es adorno: RF-VAL-01 pide que cada validador
    tenga nombre y punto declarado, y un resultado que no dice cuales corrieron
    no permite distinguir «ninguno encontro nada» de «ninguno corrio».
    """

    aprobado: bool
    bloqueantes: tuple[Defecto, ...]
    mal_formados: tuple[DefectoMalFormado, ...]
    validadores_ejecutados: tuple[str, ...]
    validadores_rotos: tuple[str, ...] = ()
    """Los que lanzaron en vez de devolver. **Se cuentan aparte**, igual que un
    defecto mal formado: lo que falla de forma distinta no se mezcla en el mismo
    monton. Un validador que revienta es un fallo del *harness*, y tratarlo como
    «no encontro nada» es la forma mas cara de tener un capitulo verde."""
    defectos_por_validador: tuple[tuple[str, int], ...] = ()
    """Cuantos hallo cada uno. Sin esto, todas las puntuaciones de un capitulo
    valdrian lo mismo y la tabla de los cinco briefs no podria decir **cual**
    fallo, que es literalmente para lo que existe."""

    @property
    def gasta_reintento(self) -> bool:
        """Solo un defecto **bien formado** consume uno de los dos intentos.

        Es la mitad de CA-17 que no se ve en `aprobado`: un capitulo con cinco
        citas inventadas y ningun defecto real sale aprobado **y con los dos
        reintentos intactos**.
        """
        return bool(self.bloqueantes)


def cruzar_g1a(
    capitulo: CapituloAValidar,
    hechos_de_canon: Collection[str],
    defectos_recibidos: Iterable[Defecto] = (),
    catalogo: Sequence[Validador] = CATALOGO,
) -> ResultadoDePuerta:
    """Corre el catalogo, comprueba la forma de todo, y decide.

    `defectos_recibidos` es la via por la que entran los defectos que **no**
    produce esta feature: hoy ninguna, porque el Continuista es de la Fase 3.
    Existe desde ahora porque la comprobacion de forma se escribio para **ellos**
    —los mecanicos citan del texto y no pueden equivocarse de cita—, y sin el
    parametro RF-VAL-07 quedaria implementado sobre el unico caso que no lo
    necesita.
    """
    hallados: list[Defecto] = []
    ejecutados: list[str] = []
    rotos: list[str] = []
    por_validador: list[tuple[str, int]] = []

    for validador in catalogo:
        try:
            suyos = list(validador.comprobar(capitulo))
        except Exception:  # noqa: BLE001 - cualquier fallo del validador, no del capitulo
            rotos.append(validador.nombre)
            continue
        ejecutados.append(validador.nombre)
        por_validador.append((validador.nombre, len(suyos)))
        hallados.extend(suyos)

    clasificados = clasificar([*hallados, *defectos_recibidos], capitulo.texto, hechos_de_canon)
    return ResultadoDePuerta(
        aprobado=not clasificados.bien_formados and not rotos,
        bloqueantes=clasificados.bien_formados,
        mal_formados=clasificados.mal_formados,
        validadores_ejecutados=tuple(ejecutados),
        validadores_rotos=tuple(rotos),
        defectos_por_validador=tuple(por_validador),
    )
