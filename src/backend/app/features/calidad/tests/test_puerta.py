"""P-67, P-69 y P-70: comprobación de forma y puerta G1a.

RF-CAL-09, RF-CAL-10 y RF-CAL-11, `architecture.md` §8.3.
"""

from app.features.calidad import (
    CodigoDeDefecto,
    Defecto,
    citar,
    comprobar_forma,
    pasar_g1a,
)

TEXTO = "La lluvia cortaba la red del taller. Ada miro la grieta."
VT = "vt1"
CANON = {"hc1", "hc2"}


def _defecto(codigo: CodigoDeDefecto, fragmento: str, **extra: object) -> Defecto:
    return citar(TEXTO, fragmento, codigo, VT, **extra)  # type: ignore[arg-type]


# --- P-67: la comprobación de forma -----------------------------------------


def test_un_defecto_bien_formado_pasa_la_comprobacion() -> None:
    defecto = _defecto(CodigoDeDefecto.CON_01, "cortaba la red")

    assert comprobar_forma(defecto, TEXTO, CANON).bien_formado is True


def test_una_cita_que_no_coincide_con_el_texto_queda_mal_formada() -> None:
    """Axioma 11. Es **la** categoría que esta comprobación elimina: el defecto
    bien formado con la cita equivocada, que antes parecía correcto y mandaba al
    Escritor a reparar un pasaje que no existe."""
    defecto = _defecto(CodigoDeDefecto.CON_01, "cortaba la red").model_copy(
        update={"desplazamiento_inicio": 0, "desplazamiento_fin": 10}
    )

    comprobado = comprobar_forma(defecto, TEXTO, CANON)

    assert comprobado.bien_formado is False
    assert "no coincide" in comprobado.detalle


def test_un_can_01_sin_hecho_canon_queda_mal_formado() -> None:
    """Axioma 12."""
    defecto = _defecto(CodigoDeDefecto.CAN_01, "Ada miro")

    comprobado = comprobar_forma(defecto, TEXTO, CANON)

    assert comprobado.bien_formado is False
    assert "axioma 12" in comprobado.detalle


def test_un_can_01_que_apunta_a_un_hecho_inventado_queda_mal_formado() -> None:
    defecto = _defecto(CodigoDeDefecto.CAN_01, "Ada miro", hecho_canon_id="hc-falso")

    comprobado = comprobar_forma(defecto, TEXTO, CANON)

    assert comprobado.bien_formado is False
    assert "no existe" in comprobado.detalle


def test_un_can_01_bien_anclado_pasa() -> None:
    defecto = _defecto(CodigoDeDefecto.CAN_01, "Ada miro", hecho_canon_id="hc1")

    assert comprobar_forma(defecto, TEXTO, CANON).bien_formado is True


# --- P-69: la puerta G1a ----------------------------------------------------


def test_g1a_bloquea_con_un_defecto_mecanico() -> None:
    """CON-01 y no CON-03: desde el 2026-09-23, CAN-01 y CON-03 se registran
    pero no bloquean, porque su contraste da falsos positivos (`defectos.py`)."""
    veredicto = pasar_g1a(
        [_defecto(CodigoDeDefecto.CON_01, "cortaba la red")], TEXTO, CANON
    )

    assert veredicto.aprobada is False
    assert len(veredicto.bloquean) == 1


def test_g1b_no_bloquea_en_la_v1() -> None:
    """RF-CAL-09. Los defectos de juicio se registran y dejan pasar: necesitan
    al Crítico con una rúbrica calibrada, que es la fase 4. Fingir que la función
    dramática se comprueba mecánicamente sería peor que declararla pendiente."""
    de_juicio = [
        _defecto(CodigoDeDefecto.VOZ_01, "Ada miro"),
        _defecto(CodigoDeDefecto.PRO_01, "la grieta"),
        _defecto(CodigoDeDefecto.GEN_02, "del taller"),
    ]

    veredicto = pasar_g1a(de_juicio, TEXTO, CANON)

    assert veredicto.aprobada is True
    assert len(veredicto.no_bloquean) == 3


