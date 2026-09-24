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

from collections.abc import Collection, Iterable
from dataclasses import dataclass

from app.features.calidad.defectos import DefectoMalFormado, clasificar
from app.features.calidad.schemas import Defecto
from app.features.calidad.validadores import CATALOGO, CapituloAValidar, nombres_del_catalogo


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
) -> ResultadoDePuerta:
    """Corre el catalogo, comprueba la forma de todo, y decide.

    `defectos_recibidos` es la via por la que entran los defectos que **no**
    produce esta feature: hoy ninguna, porque el Continuista es de la Fase 3.
    Existe desde ahora porque la comprobacion de forma se escribio para **ellos**
    —los mecanicos citan del texto y no pueden equivocarse de cita—, y sin el
    parametro RF-VAL-07 quedaria implementado sobre el unico caso que no lo
    necesita.
    """
    hallados = [defecto for validador in CATALOGO for defecto in validador.comprobar(capitulo)]
    clasificados = clasificar([*hallados, *defectos_recibidos], capitulo.texto, hechos_de_canon)
    return ResultadoDePuerta(
        aprobado=not clasificados.bien_formados,
        bloqueantes=clasificados.bien_formados,
        mal_formados=clasificados.mal_formados,
        validadores_ejecutados=nombres_del_catalogo(),
    )
