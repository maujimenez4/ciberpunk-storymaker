"""Reanudacion tras la caida. **RF-ORQ-06, RF-ORQ-07, R-2 y `CA-5`.**

`architecture.md` §3.7 son dos frases, y este fichero es las dos:

> «Al arrancar, el orquestador busca trabajos en estado no terminal y los
> retoma desde su ultimo estado persistido.»

> «Un paso interrumpido se **repite entero**, nunca se reanuda a medias: es
> posible porque la salida solo se persiste al completarse y porque el `run_id`
> evita duplicados.»

Y §3.9 pone encima la propiedad que la maquina de la novela tiene que cumplir:
**la reanudacion no duplica ni pierde capitulos.** Las dos mitades se prueban
por separado y son distintas: *duplicar* es volver a escribir un capitulo que ya
estaba, *perder* es dar por hecho uno que no llego a integrarse.

## De donde se reanuda, y de donde no

No se pregunta a la memoria del proceso, que es justo lo que la caida se llevo.
Se pregunta a `trabajo`, que es lo unico que sobrevivio, y se pregunta dos
cosas: **por donde va la novela** —`checkpoint.py`, el ultimo capitulo
integrado— y **que quedo vivo** —los trabajos en estado no terminal—. Ninguna
de las dos es una tabla nueva: el avance se deriva, como el estado en T
(`CLAUDE.md` §8 regla 3), y lo vivo es una consulta por `estado`.

## Que se hace con lo que quedo vivo: se descarta y se relanza

Un trabajo en `ESCRIBIENDO` despues de una caida **no esta escribiendo nada**.
Dejarlo ahi seria una mentira legible por `GET /trabajos/{id}` (RI-06) y un
trabajo que nadie cerrara nunca. §3.6 clasifica la caida donde le corresponde
—error tecnico, no juicio de calidad— y §3.3 dice que un `FALLIDA` «se relanza
como **trabajo nuevo**», que es exactamente lo que hace `reanudar`.

**Por que trabajo nuevo y no el mismo.** El ciclo de `ciclo.py` es una sola
funcion que recorre la maquina de `PLANIFICANDO` a `INTEGRADA` llamando a
`avanzar` en cada paso. Volver a entrar con un trabajo que quedo en `VALIDANDO`
no lo retoma: lo empuja por transiciones que no son las suyas hasta que la
maquina se niega. Repetir **el capitulo entero** si es legal —§3.7 acepta pagar
otra vez la unica llamada cara, la del Escritor— y es la lectura fuerte de «se
repite entero, nunca a medias».

**La senal es `TIEMPO_AGOTADO`** porque es la de §3.6 que describe un paso que
no termino, y porque es una averia: llega a `FALLIDA` desde cualquiera de los
seis estados vivos, que es lo que R-2 exige. `CANCELACION` no serviria —el autor
no cancelo nada, y ademas no tiene flecha desde `REPARANDO` ni desde
`EXTRAYENDO`— y `CONTEXTO_EXCEDIDO` seria un diagnostico falso.

## Y por que se retira la prosa de la corrida muerta

Porque si no, la reanudacion **duplica**. La corrida que murio en `VALIDANDO` o
despues dejo confirmada una `version_texto` marcada `vigente` que nunca paso la
puerta; al reescribir el capitulo, la escena acabaria con dos versiones del
mismo capitulo y el paquete del capitulo siguiente leeria una de ellas como
continuidad local. Es la misma limpieza que `ciclo._retirar_lo_descartado` hace
con un capitulo escalado y por el mismo motivo (R-7, `CA-10`), y se apoya en lo
mismo: el disparador de inmutabilidad vigila el `UPDATE` de `version_texto`, no
su borrado.

**`ejecucion` no se toca**, y la asimetria esta razonada: es la traza de
auditoria de la regla de dominio 7, y una llamada al modelo que se pago ocurrio
aunque su corrida muriera. Lo que se borra es manuscrito candidato; lo que se
guarda es la cuenta de lo que costo.

**`evento` y `hecho_canon` tampoco**, y aqui no hace falta: el ledger es
*append-only* y, sobre todo, esas dos tablas solo se escriben en `EXTRAYENDO`,
dentro del mismo punto de guardado que la transicion a `INTEGRADA`. Un capitulo
que no llego a integrarse **no dejo nada** en ellas. Es tambien lo que desactiva
el aviso de T6 sobre `UNIQUE(capitulo_id)` en `resumen_capitulo`: la
reanudacion arranca por el primer capitulo **no integrado**, nunca por uno
hecho, asi que no hay segundo resumen que insertar.

## El contador de reparaciones no se reinicia

`checkpoint.reparaciones_del_capitulo` cuenta el maximo de `intento` entre
**todos** los trabajos del capitulo, tambien los que murieron. Asi que el
trabajo relanzado nace con lo que el capitulo ya gasto. Si naciera a cero,
matar el proceso seria la forma de conseguir dos reparaciones mas y el limite de
RF-ORQ-04 dejaria de serlo.

## Lo que este fichero **no** hace

No recorre la novela entera: reanuda **un** capitulo, el que toca, y quien
orqueste vuelve a llamar. El bucle de los diez es de `novela.py` (T9), y
meterlo aqui haria que la reanudacion decidiera tambien cuando parar, que es
otra cosa.

Y no monta el ciclo: lo recibe inyectado en `ejecutar`. Es lo que permite
probar la decision —que capitulo, con que trabajo, con cuantas reparaciones—
sin llamar al proveedor (CA-4), y es el mismo trato que el resto de la feature
da al cliente de modelo.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.domain.errores import ErrorDeDominio
from app.features.escritura.checkpoint import (
    CapituloPendiente,
    Checkpoint,
    empezar_capitulo,
    reparaciones_del_capitulo,
    siguiente_capitulo,
    ultimo_capitulo_completado,
)
from app.features.escritura.ciclo import abrir_trabajo
from app.features.escritura.maquina import (
    ESTADOS_TERMINALES,
    Estado,
    Senal,
    avanzar,
    estado_de,
)
from app.features.escritura.modelos import Trabajo

ESTADOS_VIVOS: frozenset[Estado] = frozenset(Estado) - ESTADOS_TERMINALES
"""Los seis de §3.3 de los que **se puede volver**, y por tanto los que R-2 mide.

