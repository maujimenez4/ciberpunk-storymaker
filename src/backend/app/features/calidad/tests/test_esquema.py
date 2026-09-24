"""Fase 6 · T2 · Las tablas del juicio, y las invariantes que guardan.

**Lo que se comprueba aqui son invariantes de datos, no de prompt.** Que el juez
justifique lo que puntua es `R-4`, y pedirselo en la plantilla lo deja como un
deseo: lo que lo hace cierto es que la fila **no entre** sin justificacion. La
diferencia se nota el dia que el modelo devuelve una puntuacion sola.
"""

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.calidad.modelos import (
    AceptacionDeEntrega,
    CriterioDeRubrica,
    Puntuacion,
    RevisionHumana,
    Rubrica,
)


async def test_las_cinco_tablas_del_juicio_existen(sesion: AsyncSession) -> None:
    tablas = await sesion.run_sync(lambda s: set(inspect(s.bind).get_table_names()))

    assert {
        "rubrica",
        "criterio_de_rubrica",
        "puntuacion",
        "revision_humana",
        "aceptacion_de_entrega",
    } <= tablas


async def test_una_puntuacion_de_juicio_sin_justificacion_no_entra(
    sesion: AsyncSession,
) -> None:
    """`R-4`. El juez puntua **y justifica**, o no puntua.

    Es el test que abre la tarea, y su forma importa: no comprueba que la
    plantilla pida una justificacion, comprueba que la base **rechaza** la fila
    que no la trae.
    """
    rubrica = Rubrica(version="v1", escala_minimo=1, escala_maximo=5)
    sesion.add(rubrica)
    await sesion.flush()
    criterio = CriterioDeRubrica(
        rubrica_id=rubrica.rubrica_id,
        nombre="voz",
        definicion="La voz del narrador se sostiene de principio a fin.",
        ancla_minimo="Cambia de registro entre parrafos.",
        ancla_maximo="Un lector no notaria que la escribio una maquina.",
    )
    sesion.add(criterio)
    await sesion.flush()

    sesion.add(
        Puntuacion(
            validador="juez_con_rubrica",
            unidad="capitulo",
            unidad_id="1",
            valor=4.0,
            criterio_id=criterio.criterio_id,
            justificacion=None,
            origen="juez",
        )
    )

    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_una_justificacion_en_blanco_tampoco(sesion: AsyncSession) -> None:
    """Un espacio no es una justificacion, y sin esto la restriccion se cumple
    escribiendo `" "`. Es la diferencia entre comprobar y aparentar."""
    rubrica = Rubrica(version="v1", escala_minimo=1, escala_maximo=5)
    sesion.add(rubrica)
    await sesion.flush()
    criterio = CriterioDeRubrica(
        rubrica_id=rubrica.rubrica_id,
        nombre="voz",
        definicion="d",
        ancla_minimo="a",
        ancla_maximo="b",
    )
    sesion.add(criterio)
    await sesion.flush()

    sesion.add(
        Puntuacion(
            validador="juez_con_rubrica",
            unidad="capitulo",
            unidad_id="1",
            valor=4.0,
            criterio_id=criterio.criterio_id,
            justificacion="   ",
            origen="juez",
        )
    )

    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_un_score_mecanico_no_necesita_justificacion(sesion: AsyncSession) -> None:
    """El control negativo, y es el que impide que la restriccion se vuelva
    insufrible: `extension_de_capitulo` cuenta palabras y no tiene nada que
    justificar. La misma tabla guarda los dos, que es lo que permite leer la
    distancia del juez y los *scores* mecanicos del mismo sitio."""
    sesion.add(
        Puntuacion(
            validador="extension_de_capitulo",
            unidad="capitulo",
            unidad_id="1",
            valor=1.0,
            criterio_id=None,
            justificacion=None,
            origen="programatico",
        )
    )

    await sesion.flush()

    guardadas = (await sesion.execute(select(Puntuacion))).scalars().all()
    assert [p.origen for p in guardadas] == ["programatico"]


async def test_el_origen_distingue_los_cuatro_tipos(sesion: AsyncSession) -> None:
    """Sin `origen`, la distancia del juez sumaria los *scores* mecanicos."""
    for origen in ("juez", "humana", "programatico", "formal"):
        sesion.add(
            Puntuacion(
                validador=f"v-{origen}",
                unidad="novela",
                unidad_id="1",
                valor=3.0,
                origen=origen,
            )
        )
    await sesion.flush()

    guardadas = (await sesion.execute(select(Puntuacion))).scalars().all()
    assert {p.origen for p in guardadas} == {"juez", "humana", "programatico", "formal"}


