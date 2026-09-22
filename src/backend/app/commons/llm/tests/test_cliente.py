"""P-09: el cliente de modelo y el reloj se inyectan (RI-13).

Ninguna prueba llama al proveedor real. Hoy eso es facil porque no hay proveedor
conectado -se conecta en la fase 7-, y justo por eso conviene dejar el guardian
puesto ahora: cuando lo haya, el primer test que se olvide del doble fallara en
vez de gastar cuota.
"""

from datetime import UTC, datetime

import pytest

from app.commons.domain import Reloj, RelojDelSistema, RelojFijo
from app.commons.llm import (
    ClienteDeModelo,
    ClienteNoConfigurado,
    DobleDeModelo,
    ProveedorSinConectar,
)


def test_el_doble_devuelve_lo_previsto_y_no_llama_a_nadie() -> None:
    doble = DobleDeModelo(["primera escena", "segunda escena"])
    cliente: ClienteDeModelo = doble

    assert cliente.generar("prompt uno").texto == "primera escena"
    assert cliente.generar("prompt dos").texto == "segunda escena"


def test_el_doble_registra_lo_que_se_le_pidio() -> None:
    """Sin esto no se puede afirmar que el paquete llego entero al Escritor."""
    doble = DobleDeModelo(["x"])
    doble.generar("el paquete de contexto")

    assert doble.llamadas == ["el paquete de contexto"]


def test_el_doble_se_queja_si_le_piden_mas_de_lo_previsto() -> None:
    """Un doble que improvisa esconde un bucle que llama de mas."""
    doble = DobleDeModelo(["solo una"])
    doble.generar("uno")

    with pytest.raises(AssertionError):
        doble.generar("dos")


def test_el_proveedor_real_no_esta_conectado_todavia() -> None:
    """Documenta el estado: la conexion real es trabajo de la fase 7.

    Que falle explicitamente es mejor que devolver texto vacio: un cliente que
    calla se confundiria con una escena que el modelo no supo escribir.
    """
    with pytest.raises(ProveedorSinConectar):
        ClienteNoConfigurado().generar("lo que sea")


def test_el_reloj_fijo_no_avanza() -> None:
    """RI-13: el reloj tambien se inyecta. Sin el, ningun test sobre
    `creado_en`, plazos o timeouts seria reproducible."""
    instante = datetime(2026, 9, 22, 12, 0, tzinfo=UTC)
    reloj: Reloj = RelojFijo(instante)

    assert reloj.ahora() == instante
    assert reloj.ahora() == instante


def test_el_reloj_del_sistema_avanza() -> None:
    reloj: Reloj = RelojDelSistema()
    primera = reloj.ahora()

    assert reloj.ahora() >= primera
    assert primera.tzinfo is not None
