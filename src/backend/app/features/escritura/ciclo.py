"""El ciclo de un capitulo, de punta a punta. **No anade comportamiento: conecta.**

Cada pieza que este fichero llama ya estaba escrita y probada por su tarea. Lo
que no existia era el sitio donde se tocan, y por eso la fase dejo **siete
junturas sin dueno**: cosas que ninguna tarea hacia mal por separado y que
nadie hacia bien en conjunto. Cinco se cierran aqui:

| Juntura | Donde |
| --- | --- |
| El `PresupuestoConcurrente` es **uno por proceso** y llega inyectado | `router.py` lo compone; aqui solo se usa |
| Los tokens del portero son **los que conto el Ensamblador** | `_escribir`, con `paquete.tokens_previstos` |
| El prompt del reintento **se vuelve a presupuestar** | `service.escribir_capitulo`, con el contador |
| `sqlite-vec` se detecta **al levantar** | el *lifespan* de `main.py` |
| Un capitulo rechazado **no deja rastro, ni en el manuscrito** | `_retirar_lo_descartado` |

La sexta y la septima van juntas y son la misma frase de R-7 leida entera: hasta
ahora `canon` obedecia un veredicto que el test le daba hecho —T9 recibia los
codigos, T12 los producia, nadie unia las dos cosas— y ademas nadie retiraba la
`version_texto` descartada, que es la parte de «no deja rastro» que toca al
manuscrito. Aqui el veredicto sale de la puerta de verdad y la prosa que nunca
entro se borra.

La juntura 4 —el metodo de vectorizar de `ClienteModelo`— **no se cierra**, y va
dicho en Desviaciones: el protocolo es de T1, `DobleDeterminista` lo hereda por
subclase explicita y anadirle un miembro sin implementar romperia la suite
entera. Lo que si esta es el punto de conexion: `vectorizar` llega por parametro
y baja hasta el Extractor sin que nadie mas tenga que cambiar.

**Los estados ya no se escriben aqui: los decide `maquina.py`** (T2 de la Fase
3). Este fichero dice **que paso** —«el ensamblado no cabe», «la puerta
rechazo», «el Extractor termino»— y la maquina responde con el estado o se
niega. Es lo que hace que `VALIDANDO` no pueda llegar a `ESCALADA` sin pasar
por `REPARANDO`, que es exactamente el atajo que este fichero tomaba antes.

Lo que sigue siendo de otra tarea: el checkpoint por capitulo (T5) y la
reanudacion (T8). Aqui se escribe **un** capitulo.

**Las tablas de otras features se leen por SQL con su nombre** —`capitulo` y
`version_obra` son de `outline`, `obra` y `hecho_canon` de `obra`, `escena` de
`escena`—: una feature no entra a los ficheros internos de otra (`CLAUDE.md`
§5.1). Es el mismo trato que `contexto/service.py` da a las suyas.
"""

import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.domain.errores import ContextBudgetExceeded, ErrorDeDominio, RecursoDesconocido
from app.commons.jobs.turnos import CerrojoDeEscena, PresupuestoConcurrente
from app.commons.llm.contador import ContadorDeTokens
from app.features.calidad import (
    ConocimientoEnT,
    Continuista,
    NombreDeCanon,
    RangoDeExtension,
)
from app.features.canon import (
    Consolidacion,
    Extractor,
    Vector,
    consolidar_escena,
    leer_hechos_del_canon,
    leer_nombres_del_canon,
    registrar_uso_de_hechos,
)
from app.features.contexto import (
    Capa,
    CapaVacia,
    CapituloDesconocido,
    ContextoDelCapitulo,
    VectorStore,
    ensamblar_capitulo,
)
from app.features.escena import Planificador, RestriccionesDeDiscurso, planificar_escena
from app.features.escritura.agents import Escritor
from app.features.escritura.maquina import Estado, Senal, avanzar
from app.features.escritura.modelos import Trabajo
from app.features.escritura.service import Escritura, escribir_capitulo

