"""El ciclo de una escena, de principio a fin (§3.9, RF-ORQ-02 a RF-ORQ-18).

Vivía en `corrida.py`, 431 líneas en la raíz del repositorio, y mientras
estuviera ahí **la API no podía conducirlo**: el endpoint creaba la fila de
`trabajo` y nadie la ejecutaba. Un guion de demostración no es un orquestador;
es una copia del orquestador que se desincroniza en cuanto alguien toca uno de
los dos.

**Topología en estrella** (§3.1). Esta función invoca a un agente, recibe su
salida, la persiste y decide el siguiente. Ningún agente llama a otro: una
cadena de agentes hace imposible saber quién introdujo un defecto.

**Las capas se recolectan, no se inventan.** Es la diferencia de fondo con la
versión anterior. `corrida.py` fabricaba las siete con cadenas fijas, así que el
canon aportaba 36 tokens al paquete tanto en la escena 1 como en la 40. Ahora
salen de `recolectar` sobre los almacenes reales, y por eso este es el paso en
el que la memoria empieza a servir para algo.
"""

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict

from app.commons.db import RegistroDeEjecucion, RepositorioDeEjecuciones
from app.commons.domain import ParametrosDeDiscurso, Reloj
from app.commons.jobs import (
    CerrojoPorObra,
    Estado,
    RepositorioDeTrabajos,
    TurnoDeModelo,
    con_reintentos,
)
from app.commons.llm import (
    CargadorDePrompts,
    ClienteDeModelo,
    ContadorDeTokens,
    OrdenadorSemantico,
)
from app.features.calidad import (
    HechoDeCanon,
    RepositorioDeDefectos,
    invocar_continuista,
    pasar_g1a,
    validar_canon,
    validar_conocimiento,
    validar_continuidad_fisica,
    validar_discurso,
    validar_giro_de_valor,
    validar_nivel_de_calor,
)
from app.features.canon import (
    RepositorioDeCanon,
    derivar_estado_en_t,
    extraer_de_escena,
)
from app.features.contexto import (
    Almacenes,
    Capa,
    CapaEnsamblada,
    Pieza,
    ensamblar,
    recolectar,
)
from app.features.escena import (
    FichaDeEscena,
    RepositorioDeEscenas,
    planificar_escena,
)
from app.features.escritura.agents import invocar_escritor
from app.features.obra import RepositorioDeObras
from app.features.outline import RepositorioDeOutline

ESPERA_DE_TURNO_S = 300
ESPERA_DE_CERROJO_S = 5


@dataclass(frozen=True)
class Dependencias:
    """Todo lo que el ciclo necesita y no sabe construir.

    Van agrupadas y no como quince parámetros sueltos porque quien las arma son
    dos sitios muy distintos —`corrida.py` con dobles, el router con el CLI
    real— y lo que tiene que quedar idéntico es **el ciclo**, no la forma de
    invocarlo. Congelado a propósito: una dependencia que cambia a mitad de una
    escena es un fallo imposible de reproducir.
    """

    reloj: Reloj
    contador: ContadorDeTokens
    cargador: CargadorDePrompts
    turno: TurnoDeModelo
    cerrojo: CerrojoPorObra
    ordenador: OrdenadorSemantico
    # El Arquitecto es un agente distinto (§9.3) aunque hoy los cuatro apunten
    # al mismo cliente: separarlos es lo que permite darle otro modelo sin tocar
    # el ciclo, y lo que hace que un doble pueda contestar solo por uno.
    arquitecto: ClienteDeModelo
    planificador: ClienteDeModelo
    escritor: ClienteDeModelo
    # Sin el, los cuatro validadores de continuidad no tienen entrada: reciben
    # `Afirmacion` y nadie las produce. Es obligatorio a proposito, aunque
    # obligue a tocar los cinco sitios que arman el ciclo. Con valor por defecto
    # se podria montar un ciclo que no mira la continuidad sin que nada avise,
    # que es exactamente como se llego al manuscrito del 22-09.
    continuista: ClienteDeModelo
    extractor: ClienteDeModelo
    trabajos: RepositorioDeTrabajos
    escenas: RepositorioDeEscenas
    canon: RepositorioDeCanon
    ejecuciones: RepositorioDeEjecuciones
    obras: RepositorioDeObras
    outline: RepositorioDeOutline
    almacenes: Almacenes
    # Por el mismo motivo, obligatorio: RD-14 lleva desde la migracion inicial
    # sin que nadie escriba una fila, y un defecto que no se guarda no llega ni
    # al autor (RI-18) ni a la tasa de mal formados (§9).
    defectos: RepositorioDeDefectos
    snapshot_cada_n: int = 5


