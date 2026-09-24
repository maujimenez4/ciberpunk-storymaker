"""Las escrituras de la memoria de largo plazo. **Este fichero es el Extractor.**

`architecture.md` §4.3 lo dice en su tercera columna: canon, ledger, resumenes,
hilos e indice los escribe el Extractor y nadie mas. Aqui esa frase deja de ser
una intencion y pasa a ser una direccion concreta:
`features/canon/repository.py` es la unica ruta de produccion que construye una
fila de esas tablas, y `tests/test_solo_el_extractor_escribe.py` lo comprueba
recorriendo el arbol entero en cada commit (RF-MEM-06, que la spec marca como
Analisis).

**Que NO hay aqui, y es deliberado:**

- Ninguna escritura sobre `estado_en_t` ni sobre `cronologia`. No es disciplina:
  son vistas, y no existe tabla que escribir (regla de dominio 3, RF-MEM-05).
- Ningun `UPDATE` ni `DELETE` sobre `evento`. Tampoco es disciplina: los
  disparadores de `modelos.py` los abortan en la base.
- Ninguna transaccion. El `commit` es de quien orquesta; aqui se hace `flush`,
  que es lo que pone las restricciones en el camino de escritura en vez de
  dejarlas para mas tarde.

`HechoCanon` se importa de `app.features.obra` —su paquete, no su `modelos.py`—
porque el grafo de canon vive en la feature `obra` desde la Fase 1. Que la
tabla del canon este en otra feature que la de su unico escritor es una juntura
torcida, y queda anotada en Desviaciones.
"""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.canon.modelos import (
    Embedding,
    Evento,
    HechoUsadoEn,
    HiloNarrativo,
    ResumenCapitulo,
)
from app.features.canon.schemas import EventoExtraido, HechoExtraido, HiloExtraido, Vector
from app.features.obra import HechoCanon


async def escribir_hechos_de_escena(
    sesion: AsyncSession,
    *,
    obra_id: int,
    escena_id: int,
    hechos: Sequence[HechoExtraido],
) -> list[HechoCanon]:
    """Regla de dominio 4: todo hecho de canon cita la escena que lo establecio.

    `escena_de_origen` se escribe como texto porque la columna es `String(60)`:
    `hecho_canon` es de la Fase 1, cuando la tabla `escena` todavia no existia,
    y el dueno de ese `modelos.py` es otra tarea. Queda anotado.

    La coherencia entre `origen` y `escena_de_origen` **no se comprueba aqui**:
    la sujeta el `CheckConstraint` de la tabla, y repetir la regla en Python
    seria tener dos sitios donde puede divergir.
    """
    filas = [
        HechoCanon(
            obra_id=obra_id,
            entidad=hecho.entidad,
            atributo=hecho.atributo,
            valor=hecho.valor,
            confianza=hecho.confianza,
            origen="escena",
            escena_de_origen=str(escena_id),
        )
        for hecho in hechos
    ]
    return await _anadir(sesion, filas)


async def escribir_eventos(
    sesion: AsyncSession,
    *,
    obra_id: int,
    escena_id: int,
    eventos: Sequence[EventoExtraido],
) -> list[Evento]:
    """El ledger crece por el unico sitio por el que puede crecer: anadiendo.

    `testigos[]` y `excluye[]` se copian enteros y sin filtrar. De los primeros
    se deriva quien puede saber el hecho despues (regla de dominio 2) y de los
    segundos, quien no puede volver a aparecer: perder cualquiera de las dos
    listas por el camino dejaria las dos comprobaciones sin datos y en verde.
    """
    filas = [
        Evento(
            obra_id=obra_id,
            escena_id=escena_id,
            descripcion=evento.descripcion,
            tiempo_historia=evento.tiempo_historia,
            lugar=evento.lugar,
            participantes=list(evento.participantes),
            testigos=list(evento.testigos),
            causa=list(evento.causa),
            consecuencia=list(evento.consecuencia),
            excluye=list(evento.excluye),
        )
        for evento in eventos
    ]
    return await _anadir(sesion, filas)


async def escribir_resumen_de_capitulo(
    sesion: AsyncSession,
    *,
    capitulo_id: int,
    version_texto_id: int | None,
    texto: str,
    hechos_establecidos: Sequence[str],
    hilos_abiertos: Sequence[str],
) -> ResumenCapitulo:
    """RF-MEM-04: se deriva del texto aprobado, y dice de cual.

    `version_texto_id` puede ser nulo mientras el ciclo completo no exista: la
    columna lo admite y el resumen sigue siendo util para el capitulo
    siguiente. Cuando hay version, se cita, que es lo que hace el resumen
    regenerable en vez de una segunda verdad.
    """
    resumen = ResumenCapitulo(
        capitulo_id=capitulo_id,
        version_texto_id=version_texto_id,
        texto=texto,
        hechos_establecidos=list(hechos_establecidos),
        hilos_abiertos=list(hilos_abiertos),
    )
    sesion.add(resumen)
    await sesion.flush()
    return resumen


