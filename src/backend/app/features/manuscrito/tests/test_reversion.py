"""Revertir, y quien es la vigente (plan-5 T6, RF-PET-08, RI-10)."""

from dataclasses import dataclass

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.conftest import ObraConOutline
from app.features.manuscrito import (
    VersionDesconocida,
    VersionYaVigente,
    publicar,
    revertir,
    version_vigente,
)
from app.features.manuscrito.modelos import VersionPublicada
from app.features.manuscrito.tests.test_publicar import _instantanea, _integrar, _regenerar


@dataclass
class DosVersiones:
    obra_id: int
    primera: VersionPublicada
    segunda: VersionPublicada


@pytest.fixture
async def dos_versiones(sesion: AsyncSession, obra_con_outline: ObraConOutline) -> DosVersiones:
    await _integrar(sesion, obra_con_outline)
    primera = await publicar(sesion, obra_con_outline.obra.id)
    await _regenerar(sesion, obra_con_outline, numero=4, texto="Capitulo 4, reescrito.")
    segunda = await publicar(sesion, obra_con_outline.obra.id)
    return DosVersiones(obra_con_outline.obra.id, primera, segunda)


async def test_revertir_devuelve_la_anterior_y_no_borra_la_revertida(
    sesion: AsyncSession, dos_versiones: DosVersiones
) -> None:
    """RF-PET-08 y RF-PUB-02: lo unico que cambia es la bandera."""
    primera, segunda = dos_versiones.primera, dos_versiones.segunda
    antes = (await _instantanea(sesion, primera.id), await _instantanea(sesion, segunda.id))

    vuelta = await revertir(sesion, obra_id=dos_versiones.obra_id, version_publicada_id=primera.id)

    assert vuelta.id == primera.id and vuelta.vigente is True
    recargada = await sesion.get(VersionPublicada, segunda.id, populate_existing=True)
    assert recargada is not None, "la revertida se borro"
    assert recargada.vigente is False
    assert (await _instantanea(sesion, primera.id), await _instantanea(sesion, segunda.id)) == antes


async def test_la_vigente_no_es_la_de_mayor_ordinal_despues_de_revertir(
    sesion: AsyncSession, dos_versiones: DosVersiones
) -> None:
    """La razon entera de que `vigente` sea una columna y no una deduccion."""
    await revertir(
        sesion, obra_id=dos_versiones.obra_id, version_publicada_id=dos_versiones.primera.id
    )

    vigente = await version_vigente(sesion, obra_id=dos_versiones.obra_id)
    assert vigente is not None and vigente.id == dos_versiones.primera.id
    assert vigente.ordinal < dos_versiones.segunda.ordinal


async def test_revertir_a_la_vigente_se_rechaza(
    sesion: AsyncSession, dos_versiones: DosVersiones
) -> None:
    with pytest.raises(VersionYaVigente):
        await revertir(
            sesion, obra_id=dos_versiones.obra_id, version_publicada_id=dos_versiones.segunda.id
        )


async def test_no_se_revierte_a_la_version_de_otra_obra(
    sesion: AsyncSession, dos_versiones: DosVersiones
) -> None:
    with pytest.raises(VersionDesconocida):
        await revertir(
            sesion,
            obra_id=dos_versiones.obra_id + 1,
            version_publicada_id=dos_versiones.primera.id,
        )