def test_voz_03_si_bloquea_aunque_su_familia_sea_de_voz() -> None:
    """RF-CAL-12: persona y tiempo verbal son restricción dura declarada en la
    obra, no juicio de estilo. Comparten prefijo con VOZ-01 y VOZ-02 y no
    comparten naturaleza."""
    veredicto = pasar_g1a([_defecto(CodigoDeDefecto.VOZ_03, "Ada miro")], TEXTO, CANON)

    assert veredicto.aprobada is False


def test_un_defecto_mal_formado_no_bloquea_ni_se_pierde() -> None:
    """RF-CAL-11 y §9. No consume reintento, pero **se registra**: su tasa es hoy
    la única señal directa de que el Continuista afirma cosas que no están en el
    texto."""
    inventado = _defecto(CodigoDeDefecto.CON_03, "Ada miro").model_copy(
        update={"cita": "algo que no esta"}
    )

    veredicto = pasar_g1a([inventado], TEXTO, CANON)

    assert veredicto.aprobada is True
    assert len(veredicto.mal_formados) == 1
    assert veredicto.bloquean == []


def test_la_tasa_de_mal_formados_se_puede_medir() -> None:
    defectos = [
        _defecto(CodigoDeDefecto.CON_03, "Ada miro"),
        _defecto(CodigoDeDefecto.CON_01, "la grieta").model_copy(
            update={"cita": "no esta"}
        ),
    ]

    assert pasar_g1a(defectos, TEXTO, CANON).tasa_de_mal_formados == 0.5


def test_sin_defectos_la_escena_pasa() -> None:
    assert pasar_g1a([], TEXTO, CANON).aprobada is True


# --- P-70: un defecto de calidad no es un fallo técnico ----------------------


def test_el_veredicto_no_es_una_excepcion() -> None:
    """RF-CAL-10. Un defecto produce `REPARANDO`/`ESCALADA`, nunca `FALLIDA`.

    Por eso la puerta **devuelve** un veredicto en vez de lanzar: si lanzara,
    el orquestador no podría distinguirlo de un fallo técnico, y `ESCALADA` y
    `FALLIDA` se cuentan por separado a propósito (§3.6).
    """
    veredicto = pasar_g1a(
        [_defecto(CodigoDeDefecto.CON_01, "cortaba la red")], TEXTO, CANON
    )

    assert veredicto.bloquean[0].codigo is CodigoDeDefecto.CON_01
    assert isinstance(veredicto.aprobada, bool)


def test_can_01_y_con_03_se_registran_pero_no_bloquean() -> None:
    """Decidido por maujimenez4 el 2026-09-23, con RF-CAL-09 incumplido a
    proposito y anotado en la spec.

    Los dos contrastan texto libre por igualdad exacta contra lo que escribio el
    Extractor, y dan falsos positivos con objetos fisicos y con sinonimos
    (`calidad/tests/test_validadores.py`). Bloqueando, cada falso positivo es una
    ESCALADA. Se siguen registrando porque su tasa sobre una corrida real es lo
    que dira si el contraste sirve.
    """
    veredicto = pasar_g1a(
        [
            # Con su `hecho_canon_id`: sin el, el axioma 12 lo marca mal
            # formado y acabaria en el otro cubo.
            _defecto(CodigoDeDefecto.CAN_01, "cortaba la red", hecho_canon_id="hc1"),
            _defecto(CodigoDeDefecto.CON_03, "Ada miro"),
        ],
        TEXTO,
        CANON,
    )

    assert veredicto.aprobada is True
    assert veredicto.bloquean == []
    assert {d.codigo for d in veredicto.no_bloquean} == {
        CodigoDeDefecto.CAN_01,
        CodigoDeDefecto.CON_03,
    }
