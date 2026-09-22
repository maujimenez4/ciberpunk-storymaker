"""P-71, P-74, P-75, P-76 y P-89: la máquina de estados y su persistencia.

RF-ORQ-03 a RF-ORQ-06, RF-ORQ-14, RF-ORQ-17, RF-ORQ-18, RNF-FIA-01 y RI-19.
"""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.commons.domain import RelojFijo
from app.commons.jobs import (
    EN_CURSO,
    TERMINALES,
    Estado,
    RepositorioDeTrabajos,
    TransicionInvalida,
    puede_ir,
)


@pytest.fixture
def reloj() -> RelojFijo:
    return RelojFijo(datetime(2026, 9, 22, tzinfo=UTC))


@pytest.fixture
def repositorio(base_de_datos: Path) -> RepositorioDeTrabajos:
    conexion = sqlite3.connect(base_de_datos)
    conexion.execute("INSERT INTO serie (serie_id, titulo) VALUES ('s1','S')")
    conexion.execute(
        "INSERT INTO obra (obra_id, serie_id, titulo, genero, subgenero,"
        " extension_objetivo, persona, tiempo_verbal, esquema_de_pov, nivel_de_calor)"
        " VALUES ('o1','s1','O','romance','contemporaneo',90000,'tercera','pasado',"
        "'dual','sensual')"
    )
    conexion.execute(
        "INSERT INTO parte (parte_id, obra_id, numero, funcion_estructural)"
        " VALUES ('pa1','o1',1,'planteamiento')"
    )
    conexion.execute(
        "INSERT INTO capitulo (capitulo_id, parte_id, numero) VALUES ('ca1','pa1',1)"
    )
    for i in (1, 2):
        conexion.execute(
            "INSERT INTO escena (escena_id, capitulo_id, orden_discurso, pov)"
            " VALUES (?,'ca1',?,'pj-ada')",
            (f"es{i}", i),
        )
    conexion.commit()
    conexion.close()
    return RepositorioDeTrabajos(base_de_datos)


# --- P-71: los diez estados, y ninguno se salta -----------------------------


def test_estan_los_diez_estados() -> None:
    assert len(Estado) == 10


def test_validando_no_puede_llegar_a_integrada_sin_pasar_por_extrayendo() -> None:
    """RF-ORQ-03, y es **la** transición que la máquina existe para impedir.

    Saltársela daría una escena en el manuscrito de la que el canon no sabe
    nada, porque es el Extractor quien deja rastro en la memoria larga (§4.4).
    El síntoma aparecería capítulos después como una contradicción inexplicable.
    """
    assert puede_ir(Estado.VALIDANDO, Estado.INTEGRADA) is False
    assert puede_ir(Estado.VALIDANDO, Estado.EXTRAYENDO) is True
    assert puede_ir(Estado.EXTRAYENDO, Estado.INTEGRADA) is True


def test_ensamblando_puede_fallar_sin_pasar_por_escribiendo() -> None:
    """§3.6: `ContextBudgetExceeded` va a `FALLIDA` **sin llamar al modelo**."""
    assert puede_ir(Estado.ENSAMBLANDO, Estado.FALLIDA) is True


def test_reparando_solo_vuelve_a_escribir_o_escala() -> None:
    assert puede_ir(Estado.REPARANDO, Estado.ESCRIBIENDO) is True
    assert puede_ir(Estado.REPARANDO, Estado.ESCALADA) is True
    assert puede_ir(Estado.REPARANDO, Estado.EXTRAYENDO) is False


@pytest.mark.parametrize("desde", sorted(EN_CURSO))
def test_cualquier_paso_en_curso_puede_agotar_su_plazo(desde: Estado) -> None:
    """§3.6: `TiempoAgotado` lleva a `FALLIDA` desde donde esté."""
    assert puede_ir(desde, Estado.FALLIDA) is True


@pytest.mark.parametrize(
    "desde",
    [Estado.PLANIFICANDO, Estado.ENSAMBLANDO, Estado.ESCRIBIENDO, Estado.VALIDANDO],
)
def test_el_autor_puede_cancelar_en_los_puntos_seguros(desde: Estado) -> None:
    """RI-19: en el primer punto seguro, nunca a mitad de una escritura."""
    assert puede_ir(desde, Estado.CANCELADA) is True


def test_desde_escalada_se_puede_revalidar_o_aceptar() -> None:
    """D-08, RF-ORQ-17 y RF-ORQ-18. Sin estas dos salidas, CU-04 no podría
    prometer que una escena nunca se queda indefinidamente en `ESCALADA`."""
    assert puede_ir(Estado.ESCALADA, Estado.VALIDANDO) is True
    assert puede_ir(Estado.ESCALADA, Estado.EXTRAYENDO) is True


def test_los_terminales_definitivos_no_tienen_salida() -> None:
    for estado in (Estado.INTEGRADA, Estado.FALLIDA, Estado.CANCELADA):
        assert all(not puede_ir(estado, otro) for otro in Estado)


# --- P-74: el estado se persiste tras cada paso -----------------------------


