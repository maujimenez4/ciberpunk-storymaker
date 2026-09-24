"""`CA-21`: Lean **detiene** la publicacion. T8.

T5 hizo que Lean **diga** que una cronologia esta rota. Esto hace que eso
**impida publicar**, que es lo que el encargo exige y son cosas distintas: un
validador que detecta y no bloquea produce informes que nadie lee.

La otra mitad, y la que de verdad prueba algo: **con una cronologia rota no se
publica nada**. Una puerta que no se ha visto cerrar no es una puerta.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conftest import ObraConOutline
from app.features.canon.modelos import Evento
from app.features.manuscrito import (
    CronologiaIncoherente,
    HerramientaNoDisponible,
    publicar,
)
from app.features.manuscrito.lean import ruta_de_lean

# El **modelo**, no el esquema: desde T9 `VersionPublicada` en la puerta de la
# feature es el modelo de salida de la API, y la tabla vive en `modelos`.
from app.features.manuscrito.modelos import VersionPublicada
from app.features.manuscrito.tests.test_publicar import _integrar

hay_lean = pytest.mark.skipif(
    ruta_de_lean() is None, reason="Lean 4 no esta instalado en esta maquina"
)


async def _romper_la_cronologia(sesion: AsyncSession, obra_id: int) -> None:
    """Marta, en dos sitios en el mismo momento. El caso literal de `CA-21`."""
    for lugar in ("la cocina", "la playa"):
        sesion.add(
            Evento(
                obra_id=obra_id,
                descripcion="pasa algo",
                tiempo_historia="la manana del 3",
                lugar=lugar,
                participantes=["Marta"],
            )
        )
    await sesion.flush()


async def _cuantas(sesion: AsyncSession, obra_id: int) -> int:
    filas = (
        await sesion.execute(select(VersionPublicada.id).where(VersionPublicada.obra_id == obra_id))
    ).all()
    return len(filas)


@hay_lean
async def test_con_la_cronologia_coherente_se_publica(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """La puerta tiene que **dejar pasar** lo bueno.

    Sin este test, una puerta que rechazara siempre pasaria el siguiente y
    nadie podria publicar nunca.
    """
    await _integrar(sesion, obra_con_outline)

    version = await publicar(sesion, obra_con_outline.obra.id)

    assert version.ordinal == 1
    assert await _cuantas(sesion, obra_con_outline.obra.id) == 1


@hay_lean
async def test_si_lean_falla_la_version_no_se_publica(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """`CA-21` entero: **no basta con que Lean lo detecte**."""
    await _integrar(sesion, obra_con_outline)
    await _romper_la_cronologia(sesion, obra_con_outline.obra.id)

    with pytest.raises(CronologiaIncoherente):
        await publicar(sesion, obra_con_outline.obra.id)

    assert await _cuantas(sesion, obra_con_outline.obra.id) == 0


@hay_lean
async def test_el_fallo_vuelve_al_editor_con_el_evento_concreto(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """RF-FOR-03: «el fallo vuelve al editor como feedback».

    Con el nombre y los dos lugares. «La cronologia no es coherente» a secas
    obliga a abrir la base para saber que arreglar.
    """
    await _integrar(sesion, obra_con_outline)
    await _romper_la_cronologia(sesion, obra_con_outline.obra.id)

    with pytest.raises(CronologiaIncoherente) as fallo:
        await publicar(sesion, obra_con_outline.obra.id)

    mensaje = str(fallo.value)
    assert "Marta" in mensaje
    assert "la cocina" in mensaje and "la playa" in mensaje


async def test_sin_lean_no_se_publica_y_el_error_dice_que_falta(
    sesion: AsyncSession,
    obra_con_outline: ObraConOutline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R-7. Y **tampoco se publica**: sin verificar no se entrega.

    Que falte la herramienta no puede degradar a «pues publicamos sin
    comprobar». La verificacion formal es eliminatoria del encargo.
    """
    await _integrar(sesion, obra_con_outline)
    monkeypatch.setattr("app.features.manuscrito.lean.corredor.ruta_de_lean", lambda: None)

    with pytest.raises(HerramientaNoDisponible, match="elan"):
        await publicar(sesion, obra_con_outline.obra.id)

    assert await _cuantas(sesion, obra_con_outline.obra.id) == 0


@hay_lean
async def test_la_puerta_corre_antes_de_escribir_nada(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """Ni una fila a medias.

    `publicar` ya es atomico por su SAVEPOINT, pero verificar **antes** de
    empezar a escribir es mas barato y deja el fallo mas claro: no hay nada que
    deshacer.
    """
    await _integrar(sesion, obra_con_outline)
    await _romper_la_cronologia(sesion, obra_con_outline.obra.id)

    with pytest.raises(CronologiaIncoherente):
        await publicar(sesion, obra_con_outline.obra.id)

    from app.features.manuscrito.modelos import CapituloPublicado

    capitulos = (await sesion.execute(select(CapituloPublicado.id))).all()
    assert capitulos == []
