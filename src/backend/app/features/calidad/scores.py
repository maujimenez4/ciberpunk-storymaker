"""De un resultado de puerta a *scores* (RF-VAL-01, RF-OBS-04, media `CA-18`).

**Los validadores siguen sin saber que existe Langfuse, y es una decision, no un
descuido.** `cruzar_g1a` y `cerrar_manuscrito` son funciones puras que se prueban
sin base de datos y sin red; meterles telemetria dentro tiraria esa propiedad por
una comodidad. Lo que hace este modulo es **traducir un resultado en
puntuaciones**. Quien las emite es quien tiene el span —el orquestador— y esa
juntura es de T6.

**La traduccion no se inventa el censo.** Recorre `validadores_ejecutados`, que
nacio con este proposito exacto: un resultado que no dice cuales corrieron no
permite distinguir «ninguno encontro nada» de «ninguno corrio». Un validador
**roto** no aparece aqui: no produjo un cero, es que no llego a producir nada, y
un cero suyo seria un numero inventado.

**Los nombres son los de `verification.md` §8.1, sin traducir.** Son la llave por
la que un *score* se cruza con la tabla de validadores; renombrar uno aqui romperia
ese cruce sin que fallara nada, y por eso hay un test que ata los dos catalogos a
esa lista.

**`spec_tla` no aparece en ninguna funcion de este modulo.** Es la unica excepcion
del encargo §6 —TLC corre en desarrollo, no en cada generacion— y se comprueba por
ausencia, que es como se comprueba que algo no ocurre.
"""

from collections.abc import Iterable
from typing import Protocol

from app.commons.observabilidad import Puntuacion, Span
from app.features.calidad.puerta import ResultadoDePuerta
from app.features.calidad.validadores import CierreDelManuscrito

PASA = 1.0
FALLA = 0.0
"""La escala de un validador mecanico: paso o no paso.

No es una nota de calidad y no debe leerse como tal. Lo que la tabla de los cinco
briefs necesita saber es, validador a validador, si encontro algo; un numero
intermedio invitaria a interpretarlo, y no hay nada que interpretar en «encontro
tres defectos» frente a «encontro uno»: los dos son el mismo suceso.
"""

NOMBRE_DEL_JUEZ = "juez_con_rubrica"
"""El nombre de `verification.md` §8.1. El criterio concreto va en `criterio`."""


class _PuntuacionDelCritico(Protocol):
    criterio: str
    valor: int
    justificacion: str


class _Juicio(Protocol):
    puntuaciones: Iterable[_PuntuacionDelCritico]


def puntuaciones_de_g1a(resultado: ResultadoDePuerta) -> tuple[Puntuacion, ...]:
    """Una puntuacion por validador **ejecutado**. Ni cero ni dos.

    Cero seria telemetria muda; dos, el mismo validador contado dos veces en la
    tabla de los cinco briefs. El valor sale de `defectos_por_validador`, que es
    lo unico que distingue cual de los tres fallo: sin ello, un capitulo con un
    defecto y otro limpio producirian el mismo panel.
    """
    hallazgos = dict(resultado.defectos_por_validador)
    return tuple(
        Puntuacion(nombre=nombre, valor=FALLA if hallazgos.get(nombre, 0) else PASA)
        for nombre in resultado.validadores_ejecutados
    )


def puntuaciones_de_g4(cierre: CierreDelManuscrito) -> tuple[Puntuacion, ...]:
    """Lo mismo para la puerta del manuscrito entero.

    Aqui el hallazgo es una **ausencia** —un elemento obligatorio que no llego a
    ningun capitulo— y no un defecto con cita. Cambia lo que se mira, no la
    escala: paso o no paso.
    """
    fallo = FALLA if cierre.cobertura.ausentes else PASA
    return tuple(Puntuacion(nombre=nombre, valor=fallo) for nombre in cierre.validadores_ejecutados)


def puntuaciones_del_juez(juicio: _Juicio) -> tuple[Puntuacion, ...]:
    """Una puntuacion **por criterio**, con su justificacion.

    Es el unico validador cuyo *score* lleva texto, y no es adorno: un numero del
    juez sin justificacion no se puede comparar con el del Autor, y comparar los
    dos es lo unico para lo que el juez existe (`RF-JUZ-05`). Que la
    justificacion sea obligatoria lo impone el esquema del Critico; aqui solo se
    traslada.

    El `nombre` es uno solo —`juez_con_rubrica`— porque el validador es uno; lo
    que cambia entre puntuaciones es el `criterio`.
    """
    return tuple(
        Puntuacion(
            nombre=NOMBRE_DEL_JUEZ,
            valor=float(p.valor),
            justificacion=p.justificacion,
            criterio=p.criterio,
        )
        for p in juicio.puntuaciones
    )


def emitir(span: Span, puntuaciones: Iterable[Puntuacion]) -> None:
    """Manda las puntuaciones al span **sin poder romper la generacion**.

    Regla 11 de la fase, y esta funcion es donde se cumple o no: corre dentro de
    un camino de produccion. Una telemetria que tumba la novela que mide es peor
    que no tenerla.

    Se protege **cada puntuacion por separado** y no el bucle entero, a
    proposito: rendirse a la primera perderia las nueve restantes y produciria el
    panel vacio que R-1 describe, que es el mismo fallo visto desde el otro lado.

    Lo que **no** hace es contar los fallos. Esa cuenta existe y vive donde tiene
    que vivir —el contador de fallos del observador, de T1—, y duplicarla aqui
    daria dos numeros para lo mismo.
    """
    for puntuacion in puntuaciones:
        try:
            span.puntuar(puntuacion)
        # `S112` pide registrar la excepcion, y aqui no se registra a proposito:
        # el contador de fallos del observador es de T1 y esta es la unica via
        # por la que un fallo de telemetria puede llegar. Contarlo tambien aqui
        # daria dos numeros para lo mismo, y escribirlo en un log incumpliria
        # `CLAUDE.md` §15 el dia que la puntuacion lleve justificacion del juez,
        # que es prosa del manuscrito.
        except Exception:  # noqa: S112, BLE001
            continue