TIPO_DE_TRABAJO = "escribir_escena"
"""El unico de `architecture.md` §3.2 que esta fase produce."""

RANGO_DE_CAPITULO = RangoDeExtension(minimo=1000, maximo=1500)
"""`definitions.md` §4.1: un capitulo mide de 1.000 a 1.500 palabras.

Es el mismo rango que `outline/modelos.py` sostiene con un `CheckConstraint`, y
se duplica en vez de importarse porque esa constante no sale por el
`__init__.py` de `outline` y una feature no entra a los ficheros internos de
otra. `CLAUDE.md` §5.1, regla 4: se duplica primero.
"""


class TrabajoDesconocido(RecursoDesconocido):
    """El id que se consulta no es de ningun trabajo (RI-06)."""

    def __init__(self, trabajo_id: int) -> None:
        self.trabajo_id = trabajo_id
        super().__init__(f"No existe el trabajo {trabajo_id}")


class ObraSinBiblia(ErrorDeDominio):
    """No hay outline: no se puede planificar una escena de la nada.

    Es conflicto de estado y no recurso ausente —la obra existe—, asi que sale
    con 409, que es lo que el manejador central hace por defecto.
    """

    def __init__(self, obra_id: int) -> None:
        self.obra_id = obra_id
        super().__init__(f"La obra {obra_id} no tiene biblia: hay que planificar el outline antes")


@dataclass(frozen=True, slots=True)
class Agentes:
    """Los tres roles que el ciclo orquesta, ya compuestos con su cliente.

    Llegan hechos y no se construyen aqui: es lo que permite que un test
    sustituya el cliente de modelo sin tocar el codigo de produccion (CA-4), y
    es el mismo trato que `obra/router.py` le da al Entrevistador.

    El Ensamblador no esta porque **no es un agente**: es codigo (`CLAUDE.md`
    §9.1), y por eso se llama como una funcion y no se inyecta como un rol.
    """

    planificador: Planificador
    escritor: Escritor
    extractor: Extractor
    continuista: Continuista | None = None
    """P-17. Estaba construido, probado y exportado, y **no lo llamaba nadie**:
    se escribia la novela entera sin una sola comprobacion de continuidad.

    Opcional **mientras la ola 2 no cierre**, no por comodidad: el Critico entra
    con T4 y todavia no existe, y exigir los dos aqui habria dejado el
    Continuista fuera del ciclo hasta que se escribiera un rol distinto. Con la
    corrida real en marcha, eso era otra novela sin continuidad.

    Cuando el Critico entre, los dos dejan de tener valor por defecto: un rol
    opcional en produccion es la forma de volver a tener P-17 sin que se note.
    """


def conocimiento_desde_filas(
    filas: Iterable[tuple[str, str, str, int | None]],
) -> tuple[ConocimientoEnT, ...]:
    """La proyeccion de `estado_en_t` que el Continuista contrasta (T8).

    Se lee de la **vista**, no de las tablas de `features/canon`: una vista es
    del esquema y no un import, asi que la frontera de `CLAUDE.md` §5.1 sigue
    entera. Es la misma via por la que `cobertura` mira los hechos.

    **`sabe_desde` nulo no es cero, y aqui es donde se pierde.** Un evento sin
    escena no esta situado en el discurso; rellenarlo con 0 «para que no moleste»
    convertiria **todo** evento sin escena en anterior a cualquier capitulo, y el
    contraste de la regla de dominio 2 diria que si a cualquier cosa. La vista lo
    deja nulo con un `LEFT JOIN` y esta funcion lo conserva: sin `or 0`, sin
    `coalesce`, sin valor por defecto. Lo aviso la sesion **Vane** al entregar
    T8, y esta funcion existe para que ese aviso tenga donde caerse.
    """
    return tuple(
        ConocimientoEnT(
            personaje=personaje,
            evento_id=evento_id,
            tiempo_historia=tiempo_historia,
            sabe_desde=sabe_desde,
        )
        for personaje, evento_id, tiempo_historia, sabe_desde in filas
    )


