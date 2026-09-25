"""Regenerar un capitulo ya integrado (plan 5, T3): R-6, J-1, J-2 y J-4.

La regeneracion escribe prosa y **no** toca memoria de largo plazo hasta que
quien decide la consolida. Ninguna prueba llama al proveedor (CA-4).
"""

from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.jobs.turnos import CerrojoDeEscena, PresupuestoConcurrente
from app.features.escritura import (
    CapituloNoIntegrado,
    ResultadoDelCiclo,
    consolidar_la_regeneracion,
    ejecutar_ciclo,
    regenerar_capitulo,
    reparaciones_de_la_regeneracion,
    reparaciones_del_capitulo,
    retirar_prosa_de_la_corrida,
)
from app.features.escritura.modelos import Trabajo
from app.features.escritura.tests.test_ciclo import (
    ContadorDePalabras,
    _agentes,
    _ciclo,
    _respuestas,
    obra_lista,  # noqa: F401 -- fixture
)


def _ejecutar(sesion: AsyncSession, capitulo_id: int) -> Any:
    agentes = _agentes(_respuestas())

    async def ejecutar(trabajo: Trabajo, *, consolidar: bool) -> ResultadoDelCiclo:
        return await ejecutar_ciclo(
            sesion,
            trabajo,
            capitulo_id=capitulo_id,
            agentes=agentes,
            contador=ContadorDePalabras(),
            presupuesto=PresupuestoConcurrente(),
            cerrojo=CerrojoDeEscena(),
            consolidar=consolidar,
        )

    return ejecutar


async def _censo(sesion: AsyncSession, escena_id: int) -> tuple[int, int, int, int]:
    """Canon, ledger, indice y uso: lo que una regeneracion descartada no toca."""

    async def cuantas(sql: str) -> int:
        return int((await sesion.execute(text(sql), {"e": escena_id})).scalar_one())

    return (
        await cuantas("SELECT COUNT(*) FROM hecho_canon WHERE escena_de_origen = CAST(:e AS TEXT)"),
        await cuantas("SELECT COUNT(*) FROM evento WHERE escena_id = :e"),
        await cuantas("SELECT COUNT(*) FROM embedding WHERE escena_id = :e"),
        await cuantas("SELECT COUNT(*) FROM hilo_narrativo WHERE escena_de_apertura = :e"),
    )


@pytest.fixture
async def integrado(sesion: AsyncSession, obra_lista: Any) -> Any:  # noqa: F811
    capitulo = obra_lista.capitulos[0]
    resultado = await _ciclo(sesion, capitulo.id)
    assert resultado.estado == "INTEGRADA"
    escena_id = (
        await sesion.execute(
            text("SELECT id FROM escena WHERE capitulo_id = :c"), {"c": capitulo.id}
        )
    ).scalar_one()
    return obra_lista, capitulo, int(escena_id), resultado


async def test_el_ciclo_escribe_el_canon_con_el_run_id_de_su_corrida(
    sesion: AsyncSession, integrado: Any
) -> None:
    """J-1: sin el `run_id` en las filas, los rastros de P-6 no encuentran nada."""
    _, _, escena_id, resultado = integrado
    run_ids = set(
        (
            await sesion.execute(
                text("SELECT run_id FROM hecho_canon WHERE escena_de_origen = CAST(:e AS TEXT)"),
                {"e": escena_id},
            )
        )
        .scalars()
        .all()
    ) | set(
        (
            await sesion.execute(
                text("SELECT run_id FROM evento WHERE escena_id = :e"), {"e": escena_id}
            )
        )
        .scalars()
        .all()
    )
    assert run_ids == {resultado.run_id}


