"""P-20: tras un capitulo con intentos rechazados queda **con que decidir**.

En la primera corrida real el capitulo 1 escalo tras tres intentos con cero
texto y cero defectos guardados: `_retirar_lo_descartado` borra la prosa por
R-7 y los defectos nunca tuvieron tabla. No se distinguia «el modelo escribio
mal tres veces» de «un validador rechaza siempre».

La evidencia va **a otra tabla** (`intento_descartado`) y no deja de borrarse
la `version_texto`: tres lectores dependen de que lo vigente sea solo lo que
paso la puerta, y la evidencia no es un almacen de lectura.

Ninguna prueba llama al proveedor (CA-4): el cliente es `DobleDeterminista`.
"""

from sqlalchemy import func, select

from app.features.escritura.agents import MARCA_DE_REPARACION
from app.features.escritura.modelos import IntentoDescartado, VersionTexto
from app.features.escritura.tests.test_ciclo import (
    PROSA_BUENA,
    PROSA_CORTA,
    _agentes,
    _ciclo,
    _respuestas,
    obra_lista,  # noqa: F401  (fixture)
)


async def _contar(sesion, modelo, **filtro) -> int:
    consulta = select(func.count()).select_from(modelo)
    for columna, valor in filtro.items():
        consulta = consulta.where(getattr(modelo, columna) == valor)
    return int((await sesion.execute(consulta)).scalar_one())


async def test_la_evidencia_no_es_vigente_y_no_contamina_el_capitulo_siguiente(
    sesion,
    obra_lista,  # noqa: F811
):
    """R-7 sigue en pie: la `version_texto` de ese `run_id` queda a cero, y la
    evidencia vive aparte."""
    resultado = await _ciclo(sesion, obra_lista.capitulos[0].id, prosa=PROSA_CORTA)

    assert resultado.estado == "ESCALADA"
    assert await _contar(sesion, VersionTexto, run_id=resultado.run_id) == 0
    assert await _contar(sesion, IntentoDescartado, run_id=resultado.run_id) == 3
    assert await _contar(sesion, IntentoDescartado, trabajo_id=resultado.trabajo_id) == 3


async def test_un_capitulo_aprobado_tras_reparar_guarda_el_intento_que_se_rechazo(
    sesion,
    obra_lista,  # noqa: F811
):
    """La misma evidencia, aunque no escale: el *tuning* necesita tambien lo que
    se rechazo antes de aprobar. Y solo eso: el aprobado no es un descarte."""
    respuestas = {MARCA_DE_REPARACION: PROSA_BUENA, **_respuestas(PROSA_CORTA)}

    resultado = await _ciclo(sesion, obra_lista.capitulos[0].id, agentes=_agentes(respuestas))

    assert resultado.estado == "INTEGRADA"
    filas = (
        (
            await sesion.execute(
                select(IntentoDescartado).where(IntentoDescartado.run_id == resultado.run_id)
            )
        )
        .scalars()
        .all()
    )
    assert [f.numero for f in filas] == [1]
    assert filas[0].texto == PROSA_CORTA
    assert [d["codigo"] for d in filas[0].defectos] == ["EST-02"]