Se deriva del conjunto de terminales en vez de escribirse a mano: dos listas
que pueden divergir son dos verdades, y la que importa es la de `maquina.py`.
Un estado nuevo entra aqui solo, y el test de R-2 exige que este probado.
"""


class TrabajoTerminal(ErrorDeDominio):
    """Se quiso descartar un trabajo que ya habia terminado.

    Se lanza en vez de no hacer nada porque el caso peligroso es `INTEGRADA`:
    descartarlo retiraria la prosa de un capitulo que forma parte del
    manuscrito, que es la mitad «sin perder ninguno» de `CA-5`. Y quien lo pide
    se ha equivocado de trabajo, asi que callarselo lo deja creyendo que limpio
    algo.
    """

    def __init__(self, trabajo_id: int, estado: Estado) -> None:
        self.trabajo_id = trabajo_id
        self.estado = estado
        super().__init__(
            f"El trabajo {trabajo_id} esta en {estado.value}, que es terminal: no hay "
            "nada que reanudar ni que descartar"
        )


@dataclass(frozen=True, slots=True)
class Reanudacion:
    """Desde donde sigue la novela, leido de la base despues de la caida.

    Es la respuesta a RF-ORQ-06 y no hace nada: se puede mirar sin escribir, que
    es lo que necesita quien solo quiere informar de por donde iba.
    """

    obra_id: int
    checkpoint: Checkpoint
    pendiente: CapituloPendiente | None
    intento: int

    @property
    def terminada(self) -> bool:
        """No queda capitulo por integrar. **No es un error haber acabado.**"""
        return self.pendiente is None


@dataclass(frozen=True, slots=True)
class Retomada:
    """Lo que la reanudacion hizo, para que quien la llame pueda contarlo.

    Lleva `descartados` porque un trabajo cerrado por la reanudacion es
    informacion de operacion —alguien se pregunto por que ese `FALLIDA`— y
    porque es lo que distingue una reanudacion de un arranque limpio.
    """

    obra_id: int
    capitulo_id: int | None
    numero: int | None
    trabajo_id: int | None
    intento: int
    descartados: tuple[int, ...]
    valor: Any = None

    @property
    def terminada(self) -> bool:
        """No habia capitulo que retomar: la novela esta escrita entera."""
        return self.capitulo_id is None


async def trabajos_en_vuelo(sesion: AsyncSession, *, obra_id: int | None = None) -> list[Trabajo]:
    """§3.7: los trabajos en estado no terminal, que es lo que la caida dejo vivo.

    `obra_id` es opcional y las dos formas son ciertas a la vez: al arrancar, el
    proceso todavia no sabe de que obras tiene que ocuparse, y a partir de ahi
    cada obra se reanuda sola (§3.8) — que una se detenga no para a las demas.

    Se ordena por `id` para que dos arranques sobre la misma base hagan lo mismo
    en el mismo orden.
    """
    consulta = select(Trabajo).where(Trabajo.estado.in_([e.value for e in ESTADOS_VIVOS]))
    if obra_id is not None:
        consulta = consulta.where(Trabajo.obra_id == obra_id)
    return list((await sesion.execute(consulta.order_by(Trabajo.id))).scalars().all())


async def planificar_reanudacion(sesion: AsyncSession, *, obra_id: int) -> Reanudacion:
    """RF-ORQ-06: por donde va la novela y cual es el capitulo que toca.

    El pendiente es **el primero no integrado**, no el siguiente al checkpoint.
    Los dos coinciden en una corrida ordenada y dejan de coincidir en cuanto hay
    un hueco: con el 2 integrado y el 1 no, el checkpoint dice «vas por el 2» y
    lo que toca es el 1. Reanudar por el 3 escribiria encima del agujero, que es
    lo que `CapituloAnteriorSinIntegrar` existe para impedir.
    """
    pendiente = await siguiente_capitulo(sesion, obra_id=obra_id)
    return Reanudacion(
        obra_id=obra_id,
        checkpoint=await ultimo_capitulo_completado(sesion, obra_id=obra_id),
        pendiente=pendiente,
        intento=(
            0
            if pendiente is None
            else await reparaciones_del_capitulo(
                sesion, obra_id=obra_id, capitulo_id=pendiente.capitulo_id
            )
        ),
    )


async def descartar(sesion: AsyncSession, trabajo: Trabajo) -> None:
    """Cierra un trabajo que la caida dejo vivo y retira lo que dejo a medias.

    Las dos cosas en este orden y en la misma transaccion: `avanzar` confirma, y
    si el borrado fuera despues, una segunda caida entre medias dejaria un
    `FALLIDA` con su prosa todavia `vigente` — que es precisamente el estado que
    esta funcion existe para que no exista.
    """
    estado = estado_de(trabajo.estado)
    if estado in ESTADOS_TERMINALES:
        raise TrabajoTerminal(trabajo.id, estado)
    await _retirar_la_prosa_de(sesion, trabajo.run_id)
    await avanzar(
        sesion, trabajo, Senal.TIEMPO_AGOTADO, causa=f"caida del proceso en {estado.value}"
    )


async def reanudar(
    sesion: AsyncSession,
    *,
    obra_id: int,
    ejecutar: Callable[[Trabajo], Awaitable[Any]],
) -> Retomada:
    """RF-ORQ-07 y `CA-5`: la novela sigue, sin duplicar ni perder ningun capitulo.

    El orden de los cuatro pasos no es indiferente, y **la puerta va antes que
    la primera escritura**:

    1. **Se mira por donde va la novela**, que no escribe nada.
    2. **Si no queda capitulo pendiente, se acabo.** Se devuelve `terminada` y
       no se lanza: haber terminado no es un fallo, y no se toca nada.
    3. **`empezar_capitulo`**, que es la unica puerta: R-6 —hay un capitulo
       escalado esperando a una persona— y las dos comprobaciones de `CA-5`
       —ni un capitulo ya integrado ni un hueco anterior—, y de paso el
       contador **del capitulo**. Va **antes** de descartar nada: reanudar una
       obra detenida tiene que informar y no hacer, o cerrar trabajos seria
       decidir por quien tiene que decidir.
    4. **Se descarta lo que quedo vivo** y se relanza, que es lo que hace que
       el ciclo encuentre la escena limpia.

    **La puerta se llama aunque el capitulo pendiente ya cumpla sus dos
    comprobaciones por construccion** —es el primero no integrado, asi que no
    esta hecho ni deja hueco detras—. Se llama igual porque es la puerta de
    `checkpoint.py` y no una copia suya: repetir aqui la decision seria tener
    dos sitios que deciden cuando se puede empezar un capitulo, y R-6 llegaria a
    depender de cual de los dos se toco por ultima vez.

    El trabajo nace con las reparaciones que el capitulo ya gasto. Es la unica
    linea que impide que matar el proceso sea una forma de conseguir reintentos.
    """
    plan = await planificar_reanudacion(sesion, obra_id=obra_id)
    if plan.pendiente is None:
        return Retomada(
            obra_id=obra_id,
            capitulo_id=None,
            numero=None,
            trabajo_id=None,
            intento=0,
            descartados=(),
        )

    arranque = await empezar_capitulo(
        sesion, obra_id=obra_id, capitulo_id=plan.pendiente.capitulo_id
    )

    descartados: list[int] = []
    for vivo in await trabajos_en_vuelo(sesion, obra_id=obra_id):
        await descartar(sesion, vivo)
        descartados.append(vivo.id)

    trabajo = await abrir_trabajo(sesion, capitulo_id=arranque.capitulo_id)
    trabajo.intento = arranque.intento
    await sesion.flush()
    trabajo_id = trabajo.id

    return Retomada(
        obra_id=obra_id,
        capitulo_id=arranque.capitulo_id,
        numero=arranque.numero,
        trabajo_id=trabajo_id,
        intento=arranque.intento,
        descartados=tuple(descartados),
        valor=await ejecutar(trabajo),
    )


async def _retirar_la_prosa_de(sesion: AsyncSession, run_id: str) -> None:
    """Borra las `version_texto` de una corrida muerta y devuelve la vigente anterior.

    Por `run_id` y no por escena: lo que se retira es lo de **esta** corrida, y
    una escena puede tener detras versiones aprobadas de otra que si termino.

    Y se vuelve a encender la superviviente de mayor numero, si la hay, por lo
    mismo que hace `ciclo._retirar_lo_descartado`: `escribir_capitulo` apaga la
    anterior al guardar la suya, y una escena sin ninguna vigente es una escena
    sin manuscrito.
    """
    escenas = (
        (
            await sesion.execute(
                text("SELECT DISTINCT escena_id FROM version_texto WHERE run_id = :run_id"),
                {"run_id": run_id},
            )
        )
        .scalars()
        .all()
    )
    if not escenas:
        return
    await sesion.execute(
        text("DELETE FROM version_texto WHERE run_id = :run_id"), {"run_id": run_id}
    )
    for escena_id in escenas:
        superviviente = (
            await sesion.execute(
                text(
                    "SELECT id FROM version_texto WHERE escena_id = :escena_id "
                    "ORDER BY numero DESC LIMIT 1"
                ),
                {"escena_id": escena_id},
            )
        ).scalar_one_or_none()
        if superviviente is not None:
            await sesion.execute(
                text("UPDATE version_texto SET vigente = 1 WHERE id = :id"), {"id": superviviente}
            )
    await sesion.flush()
