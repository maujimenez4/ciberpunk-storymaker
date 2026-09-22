"""P-77, P-78, P-80 a P-82, P-87 y P-88: turno, plazos, cerrojo y reintentos.

RNF-TOK-03 a RNF-TOK-05, RNF-FIA-02, RNF-FIA-04, RF-ORQ-11 y `architecture.md`
§3.8. Ninguno de estos tests duerme: el reloj y la espera se inyectan, así que la
suite sigue corriendo en segundos.
"""

import threading

import pytest

from app.commons.errors import FalloDeProveedor, TiempoAgotado
from app.commons.jobs import (
    INTENTOS_DE_PROVEEDOR,
    PASOS_CON_MODELO,
    PLAZO_CODIGO_S,
    PLAZO_MODELO_S,
    CerrojoPorObra,
    Estado,
    TurnoDeModelo,
    con_reintentos,
    ejecutar_con_plazo,
    plazo_de,
)

# --- P-81: el plazo depende del tipo de paso --------------------------------


@pytest.mark.parametrize("paso", sorted(PASOS_CON_MODELO))
def test_los_pasos_con_modelo_llevan_el_plazo_largo(paso: Estado) -> None:
    assert plazo_de(paso) == PLAZO_MODELO_S


@pytest.mark.parametrize(
    "paso", [Estado.ENSAMBLANDO, Estado.VALIDANDO, Estado.REPARANDO]
)
def test_los_pasos_de_codigo_llevan_el_plazo_corto(paso: Estado) -> None:
    """D-04. Un plazo único que tolerase los 600 s del modelo no vigilaría un
    ensamblado colgado, que es donde el cuelgue pasa desapercibido."""
    assert plazo_de(paso) == PLAZO_CODIGO_S


def test_un_paso_que_se_pasa_de_plazo_da_tiempo_agotado() -> None:
    marcas = iter([0.0, 100.0])

    with pytest.raises(TiempoAgotado) as error:
        ejecutar_con_plazo(
            Estado.ENSAMBLANDO, lambda: "hecho", ahora=lambda: next(marcas)
        )

    assert error.value.paso == Estado.ENSAMBLANDO.value


def test_un_paso_dentro_de_plazo_devuelve_su_resultado() -> None:
    marcas = iter([0.0, 1.0])

    assert (
        ejecutar_con_plazo(
            Estado.ENSAMBLANDO, lambda: "hecho", ahora=lambda: next(marcas)
        )
        == "hecho"
    )


def test_el_plazo_no_interrumpe_el_paso_a_mitad() -> None:
    """Se mide **después** de ejecutar. Matar un paso en curso dejaría
    escrituras parciales, y toda la reanudación se apoya en que la salida solo
    se persiste al completarse (§3.7)."""
    hecho: list[str] = []
    marcas = iter([0.0, 100.0])

    with pytest.raises(TiempoAgotado):
        ejecutar_con_plazo(
            Estado.ENSAMBLANDO,
            lambda: hecho.append("completado"),
            ahora=lambda: next(marcas),
        )

    assert hecho == ["completado"]


# --- P-77, P-78, P-80: el turno único ---------------------------------------


def test_solo_una_llamada_al_modelo_en_vuelo() -> None:
    """RNF-TOK-03, D-03: una por proceso."""
    turno = TurnoDeModelo(simultaneas=1)

    assert turno.tomar(espera_s=0) is True
    assert turno.tomar(espera_s=0) is False


def test_sin_turno_se_espera_y_el_paquete_no_se_toca() -> None:
    """RNF-TOK-04. Recortar obedece al presupuesto de §2.1, **no** a la carga
    del sistema: un paquete recortado por prisa produce una escena peor sin que
    nada lo registre."""
    turno = TurnoDeModelo(simultaneas=1)
    turno.tomar(espera_s=0)

    assert turno.tomar(espera_s=0) is False
    assert not hasattr(turno, "recortar")
    assert not hasattr(turno, "degradar")


def test_el_timeout_de_turno_no_deja_el_proceso_colgado() -> None:
    """RNF-TOK-05: al vencer, `FALLIDA` con `TiempoAgotado` y **sin coste**,
    porque no se llegó a llamar. Es relanzable tal cual."""
    turno = TurnoDeModelo(simultaneas=1)
    turno.tomar(espera_s=0)

    obtenido = turno.tomar(espera_s=0.01)

    assert obtenido is False


