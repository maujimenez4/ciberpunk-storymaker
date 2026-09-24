"""RF-ENT-06 y regla de dominio 4: el canon nace antes del texto.

Los dos tests de esquema de la regla 4 —que la base rechaza `origen='escena'`
sin escena y `origen='brief'` con ella— son de la Tarea 4 y viven en
`test_esquema.py`. Aqui se comprueba lo otro: que el camino por el que de
verdad se escribe pone el origen correcto, no inventa escena, y **tampoco
puede esquivar** la restriccion aunque se le pida.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.obra.modelos import HechoCanon, Obra
from app.features.obra.repository import guardar_hechos_del_brief
from app.features.obra.service import registrar_hechos_del_brief


async def test_un_hecho_del_brief_no_tiene_escena_de_origen(sesion: AsyncSession, obra: Obra):
    """RF-ENT-06 y regla 4: existia antes del texto, y no se inventa escena."""
    hechos = await guardar_hechos_del_brief(sesion, obra.id, ["El perro se llama Luna"])
    assert hechos[0].origen == "brief"
    assert hechos[0].escena_de_origen is None
    assert hechos[0].obra_id == obra.id


async def test_cada_enunciado_es_un_hecho_y_conserva_el_orden(sesion: AsyncSession, obra: Obra):
    hechos = await guardar_hechos_del_brief(
        sesion, obra.id, ["El perro se llama Luna", "Se conocieron en Cadiz"]
    )
    assert [h.enunciado for h in hechos] == [
        "El perro se llama Luna",
        "Se conocieron en Cadiz",
    ]
    guardados = (await sesion.execute(select(HechoCanon).order_by(HechoCanon.id))).scalars().all()
    assert [h.enunciado for h in guardados] == [
        "El perro se llama Luna",
        "Se conocieron en Cadiz",
    ]


async def test_el_repositorio_no_puede_esquivar_la_regla_4(sesion: AsyncSession, obra: Obra):
    """Pedirle 'escena' sin escena choca con el CheckConstraint de la Tarea 4.

    No basta con que el repositorio se porte bien: hay que comprobar que la
    base de datos lo sujeta aunque alguien lo llame mal desde otra ruta, que
    es exactamente lo que hara la Fase 2.
    """
    with pytest.raises(IntegrityError):
        await guardar_hechos_del_brief(sesion, obra.id, ["x"], origen="escena")


async def test_una_lista_vacia_no_escribe_nada(sesion: AsyncSession, obra: Obra):
    """R-2: un TextoAportado en blanco no crea un hecho de canon vacio."""
    assert await guardar_hechos_del_brief(sesion, obra.id, []) == []
    assert (await sesion.execute(select(HechoCanon))).scalars().all() == []


async def test_un_enunciado_en_blanco_no_crea_un_hecho_vacio(sesion: AsyncSession, obra: Obra):
    """R-2 otra vez, por el otro lado: la lista trae algo, y ese algo no dice nada.

    Un enunciado vacio es subcadena de cualquier capitulo, asi que el validador
    de cobertura de la regla 11 lo daria por cubierto siempre. Es el mismo
    defecto que R-6 caza en `elementos_obligatorios`.
    """
    hechos = await guardar_hechos_del_brief(
        sesion, obra.id, ["", "   \n", "Se conocieron en Cadiz"]
    )
    assert [h.enunciado for h in hechos] == ["Se conocieron en Cadiz"]
    guardados = (await sesion.execute(select(HechoCanon))).scalars().all()
    assert len(guardados) == 1


async def test_el_caso_de_uso_escribe_los_hechos_del_brief_y_no_admite_otro_origen(
    sesion: AsyncSession, obra: Obra
):
    """El servicio es la frontera donde `origen` deja de ser un parametro.

    El repositorio lo acepta porque la Fase 2 escribira hechos de escena por
    ahi; el caso de uso de la entrevista, no. Es la via que usara el router de
    la Tarea 9, y por ella no se puede pedir un origen distinto de `brief`.
    """
    hechos = await registrar_hechos_del_brief(sesion, obra.id, ["El perro se llama Luna"])
    assert [(h.origen, h.escena_de_origen) for h in hechos] == [("brief", None)]
    with pytest.raises(TypeError):
        await registrar_hechos_del_brief(sesion, obra.id, ["x"], origen="escena")  # type: ignore[call-arg]