@dataclass(frozen=True, slots=True)
class ResultadoDelCiclo:
    """Lo que el ciclo devuelve. **Se informa, no se lanza.**

    Un capitulo que se escala o que no cabe en el presupuesto no es una averia
    del proceso: es un final previsto, y quien orqueste tiene que poder
    contarselo a una persona. Lo que si se propaga es lo que no es de dominio.
    """

    trabajo_id: int
    estado: str
    run_id: str
    escritura: Escritura | None = None
    consolidacion: Consolidacion | None = None
    causa_fallo: str | None = None


async def abrir_trabajo(sesion: AsyncSession, *, capitulo_id: int) -> Trabajo:
    """La unidad de trabajo de `architecture.md` §3.2, en `PLANIFICANDO`.

    Nace **antes** de que empiece nada, y ese es el punto: el endpoint responde
    con su id y quien pregunte por `GET /trabajos/{id}` ve el estado aunque el
    proceso se caiga a mitad. Un trabajo creado al final solo sabria contar lo
    que ya termino.

    El `run_id` se deriva del capitulo y del identificador del propio trabajo:
    es la clave de idempotencia (§3.2) y lo que ata cada `version_texto` y cada
    fila de `ejecucion` a esta corrida y no a otra.
    """
    capitulo = await _capitulo(sesion, capitulo_id)
    trabajo = Trabajo(
        obra_id=int(capitulo["obra_id"]),
        # `capitulo_id` lo anadio T1 justo para esto y nadie lo rellenaba: sin
        # el, el checkpoint de T5 no sabe de que capitulo es cada trabajo y la
        # reanudacion de T8 no tiene de donde leer por donde iba la novela.
        capitulo_id=capitulo_id,
        escena_id=None,
        tipo=TIPO_DE_TRABAJO,
        estado=Estado.PLANIFICANDO.value,
        intento=0,
        run_id="pendiente",
    )
    sesion.add(trabajo)
    await sesion.flush()
    trabajo.run_id = f"cap{capitulo_id}-trb{trabajo.id}"
    await sesion.flush()
    return trabajo


async def leer_trabajo(sesion: AsyncSession, trabajo_id: int) -> Trabajo:
    """RI-06. Lo que no existe responde 404, no 409 (manejador de `commons/`)."""
    trabajo = await sesion.get(Trabajo, trabajo_id)
    if trabajo is None:
        raise TrabajoDesconocido(trabajo_id)
    return trabajo


