"""Corregir un hecho sin editarlo: el llamador que `sustituye_a` no tenia (P-8).

La columna y `escribir_hecho_que_sustituye` entraron en la Fase 3 y **ningun
camino de produccion las usaba**. El camino es este: cuando el lector dice «el
perro se llama Nala, no Luna», no hay edicion —`CLAUDE.md` §15: «ni hechos de
canon: siempre uno que sustituye»— sino un hecho nuevo que cita al anterior.

`origen_del_hecho` responde de que capitulo salio un hecho (RF-PET-04: «el
origen del hecho sustituido»); `corregir_por_peticion` escribe la correccion.

**Las tablas de otras features se leen por SQL con su nombre** —`escena` es de
`escena` y `capitulo` de `outline`— (`CLAUDE.md` §5.1).
"""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.domain.errores import ErrorDeDominio, RecursoDesconocido
from app.features.canon.repository import escribir_hecho_que_sustituye
from app.features.obra import HechoCanon


class HechoDesconocido(RecursoDesconocido):
    """Se pidio corregir un hecho que no esta en el grafo."""

    def __init__(self, hecho_canon_id: int) -> None:
        self.hecho_canon_id = hecho_canon_id
        super().__init__(f"El hecho de canon {hecho_canon_id} no existe")


class HechoYaSustituido(ErrorDeDominio):
    """R-5. Ya hay una correccion sobre este hecho; la nueva ramificaria la cadena.

    No se redirige en silencio al sustituto **porque el lector pidio otra
    cosa**: estaba leyendo la version anterior, y su peticion puede ser obsoleta
    o una tercera correccion. Solo una persona lo sabe.
    """

    def __init__(self, hecho_canon_id: int, sustituto_id: int, valor: str) -> None:
        self.hecho_canon_id = hecho_canon_id
        self.sustituto_id = sustituto_id
        super().__init__(
            f"El hecho {hecho_canon_id} ya fue sustituido por el {sustituto_id}, "
            f"cuyo valor es «{valor}»"
        )


async def corregir_por_peticion(
    sesion: AsyncSession, *, hecho_canon_id: int, nuevo_valor: str
) -> HechoCanon:
    """RF-PET-02. Escribe el hecho que sustituye, y solo si el viejo sigue vivo."""
    hecho = await sesion.get(HechoCanon, hecho_canon_id)
    if hecho is None:
        raise HechoDesconocido(hecho_canon_id)

    sustituto = (
        await sesion.execute(
            select(HechoCanon).where(HechoCanon.sustituye_a == hecho_canon_id).limit(1)
        )
    ).scalar_one_or_none()
    if sustituto is not None:
        raise HechoYaSustituido(hecho_canon_id, sustituto.id, sustituto.valor)

    return await escribir_hecho_que_sustituye(
        sesion, hecho=hecho, nuevo_valor=nuevo_valor, origen="edicion_humana"
    )


async def origen_del_hecho(sesion: AsyncSession, *, hecho_canon_id: int) -> int | None:
    """El **numero** de capitulo que establecio el hecho, o `None` si ninguno.

    `None` es el caso normal y no un fallo: un hecho de `origen: brief` existia
    antes del texto y `ck_hecho_origen_coherente` **prohibe** que tenga escena
    (regla de dominio 4). Quien pregunta decide; RF-PET-04 revalida entonces
    desde el principio (R-1).

    Numero y no `capitulo_id`: el resultado lo lee una persona.
    `CAST(e.id AS TEXT)` y no al reves: `escena_de_origen` es `String(60)`, y
    convertir texto basura a entero daria `0` en vez de nada.
    """
    numero = (
        await sesion.execute(
            text(
                "SELECT c.numero "
                "FROM hecho_canon AS h "
                "JOIN escena AS e ON CAST(e.id AS TEXT) = h.escena_de_origen "
                "JOIN capitulo AS c ON c.id = e.capitulo_id "
                "WHERE h.id = :id AND h.escena_de_origen IS NOT NULL"
            ),
            {"id": hecho_canon_id},
        )
    ).scalar_one_or_none()
    return None if numero is None else int(numero)
