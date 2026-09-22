"""P-01 y P-02: el arranque falla si la configuracion no permite arrancar.

RI-21 (falta una variable obligatoria) y RI-24 (el plazo de un paso con llamada
al modelo debe superar el timeout de espera de turno).
"""

import pytest

from app.commons.config import AjustesInvalidos, cargar_ajustes

# Entorno minimo valido: solo las variables sin valor por defecto.
ENTORNO_COMPLETO = {
    "STORYMAKER_PROVEEDOR_GENERACION_CLAVE": "clave-de-prueba",
    "STORYMAKER_PROVEEDOR_GENERACION_URL": "https://ejemplo.invalid",
    "STORYMAKER_MODELO": "modelo-de-prueba",
    "STORYMAKER_PROVEEDOR_EMBEDDINGS_CLAVE": "clave-de-prueba",
    "STORYMAKER_RUTA_BASE_DATOS": "obra.db",
}

OBLIGATORIAS = sorted(ENTORNO_COMPLETO)


@pytest.mark.parametrize("ausente", OBLIGATORIAS)
def test_arranque_falla_si_falta_una_variable_obligatoria(
    ausente: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RI-21: falta una obligatoria -> el arranque falla, y dice cual."""
    for nombre, valor in ENTORNO_COMPLETO.items():
        monkeypatch.setenv(nombre, valor)
    monkeypatch.delenv(ausente)

    with pytest.raises(AjustesInvalidos) as error:
        cargar_ajustes()

    assert ausente in str(error.value)


def test_los_valores_por_defecto_son_los_de_las_decisiones(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RI-21: con solo las obligatorias, el resto toma el valor decidido."""
    for nombre, valor in ENTORNO_COMPLETO.items():
        monkeypatch.setenv(nombre, valor)

    ajustes = cargar_ajustes()

    assert ajustes.llamadas_simultaneas == 1  # D-03
    assert ajustes.timeout_turno_s == 300  # D-03
    assert ajustes.plazo_paso_codigo_s == 30  # D-04
    assert ajustes.plazo_paso_modelo_s == 600  # D-04
    assert ajustes.snapshot_cada_n_escenas == 5  # D-01
    assert ajustes.dimension_embeddings == 1024  # D-02


def test_arranque_rechaza_plazo_de_paso_menor_que_timeout_de_turno(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RI-24: si el plazo del paso vence antes, RNF-TOK-05 es codigo muerto."""
    for nombre, valor in ENTORNO_COMPLETO.items():
        monkeypatch.setenv(nombre, valor)
    monkeypatch.setenv("STORYMAKER_TIMEOUT_TURNO_S", "600")
    monkeypatch.setenv("STORYMAKER_PLAZO_PASO_MODELO_S", "300")

    with pytest.raises(AjustesInvalidos) as error:
        cargar_ajustes()

    assert "plazo_paso_modelo_s" in str(error.value)