async def ejecutar_ciclo(
    sesion: AsyncSession,
    trabajo: Trabajo,
    *,
    capitulo_id: int,
    agentes: Agentes,
    contador: ContadorDeTokens,
    presupuesto: PresupuestoConcurrente,
    cerrojo: CerrojoDeEscena,
    almacen: VectorStore | None = None,
    consulta: Sequence[float] | None = None,
    vectorizar: Callable[[str], Vector] | None = None,
    modelo: str = "desconocido",
    semilla: int = 0,
    rango_de_extension: RangoDeExtension = RANGO_DE_CAPITULO,
) -> ResultadoDelCiclo:
    """Planifica, ensambla, escribe, valida y consolida. En ese orden.

    **El cerrojo envuelve el ciclo entero y no solo la llamada** (RF-ORQ-08):
    la escena N+1 necesita el estado en T posterior a N, asi que dos escenas de
    la misma obra a la vez no son arriesgadas, son incorrectas. Obras distintas
    se solapan sin mas.

    **El turno del presupuesto concurrente envuelve solo la escritura**, que es
    donde se llama al modelo, y se pide con los tokens que conto el Ensamblador.
    Pedirlo antes de ensamblar seria pedirlo sin saber cuantos, que es la forma
    elegante de pedir cero.
    """
    async with cerrojo.por_obra(trabajo.obra_id):
        try:
            contexto = await _planificar_y_ensamblar(
                sesion,
                trabajo,
                capitulo_id,
                agentes.planificador,
                contador,
                almacen=almacen,
                consulta=consulta,
            )
        except (ContextBudgetExceeded, CapaVacia) as fallo:
            # Las dos viajan con la **misma** senal, y es la fila de §3.6 que
            # dice «fallo de diseno del ensamblado, no de ejecucion»: el
            # paquete no se pudo construir y no se llega a llamar al modelo.
            # Que una sea el presupuesto y la otra una capa obligatoria vacia
            # cambia el diagnostico, no el destino, y el diagnostico se guarda
            # en `causa_fallo`.
            return await _terminar(sesion, trabajo, Senal.CONTEXTO_EXCEDIDO, causa=str(fallo))

        escritura = await _escribir(
            sesion,
            trabajo,
            agentes,
            contexto=contexto,
            contador=contador,
            presupuesto=presupuesto,
            modelo=modelo,
            semilla=semilla,
            rango_de_extension=rango_de_extension,
        )

        # La puerta mecanica de T12 ya corrio dentro de `escribir_capitulo`, y
        # sus codigos son los que deciden si se escribe memoria de largo plazo.
        # **Ese es el hilo que faltaba:** T9 recibia los codigos como dato de
        # entrada y T12 los producia, y nadie los unia.
        bloqueantes = _codigos_bloqueantes(escritura)
        if not escritura.aprobado:
            await _retirar_lo_descartado(sesion, contexto.escena_id, trabajo.run_id)
            # **Se pasa por `REPARANDO`, que no es ceremonia.** `architecture.md`
            # §3.3 no dibuja ninguna flecha de `VALIDANDO` a `ESCALADA`: el
            # escalado es la salida de `REPARANDO` cuando el contador se agota,
            # y hacerlo asi es lo que hace que sea el contador —y no este
            # `if`— quien decide que la escena va a una persona.
            await avanzar(sesion, trabajo, Senal.DEFECTO_BLOQUEANTE)
            return await _terminar(
                sesion,
                trabajo,
                Senal.PASO_COMPLETADO,
                causa=escritura.motivo_de_escalado,
                escritura=escritura,
            )

        await avanzar(sesion, trabajo, Senal.APROBADA)
        extraccion = await agentes.extractor.extraer(escritura.texto)
        consolidacion = await consolidar_escena(
            sesion,
            obra_id=trabajo.obra_id,
            escena_id=contexto.escena_id,
            capitulo_id=contexto.capitulo_id,
            extraccion=extraccion,
            prosa=escritura.texto,
            version_texto_id=escritura.version_texto_id,
            vectorizar=vectorizar,
            defectos_bloqueantes=bloqueantes,
        )
        await _registrar_uso(sesion, contexto)

        resultado = await _terminar(sesion, trabajo, Senal.PASO_COMPLETADO, escritura=escritura)
        return ResultadoDelCiclo(
            trabajo_id=resultado.trabajo_id,
            estado=resultado.estado,
            run_id=resultado.run_id,
            escritura=escritura,
            consolidacion=consolidacion,
        )


# ---------------------------------------------------------------------------
# Los pasos, uno a uno
# ---------------------------------------------------------------------------