class SinTurno(RuntimeError):
    """No hubo turno de modelo dentro del plazo (RNF-TOK-04)."""


class ResultadoDeEscena(BaseModel):
    model_config = ConfigDict(frozen=True)

    escena_id: str
    trabajo_id: str
    estado: str
    texto: str | None
    tokens_por_capa: dict[str, int]
    coste: float
    defectos: list[str]


def ciclo_de_escena(
    escena_id: str,
    obra_id: str,
    serie_id: str,
    dep: Dependencias,
    trabajo_id: str | None = None,
) -> ResultadoDeEscena:
    """Recorre los estados de §3.3 para una escena. Nunca se salta ninguno.

    `trabajo_id` viene dado cuando quien llama ya creo el trabajo y devolvio su
    identificador al cliente -es lo que hace el endpoint, que no puede esperar a
    que el ciclo termine para decir a quien pregunta por donde va-. Sin el, se
    crea aqui: es el caso del guion de demostracion.
    """
    with dep.cerrojo.en_uso(obra_id, espera_s=ESPERA_DE_CERROJO_S) as tomado:
        if not tomado:
            # RF-ORQ-11: una escena en vuelo por obra. Dos a la vez escribirían
            # sobre el mismo canon y el segundo leería un estado a medias.
            raise RuntimeError(f"la obra {obra_id} ya tiene una escena en vuelo")

        trabajo = (
            dep.trabajos.leer(trabajo_id)
            if trabajo_id
            else dep.trabajos.crear(obra_id, escena_id, "escribir_escena", dep.reloj)
        )
        parametros = dep.obras.leer(obra_id).parametros_para_una_escena()

        # --- PLANIFICANDO ----------------------------------------------------
        ficha = _planificar(escena_id, parametros, dep)
        # Sin esto, la capa de instrucción del paquete saldría de la ficha
        # gruesa del outline y el Escritor recibiría menos de lo decidido.
        dep.escenas.guardar_ficha(ficha)
        dep.trabajos.transitar(trabajo.trabajo_id, Estado.ENSAMBLANDO, dep.reloj)

        # --- ENSAMBLANDO -----------------------------------------------------
        prompt_escritor = dep.cargador.cargar("escritor")
        instruccion = prompt_escritor.texto.format(
            persona=ficha.persona,
            tiempo_verbal=ficha.tiempo_verbal,
            pov=ficha.pov,
            nivel_de_calor=ficha.nivel_de_calor.value,
            extension_objetivo=ficha.extension_objetivo,
        )
        capas = recolectar(
            escena_id=escena_id,
            almacenes=dep.almacenes,
            ordenador=dep.ordenador,
            consulta=f"{ficha.objetivo_del_pov} {ficha.obstaculo} {ficha.lugar}",
        )
        # El prompt versionado entra **dentro** de la capa, no pegado al final
        # del paquete: si fuera por fuera no lo contaría nadie y RNF-TOK-01 se
        # incumpliría por la diferencia justo cuando el paquete va lleno.
        capas[Capa.INSTRUCCION] = CapaEnsamblada(
            capa=Capa.INSTRUCCION,
            piezas=[
                Pieza(texto=instruccion, prioridad=100, etiqueta="prompt-escritor"),
                *capas[Capa.INSTRUCCION].piezas,
            ],
        )
        paquete = ensamblar(capas, dep.contador)
        dep.trabajos.transitar(trabajo.trabajo_id, Estado.ESCRIBIENDO, dep.reloj)

        # --- ESCRIBIENDO -----------------------------------------------------
        with dep.turno.en_uso(espera_s=ESPERA_DE_TURNO_S) as hay_turno:
            if not hay_turno:
                raise SinTurno(escena_id)
            respuesta = con_reintentos(
                lambda: invocar_escritor(dep.escritor, paquete.texto)
            )
        prosa = respuesta.texto
        version = dep.escenas.guardar_version(
            escena_id, prosa, trabajo.run_id, dep.reloj
        )
        coste = _coste_de(respuesta.parametros)
        dep.ejecuciones.registrar(
            RegistroDeEjecucion(
                run_id=trabajo.run_id,
                escena_id=escena_id,
                prompt_id=prompt_escritor.prompt_id,
                prompt_version=prompt_escritor.version,
                prompt_hash=prompt_escritor.hash,
                version_obra_id=dep.escenas.leer_escena(escena_id).version_obra_id,
                ids_recuperados=paquete.ids_recuperados,
                modelo=respuesta.modelo or "doble",
                parametros={"tokens_salida": respuesta.tokens_salida},
                semilla=None,
                tokens_por_capa=paquete.desglose.por_capa,
                coste=coste,
                veredicto=None,
            ),
            dep.reloj,
        )
        dep.trabajos.transitar(trabajo.trabajo_id, Estado.VALIDANDO, dep.reloj)

        # --- VALIDANDO (G1a, mecánica) ---------------------------------------
        # Los tres primeros salen de la ficha y del texto. Los tres siguientes
        # necesitan saber **qué afirma la prosa**, y eso lo extrae el
        # Continuista: sin él, RF-CAL-04 a RF-CAL-06 estaban escritos, probados
        # y sin llamar desde ningún sitio.
        prompt_continuista = dep.cargador.cargar("continuista")
        encargo_continuista = (
            prompt_continuista.texto + "\n\n## Escena escrita\n\n" + prosa
        )
        with dep.turno.en_uso(espera_s=ESPERA_DE_TURNO_S) as hay_turno:
            if not hay_turno:
                raise SinTurno(escena_id)
            lectura = con_reintentos(
                lambda: invocar_continuista(dep.continuista, encargo_continuista)
            )
        afirmaciones = lectura.afirmaciones
        coste += _coste_de(lectura.parametros)
        canon_previo = _canon_para_contrastar(dep.canon.orden_de(escena_id), dep)
        conocimientos = derivar_estado_en_t(dep.canon, escena_id).conocimientos
        defectos = [
            *validar_giro_de_valor(
                ficha.valor_entrada, ficha.valor_salida, prosa, version.version_texto_id
            ),
            *validar_nivel_de_calor(
                prosa, ficha.nivel_de_calor.value, version.version_texto_id
            ),
            *validar_discurso(
                prosa, ficha.persona, ficha.tiempo_verbal, version.version_texto_id
            ),
            *validar_canon(afirmaciones, canon_previo, prosa, version.version_texto_id),
            *validar_conocimiento(
                afirmaciones, conocimientos, prosa, version.version_texto_id
            ),
            # RG-04, la mitad que no necesita tiempos de viaje: estar en dos
            # lugares en el mismo `momento`. La otra mitad queda fuera porque el
            # `momento` del Continuista es un entero relativo a la escena y el
            # `tiempo_de_viaje` de la biblia es texto libre: no son magnitudes
            # comparables, y unirlas es una decisión, no un paso.
            *validar_continuidad_fisica(
                afirmaciones, {}, prosa, version.version_texto_id
            ),
        ]
        # El grafo de canon, no `set()`: sin él, un CAN-01 perfectamente formado
        # se marcaba mal formado (axioma 12), **no bloqueaba**, y se contaba como
        # ruido del Continuista en la única señal que lo mide.
        veredicto = pasar_g1a(defectos, prosa, {h.hc_id for h in canon_previo})
        dep.defectos.registrar(
            [*veredicto.bloquean, *veredicto.no_bloquean, *veredicto.mal_formados]
        )
        dep.ejecuciones.registrar(
            RegistroDeEjecucion(
                run_id=trabajo.run_id,
                escena_id=escena_id,
                prompt_id=prompt_continuista.prompt_id,
                prompt_version=prompt_continuista.version,
                prompt_hash=prompt_continuista.hash,
                version_obra_id=dep.escenas.leer_escena(escena_id).version_obra_id,
                ids_recuperados=[],
                modelo=lectura.modelo,
                parametros={"afirmaciones": len(afirmaciones)},
                semilla=None,
                tokens_por_capa={},
                coste=_coste_de(lectura.parametros),
                veredicto="aprobada" if veredicto.aprobada else "rechazada",
            ),
            dep.reloj,
        )
        codigos = [d.codigo.value for d in veredicto.bloquean]

        if not veredicto.aprobada:
            # RF-CAL-10: un defecto de calidad lleva a REPARANDO, nunca a
            # FALLIDA. Fallida es un fallo técnico, y confundirlos hace que el
            # panel cuente como caídas lo que son escenas mejorables.
            dep.trabajos.transitar(
                trabajo.trabajo_id,
                Estado.REPARANDO,
                dep.reloj,
                causa_fallo="DefectoBloqueante",
                incrementa_intento=True,
            )
            dep.trabajos.transitar(trabajo.trabajo_id, Estado.ESCALADA, dep.reloj)
            return ResultadoDeEscena(
                escena_id=escena_id,
                trabajo_id=trabajo.trabajo_id,
                estado=Estado.ESCALADA.value,
                texto=prosa,
                tokens_por_capa=paquete.desglose.por_capa,
                coste=coste,
                defectos=codigos,
            )

        dep.trabajos.transitar(trabajo.trabajo_id, Estado.EXTRAYENDO, dep.reloj)

        # --- EXTRAYENDO ------------------------------------------------------
        prompt_extractor = dep.cargador.cargar("extractor")
        encargo = prompt_extractor.texto + "\n\n## Escena aprobada\n\n" + prosa
        with dep.turno.en_uso(espera_s=ESPERA_DE_TURNO_S) as hay_turno:
            if not hay_turno:
                raise SinTurno(escena_id)
            con_reintentos(
                lambda: extraer_de_escena(
                    serie_id=serie_id,
                    escena_id=escena_id,
                    version_texto_id=version.version_texto_id,
                    cliente=dep.extractor,
                    prompt=encargo,
                    repositorio=dep.canon,
                    reloj=dep.reloj,
                )
            )
        dep.canon.crear_snapshot_si_toca(escena_id, dep.snapshot_cada_n, dep.reloj)
        dep.trabajos.transitar(trabajo.trabajo_id, Estado.INTEGRADA, dep.reloj)

    return ResultadoDeEscena(
        escena_id=escena_id,
        trabajo_id=trabajo.trabajo_id,
        estado=Estado.INTEGRADA.value,
        texto=prosa,
        tokens_por_capa=paquete.desglose.por_capa,
        coste=coste,
        defectos=codigos,
    )


