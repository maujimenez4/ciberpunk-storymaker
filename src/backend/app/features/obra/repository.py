"""Acceso a las tablas de la feature `obra`.

Los hechos de canon que nacen del brief (Tarea 8) y, desde la Tarea 9, la
entrevista: abrirla, guardar lo respondido y el texto aportado, y escribir de
una vez la obra con su destinatario y sus vetos.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.obra.modelos import (
    Destinatario,
    Entrevista,
    HechoCanon,
    Obra,
    PalabraProhibida,
    TextoAportado,
)
from app.features.obra.schemas import BriefEntrada, HechoDelBrief


async def guardar_hechos_del_brief(
    sesion: AsyncSession,
    obra_id: int,
    hechos: list[HechoDelBrief],
    origen: str = "brief",
) -> list[HechoCanon]:
    """Un `HechoCanon` por hecho, en el mismo orden, y sin escena de origen.

    `origen` es parametro y no constante porque la Fase 2 escribira por aqui los
    hechos que si nacen de una escena. **No se valida aqui:** de la coherencia
    entre `origen` y `escena_de_origen` responde el `CheckConstraint` de la
    Tarea 4 (regla de dominio 4), y repetir la regla en Python es tener dos
    sitios donde puede divergir. El `flush` no es de conveniencia: es lo que
    pone esa restriccion en el camino de escritura en vez de dejarla para el
    `commit` de quien llame.

    Un hecho en blanco no llega hasta aqui: `HechoDelBrief` exige texto en sus
    tres campos (R-2), asi que lo que no dice nada no se construye siquiera. Lo
    que si tiene texto entra tal cual, sin recortar: es la palabra del comprador.
    """
    filas = [
        HechoCanon(
            obra_id=obra_id,
            entidad=hecho.entidad,
            atributo=hecho.atributo,
            valor=hecho.valor,
            confianza=hecho.confianza,
            origen=origen,
            escena_de_origen=None,
        )
        for hecho in hechos
    ]
    if not filas:
        return []
    sesion.add_all(filas)
    await sesion.flush()
    return filas


async def abrir_entrevista(sesion: AsyncSession) -> Entrevista:
    """Una fila vacia a la que el comprador ira anadiendo respuestas (RI-01)."""
    entrevista = Entrevista(respuestas={})
    sesion.add(entrevista)
    await sesion.flush()
    return entrevista


async def obtener_entrevista(sesion: AsyncSession, entrevista_id: int) -> Entrevista | None:
    """`None` si no existe. Quien decide que hacer con eso es el servicio."""
    return (
        await sesion.execute(select(Entrevista).where(Entrevista.id == entrevista_id))
    ).scalar_one_or_none()


async def guardar_respuestas(
    sesion: AsyncSession,
    entrevista: Entrevista,
    respuestas: dict[str, Any],
) -> Entrevista:
    """Acumula lo respondido: RI-02 se llama varias veces, no una.

    Se **reasigna** el diccionario entero en vez de mutarlo: SQLAlchemy no
    vigila el interior de una columna `JSON`, asi que un `update` en sitio no
    llegaria a la base y la siguiente llamada leeria lo de antes.
    """
    entrevista.respuestas = {**entrevista.respuestas, **respuestas}
    await sesion.flush()
    return entrevista


async def guardar_texto_aportado(
    sesion: AsyncSession,
    entrevista_id: int,
    contenido: str,
) -> TextoAportado | None:
    """RF-ENT-05: el texto libre **se guarda**, no solo se marca en el prompt.

    Un texto en blanco no se escribe y se devuelve `None` (R-2): es opcional, y
    un `TextoAportado` vacio acabaria produciendo un hecho de canon vacio. El
    contenido entra **sin recortar ni sanear**: es la palabra del comprador, y
    lo que lo hace inofensivo no es limpiarlo sino que nunca se concatene a un
    prompt sin la marca de dato (`agents.render_entrevistador`).
    """
    if not contenido.strip():
        return None
    texto = TextoAportado(
        entrevista_id=entrevista_id,
        contenido=contenido,
        procedencia="entrevista",
    )
    sesion.add(texto)
    await sesion.flush()
    return texto


async def leer_textos_aportados(sesion: AsyncSession, entrevista_id: int) -> list[TextoAportado]:
    """Lo que el comprador pego, en orden de llegada."""
    filas = await sesion.execute(
        select(TextoAportado)
        .where(TextoAportado.entrevista_id == entrevista_id)
        .order_by(TextoAportado.id)
    )
    return list(filas.scalars().all())


async def crear_obra_desde_brief(sesion: AsyncSession, brief: BriefEntrada) -> Obra:
    """La postcondicion de CU-01, entera: la obra con su destinatario y sus vetos.

    Los vetos van al ambito `brief` de `palabra_prohibida` (RF-ENT-02). La tabla
    existe desde la Tarea 4 y hasta ahora nadie escribia en ella: sin esta
    escritura, «lo que este comprador no quiere leer» no llegaba a ningun sitio
    donde el guardarrail de la Fase 2 pudiera consultarlo.

    El `titulo` es provisional y se deriva del destinatario. El definitivo lo
    pone el Arquitecto, que es de la Fase 2; la columna es obligatoria y el
    brief no trae titulo, asi que el plan dejaba aqui un hueco (ver
    Desviaciones). No es prosa generada: es el nombre con el que la obra se
    encuentra hasta que tenga el suyo.
    """
    destinatario = Destinatario(
        nombre=brief.destinatario.nombre,
        edad=brief.destinatario.edad,
        rasgos=list(brief.destinatario.rasgos),
        recuerdos_aportados=list(brief.destinatario.recuerdos_aportados),
        fecha_de_nacimiento=brief.destinatario.fecha_de_nacimiento,
    )
    sesion.add(destinatario)
    await sesion.flush()

    obra = Obra(
        titulo=f"Novela para {brief.destinatario.nombre}",
        genero=brief.genero,
        tono=brief.tono,
        nivel_de_calor=brief.nivel_de_calor,
        destinatario_id=destinatario.id,
    )
    sesion.add(obra)
    await sesion.flush()

    sesion.add_all(
        PalabraProhibida(
            ambito="brief",
            termino=veto,
            obra_id=obra.id,
            motivo="Veto del comprador, recogido en la entrevista",
        )
        for veto in brief.vetos
    )
    await sesion.flush()
    return obra
