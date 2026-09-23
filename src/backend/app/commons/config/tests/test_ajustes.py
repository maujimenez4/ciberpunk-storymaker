"""P-01 y P-02: el arranque falla si la configuracion no permite arrancar.

RI-21 (falta una variable obligatoria) y RI-24 (el plazo de un paso con llamada
al modelo debe superar el timeout de espera de turno).
"""

import pytest

from app.commons.config import Ajustes, AjustesInvalidos, cargar_ajustes

# RI-21, tras la decision (a) de 2026-09-22: el proveedor es el CLI de Claude
# Code y la credencial es su sesion, fuera del proceso. La aplicacion no guarda
# ninguna.
CAMPOS_DE_RI_21 = {
    "modelo",
    "ruta_base_de_datos",
    "llamadas_simultaneas",
    "timeout_turno_s",
    "plazo_paso_codigo_s",
    "plazo_paso_modelo_s",
    "snapshot_cada_n_escenas",
}


def test_los_ajustes_declaran_exactamente_lo_que_pide_ri_21() -> None:
    """Ni mas ni menos.

    Menos se nota al arrancar. **Mas no se nota nunca**: un campo obligatorio
    que ningun codigo consume obliga a exportar una variable inventada y hace
    creer que el sistema necesita algo que no necesita. Paso exactamente eso con
    `proveedor_embeddings_clave`, que sobrevivio a D-02 catorce dias.
    """
    assert set(Ajustes.model_fields) == CAMPOS_DE_RI_21


# Entorno minimo valido: solo las variables sin valor por defecto.
ENTORNO_COMPLETO = {
    "STORYMAKER_MODELO": "modelo-de-prueba",
    "STORYMAKER_RUTA_BASE_DE_DATOS": "obra.db",
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
