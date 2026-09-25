"""El ciclo de escritura de un capitulo: escribir, validar, reparar, detenerse.

Aqui vive todo lo que el Escritor **no** hace, y la separacion es el diseno:

| Quien | Que hace | Que no hace |
| --- | --- | --- |
| `agents.py` | Manda el prompt, devuelve prosa | No juzga, no guarda, no cuenta |
| esto | Guarda, cruza la puerta, cuenta y para | No escribe prosa, no puntua |
| `calidad` | Decide si el capitulo pasa | No repara, no reintenta, no persiste |

Si el Escritor decidiera cuando su propia prosa esta bien, el mismo codigo que
escribe se estaria dando permiso. Y si la puerta reparase, dejaria de poder
probarse el rechazo sin un ciclo entero alrededor.

**Los reintentos van dirigidos, siempre.** `CLAUDE.md` §15 prohibe con esas
palabras los reintentos genericos: cada vuelta lleva el defecto concreto con la
cita del pasaje (RF-ESC-03), y un defecto que no se puede citar no vuelve. El
tope son **dos reparaciones por capitulo** (RF-ORQ-04), y el contador es una
variable local: no hay ningun sitio donde pudiera sobrevivir al capitulo.

**Lo que no es de esta tarea y se ve desde aqui:** el estado del `Trabajo`, el
turno del presupuesto concurrente y la consolidacion en canon son del ciclo de
punta a punta (T11). Esto devuelve un resultado y no toca ninguna de las tres.
"""

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, runtime_checkable

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.db.auditoria import registrar
from app.commons.domain.errores import ContextBudgetExceeded
from app.commons.llm.contador import ContadorDeTokens
from app.commons.observabilidad import Observacion
from app.features.calidad import (
    CODIGO_DE_PALABRA_PROHIBIDA,
    CapituloAContrastar,
    CapituloAJuzgar,
    CapituloAPolicy,
    CapituloAValidar,
    ConocimientoEnT,
    Continuista,
    Critico,
    Defecto,
    HechoDeCanon,
    Juicio,
    NombreDeCanon,
    ParametrosDeDiscurso,
    Persona,
    RangoDeExtension,
    ResultadoDePuerta,
    TiempoVerbal,
    aplicar_policy,
    cruzar_g1a,
    emitir,
    puntuaciones_de_g1a,
    puntuaciones_de_policy,
    puntuaciones_del_juez,
)

NOMBRE_DEL_CONTINUISTA = "continuidad_y_canon"
"""El nombre de `verification.md` §8.1, sin traducir: es la llave por la que su
*score* se cruza con la tabla de validadores (T5)."""
from app.features.contexto import Capa, ContextoDelCapitulo, DatosDeLlamada, registrar_ejecucion
from app.features.escena import RestriccionesDeDiscurso
from app.features.escritura.agents import (
    HASH_DE_PLANTILLA_V1,
    PLANTILLA_V1,
    PROMPT_ID,
    PROMPT_VERSION,
    Escritor,
    Reparacion,
    render_escritor,
)
from app.features.escritura.modelos import (
    INTENTOS_MAXIMOS,
    Ejecucion,
    IntentoDescartado,
    VersionTexto,
)

PERSONA_DE_LA_OBRA: dict[str, Persona] = {
    "1ª": Persona.PRIMERA,
    "3ª limitada": Persona.TERCERA_LIMITADA,
    "3ª omnisciente": Persona.TERCERA_OMNISCIENTE,
}
"""De la cadena que declara la obra al enum con que juzga `calidad`.

**Hoy es la identidad, y no siempre lo fue.** `calidad` nacio con `primera` y
`tercera_limitada` mientras `outline` y `escena` usaban los literales de
`definitions.md` §5; convivieron una ola entera y lo destapo esta tarea al
tener que traducir. Se alinearon al cerrar la ola 4.

El mapa se queda aunque sea la identidad, y no es ceremonia: es la frontera
entre un texto que viene de la biblia --dato-- y un tipo cerrado, y lleva un
test que cae si aparece una persona sin traducir. Si alguien vuelve a
desalinear las dos grafias, ese test lo dice en vez de descubrirse tres olas
despues.
"""