async def abrir_hilos(
    sesion: AsyncSession,
    *,
    obra_id: int,
    escena_id: int,
    hilos: Sequence[HiloExtraido],
) -> list[HiloNarrativo]:
    """Nacen `abierto` y con la escena que los abre, nunca con escena de cierre.

    El Extractor **abre** preguntas; cerrarlas es de quien escribe la escena que
    las paga. Si pudiera nacer `pagado`, el `CheckConstraint` que exige escena
    de cierre seria lo unico entre una promesa y darla por cumplida.
    """
    filas = [
        HiloNarrativo(
            obra_id=obra_id,
            pregunta=hilo.pregunta,
            estado="abierto",
            escena_de_apertura=escena_id,
            escena_de_cierre=None,
        )
        for hilo in hilos
    ]
    return await _anadir(sesion, filas)


async def indexar_fragmentos(
    sesion: AsyncSession,
    *,
    obra_id: int,
    escena_id: int,
    fragmentos: Sequence[tuple[str, Vector]],
) -> list[Embedding]:
    """El indice vectorial, que es **regenerable entero** desde el texto.

    Si se pierde, no se pierde canon: por eso es el unico almacen de §4.3 cuya
    ausencia no detiene una consolidacion.
    """
    filas = [
        Embedding(
            obra_id=obra_id,
            escena_id=escena_id,
            fragmento=fragmento,
            vector=vector.datos,
            dimension=vector.dimension,
            modelo=vector.modelo,
        )
        for fragmento, vector in fragmentos
    ]
    return await _anadir(sesion, filas)


async def escribir_uso_de_hechos(
    sesion: AsyncSession,
    *,
    capitulo_id: int,
    hecho_canon_ids: Sequence[int],
) -> list[HechoUsadoEn]:
    """RF-MEM-02, la relacion **hacia adelante**: en que capitulos se apoya un hecho.

    Sin ella, «el perro se llama Nala, no Luna» no se puede atender, porque no
    hay forma de saber que capitulos hay que rehacer.

    Los pares que ya estan se omiten en vez de chocar con la clave primaria:
    integrar dos veces el mismo capitulo es una repeticion prevista —un
    reintento, una reanudacion—, no un error, y registrar el uso dos veces
    sobre-reportaria que hay que regenerar.
    """
    if not hecho_canon_ids:
        return []
    ya_estan = set(
        (
            await sesion.execute(
                select(HechoUsadoEn.hecho_canon_id).where(
                    HechoUsadoEn.capitulo_id == capitulo_id,
                    HechoUsadoEn.hecho_canon_id.in_(hecho_canon_ids),
                )
            )
        )
        .scalars()
        .all()
    )
    filas = [
        HechoUsadoEn(hecho_canon_id=hc_id, capitulo_id=capitulo_id)
        for hc_id in dict.fromkeys(hecho_canon_ids)
        if hc_id not in ya_estan
    ]
    return await _anadir(sesion, filas)


async def escribir_hecho_que_sustituye(
    sesion: AsyncSession,
    *,
    hecho: HechoCanon,
    nuevo_valor: str,
    origen: str = "edicion_humana",
) -> HechoCanon:
    """RF-MEM-08: corregir un hecho **no lo edita**.

    Se escribe uno nuevo sobre la misma entidad y el mismo atributo, y el
    anterior se queda intacto. Si se editara en sitio, la escena que se apoyo
    en el valor viejo quedaria rota y sin rastro de por que
    (`architecture.md` §4.7).

    El hecho que sustituye **no puede declarar escena de origen**: no sale de
    una escena, y el `CheckConstraint` de la tabla lo exige para todo origen que
    no sea `escena`.
    """
    nuevo = HechoCanon(
        obra_id=hecho.obra_id,
        entidad=hecho.entidad,
        atributo=hecho.atributo,
        valor=nuevo_valor,
        confianza=hecho.confianza,
        origen=origen,
        escena_de_origen=None,
    )
    sesion.add(nuevo)
    await sesion.flush()
    return nuevo


async def _anadir[T](sesion: AsyncSession, filas: list[T]) -> list[T]:
    """El `flush` no es de conveniencia: adelanta las restricciones de la base.

    Sin el, un `CheckConstraint` incumplido saldria en el `commit` de quien
    llame, ya fuera de la transaccion por escena, y no habria forma de saber
    que pieza lo rompio.
    """
    if not filas:
        return []
    sesion.add_all(filas)
    await sesion.flush()
    return filas
