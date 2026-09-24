"""El esquema de `outline`: la biblia versionada y los diez capitulos."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.features.outline.modelos import Capitulo, VersionObra
from app.features.outline.schemas import BeatDeGenero


async def test_una_version_de_obra_congela_la_biblia(sesion, obra):
    """RF-PLA-01: la biblia es versionada, y una version es un estado congelado."""
    sesion.add(VersionObra(obra_id=obra.id, numero=1, biblia={"protagonista": "Nadia"}))
    await sesion.flush()
    guardadas = (await sesion.execute(select(VersionObra))).scalars().all()
    assert [(v.numero, v.biblia) for v in guardadas] == [(1, {"protagonista": "Nadia"})]


async def test_dos_versiones_de_obra_no_repiten_numero(sesion, obra):
    """Sin esto, «la version 2 de la biblia» deja de nombrar una sola cosa."""
    sesion.add_all(
        [
            VersionObra(obra_id=obra.id, numero=1, biblia={}),
            VersionObra(obra_id=obra.id, numero=1, biblia={}),
        ]
    )
    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_el_outline_tiene_diez_capitulos(sesion, obra):
    """RF-PLA-02, la mitad que el esquema sostiene: los diez caben y se leen por numero."""
    sesion.add_all([_capitulo(obra.id, n) for n in range(1, 11)])
    await sesion.flush()
    guardados = (await sesion.execute(select(Capitulo))).scalars().all()
    assert sorted(c.numero for c in guardados) == list(range(1, 11))


async def test_dos_capitulos_no_comparten_numero_en_la_misma_obra(sesion, obra):
    """«El capitulo 4» tiene que nombrar uno solo: el outline se lee por numero."""
    sesion.add_all([_capitulo(obra.id, 4), _capitulo(obra.id, 4)])
    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_un_capitulo_fuera_del_rango_de_extension_no_entra(sesion, obra):
    """`definitions.md` §4.1 fija 1.000-1.500 palabras por capitulo."""
    sesion.add(_capitulo(obra.id, 1, extension_objetivo=4000))
    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_un_capitulo_guarda_su_beat_de_genero(sesion, obra):
    """`CA-32` dejaba de estar cerrado justo aqui: el Arquitecto asignaba el
    beat, `_comprobar_beats` lo validaba **sobre su salida**, y la columna no
    existia, asi que se tiraba al guardar. El Planificador lo volvia a decidir:
    dos verdades para el mismo hecho."""
    sesion.add(_capitulo(obra.id, 1, beat_de_genero=BeatDeGenero.ENCUENTRO.value))
    await sesion.flush()

    guardado = (await sesion.execute(select(Capitulo))).scalars().one()
    assert guardado.beat_de_genero == "encuentro"


async def test_un_capitulo_sin_beat_de_genero_sigue_siendo_valido(sesion, obra):
    """`definitions.md` §4.1 da cardinalidad 0..1: hay capitulos que no cargan
    ningun hito, y la columna no puede exigirlo."""
    sesion.add(_capitulo(obra.id, 1))
    await sesion.flush()

    assert (await sesion.execute(select(Capitulo))).scalars().one().beat_de_genero is None


async def test_un_beat_de_genero_inventado_no_entra(sesion, obra):
    """El conjunto de los diez es cerrado (`definitions.md` §6). Lo para el
    esquema del Arquitecto, y lo para tambien la base: un beat escrito por otra
    ruta -- el Planificador, una migracion de datos -- no tendria quien lo
    parase, y es el mismo motivo que el `ambito` de `palabra_prohibida`."""
    sesion.add(_capitulo(obra.id, 1, beat_de_genero="escena_de_persecucion"))
    with pytest.raises(IntegrityError):
        await sesion.flush()


def _capitulo(
    obra_id: int,
    numero: int,
    extension_objetivo: int = 1200,
    beat_de_genero: str | None = None,
) -> Capitulo:
    return Capitulo(
        lugar="Cadiz",
        objetivo="Encontrarla",
        obstaculo="Nadie recuerda",
        giro_de_valor_previsto="a -> b",
        obra_id=obra_id,
        numero=numero,
        titulo=f"Capitulo {numero}",
        pov_dominante="Nadia",
        gancho_de_apertura="La puerta estaba abierta",
        tipo_de_corte_final="pregunta",
        extension_objetivo=extension_objetivo,
        beat_de_genero=beat_de_genero,
    )