async def _planificar_y_ensamblar(
    sesion: AsyncSession,
    trabajo: Trabajo,
    capitulo_id: int,
    planificador: Planificador,
    contador: ContadorDeTokens,
    *,
    almacen: VectorStore | None,
    consulta: Sequence[float] | None,
) -> ContextoDelCapitulo:
    """`PLANIFICANDO` y `ENSAMBLANDO`, que son dos estados y no uno.

    Se planifica **solo si no hay ficha**: replanificar una escena ya escrita
    cambiaria la entrada del Escritor sin que nadie lo pidiera, y `Escena` tiene
    una sola fila por capitulo (P-C).
    """
    capitulo = await _capitulo(sesion, capitulo_id)
    if await _ficha_del_capitulo(sesion, capitulo_id) is None:
        await _planificar(sesion, planificador, capitulo)

    await avanzar(sesion, trabajo, Senal.PASO_COMPLETADO)
    contexto = await ensamblar_capitulo(
        sesion, capitulo_id, contador, consulta=consulta, almacen=almacen
    )
    trabajo.escena_id = contexto.escena_id
    await sesion.flush()
    return contexto


async def _planificar(
    sesion: AsyncSession, planificador: Planificador, capitulo: Mapping[str, Any]
) -> None:
    """La ficha de escena, con las restricciones que la obra declara.

    `persona` y `tiempo_verbal` viven en la biblia vigente y `nivel_de_calor` en
    la obra, que es exactamente lo que `RestriccionesDeDiscurso.de_la_obra`
    espera. El estado en T se lee de su vista derivada y llega **como dato**: el
    Planificador no toca la base.
    """
    obra_id = int(capitulo["obra_id"])
    version_obra = await _version_obra_vigente(sesion, obra_id)
    nivel_de_calor = await _nivel_de_calor(sesion, obra_id)
    await planificar_escena(
        sesion,
        planificador,
        capitulo_id=int(capitulo["id"]),
        version_obra_id=int(version_obra["id"]),
        orden_discurso=int(capitulo["numero"]),
        capitulo=dict(capitulo),
        estado_en_t=await _estado_en_t(sesion, obra_id),
        biblia=_biblia(version_obra),
        nivel_de_calor=nivel_de_calor,
    )


async def _escribir(
    sesion: AsyncSession,
    trabajo: Trabajo,
    agentes: Agentes,
    *,
    contexto: ContextoDelCapitulo,
    contador: ContadorDeTokens,
    presupuesto: PresupuestoConcurrente,
    modelo: str,
    semilla: int,
    rango_de_extension: RangoDeExtension,
) -> Escritura:
    """`ESCRIBIENDO`, `VALIDANDO` y `REPARANDO`, dentro del turno del portero.

    **Los tokens que recibe el portero son los que conto el Ensamblador**, y esa
    es la juntura T5-T6-T10 que nadie tenia asignada: hasta hoy nada impedia un
    `turno(0)`, que pasa todas las puertas y deja el techo concurrente
    cumpliendose por consecuencia y no por regla.
    """
    await avanzar(sesion, trabajo, Senal.PASO_COMPLETADO)
    restricciones = await _restricciones(sesion, trabajo.obra_id, contexto.version_obra_id)

    async with presupuesto.turno(
        contexto.paquete.tokens_previstos, paso=f"capitulo {contexto.capitulo_id}"
    ):
        escritura = await escribir_capitulo(
            sesion,
            agentes.escritor,
            contexto=contexto,
            contador=contador,
            run_id=trabajo.run_id,
            modelo=modelo,
            restricciones=restricciones,
            rango_de_extension=rango_de_extension,
            nombres_del_canon=await _nombres_del_canon(sesion, trabajo.obra_id),
            hechos_de_canon=[str(i) for i in _ids_de_canon(contexto)],
            vetos=await _vetos(sesion, trabajo.obra_id),
            semilla=semilla,
            continuista=agentes.continuista,
            grafo=await leer_hechos_del_canon(sesion, obra_id=trabajo.obra_id),
            conocimiento=await _conocimiento(sesion, trabajo.obra_id),
            orden_discurso=await _orden_discurso(sesion, contexto.escena_id),
        )

    await avanzar(sesion, trabajo, Senal.PASO_COMPLETADO)
    trabajo.intento = escritura.reparaciones_gastadas
    await sesion.flush()
    return escritura


