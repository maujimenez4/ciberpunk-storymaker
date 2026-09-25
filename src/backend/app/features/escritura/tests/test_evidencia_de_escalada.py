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

import pytest
from sqlalchemy import func, select

from app.commons.llm.doble import DobleDeterminista
from app.features.calidad import Critico, rubrica_vigente
from app.features.canon.agents import Extractor
from app.features.escena.agents import Planificador
from app.features.escritura.agents import MARCA_DE_REPARACION, Escritor
from app.features.escritura.ciclo import Agentes
from app.features.escritura.modelos import IntentoDescartado, VersionTexto
from app.features.escritura.tests.test_ciclo import (
    PROSA_BUENA,
    PROSA_CORTA,
    _agentes,
    _ciclo,
    _respuestas,
    obra_lista,  # noqa: F401  (fixture)
)
from app.features.outline.modelos import Capitulo


@pytest.fixture
def respuestas_del_modelo() -> dict[str, str]:
    """El Escritor devuelve siempre trece palabras: `EST-02` en cada vuelta."""
    return _respuestas(PROSA_CORTA)


async def _contar(sesion, modelo, **filtro) -> int:
    consulta = select(func.count()).select_from(modelo)
    for columna, valor in filtro.items():
        consulta = consulta.where(getattr(modelo, columna) == valor)
    return int((await sesion.execute(consulta)).scalar_one())


async def test_un_capitulo_escalado_deja_sus_tres_intentos_con_sus_defectos(cliente, sesion, obra):
    """Por HTTP y con los cinco roles, que es el camino de la corrida real."""
    assert cliente.post(f"/obras/{obra.id}/outline").status_code == 201
    capitulo_id = (
        await sesion.execute(
            select(Capitulo.id).where(Capitulo.obra_id == obra.id, Capitulo.numero == 1)
        )
    ).scalar_one()
    trabajo_id = cliente.post(f"/capitulos/{capitulo_id}/escribir").json()["id"]
    assert cliente.get(f"/trabajos/{trabajo_id}").json()["estado"] == "ESCALADA"

    respuesta = cliente.get(f"/trabajos/{trabajo_id}/intentos")

    assert respuesta.status_code == 200
    intentos = respuesta.json()
    assert [i["numero"] for i in intentos] == [1, 2, 3]
    assert all(i["texto"] == PROSA_CORTA for i in intentos)
    assert all("EST-02" in [d["codigo"] for d in i["defectos"]] for i in intentos)
    assert all(d["cita"] for i in intentos for d in i["defectos"])
    assert all(i["termino_vetado"] is None for i in intentos)


async def test_los_intentos_de_un_trabajo_inexistente_responden_404(cliente):
    respuesta = cliente.get("/trabajos/9999/intentos")

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "No existe el trabajo 9999"


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


async def test_el_capitulo_escalado_trae_el_juicio_del_critico(
    sesion,
    obra_lista,  # noqa: F811
):
    """Paso 6: el Critico corre en cada vuelta, y al escalar su juicio se perdia.

    El retorno aprobado lo llevaba y el escalado no, que es justo el caso en que
    una persona tiene que decidir y el juez tenia algo que decir.
    """
    doble = DobleDeterminista(_respuestas(PROSA_CORTA))
    agentes = Agentes(
        planificador=Planificador(doble),
        escritor=Escritor(doble),
        extractor=Extractor(doble),
        critico=Critico(doble, rubrica_vigente()),
    )

    resultado = await _ciclo(sesion, obra_lista.capitulos[0].id, agentes=agentes)

    assert resultado.estado == "ESCALADA"
    assert resultado.escritura is not None
    assert resultado.escritura.juicio is not None
