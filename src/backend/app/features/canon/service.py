"""Casos de uso del Extractor: consolidar una escena, y corregir sin editar.

Aqui vive lo que `architecture.md` §4.4 llama consolidacion, con sus dos reglas:

1. **Solo tras ser aprobada.** Un borrador rechazado no deja hechos en canon,
   ni eventos en el ledger, ni fragmentos en el indice (R-7, RF-MEM-07, CA-10).
2. **Orden fijo y una transaccion por escena:** hechos -> eventos -> resumen ->
   hilos -> embeddings. O entra el conjunto, o no entra nada.

**Quien juzga no es esta feature.** El defecto llega ya emitido por el
Continuista y ya comprobado por la puerta mecanica de `calidad`; `canon` recibe
los codigos bloqueantes y decide una sola cosa: escribir o no escribir. Si
juzgara aqui, el mismo codigo que escribe se estaria dando permiso.

**Ningun `HTTPException` entra en este fichero** (`CLAUDE.md` §6).
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.canon.agents import MARCA_PROSA, sin_etiquetas
from app.features.canon.modelos import Embedding, Evento, HiloNarrativo, ResumenCapitulo
from app.features.canon.repository import (
    abrir_hilos,
    escribir_eventos,
    escribir_hecho_que_sustituye,
    escribir_hechos_de_escena,
    escribir_resumen_de_capitulo,
    escribir_uso_de_hechos,
    indexar_fragmentos,
)
from app.features.canon.schemas import Extraccion, Vector
from app.features.obra import HechoCanon


@dataclass(frozen=True)
class Consolidacion:
    """Que quedo en memoria de largo plazo, por almacen.

    Se devuelve entera —y no un booleano— porque quien orquesta necesita los
    identificadores: `ejecucion` guarda los IDs de canon (RF-CTX-09) y
    RF-MEM-02 necesita saber que hechos entraron para registrar despues en que
    capitulos se usan.
    """

    hechos: list[HechoCanon]
    eventos: list[Evento]
    resumen: ResumenCapitulo | None
    hilos: list[HiloNarrativo]
    fragmentos: list[Embedding]

    @property
    def vacia(self) -> bool:
        """«No entro nada», sin obligar a quien llama a contar filas."""
        return not (self.hechos or self.eventos or self.hilos or self.fragmentos) and (
            self.resumen is None
        )


_VACIA = Consolidacion(hechos=[], eventos=[], resumen=None, hilos=[], fragmentos=[])


async def consolidar_escena(
    sesion: AsyncSession,
    *,
    obra_id: int,
    escena_id: int,
    capitulo_id: int,
    extraccion: Extraccion,
    prosa: str = "",
    version_texto_id: int | None = None,
    vectorizar: Callable[[str], Vector] | None = None,
    defectos_bloqueantes: Sequence[str] = (),
) -> Consolidacion:
    """La escena aprobada pasa a memoria de largo plazo. La rechazada, no.

    **R-7 · CA-10 · RF-MEM-07.** Si llega un solo codigo bloqueante no se
    escribe nada y se devuelve una consolidacion vacia. No se escribe «casi
    todo» ni se marca para limpiar despues: lo que se descarta no puede
    contaminar el capitulo siguiente, y un canon a medias es peor que ninguno
    porque el defecto se atribuiria al Escritor, que no lo cometio.

    **El orden es el de `architecture.md` §4.4** y no es estetico: el resumen
    cita los hechos que acaban de entrar, y los hilos se abren sabiendo ya que
    eventos los sostienen.

    Todo va dentro de un punto de guardado, asi que un fallo a mitad —el indice
    que no responde, una restriccion que salta— deja los almacenes como
    estaban. El `commit` sigue siendo de quien orqueste.
    """
    if defectos_bloqueantes:
        return _VACIA

    async with sesion.begin_nested():
        hechos = await escribir_hechos_de_escena(
            sesion, obra_id=obra_id, escena_id=escena_id, hechos=extraccion.hechos
        )
        eventos = await escribir_eventos(
            sesion, obra_id=obra_id, escena_id=escena_id, eventos=extraccion.eventos
        )
        resumen = await escribir_resumen_de_capitulo(
            sesion,
            capitulo_id=capitulo_id,
            version_texto_id=version_texto_id,
            texto=extraccion.resumen,
            hechos_establecidos=[f"{h.entidad}.{h.atributo}={h.valor}" for h in hechos],
            hilos_abiertos=[hilo.pregunta for hilo in extraccion.hilos],
        )
        hilos = await abrir_hilos(
            sesion, obra_id=obra_id, escena_id=escena_id, hilos=extraccion.hilos
        )
        fragmentos = await indexar_fragmentos(
            sesion,
            obra_id=obra_id,
            escena_id=escena_id,
            fragmentos=_a_vectorizar(prosa, vectorizar),
        )

    return Consolidacion(
        hechos=hechos, eventos=eventos, resumen=resumen, hilos=hilos, fragmentos=fragmentos
    )


def _a_vectorizar(
    prosa: str, vectorizar: Callable[[str], Vector] | None
) -> list[tuple[str, Vector]]:
    """Trocea la prosa por parrafos y la neutraliza antes de indexarla.

    **Los dos pasos importan por motivos distintos.** El troceo es lo que hace
    util la recuperacion: un capitulo entero como un solo vector se parece a
    todo y no es pertinente para nada.

    La neutralizacion es R-8. Lo indexado vuelve al paquete del capitulo
    siguiente por la capa de memoria recuperada, donde entrara otra vez dentro
    de una etiqueta de dato; un fragmento que se llevara el cierre de la
    etiqueta podria salirse de ella. Se limpia **al escribir**, que es una sola
    ruta, y no al leer, que serian tantas como lectores.

    Sin `vectorizar` no se indexa nada y no es un fallo: el indice es
    regenerable entero desde el texto, y exigirlo haria que el sistema no
    arrancara en una maquina sin la extension vectorial (R-6, RNF-FIA-02).
    """
    if vectorizar is None:
        return []
    fragmentos = [trozo.strip() for trozo in prosa.split("\n\n")]
    return [
        (limpio, vectorizar(limpio))
        for trozo in fragmentos
        if (limpio := sin_etiquetas(trozo, MARCA_PROSA).strip())
    ]


async def registrar_uso_de_hechos(
    sesion: AsyncSession, *, capitulo_id: int, hecho_canon_ids: Sequence[int]
) -> None:
    """RF-MEM-02. Lo escribe quien **integra** el capitulo, no quien crea el hecho.

    Lo que se registra es que hechos **entraron en el paquete** del capitulo, no
    cuales acabo usando la prosa: es una sobreaproximacion, y es la direccion
    segura del error —se rehace de mas, nunca de menos— cuando hay que decidir
    que regenerar (`architecture.md` §4.3).
    """
    await escribir_uso_de_hechos(sesion, capitulo_id=capitulo_id, hecho_canon_ids=hecho_canon_ids)


async def corregir_hecho(
    sesion: AsyncSession, *, hecho: HechoCanon, nuevo_valor: str
) -> HechoCanon:
    """RF-MEM-08: se registra un hecho nuevo que sustituye al anterior.

    **Lo que hoy NO queda escrito, y conviene leerlo antes de confiar en esto:**
    la cita al hecho sustituido. `hecho_canon` no tiene columna donde
    guardarla, y su `modelos.py` tiene un solo dueno en esta fase, asi que el
    vinculo se deduce por entidad y atributo en vez de declararse. Queda
    anotado en Desviaciones, junto con los *snapshots* que el requisito manda
    invalidar y que todavia no existen.
    """
    return await escribir_hecho_que_sustituye(sesion, hecho=hecho, nuevo_valor=nuevo_valor)