def _codigos_bloqueantes(escritura: Escritura) -> tuple[str, ...]:
    """Los codigos con los que la puerta rechazo la **ultima** vuelta.

    Son los que `consolidar_escena` necesita para decidir si escribe memoria de
    largo plazo (R-7). Se ordenan y se deduplican para que el dato sea el mismo
    ejecucion tras ejecucion, que es lo que hace comparables dos corridas.
    """
    ultimo = escritura.intentos[-1]
    return tuple(sorted({defecto.codigo for defecto in ultimo.resultado.bloqueantes}))


async def _retirar_lo_descartado(sesion: AsyncSession, escena_id: int, run_id: str) -> None:
    """R-7, la parte que nadie hacia: **el manuscrito tampoco queda sucio.**

    R-7 nombra canon, ledger e indice, y esas tres las guarda `consolidar_escena`
    no escribiendo. Pero un capitulo escalado deja detras hasta tres
    `version_texto` que nunca pasaron la puerta, y una de ellas **marcada como
    vigente**: el capitulo siguiente la leeria como continuidad local y la prosa
    descartada contaminaria el paquete, que es justo lo que R-7 prohibe.

    Se borra por `run_id` y no por escena: lo que se retira es lo de **esta**
    corrida. T2 dejo el `DELETE` permitido en `version_texto` para esto — el
    disparador de inmutabilidad vigila el `UPDATE`, no el borrado.

    Y despues se vuelve a encender la version que estuviera vigente antes, si la
    habia: `escribir_capitulo` apaga la anterior al guardar la suya, y una escena
    sin ninguna vigente es una escena sin manuscrito.
    """
    await sesion.execute(
        text("DELETE FROM version_texto WHERE escena_id = :escena_id AND run_id = :run_id"),
        {"escena_id": escena_id, "run_id": run_id},
    )
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


async def _conocimiento(sesion: AsyncSession, obra_id: int) -> tuple[ConocimientoEnT, ...]:
    """Lee la vista `estado_en_t`, que es donde el ledger dice **quien sabe que**.

    Se consulta la **vista** y no las tablas de `features/canon`: una vista es
    del esquema y no un import, asi que la frontera de §5.1 sigue entera. Es la
    misma via por la que esta funcion no necesita que `canon` exporte nada.
    """
    filas = await sesion.execute(
        text(
            "SELECT personaje, evento_id, tiempo_historia, sabe_desde "
            "FROM estado_en_t WHERE obra_id = :obra_id "
            # Orden estable: sin el, el paquete cambia entre ejecuciones y el
            # determinismo de §3.6 se pierde sin que falle ningun test.
            "ORDER BY personaje, evento_id"
        ),
        {"obra_id": obra_id},
    )
    return conocimiento_desde_filas(
        (str(personaje), str(evento_id), str(tiempo_historia), sabe_desde)
        for personaje, evento_id, tiempo_historia, sabe_desde in filas.all()
    )


async def _orden_discurso(sesion: AsyncSession, escena_id: int) -> int:
    """Desde donde mira el Continuista. Es el punto del discurso contra el que se
    decide si un conocimiento es **anterior**, y sin el la regla de dominio 2 no
    se puede evaluar."""
    orden = (
        await sesion.execute(
            text("SELECT orden_discurso FROM escena WHERE id = :id"), {"id": escena_id}
        )
    ).scalar_one()
    return int(orden)


def _ids_de_canon(contexto: ContextoDelCapitulo) -> list[int]:
    """Los hechos que **sobrevivieron al recorte** y entraron en el paquete.

    Se leen del propio paquete y no del grafo: RF-CTX-09 dice que lo que se
    persiste es lo que el modelo vio, no lo que estaba disponible.
    """
    return [
        int(identificador.split(":", 1)[1])
        for identificador in contexto.paquete.ids_por_capa.get(Capa.CANON, ())
        if identificador.startswith("hc:")
    ]