# --- P-82, P-87: cerrojo por obra -------------------------------------------


def test_una_escena_en_vuelo_por_obra() -> None:
    """RF-ORQ-11. Es restricción de **corrección**: la escena N+1 necesita el
    estado en T posterior a N. Paralelizar escenas de la misma obra no es
    arriesgado, es incorrecto."""
    cerrojo = CerrojoPorObra()

    assert cerrojo.tomar("obra-1") is True
    assert cerrojo.tomar("obra-1") is False


def test_dos_obras_avanzan_a_la_vez() -> None:
    """§3.8: el paralelismo entre obras es de **trabajo**, no de llamadas."""
    cerrojo = CerrojoPorObra()

    assert cerrojo.tomar("obra-1") is True
    assert cerrojo.tomar("obra-2") is True


def test_dos_obras_comparten_el_turno_del_modelo() -> None:
    """Y esa es la otra mitad de §3.8: aunque avancen a la vez, sus llamadas se
    serializan, porque el turno es del proceso y no de la obra."""
    turno = TurnoDeModelo(simultaneas=1)
    cerrojo = CerrojoPorObra()
    cerrojo.tomar("obra-1")
    cerrojo.tomar("obra-2")

    assert turno.tomar(espera_s=0) is True
    assert turno.tomar(espera_s=0) is False


def test_el_cerrojo_se_suelta_aunque_el_paso_falle() -> None:
    cerrojo = CerrojoPorObra()

    with pytest.raises(RuntimeError), cerrojo.en_uso("obra-1"):
        raise RuntimeError("el paso exploto")

    assert cerrojo.tomar("obra-1") is True


def test_el_cerrojo_de_verdad_serializa_dos_hilos() -> None:
    cerrojo = CerrojoPorObra()
    orden: list[str] = []

    def trabajar(nombre: str) -> None:
        with cerrojo.en_uso("obra-1", espera_s=2) as tomado:
            assert tomado
            orden.append(f"entra-{nombre}")
            orden.append(f"sale-{nombre}")

    hilos = [threading.Thread(target=trabajar, args=(n,)) for n in ("a", "b")]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    # Nunca se solapan: cada entrada va seguida de su propia salida.
    assert orden[0].startswith("entra") and orden[1].startswith("sale")
    assert orden[1][-1] == orden[0][-1]


# --- P-88: reintento del proveedor ------------------------------------------


def test_se_reintenta_tres_veces_con_espera_creciente() -> None:
    """RNF-FIA-02. La espera crece porque un proveedor que acaba de fallar por
    tasa vuelve a fallar si se le insiste de inmediato: reintentar sin esperar
    convierte un fallo transitorio en tres."""
    llamadas: list[int] = []
    esperas: list[float] = []

    def siempre_falla() -> str:
        llamadas.append(1)
        raise ConnectionError("5xx")

    with pytest.raises(FalloDeProveedor) as error:
        con_reintentos(siempre_falla, esperar=esperas.append)

    assert len(llamadas) == INTENTOS_DE_PROVEEDOR
    assert esperas == [1, 2]
    assert error.value.intentos == INTENTOS_DE_PROVEEDOR


def test_si_el_segundo_intento_funciona_no_hay_tercero() -> None:
    llamadas: list[int] = []

    def falla_una_vez() -> str:
        llamadas.append(1)
        if len(llamadas) == 1:
            raise ConnectionError("5xx")
        return "prosa"

    assert con_reintentos(falla_una_vez, esperar=lambda _: None) == "prosa"
    assert len(llamadas) == 2


def test_un_fallo_de_proveedor_ya_agotado_no_se_reintenta() -> None:
    """Reintentar lo que ya agotó sus intentos multiplicaría el gasto sin
    cambiar el resultado."""
    llamadas: list[int] = []

    def ya_agotado() -> str:
        llamadas.append(1)
        raise FalloDeProveedor(intentos=3)

    with pytest.raises(FalloDeProveedor):
        con_reintentos(ya_agotado, esperar=lambda _: None)

    assert len(llamadas) == 1
