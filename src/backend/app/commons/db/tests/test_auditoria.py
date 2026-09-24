import pytest
from sqlalchemy.exc import IntegrityError

from app.commons.config.ajustes import Ajustes
from app.commons.db.auditoria import borrar_auditoria, leer_auditoria, registrar
from app.commons.domain.errores import OperacionNoPermitida


async def test_registra_lo_permitido_y_no_solo_lo_bloqueado(sesion, obra):
    """RF-GUA-05: 'que se permitio y que se bloqueo, y por que'.

    Un registro que solo guarda los bloqueos no permite responder 'por que
    paso esto', que es justo lo que se le pregunta.
    """
    await registrar(sesion, obra.id, "permitido", "sin veto", {"ambito": "brief"})
    await registrar(sesion, obra.id, "bloqueado", "veto: sangre", {"ambito": "brief"})
    filas = await leer_auditoria(sesion, obra.id)
    assert [f.decision for f in filas] == ["permitido", "bloqueado"]


async def test_es_append_only(sesion, obra):
    """RF-GUA-05. Escribe su propia fila: no hereda la del test anterior.

    El borrador leia `(await leer_auditoria(...))[0]` sin escribir nada, y
    solo pasaba si la fixture `sesion` arrastraba lo que habia escrito el
    test de arriba. Con `sesion` por test y con reversion -- que es como la
    crea la Tarea 2 -- eso es un IndexError, no un fallo de `borrar_auditoria`.
    Un test que depende del orden de ejecucion no comprueba lo que dice.
    """
    await registrar(sesion, obra.id, "bloqueado", "veto: sangre", {"ambito": "brief"})
    fila = (await leer_auditoria(sesion, obra.id))[0]
    with pytest.raises(OperacionNoPermitida):
        await borrar_auditoria(sesion, fila.id)


async def test_una_decision_que_no_es_ni_permitido_ni_bloqueado_no_entra(sesion, obra):
    """El plan exige `decision` en {permitido, bloqueado} y no deja test que lo pruebe.

    Sin esto, el `CheckConstraint` se podria borrar del modelo y de la migracion
    sin que la suite se inmutara -- que es justo lo que CA-6 manda comprobar. Y
    la restriccion no es decorativa: `leer_auditoria` responde «que se permitio
    y que se bloqueo» (RF-GUA-05) repartiendo las filas entre esos dos valores,
    y un tercero las deja fuera de las dos respuestas sin avisar a nadie.

    Va contra la BASE, no contra un validador de Python, porque `registrar` no
    es la unica puerta: el dia que un servicio inserte por su cuenta, lo que lo
    pare tiene que estar en el esquema.
    """
    with pytest.raises(IntegrityError):
        await registrar(sesion, obra.id, "quiza", "ni lo uno ni lo otro", {})


async def test_ninguna_clave_se_lee_del_repositorio_ni_de_la_base(monkeypatch):
    """RF-OBS-07. Solo del entorno."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert Ajustes.desde_entorno().clave_proveedor is None