async def _registrar_uso(sesion: AsyncSession, contexto: ContextoDelCapitulo) -> None:
    """RF-MEM-02: en que capitulo se apoyo cada hecho.

    Es una sobreaproximacion declarada —lo que entro en el paquete, no lo que la
    prosa acabo usando— y es la direccion segura del error: se rehace de mas,
    nunca de menos (`architecture.md` §4.3).
    """
    ids = _ids_de_canon(contexto)
    if ids:
        await registrar_uso_de_hechos(sesion, capitulo_id=contexto.capitulo_id, hecho_canon_ids=ids)


async def _terminar(
    sesion: AsyncSession,
    trabajo: Trabajo,
    senal: Senal,
    *,
    causa: str | None = None,
    escritura: Escritura | None = None,
) -> ResultadoDelCiclo:
    """El ultimo paso, y el resultado que quien orqueste lee.

    **El estado terminal no se elige aqui: lo dice la maquina.** Antes este
    parametro era la cadena del destino, y eso ponia la decision en el sitio
    equivocado -- cualquier llamada podia terminar un trabajo donde quisiera,
    incluso donde el documento no tiene flecha. Ahora lo que se pasa es la
    senal, y `avanzar` responde con el destino o se niega.

    El `commit` lo hace `avanzar`, y esta bien que sea el: quien sabe que la
    unidad de trabajo termino es el caso de uso (`commons/db/sesion.py`), y el
    trabajo tiene que quedar legible por `GET /trabajos/{id}` precisamente
    cuando algo salio mal.
    """
    estado = await avanzar(sesion, trabajo, senal, causa=causa)
    return ResultadoDelCiclo(
        trabajo_id=trabajo.id,
        estado=estado.value,
        run_id=trabajo.run_id,
        escritura=escritura,
        causa_fallo=causa,
    )


# ---------------------------------------------------------------------------
# Lo que se lee de otras features, por SQL y con su nombre de tabla
# ---------------------------------------------------------------------------


async def _capitulo(sesion: AsyncSession, capitulo_id: int) -> Mapping[str, Any]:
    fila = (
        (
            await sesion.execute(
                text(
                    # Sin `beat_de_genero`: **la tabla no lo tiene.** El
                    # Arquitecto lo asigna y el servicio comprueba CA-32 sobre
                    # su salida, pero `capitulo` no lo guarda, asi que el
                    # Planificador no puede heredarlo del outline. Queda en
                    # Desviaciones; el efecto de hoy es que el beat de la ficha
                    # lo vuelve a decidir el Planificador.
                    "SELECT id, obra_id, numero, titulo, pov_dominante, lugar, objetivo, "
                    "obstaculo, giro_de_valor_previsto, gancho_de_apertura, "
                    "tipo_de_corte_final, extension_objetivo "
                    "FROM capitulo WHERE id = :id"
                ),
                {"id": capitulo_id},
            )
        )
        .mappings()
        .first()
    )
    if fila is None:
        raise CapituloDesconocido(capitulo_id)
    datos: dict[str, Any] = dict(fila)
    return datos


async def _ficha_del_capitulo(sesion: AsyncSession, capitulo_id: Any) -> int | None:
    return (
        await sesion.execute(
            text("SELECT id FROM escena WHERE capitulo_id = :id"), {"id": capitulo_id}
        )
    ).scalar_one_or_none()


async def _version_obra_vigente(sesion: AsyncSession, obra_id: int) -> Mapping[str, Any]:
    fila = (
        (
            await sesion.execute(
                text(
                    "SELECT id, numero, biblia FROM version_obra WHERE obra_id = :obra_id "
                    "ORDER BY numero DESC LIMIT 1"
                ),
                {"obra_id": obra_id},
            )
        )
        .mappings()
        .first()
    )
    if fila is None:
        raise ObraSinBiblia(obra_id)
    datos: dict[str, Any] = dict(fila)
    return datos


