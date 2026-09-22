"""P-96 a P-98: la traza estructural y las dos métricas que miden al sistema.

RNF-OBS-02, RNF-OBS-03 y `architecture.md` §9.
"""

import pytest

from app.commons.config import Metricas, TrazaConProsa, traza

# --- P-96: la traza es estructural, no textual ------------------------------


def test_una_traza_de_identificadores_y_numeros_pasa() -> None:
    entrada = traza("escena_integrada", escena_id="es1", tokens=1234, intento=1)

    assert entrada["evento"] == "escena_integrada"
    assert entrada["escena_id"] == "es1"


@pytest.mark.parametrize(
    "campo", ["texto", "prosa_generada", "cita_del_defecto", "prompt_id_texto"]
)
def test_los_campos_con_prosa_se_rechazan_por_nombre(campo: str) -> None:
    """RNF-OBS-03. Un log con prosa dentro convierte cualquier copia de los
    registros en una copia del manuscrito."""
    with pytest.raises(TrazaConProsa):
        traza("escena_integrada", **{campo: "lo que sea"})


def test_un_valor_con_pinta_de_prosa_se_rechaza_aunque_el_campo_se_llame_bien() -> None:
    """El nombre del campo se puede disfrazar; la longitud del valor, no tanto."""
    with pytest.raises(TrazaConProsa):
        traza(
            "escena_integrada",
            detalle="La lluvia cortaba la red del taller y Ada miro la grieta "
            "sabiendo que aquello no iba a terminar bien para ninguno de los dos",
        )


def test_falla_en_vez_de_recortar_en_silencio() -> None:
    """Si recortara, el llamante creería que registró algo y estaría registrando
    otra cosa, y nadie lo notaría hasta necesitar ese dato."""
    with pytest.raises(TrazaConProsa):
        traza("x", texto="a")


# --- P-97: la tasa de defectos mal formados ---------------------------------


def test_la_tasa_de_mal_formados_se_acumula() -> None:
    """§9 y `verification.md` §6.3: hoy es la única señal directa de que el
    Continuista afirma cosas que no están en el texto."""
    metricas = Metricas()

    metricas.anotar_defecto("CON-03", bien_formado=True)
    metricas.anotar_defecto("CAN-01", bien_formado=False)
    metricas.anotar_defecto("CON-01", bien_formado=True)
    metricas.anotar_defecto("CON-01", bien_formado=True)

    assert metricas.tasa_de_defectos_mal_formados == 0.25
    assert metricas.defectos_por_codigo["CON-01"] == 2


def test_sin_defectos_la_tasa_es_cero_y_no_revienta() -> None:
    assert Metricas().tasa_de_defectos_mal_formados == 0.0


# --- P-98: la espera de turno -----------------------------------------------


def test_se_miden_la_espera_media_y_las_vencidas() -> None:
    """RNF-OBS-02. Es lo que dice si el límite de concurrencia de §2.2 está
    estrangulando el proceso o solo ordenándolo."""
    metricas = Metricas()

    metricas.anotar_espera_de_turno(2.0, vencida=False)
    metricas.anotar_espera_de_turno(4.0, vencida=False)
    metricas.anotar_espera_de_turno(300.0, vencida=True)

    assert metricas.espera_media_de_turno_s == pytest.approx(102.0)
    assert metricas.esperas_vencidas == 1


# --- las de la obra ---------------------------------------------------------


def test_los_escalados_por_cien_escenas() -> None:
    """§9. Avisa de que la revisión humana se degrada por volumen, que es un
    riesgo declarado en `verification.md` §7 y hoy sin umbral."""
    metricas = Metricas()
    for i in range(50):
        metricas.anotar_escena(f"es{i}", coste=0.1, por_capa={"canon_relevante": 100})
    metricas.escalados = 3

    assert metricas.escalados_por_cien_escenas == 6.0


def test_el_porcentaje_por_capa_suma_cien() -> None:
    metricas = Metricas()
    metricas.anotar_escena(
        "es1", coste=0.1, por_capa={"constitucional": 25, "canon_relevante": 75}
    )

    porcentajes = metricas.porcentaje_por_capa()

    assert porcentajes["constitucional"] == pytest.approx(25.0)
    assert sum(porcentajes.values()) == pytest.approx(100.0)
