"""Preexistente o introducido (plan-5 T5, RF-PET-05, RF-PET-06, R-2)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.conftest import ObraConOutline
from app.features.calidad import Defecto
from app.features.manuscrito import clasificar_contra_el_cuadro, cuadro_guardado, publicar
from app.features.manuscrito.tests.test_publicar import _integrar


def test_un_defecto_preexistente_lo_sigue_siendo_aunque_el_texto_sea_nuevo() -> None:
    """R-2 y CA-25. El capitulo se regenero: otro `version_texto_id` y otro
    desplazamiento. Si la huella los arrastrara, saldria «introducido»."""
    del_cuadro = Defecto(
        codigo="VOZ-02",
        version_texto_id="41",
        cita="dijo ella, secamente",
        desplazamiento_inicio=120,
        desplazamiento_fin=140,
    )
    tras_regenerar = Defecto(
        codigo="VOZ-02",
        version_texto_id="87",
        cita="dijo ella,\nsecamente",
        desplazamiento_inicio=95,
        desplazamiento_fin=115,
    )

    clasificacion = clasificar_contra_el_cuadro(
        hallados=[(7, tras_regenerar)], cuadro=[(7, del_cuadro)]
    )

    assert clasificacion.preexistentes == (tras_regenerar,)
    assert clasificacion.introducidos == ()
    assert clasificacion.impide_publicar is False


def test_un_defecto_que_no_estaba_en_el_cuadro_es_introducido_e_impide_publicar() -> None:
    nuevo = Defecto(
        codigo="CAN-01",
        version_texto_id="87",
        cita="el perro Luna ladro",
        desplazamiento_inicio=10,
        desplazamiento_fin=29,
        hecho_canon_id="14",
    )

    clasificacion = clasificar_contra_el_cuadro(hallados=[(7, nuevo)], cuadro=[])

    assert clasificacion.introducidos == (nuevo,)
    assert clasificacion.impide_publicar is True


def test_el_mismo_codigo_en_otro_capitulo_no_se_da_por_conocido() -> None:
    """Sin el capitulo en la huella, una muletilla marcada en el 3 taparia la del 8."""
    en_el_3 = Defecto(
        codigo="VOZ-01",
        version_texto_id="12",
        cita="dijo ella",
        desplazamiento_inicio=0,
        desplazamiento_fin=9,
    )
    en_el_8 = Defecto(
        codigo="VOZ-01",
        version_texto_id="44",
        cita="dijo ella",
        desplazamiento_inicio=0,
        desplazamiento_fin=9,
    )

    clasificacion = clasificar_contra_el_cuadro(hallados=[(8, en_el_8)], cuadro=[(3, en_el_3)])

    assert clasificacion.introducidos == (en_el_8,)


async def test_el_cuadro_guardado_al_publicar_se_relee_con_su_capitulo(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """La juntura con T7: lo que `publicar` guarda es lo que se clasifica despues,
    y la cobertura que va en el mismo cuadro no se cuela como defecto."""
    await _integrar(sesion, obra_con_outline)
    vigente = Defecto(
        codigo="VOZ-02",
        version_texto_id="3",
        cita="dijo ella",
        desplazamiento_inicio=0,
        desplazamiento_fin=9,
    )

    version = await publicar(sesion, obra_con_outline.obra.id, defectos_vigentes=[(2, vigente)])

    assert await cuadro_guardado(sesion, version_publicada_id=version.id) == [(2, vigente)]