def _biblia(version_obra: Mapping[str, Any]) -> Mapping[str, Any]:
    """La biblia, venga como `dict` de SQLAlchemy o como JSON crudo de `text()`."""
    biblia = version_obra["biblia"]
    if isinstance(biblia, str):
        cargada: dict[str, Any] = json.loads(biblia)
        return cargada
    return dict(biblia)


async def _nivel_de_calor(sesion: AsyncSession, obra_id: int) -> int:
    return int(
        (
            await sesion.execute(
                text("SELECT nivel_de_calor FROM obra WHERE id = :id"), {"id": obra_id}
            )
        ).scalar_one()
    )


async def _restricciones(
    sesion: AsyncSession, obra_id: int, version_obra_id: int
) -> RestriccionesDeDiscurso:
    """Las mismas con las que se planifico, releidas de **esa** version de biblia.

    No de la vigente de hoy: la escena se escribio contra una version concreta
    (RF-PLA-01), y es lo que hace atribuible un defecto de persona o de tiempo
    verbal al prompt que lo produjo y no al estado de ahora.
    """
    fila = (
        (
            await sesion.execute(
                text("SELECT id, biblia FROM version_obra WHERE id = :id"),
                {"id": version_obra_id},
            )
        )
        .mappings()
        .one()
    )
    # `dict(...)` y no la `RowMapping` en crudo: es lo que hace que el tipo que
    # entra sea el que se declara, sin apagar el comprobador.
    return RestriccionesDeDiscurso.de_la_obra(
        _biblia(dict(fila)), await _nivel_de_calor(sesion, obra_id)
    )


async def _estado_en_t(sesion: AsyncSession, obra_id: int) -> Mapping[str, Any]:
    """La vista derivada del ledger, resumida para el Planificador.

    Se pasa como dato —no como filas— porque `planificar_escena` lo pide asi:
    `Evento` es de `canon` y una feature no importa de los ficheros internos de
    otra. Y se lee de la **vista**, que es lo que hace cumplir la regla de
    dominio 3 sin depender de que nadie escriba una tabla.
    """
    filas = (
        (
            await sesion.execute(
                text(
                    "SELECT personaje, tiempo_historia, sabe_desde FROM estado_en_t "
                    "WHERE obra_id = :obra_id ORDER BY COALESCE(sabe_desde, 0) DESC"
                ),
                {"obra_id": obra_id},
            )
        )
        .mappings()
        .all()
    )
    return {"conocimientos": [dict(f) for f in filas]}


async def _nombres_del_canon(sesion: AsyncSession, obra_id: int) -> tuple[NombreDeCanon, ...]:
    """Las entidades que el canon declara, **con sus variantes** (CA-16, RF-VAL-03).

    Antes iba sin ellas porque `hecho_canon` no tenia donde guardarlas. T1 de la
    Fase 3 creo `variante_de_nombre` y `leer_nombres_del_canon`, asi que el
    validador deja de ser estricto: «Mari» por «Maria» **no** es defecto si el
    canon la declara, y «Maria» por «Maria» lo sigue siendo. Es la diferencia
    que `CA-16` pide, y que un validador literal no puede dar por listo que sea.

    Cerrado al integrar la ola 2: la funcion vive aqui, en `escritura`, y quien
    la surte vive en `canon`, asi que ninguna de las dos tareas podia hacerlo
    sola sin saltarse la regla 1 del reparto.
    """
    return await leer_nombres_del_canon(sesion, obra_id=obra_id)


async def _vetos(sesion: AsyncSession, obra_id: int) -> tuple[str, ...]:
    """Los tres ambitos de RF-GUA-01: `global` no pertenece a ninguna obra."""
    terminos = (
        (
            await sesion.execute(
                text(
                    "SELECT termino FROM palabra_prohibida "
                    "WHERE obra_id = :obra_id OR ambito = 'global'"
                ),
                {"obra_id": obra_id},
            )
        )
        .scalars()
        .all()
    )
    return tuple(str(t) for t in terminos)