async def test_un_origen_inventado_no_entra(sesion: AsyncSession) -> None:
    sesion.add(
        Puntuacion(validador="v", unidad="novela", unidad_id="1", valor=3.0, origen="opinion")
    )

    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_los_anclajes_de_un_criterio_son_obligatorios(sesion: AsyncSession) -> None:
    """«Una rubrica sin anclajes descritos no es una rubrica, es una escala»."""
    rubrica = Rubrica(version="v1", escala_minimo=1, escala_maximo=5)
    sesion.add(rubrica)
    await sesion.flush()

    sesion.add(
        CriterioDeRubrica(
            rubrica_id=rubrica.rubrica_id,
            nombre="voz",
            definicion="d",
            ancla_minimo=None,
            ancla_maximo="b",
        )
    )

    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_la_rubrica_se_versiona_y_su_version_es_unica(sesion: AsyncSession) -> None:
    """`definitions.md` §8: cambiar un criterio invalida la comparacion con las
    puntuaciones anteriores, asi que la version es la que las separa."""
    sesion.add(Rubrica(version="v1", escala_minimo=1, escala_maximo=5))
    await sesion.flush()
    sesion.add(Rubrica(version="v1", escala_minimo=1, escala_maximo=5))

    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_la_aceptacion_del_comprador_no_es_una_puntuacion(
    sesion: AsyncSession,
) -> None:
    """`R-7`, y la separacion es lo que lo hace comprobable en vez de prometido.

    De un si o un no **no sale una distancia** (P-05): el Comprador acepta o
    rechaza, y quien revisa con rubrica es el Autor. Estando en otra tabla, no
    hay ninguna consulta de distancia que pueda alcanzarla por accidente.
    """
    columnas = await sesion.run_sync(
        lambda s: {c["name"] for c in inspect(s.bind).get_columns("aceptacion_de_entrega")}
    )

    assert "aceptada" in columnas
    assert "valor" not in columnas, "una aceptacion no tiene escala"

    puntuacion = await sesion.run_sync(
        lambda s: {c["name"] for c in inspect(s.bind).get_columns("puntuacion")}
    )
    assert "aceptada" not in puntuacion


async def test_la_revision_humana_guarda_quien_y_cuando(sesion: AsyncSession) -> None:
    """El revisor es **el Autor** (P-05). Sin `revisor` y `fecha`, la
    correlacion que `RF-JUZ-06` exige medir no se podria auditar despues."""
    columnas = await sesion.run_sync(
        lambda s: {c["name"] for c in inspect(s.bind).get_columns("revision_humana")}
    )

    assert {"obra_id", "rubrica_id", "revisor", "fecha"} <= columnas


async def test_ejecucion_tiene_latencia(sesion: AsyncSession) -> None:
    """RF-OBS-03 pide tokens, coste **y latencia** por llamada.

    Los dos primeros ya salen de `ejecucion`. Si la latencia saliera solo de
    Langfuse, el numero **dejaria de existir cuando el servicio no responde**,
    que es exactamente `R-1`: las tres salen del mismo sitio o ninguna.
    """
    columnas = await sesion.run_sync(
        lambda s: {c["name"] for c in inspect(s.bind).get_columns("ejecucion")}
    )

    assert "latencia_ms" in columnas


async def test_la_aceptacion_apunta_a_una_version_publicada(sesion: AsyncSession) -> None:
    claves = await sesion.run_sync(
        lambda s: inspect(s.bind).get_foreign_keys("aceptacion_de_entrega")
    )

    assert any(c["referred_table"] == "version_publicada" for c in claves)


async def test_una_revision_sin_revisor_no_entra(sesion: AsyncSession) -> None:
    rubrica = Rubrica(version="v1", escala_minimo=1, escala_maximo=5)
    sesion.add(rubrica)
    await sesion.flush()

    sesion.add(RevisionHumana(obra_id=1, rubrica_id=rubrica.rubrica_id, revisor=None))

    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_una_aceptacion_es_un_booleano_y_no_admite_nulo(
    sesion: AsyncSession,
) -> None:
    sesion.add(AceptacionDeEntrega(version_publicada_id=1, aceptada=None))

    with pytest.raises(IntegrityError):
        await sesion.flush()