TIEMPO_VERBAL_DE_LA_OBRA: dict[str, TiempoVerbal] = {
    "pasado": TiempoVerbal.PASADO,
    "presente": TiempoVerbal.PRESENTE,
}
"""Aqui los dos literales si coinciden. Se escribe igual que el de arriba para
que la comprobacion sea la misma y no dos reglas distintas."""


@runtime_checkable
class _Consumo(Protocol):
    tokens_entrada: int
    tokens_salida: int
    coste_usd: Decimal
    cache_read_input_tokens: int
    cache_creation_input_tokens: int


@runtime_checkable
class _ClienteQueDeclaraConsumo(Protocol):
    @property
    def ultimo_consumo(self) -> "_Consumo | None": ...


@dataclass(frozen=True, slots=True)
class IntentoDeEscritura:
    """Una vuelta del ciclo: lo que se escribio y que dijo la puerta.

    Se conservan **todos**, aprobados y rechazados. Sin ellos, «se reparo dos
    veces y se escalo» seria una afirmacion del codigo sobre si mismo.
    """

    numero: int
    version_texto_id: int
    texto: str
    resultado: ResultadoDePuerta
    termino_vetado: str | None = None


@dataclass(frozen=True, slots=True)
class Escritura:
    """Lo que el ciclo devuelve. **Se informa, no se lanza.**

    RF-GUA-03 pide que, agotado el limite, «la generacion se detiene y **se
    informa**». Una excepcion detendria tambien a quien orqueste, que es
    justamente quien tiene que pasar el trabajo a `ESCALADA` y contarselo a una
    persona: un final previsto del ciclo no es una averia.
    """

    aprobado: bool
    version_texto_id: int
    texto: str
    intentos: tuple[IntentoDeEscritura, ...]
    motivo_de_escalado: str | None = None
    juicio: Juicio | None = None
    """Lo que dijo el juez, **y nada mas que lo que dijo**.

    Vive aqui y no en `ResultadoDePuerta` a proposito: la puerta decide y este
    campo no, asi que separarlos hace estructural lo que RF-JUZ-06 pide. Es
    `None` cuando no hay Critico, que no es lo mismo que un juicio vacio."""

    @property
    def reparaciones_gastadas(self) -> int:
        """Las vueltas que no fueron la primera. Tope: `INTENTOS_MAXIMOS`."""
        return len(self.intentos) - 1


def _discurso(restricciones: RestriccionesDeDiscurso) -> ParametrosDeDiscurso:
    """Regla de dominio 10: lo que la obra declara, traducido al validador.

    Falla con `KeyError` si la persona no tiene traduccion, y es lo correcto:
    inventar un valor por defecto haria que el validador comprobara el texto
    contra algo que nadie decidio, que es lo mismo que T4 rechazo para la ficha.
    """
    return ParametrosDeDiscurso(
        persona=PERSONA_DE_LA_OBRA[restricciones.persona],
        tiempo_verbal=TIEMPO_VERBAL_DE_LA_OBRA[restricciones.tiempo_verbal],
    )