async def test_una_regeneracion_descartada_no_deja_rastro(
    sesion: AsyncSession, integrado: Any
) -> None:
    """R-6 y RF-PET-07. Lo que no se publica no contamina canon ni manuscrito."""
    obra, capitulo, escena_id, _ = integrado
    vigente_antes = (
        await sesion.execute(
            text("SELECT id FROM version_texto WHERE escena_id = :e AND vigente = 1"),
            {"e": escena_id},
        )
    ).scalar_one()
    antes = await _censo(sesion, escena_id)

    resultado = await regenerar_capitulo(
        sesion,
        obra_id=obra.obra.id,
        capitulo_id=capitulo.id,
        ejecutar=_ejecutar(sesion, capitulo.id),
    )
    assert resultado.escritura is not None and resultado.escritura.aprobado
    assert resultado.consolidacion is None
    assert resultado.extraccion is not None
    assert await _censo(sesion, escena_id) == antes, "la regeneracion consolido sin permiso"

    await retirar_prosa_de_la_corrida(sesion, escena_id=escena_id, run_id=resultado.run_id)

    assert await _censo(sesion, escena_id) == antes
    vigentes = (
        (
            await sesion.execute(
                text("SELECT id FROM version_texto WHERE escena_id = :e AND vigente = 1"),
                {"e": escena_id},
            )
        )
        .scalars()
        .all()
    )
    assert vigentes == [vigente_antes], "la escena tiene que volver a la version entregada"


async def test_una_regeneracion_que_prospera_si_consolida_sobre_lo_consolidado(
    sesion: AsyncSession, integrado: Any
) -> None:
    """P-6 y P-7 juntos: la corrida nueva escribe canon y el resumen se sobrescribe."""
    obra, capitulo, escena_id, _ = integrado
    hechos_antes = (await _censo(sesion, escena_id))[0]

    resultado = await regenerar_capitulo(
        sesion,
        obra_id=obra.obra.id,
        capitulo_id=capitulo.id,
        ejecutar=_ejecutar(sesion, capitulo.id),
    )
    consolidacion = await consolidar_la_regeneracion(
        sesion,
        resultado=resultado,
        obra_id=obra.obra.id,
        escena_id=escena_id,
        capitulo_id=capitulo.id,
    )

    assert not consolidacion.vacia
    assert (await _censo(sesion, escena_id))[0] > hechos_antes
    resumen = (
        await sesion.execute(
            text("SELECT version_texto_id FROM resumen_capitulo WHERE capitulo_id = :c"),
            {"c": capitulo.id},
        )
    ).all()
    assert resumen == [(resultado.escritura.version_texto_id,)]  # type: ignore[union-attr]


async def test_no_se_regenera_un_capitulo_que_no_esta_integrado(
    sesion: AsyncSession,
    obra_lista: Any,  # noqa: F811
) -> None:
    with pytest.raises(CapituloNoIntegrado):
        await regenerar_capitulo(
            sesion,
            obra_id=obra_lista.obra.id,
            capitulo_id=obra_lista.capitulos[1].id,
            ejecutar=_ejecutar(sesion, obra_lista.capitulos[1].id),
        )


async def test_la_regeneracion_no_hereda_las_reparaciones_del_capitulo(
    sesion: AsyncSession,
    obra_lista: Any,  # noqa: F811
) -> None:
    """Un capitulo que costo dos reparaciones al escribirse no empieza su
    regeneracion con las dos gastadas; dos regeneraciones si se cuentan."""
    obra_id = obra_lista.obra.id
    capitulo_id = obra_lista.capitulos[0].id

    def trabajo(run_id: str, intento: int, estado: str) -> Trabajo:
        return Trabajo(
            obra_id=obra_id,
            capitulo_id=capitulo_id,
            tipo="escribir_escena",
            estado=estado,
            intento=intento,
            run_id=run_id,
        )

    sesion.add(trabajo("cap1-trb90", 2, "INTEGRADA"))
    await sesion.flush()
    assert (
        await reparaciones_de_la_regeneracion(sesion, obra_id=obra_id, capitulo_id=capitulo_id) == 0
    )
    assert await reparaciones_del_capitulo(sesion, obra_id=obra_id, capitulo_id=capitulo_id) == 2

    sesion.add(trabajo("reg-cap1-trb91", 1, "ESCALADA"))
    await sesion.flush()
    assert (
        await reparaciones_de_la_regeneracion(sesion, obra_id=obra_id, capitulo_id=capitulo_id) == 1
    )