def test_cada_transicion_se_persiste(
    repositorio: RepositorioDeTrabajos, reloj: RelojFijo
) -> None:
    """RF-ORQ-04. En SQLite, nunca en memoria del proceso: una caída a mitad de
    escena no puede perder trabajo."""
    trabajo = repositorio.crear("o1", "es1", "escribir_escena", reloj)

    repositorio.transitar(trabajo.trabajo_id, Estado.ENSAMBLANDO, reloj)

    # Se relee desde la base, no del objeto en memoria.
    assert repositorio.leer(trabajo.trabajo_id).estado is Estado.ENSAMBLANDO


def test_un_salto_no_declarado_se_rechaza(
    repositorio: RepositorioDeTrabajos, reloj: RelojFijo
) -> None:
    trabajo = repositorio.crear("o1", "es1", "escribir_escena", reloj)

    with pytest.raises(TransicionInvalida):
        repositorio.transitar(trabajo.trabajo_id, Estado.INTEGRADA, reloj)

    assert repositorio.leer(trabajo.trabajo_id).estado is Estado.PLANIFICANDO


def test_el_intento_solo_crece_cuando_se_le_dice(
    repositorio: RepositorioDeTrabajos, reloj: RelojFijo
) -> None:
    """RF-ORQ-07: el contador es de reparaciones dirigidas, no de transiciones."""
    trabajo = repositorio.crear("o1", "es1", "escribir_escena", reloj)

    repositorio.transitar(trabajo.trabajo_id, Estado.ENSAMBLANDO, reloj)
    assert repositorio.leer(trabajo.trabajo_id).intento == 0

    repositorio.transitar(trabajo.trabajo_id, Estado.ESCRIBIENDO, reloj)
    repositorio.transitar(trabajo.trabajo_id, Estado.VALIDANDO, reloj)
    repositorio.transitar(
        trabajo.trabajo_id, Estado.REPARANDO, reloj, incrementa_intento=True
    )
    assert repositorio.leer(trabajo.trabajo_id).intento == 1


# --- P-76: la reanudación ----------------------------------------------------


def test_al_arrancar_se_retoman_los_trabajos_no_terminales(
    repositorio: RepositorioDeTrabajos, reloj: RelojFijo
) -> None:
    """RF-ORQ-05 y RNF-FIA-01."""
    vivo = repositorio.crear("o1", "es1", "escribir_escena", reloj)
    muerto = repositorio.crear("o1", "es2", "escribir_escena", reloj)
    repositorio.transitar(muerto.trabajo_id, Estado.CANCELADA, reloj)

    retomados = [t.trabajo_id for t in repositorio.vivos()]

    assert vivo.trabajo_id in retomados
    assert muerto.trabajo_id not in retomados


def test_un_trabajo_escalado_no_se_retoma_solo(
    repositorio: RepositorioDeTrabajos, reloj: RelojFijo
) -> None:
    """`ESCALADA` es terminal **hasta que el autor actúe**. Retomarlo lo
    devolvería a la misma espera, y además pisaría una decisión humana
    pendiente."""
    trabajo = repositorio.crear("o1", "es1", "escribir_escena", reloj)
    for estado in (
        Estado.ENSAMBLANDO,
        Estado.ESCRIBIENDO,
        Estado.VALIDANDO,
        Estado.REPARANDO,
        Estado.ESCALADA,
    ):
        repositorio.transitar(trabajo.trabajo_id, estado, reloj)

    assert trabajo.trabajo_id not in [t.trabajo_id for t in repositorio.vivos()]


def test_escalada_es_terminal_pero_no_definitivo() -> None:
    assert Estado.ESCALADA in TERMINALES
    assert puede_ir(Estado.ESCALADA, Estado.VALIDANDO) is True


# --- P-85: la aceptación con defecto anulado --------------------------------


def test_aceptar_registra_que_defecto_se_anulo_y_quien(
    repositorio: RepositorioDeTrabajos, reloj: RelojFijo
) -> None:
    """RF-ORQ-18. Sin este registro no se avanza: es lo que impide que un
    validador equivocado deje el trabajo atrapado, dejando constancia de quién
    decidió saltarse la puerta."""
    trabajo = repositorio.crear("o1", "es1", "escribir_escena", reloj)

    actualizado = repositorio.registrar_anulacion(
        trabajo.trabajo_id, "def-7", "maujimenez4", reloj
    )

    assert actualizado.defecto_anulado_id == "def-7"
    assert actualizado.anulado_por == "maujimenez4"


def test_el_esquema_impide_mas_de_dos_reparaciones(
    repositorio: RepositorioDeTrabajos, reloj: RelojFijo
) -> None:
    """RF-ORQ-07, impuesto por el CHECK de la migración y no por el contador del
    orquestador: si solo lo vigilara el código, un fallo de conteo daría un bucle
    de reparaciones que se paga en cuota."""
    trabajo = repositorio.crear("o1", "es1", "escribir_escena", reloj)
    conexion = sqlite3.connect(repositorio.ruta)

    with pytest.raises(sqlite3.IntegrityError):
        conexion.execute(
            "UPDATE trabajo SET intento = 3 WHERE trabajo_id = ?",
            (trabajo.trabajo_id,),
        )
    conexion.close()