async def _guardar_version(
    sesion: AsyncSession, escena_id: int, texto: str, run_id: str
) -> VersionTexto:
    """Una version nueva, vigente, sin tocar la anterior (RF-ESC-02).

    El orden es obligatorio y no estetico: el indice parcial de T2 admite **una
    sola** vigente por escena, asi que la anterior se apaga antes de encender la
    nueva. Y se apaga con un `UPDATE` de `vigente` y de nada mas, que es la
    unica columna que el disparador de inmutabilidad deja cambiar.

    La descartada **no se borra**: R-7 nombra canon, ledger e indice, no el
    manuscrito, y lo entregado tiene que seguir siendo recuperable.
    """
    ultimo = (
        await sesion.execute(
            select(VersionTexto.numero)
            .where(VersionTexto.escena_id == escena_id)
            .order_by(VersionTexto.numero.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    await sesion.execute(
        update(VersionTexto)
        .where(VersionTexto.escena_id == escena_id, VersionTexto.vigente.is_(True))
        .values(vigente=False)
    )
    version = VersionTexto(
        escena_id=escena_id,
        numero=1 if ultimo is None else ultimo + 1,
        texto=texto,
        vigente=True,
        run_id=run_id,
    )
    sesion.add(version)
    await sesion.flush()
    return version


async def _completar_ejecucion(
    sesion: AsyncSession, ejecucion_id: int, escritor: Escritor, veredicto: str
) -> None:
    """Cierra la fila que nacio antes de la llamada (P-A, decision de T6).

    `tokens_previstos` ya estaba —es lo que decidio que se podia llamar— y aqui
    entran los tres que solo existen despues: tokens reales, coste y veredicto.

    **El consumo se pregunta y puede no estar**, y por eso no se imputa cero:
    `ClienteModelo` declara `completar` y nada mas —su fichero es de T1 y ya
    cerro—, asi que el cliente real expone `ultimo_consumo` y un doble puede no
    hacerlo. Un cero se guarda, se suma y se publica sin que nadie note que el
    dato no estaba; un nulo se ve.
    """
    valores: dict[str, object] = {"veredicto": veredicto}
    cliente = escritor.cliente
    if isinstance(cliente, _ClienteQueDeclaraConsumo):
        consumo = cliente.ultimo_consumo
        if consumo is not None:
            valores["tokens_reales"] = consumo.tokens_entrada + consumo.tokens_salida
            valores["coste"] = float(consumo.coste_usd)
            # P-18: se guardan y **no se suman** a `tokens_reales`. El coste de
            # arriba sigue saliendo de los mismos dos numeros que antes.
            valores["cache_read_input_tokens"] = consumo.cache_read_input_tokens
            valores["cache_creation_input_tokens"] = consumo.cache_creation_input_tokens

    await sesion.execute(update(Ejecucion).where(Ejecucion.id == ejecucion_id).values(**valores))


def _coste_de_la_reparacion(
    contexto: ContextoDelCapitulo,
    restricciones: RestriccionesDeDiscurso,
    texto_anterior: str | None,
    reparaciones: Sequence[Reparacion],
    contador: ContadorDeTokens,
) -> int:
    """Cuanto crece el prompt al anadirle el defecto con su cita. Cero la primera vez.

    **Es la juntura T5-T6-T8, y ninguna de las tres la tenia asignada.** El
    Ensamblador cuenta el **paquete**; lo que se manda es el **prompt**, que
    ademas del paquete lleva la plantilla y, en las vueltas de reparacion, el
    capitulo anterior integro mas una linea por defecto. `CLAUDE.md` §4.1 dice
    que la reserva de 10.000 existe «para que el reintento con el defecto
    anadido siga cabiendo», y hasta hoy nadie lo comprobaba.

    Se mide el **incremento** y no el prompt entero a proposito: lo que la
    reserva cubre es lo que se anade. Contar aqui la plantilla haria que el
    primer intento consumiera reserva sin haber reparado nada.

    Si no cabe, `ContextBudgetExceeded` sobre la capa `reserva` **sin llamar al
    modelo** (RF-CTX-02, RF-CTX-03): nunca se recorta el paquete para hacerlo
    caber, y nunca se manda a ver si suena la flauta.
    """
    if not reparaciones:
        return 0

    base = contador.contar(render_escritor(PLANTILLA_V1, contexto.paquete.texto, restricciones))
    entero = contador.contar(
        render_escritor(
            PLANTILLA_V1,
            contexto.paquete.texto,
            restricciones,
            texto_anterior=texto_anterior,
            reparaciones=reparaciones,
        )
    )
    extra = entero - base
    libre = contexto.paquete.desglose.reserva_libre
    if extra > libre:
        raise ContextBudgetExceeded(Capa.RESERVA, extra, libre)
    return extra


async def _juzgar(
    critico: Critico | None, version_texto_id: str, texto: str, observacion: Observacion
) -> Juicio | None:
    """Puntua, y lo que devuelve **no decide nada**.

    Que el juicio salga en `Escritura` y no en la puerta es la forma de que eso
    sea estructural y no disciplina: no hay ningun sitio donde una puntuacion
    pueda cambiar `aprobado`, asi que empezar a bloquear exigiria un cambio que
    se ve en una revision, no un descuido.

    Sus *scores* van a Langfuse, uno por criterio y con su justificacion: es la
    unica salida del juez **mientras no bloquee**, y lo que `RF-JUZ-05` compara
    con la revision humana.
    """
    if critico is None:
        return None
    async with observacion.span("critico") as span:
        juicio = await critico.juzgar(
            CapituloAJuzgar(
                version_texto_id=version_texto_id,
                texto=texto,
                # La rubrica sale del propio juez y no se importa aqui: asi hay
                # **una** en juego, que es lo que `CA-20` pide.
                rubrica=critico.rubrica,
            )
        )
        emitir(span, puntuaciones_del_juez(juicio))
    return juicio


async def escribir_capitulo(
    sesion: AsyncSession,
    escritor: Escritor,
    *,
    contexto: ContextoDelCapitulo,
    contador: ContadorDeTokens,
    run_id: str,
    modelo: str,
    restricciones: RestriccionesDeDiscurso,
    rango_de_extension: RangoDeExtension,
    nombres_del_canon: Sequence[NombreDeCanon] = (),
    hechos_de_canon: Collection[str] = (),
    vetos: Sequence[str] = (),
    semilla: int = 0,
    continuista: Continuista | None = None,
    critico: Critico | None = None,
    grafo: Sequence[HechoDeCanon] = (),
    conocimiento: Sequence[ConocimientoEnT] = (),
    orden_discurso: int = 0,
    observacion: Observacion | None = None,
) -> Escritura:
    """Escribe el capitulo y lo repara dirigidamente hasta dos veces.

    El orden de cada vuelta es este, y ninguno de los pasos se puede adelantar:

    1. **Nace la fila de `ejecucion`**, con el recuento previo del paquete. Es
       lo que acredita que se conto **antes** de llamar (RF-CTX-02, P-A).
    2. Se llama al Escritor, que solo ve el paquete.
    3. **Se guarda la version**, aprobada o no. Una prosa que no se guardara no
       se podria citar, y un defecto sin cita no vuelve dirigido.
    4. Se busca la palabra vetada y se anota la decision en el registro de
       auditoria —lo permitido tambien, no solo lo bloqueado (RF-GUA-04)—.
    5. Se cruza la puerta mecanica, con el veto entre los defectos recibidos.
    6. Si bloquea y quedan reparaciones, los defectos vuelven **con su cita**.

    `contexto` entra entero y no troceado porque `registrar_ejecucion` lo pide
    asi: la fila de cada llamada necesita obra, escena, version de biblia,
    tokens por capa e IDs recuperados, y trocearlo aqui seria volver a montarlo
    alli. El paquete que se envia es `contexto.paquete` y ningun otro.

    **Cada vuelta abre sus spans** en la traza del capitulo (`CLAUDE.md` §4.3):
    `escritor`, `policy`, `continuista`, `puerta_g1a` y `critico`, y los
    *scores* de cada validador van en el span del que los produjo. Sin
    `observacion`, los spans son nulos: el mismo camino, sin efecto.
    """
    observacion = observacion if observacion is not None else Observacion.nula()
    intentos: list[IntentoDeEscritura] = []
    reparaciones: tuple[Reparacion, ...] = ()
    texto_anterior: str | None = None

    while True:
        # **El prompt del reintento se vuelve a presupuestar**, y es lo que hace
        # de la reserva un mecanismo y no una fila de una tabla. Va ANTES de
        # crear la fila y antes de llamar: lo que no cabe no llega a gastarse.
        extra = _coste_de_la_reparacion(
            contexto, restricciones, texto_anterior, reparaciones, contador
        )

        ejecucion_id = await registrar_ejecucion(
            sesion,
            contexto,
            DatosDeLlamada(
                run_id=run_id,
                prompt_id=PROMPT_ID,
                prompt_version=PROMPT_VERSION,
                prompt_hash=HASH_DE_PLANTILLA_V1,
                modelo=modelo,
                semilla=semilla,
            ),
        )
        if extra:
            # La fila nace con el recuento del paquete (decision de T6); esta
            # vuelta manda mas, y `tokens_previstos` tiene que decirlo o P-A no
            # puede medir la deriva del contador contra `tokens_reales`.
            await sesion.execute(
                update(Ejecucion)
                .where(Ejecucion.id == ejecucion_id)
                .values(tokens_previstos=contexto.paquete.tokens_previstos + extra)
            )

        async with observacion.span("escritor"):
            texto = await escritor.escribir(
                contexto.paquete,
                restricciones,
                texto_anterior=texto_anterior,
                reparaciones=reparaciones,
            )
        version = await _guardar_version(sesion, contexto.escena_id, texto, run_id)

        async with observacion.span("policy") as span:
            resultado_policy = aplicar_policy(
                CapituloAPolicy(
                    version_texto_id=str(version.id),
                    texto=texto,
                    vetos=tuple(vetos),
                )
            )
            emitir(span, puntuaciones_de_policy(resultado_policy))
        for decision in resultado_policy.decisiones:
            await registrar(
                sesion,
                contexto.obra_id,
                decision.decision,
                f"{decision.regla}: {decision.motivo}",
                decision.evidencia,
            )
        recibidos: list[Defecto] = list(resultado_policy.defectos)

        # P-17. El Continuista corre **antes** de la puerta y entra por
        # `defectos_recibidos`, que la Fase 2 dejo preparado exactamente para
        # esto: «hoy ninguna, porque el Continuista es de la Fase 3». Estaba
        # construido, probado y exportado, y no lo llamaba nadie.
        #
        # Se le nombra en `emisores_externos` aunque no encuentre nada: un
        # validador que corre y no consta no emite *score*, y su casilla en la
        # tabla de los cinco briefs no distinguiria «limpio» de «no corrio».
        emisores: tuple[str, ...] = ()
        if continuista is not None:
            async with observacion.span("continuista"):
                revision = await continuista.revisar(
                    CapituloAContrastar(
                        version_texto_id=str(version.id),
                        texto=texto,
                        grafo=tuple(grafo),
                        conocimiento=tuple(conocimiento),
                        orden_discurso=orden_discurso,
                    )
                )
            recibidos.extend(revision.defectos)
            emisores = (NOMBRE_DEL_CONTINUISTA,)

        # El *score* de `continuidad_y_canon` sale **de aqui** y no del span del
        # Continuista: la puerta es quien decide si su defecto bloquea, y quien
        # lo cuenta en `defectos_por_validador`.
        async with observacion.span("puerta_g1a") as span:
            resultado = cruzar_g1a(
                CapituloAValidar(
                    version_texto_id=str(version.id),
                    texto=texto,
                    rango_de_extension=rango_de_extension,
                    discurso=_discurso(restricciones),
                    nombres_del_canon=tuple(nombres_del_canon),
                ),
                hechos_de_canon,
                recibidos,
                emisores_externos=emisores,
            )
            emitir(span, puntuaciones_de_g1a(resultado))
            span.salida(_veredicto_de_la_puerta(resultado))
        intentos.append(
            IntentoDeEscritura(
                numero=len(intentos) + 1,
                version_texto_id=version.id,
                texto=texto,
                resultado=resultado,
                termino_vetado=resultado_policy.termino_vetado,
            )
        )

        # El juez corre **despues** de la puerta y su resultado no entra en
        # ninguna decision: `RF-JUZ-06` dice que no bloquea hasta que su
        # correlacion con la revision humana este medida y **firmada con el
        # numero delante**. Se le llama igualmente porque lo que no corre no
        # puede calibrarse, y sin calibrar no deja de bloquear nunca.
        juicio = await _juzgar(critico, str(version.id), texto, observacion)

        if resultado.aprobado:
            await _completar_ejecucion(sesion, ejecucion_id, escritor, "aprobada")
            return Escritura(
                aprobado=True,
                version_texto_id=version.id,
                texto=texto,
                intentos=tuple(intentos),
                motivo_de_escalado=None,
                juicio=juicio,
            )

        # RF-ORQ-04: dos reparaciones dirigidas y ni una mas. El contador es
        # `len(intentos)` y vive en esta llamada, asi que no hay donde pudiera
        # sobrevivir al capitulo: avanzar al siguiente no consume nada.
        if len(intentos) > INTENTOS_MAXIMOS:
            await _completar_ejecucion(sesion, ejecucion_id, escritor, "escalada")
            return Escritura(
                aprobado=False,
                version_texto_id=version.id,
                texto=texto,
                intentos=tuple(intentos),
                motivo_de_escalado=_motivo(resultado, intentos[-1].termino_vetado),
            )

        await _completar_ejecucion(sesion, ejecucion_id, escritor, "rechazada")
        reparaciones = tuple(
            Reparacion.de_defecto(
                defecto,
                termino_vetado=(
                    intentos[-1].termino_vetado
                    if defecto.codigo == CODIGO_DE_PALABRA_PROHIBIDA
                    else None
                ),
            )
            for defecto in resultado.bloqueantes
        )
        texto_anterior = texto


def _veredicto_de_la_puerta(resultado: ResultadoDePuerta) -> str:
    """Lo que la puerta decidio, en una linea para el span: sin prosa."""
    if resultado.aprobado:
        return "aprobado"
    codigos = ", ".join(sorted({defecto.codigo for defecto in resultado.bloqueantes}))
    return f"bloqueado: {codigos}" if codigos else "bloqueado"


def _motivo(resultado: ResultadoDePuerta, termino_vetado: str | None) -> str:
    """Por que se escala, **nombrando** el termino cuando lo hay.

    «Se agotaron los intentos» no deja actuar a quien lo lea. RF-GUA-03 pide el
    termino concreto en el camino de vuelta al escritor, y el mismo criterio
    vale para el camino de vuelta a la persona.
    """
    codigos = ", ".join(sorted({defecto.codigo for defecto in resultado.bloqueantes}))
    motivo = (
        f"agotadas las {INTENTOS_MAXIMOS} reparaciones dirigidas; sigue bloqueado por {codigos}"
    )
    if termino_vetado is not None:
        motivo += f"; palabra vetada: {termino_vetado}"
    return motivo


async def intentos_descartados(
    sesion: AsyncSession, trabajo_id: int
) -> Sequence[IntentoDescartado]:
    """P-20: la evidencia de un trabajo, **en el orden en que se escribio**.

    Solo lee. Que el trabajo exista lo comprueba quien llama (`leer_trabajo`),
    para que un id desconocido responda 404 y no una lista vacia que se
    confundiria con «no hubo rechazos».
    """
    filas = await sesion.execute(
        select(IntentoDescartado)
        .where(IntentoDescartado.trabajo_id == trabajo_id)
        .order_by(IntentoDescartado.numero, IntentoDescartado.id)
    )
    return filas.scalars().all()
