"""R-7 · CA-10 · RF-MEM-07: un capitulo rechazado no deja rastro.

`architecture.md` §4.4 lo dice con esas palabras: una escena pasa a memoria de
largo plazo **solo tras ser aprobada**. Un borrador rechazado no deja hechos en
canon, ni eventos en el ledger, ni fragmentos en el indice. Si los dejara, el
canon quedaria contaminado con afirmaciones de un texto que nunca llego al
manuscrito, y el capitulo siguiente se escribiria contra ellas.

**Que rechaza aqui, y que no.** El defecto llega ya juzgado: quien lo emite es
el Continuista y quien lo comprueba es la puerta mecanica de la feature
`calidad`. `canon` no juzga — si lo hiciera, el mismo codigo escribiria y se
daria permiso —: recibe los codigos bloqueantes y se limita a no escribir.

**Y que no borra.** R-7 nombra canon, ledger e indice, que son estas tablas. La
`version_texto` descartada la retira quien la escribio (`escritura`), y por eso
la Tarea 2 dejo el `DELETE` permitido alli y no aqui.
"""

from sqlalchemy import func, select

from app.features.canon.modelos import Embedding, Evento, HiloNarrativo, ResumenCapitulo
from app.features.canon.schemas import Vector
from app.features.canon.service import consolidar_escena
from app.features.canon.tests.test_consolidacion import EXTRACCION
from app.features.obra import HechoCanon

DEFECTO_BLOQUEANTE = ("CAN-01",)


def _vector(fragmento: str) -> Vector:
    return Vector(datos=fragmento.encode()[:8].ljust(8, b"\0"), dimension=8, modelo="doble")


async def _consolidar_rechazada(sesion, obra_con_outline):
    return await consolidar_escena(
        sesion,
        obra_id=obra_con_outline.obra.id,
        escena_id=obra_con_outline.escena.id,
        capitulo_id=obra_con_outline.capitulos[0].id,
        extraccion=EXTRACCION,
        prosa="Nadia abrio la puerta.\n\nDentro olia a tierra mojada.",
        vectorizar=_vector,
        defectos_bloqueantes=DEFECTO_BLOQUEANTE,
    )


async def test_un_capitulo_rechazado_no_deja_rastro_en_canon_ledger_ni_indice(
    sesion, obra_con_outline
):
    """Los tres almacenes que R-7 nombra, contados uno a uno.

    El hecho de canon se cuenta por `origen='escena'`: la fixture trae uno de
    `origen='brief'`, que existia antes del texto y que un rechazo **no** debe
    llevarse por delante.
    """
    await _consolidar_rechazada(sesion, obra_con_outline)

    assert (
        await sesion.scalar(
            select(func.count()).select_from(HechoCanon).where(HechoCanon.origen == "escena")
        )
        == 0
    )
    assert await sesion.scalar(select(func.count()).select_from(Evento)) == 0
    assert await sesion.scalar(select(func.count()).select_from(Embedding)) == 0


async def test_un_capitulo_rechazado_tampoco_deja_resumen_ni_hilos(sesion, obra_con_outline):
    """Los otros dos almacenes de §4.3 que alimentan el capitulo siguiente."""
    await _consolidar_rechazada(sesion, obra_con_outline)

    assert await sesion.scalar(select(func.count()).select_from(ResumenCapitulo)) == 0
    assert await sesion.scalar(select(func.count()).select_from(HiloNarrativo)) == 0


async def test_el_rechazo_devuelve_una_consolidacion_vacia(sesion, obra_con_outline):
    """Quien llama tiene que poder distinguir «no entro nada» sin contar filas."""
    consolidacion = await _consolidar_rechazada(sesion, obra_con_outline)

    assert consolidacion.vacia
    assert consolidacion.hechos == []
    assert consolidacion.eventos == []
    assert consolidacion.resumen is None
    assert consolidacion.hilos == []
    assert consolidacion.fragmentos == []


async def test_el_hecho_del_brief_sobrevive_al_rechazo(sesion, obra_con_outline):
    """Un rechazo no es un borrado: lo que existia antes del texto sigue ahi."""
    await _consolidar_rechazada(sesion, obra_con_outline)
    await sesion.refresh(obra_con_outline.hecho_canon)
    assert obra_con_outline.hecho_canon.valor == "Luna"


async def test_sin_defecto_bloqueante_si_entra(sesion, obra_con_outline):
    """El contraste que hace que el test anterior pueda caer.

    Sin esto, «no deja rastro» lo cumpliria igual un consolidador que no
    escribiera nunca — que es justo el tipo de restriccion sobre la que ningun
    test puede caer, y este plan ya la ha encontrado dos veces.
    """
    consolidacion = await consolidar_escena(
        sesion,
        obra_id=obra_con_outline.obra.id,
        escena_id=obra_con_outline.escena.id,
        capitulo_id=obra_con_outline.capitulos[0].id,
        extraccion=EXTRACCION,
    )
    assert not consolidacion.vacia
    assert await sesion.scalar(select(func.count()).select_from(Evento)) == 1