def _canon_para_contrastar(
    orden_discurso: int, dep: Dependencias
) -> list[HechoDeCanon]:
    """Los hechos vigentes anteriores a la escena, con su orden.

    `HechoCanon` no lleva `orden_discurso` -su clave es la escena de origen- y
    RG-03 arbitra justo por ese orden: prevalece el hecho de menor orden, porque
    el lector ya lo leyo y no se le puede desmentir sin pagarlo.
    """
    return [
        HechoDeCanon(
            hc_id=hecho.hc_id,
            entidad=hecho.entidad,
            atributo=hecho.atributo,
            valor=hecho.valor,
            orden_discurso=dep.canon.orden_de(hecho.escena_de_origen),
        )
        for hecho in dep.canon.hechos_hasta(orden_discurso)
    ]


def _coste_de(parametros: dict[str, object]) -> float:
    """El proveedor lo devuelve o no. Un doble no cobra, y eso no es un fallo."""
    valor = parametros.get("coste_usd")
    return float(valor) if isinstance(valor, int | float | str) else 0.0


def _planificar(
    escena_id: str, parametros: ParametrosDeDiscurso, dep: Dependencias
) -> FichaDeEscena:
    """El Planificador necesita material, no solo su prompt de rol.

    El doble ignora el prompt, así que la corrida en seco nunca detectó esto; el
    modelo real contesta «espero el outline» y el paso falla con una salida que
    no valida. El material sale de los mismos almacenes que el paquete, para que
    no haya dos versiones de la verdad.
    """
    prompt = dep.cargador.cargar("planificador")
    material = "\n".join(
        [
            "## Material",
            "",
            *dep.almacenes.biblia_y_discurso(escena_id),
            *dep.almacenes.outline_del_capitulo(escena_id),
            "",
            "Escena anterior: "
            + (dep.almacenes.escena_anterior_integra(escena_id) or "ninguna")[:300],
            "",
            "Produce ahora la ficha de esta escena.",
        ]
    )
    with dep.turno.en_uso(espera_s=ESPERA_DE_TURNO_S) as hay_turno:
        if not hay_turno:
            raise SinTurno(escena_id)
        return con_reintentos(
            lambda: planificar_escena(
                escena_id,
                parametros,
                dep.planificador,
                prompt.texto + "\n\n" + material,
                dep.reloj,
            )
        )


def ejecutar_en_segundo_plano(
    trabajo_id: str, escena_id: str, obra_id: str, serie_id: str, dep: Dependencias
) -> None:
    """El ciclo, envuelto para que un fallo tecnico no deje el trabajo colgado.

    Sin esto, el hilo del ejecutor se traga la excepcion y el cliente ve
    `ENSAMBLANDO` para siempre: un fallo que se presenta como lentitud, que es
    la forma mas cara de presentarse porque nadie va a buscarlo.

    `FALLIDA` y no `ESCALADA`: escalada es para un defecto de calidad, que una
    persona puede resolver leyendo (RF-CAL-10). Esto es que algo se rompio.
    """
    try:
        ciclo_de_escena(escena_id, obra_id, serie_id, dep, trabajo_id=trabajo_id)
    except Exception as error:  # noqa: BLE001 - aqui se atrapa todo a proposito
        dep.trabajos.transitar(
            trabajo_id,
            Estado.FALLIDA,
            dep.reloj,
            causa_fallo=type(error).__name__,
        )
