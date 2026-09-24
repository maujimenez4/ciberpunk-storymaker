"""RF-ENT-06 y regla de dominio 4: el canon nace antes del texto.

Los dos tests de esquema de la regla 4 —que la base rechaza `origen='escena'`
sin escena y `origen='brief'` con ella— son de la Tarea 4 y viven en
`test_esquema.py`. Aqui se comprueba lo otro: que el camino por el que de
verdad se escribe pone el origen correcto, no inventa escena, y **tampoco
puede esquivar** la restriccion aunque se le pida.
"""

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.obra.modelos import HechoCanon, Obra
from app.features.obra.repository import guardar_hechos_del_brief
from app.features.obra.schemas import HechoDelBrief
from app.features.obra.service import registrar_hechos_del_brief


async def test_un_hecho_del_brief_no_tiene_escena_de_origen(sesion: AsyncSession, obra: Obra):
    """RF-ENT-06 y regla 4: existia antes del texto, y no se inventa escena."""
    hechos = await guardar_hechos_del_brief(
        sesion, obra.id, [HechoDelBrief(entidad="perro", atributo="nombre", valor="Luna")]
    )
    assert hechos[0].origen == "brief"
    assert hechos[0].escena_de_origen is None
    assert hechos[0].obra_id == obra.id


async def test_cada_hecho_conserva_su_forma_y_su_orden(sesion: AsyncSession, obra: Obra):
    """`definitions.md` §4.5: un hecho es entidad + atributo + valor, no una frase.

    No es cosmetica. La regla de arbitraje del mismo §4.5 —«si dos hechos sobre
    el mismo ATRIBUTO difieren, prevalece el de menor orden_discurso»— no se
    puede implementar sobre una cadena libre: hay que poder comparar el atributo.
    Lo mismo el defecto CAN-01. Con `enunciado` eso era imposible.
    """
    hechos = await guardar_hechos_del_brief(
        sesion,
        obra.id,
        [
            HechoDelBrief(entidad="perro", atributo="nombre", valor="Luna"),
            HechoDelBrief(entidad="pareja", atributo="lugar_de_encuentro", valor="Cadiz"),
        ],
    )
    assert [(h.entidad, h.atributo, h.valor) for h in hechos] == [
        ("perro", "nombre", "Luna"),
        ("pareja", "lugar_de_encuentro", "Cadiz"),
    ]
    guardados = (await sesion.execute(select(HechoCanon).order_by(HechoCanon.id))).scalars().all()
    assert [g.atributo for g in guardados] == ["nombre", "lugar_de_encuentro"]


async def test_un_hecho_del_brief_nace_con_confianza_plena(sesion: AsyncSession, obra: Obra):
    """Lo dijo el comprador sobre una persona real: no hay nada que inferir."""
    hechos = await guardar_hechos_del_brief(
        sesion, obra.id, [HechoDelBrief(entidad="perro", atributo="nombre", valor="Luna")]
    )
    assert hechos[0].confianza == 1.0


async def test_el_repositorio_no_puede_esquivar_la_regla_4(sesion: AsyncSession, obra: Obra):
    """Pedirle 'escena' sin escena choca con el CheckConstraint de la Tarea 4.

    No basta con que el repositorio se porte bien: hay que comprobar que la
    base de datos lo sujeta aunque alguien lo llame mal desde otra ruta, que
    es exactamente lo que hara la Fase 2.
    """
    with pytest.raises(IntegrityError):
        await guardar_hechos_del_brief(
            sesion,
            obra.id,
            [HechoDelBrief(entidad="perro", atributo="nombre", valor="Luna")],
            origen="escena",
        )


async def test_una_lista_vacia_no_escribe_nada(sesion: AsyncSession, obra: Obra):
    """R-2: un TextoAportado en blanco no crea un hecho de canon vacio."""
    assert await guardar_hechos_del_brief(sesion, obra.id, []) == []
    assert (await sesion.execute(select(HechoCanon))).scalars().all() == []


async def test_un_hecho_en_blanco_no_llega_a_escribirse(sesion: AsyncSession, obra: Obra):
    """R-2, ahora en el esquema y no en el repositorio.

    Un valor vacio es subcadena de cualquier capitulo, asi que el validador de
    cobertura de la regla de dominio 11 lo daria por cubierto SIEMPRE, en todas
    las novelas. Antes lo filtraba el repositorio mirando `enunciado.strip()`;
    con la forma del documento lo para `HechoDelBrief` **antes**, porque sus
    tres campos son `TextoNoVacio`. Es mejor sitio: lo que no dice nada no
    llega a construirse.
    """
    with pytest.raises(ValidationError):
        HechoDelBrief(entidad="perro", atributo="nombre", valor="   ")
    with pytest.raises(ValidationError):
        HechoDelBrief(entidad="", atributo="nombre", valor="Luna")


async def test_el_caso_de_uso_escribe_los_hechos_del_brief_y_no_admite_otro_origen(
    sesion: AsyncSession, obra: Obra
):
    """El servicio es la frontera donde `origen` deja de ser un parametro.

    El repositorio lo acepta porque la Fase 2 escribira hechos de escena por
    ahi; el caso de uso de la entrevista, no. Es la via que usara el router de
    la Tarea 9, y por ella no se puede pedir un origen distinto de `brief`.
    """
    hechos = await registrar_hechos_del_brief(
        sesion, obra.id, [HechoDelBrief(entidad="perro", atributo="nombre", valor="Luna")]
    )
    assert [(h.origen, h.escena_de_origen) for h in hechos] == [("brief", None)]
    with pytest.raises(TypeError):
        await registrar_hechos_del_brief(
            sesion,
            obra.id,
            [HechoDelBrief(entidad="perro", atributo="nombre", valor="Luna")],
            origen="escena",  # type: ignore[call-arg]
        )
