"""Sonda de dominio — las propiedades **universales** de RF-CAL-13, 14, 15 y 17.

Complementa a [`sonda_invariantes.py`](sonda_invariantes.py), que reproduce los seis
hallazgos uno a uno. Esta hace la otra mitad del trabajo: comprobar que los requisitos
se cumplen **para todos los validadores**, no solo para los dos o tres que un hallazgo
concreto tocó.

Por qué hace falta. RF-CAL-13 dice «**ningún** validador mecánico devuelve lista vacía
ante una entrada que no pertenece a su dominio declarado». Los criterios CA-2 y CA-6 lo
comprueban en `validar_nivel_de_calor` y en `solo_narracion`. Quedan cinco funciones sin
comprobar, y **en una de ellas el fallo ya está** (H-7, aquí abajo): se puede arreglar
H-2 y H-6, poner los siete criterios en verde y dejar el requisito incumplido.

Lo mismo con RF-CAL-15: CA-4 cubre `validar_canon` y `validar_continuidad_fisica`, pero
el requisito habla de «sus colecciones de entrada», y hay dos validadores más
que también las reciben.

**Fuera de `testpaths`**, igual que la otra sonda: es evidencia de la spec, no suite.

    uv run pytest specs/002-validadores-fallo-cerrado/sonda_dominio.py -q

Hoy falla en H-7 y en el guardián de RF-CAL-17. Lo demás pasa, y eso también es
información: dice qué parte del requisito ya se cumple y no hay que tocar.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.features.calidad import (
    Afirmacion,
    validar_conocimiento,
    validar_discurso,
    validar_nivel_de_calor,
    validar_objetos,
)
from app.features.calidad import validadores as V

VT = "vt1"
RAIZ = Path(__file__).resolve().parents[2]
AJUSTE = settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])

PERSONAS = tuple(V._MARCAS_DE_PERSONA)  # ("primera", "tercera")
TIEMPOS = tuple(V._MARCAS_DE_TIEMPO)  # ("pasado", "presente")

# Un texto con narración inequívoca: en tercera persona y en pasado. Sirve de sonda
# porque cualquier validador de discurso tiene *algo* que decir sobre él.
NARRACION = "Ella camino hasta la puerta y ella espero alli mucho rato."


def huella(defectos):
    return sorted(
        (d.codigo.value, d.cita, d.desplazamiento_inicio, d.detalle) for d in defectos
    )


# --- H-7: `validar_discurso` fuera de su dominio (RF-CAL-13 y RF-CAL-14) -----
#
# Hallazgo nuevo, del mismo patrón que H-2 y H-1, en el validador que H-6 ya toca.
# No está en §Hallazgos de la spec. Contraejemplos ejecutados el 2026-09-23.


@AJUSTE
@given(st.text(min_size=1, max_size=12).filter(lambda t: t not in TIEMPOS))
def test_h7a_discurso_falla_cerrado_con_tiempo_fuera_de_escala(tiempo: str) -> None:
    """`_MARCAS_DE_TIEMPO.get(tiempo)` devuelve None y la comprobación **se salta
    entera**: devuelve [], que la puerta lee como «sin defectos».

    Basta una errata de mayúsculas —`"PASADO"`— para apagar la mitad de VOZ-03 sin
    ruido de ningún tipo. Es H-2 otra vez, en otra función: la regla 10 de
    `CLAUDE.md` §8 deja de comprobarse y nadie se entera.
    """
    with pytest.raises(Exception) as fallo:
        validar_discurso(NARRACION, "tercera", tiempo, VT)
    assert not isinstance(fallo.value, KeyError), (
        "un KeyError no es un error de dominio tipado de commons/errors/ (RF-CAL-14)"
    )


@AJUSTE
@given(st.text(min_size=1, max_size=12).filter(lambda p: p not in PERSONAS))
def test_h7b_discurso_no_revienta_con_persona_fuera_de_escala(persona: str) -> None:
    """`_MARCAS_DE_PERSONA[persona]` es un acceso directo: con cualquier persona que
    no sea "primera" ni "tercera" sube un `KeyError` pelado.

    Es H-1 con otra cara, y peor: allí al menos era un `ValidationError` de Pydantic.
    """
    with pytest.raises(Exception) as fallo:
        validar_discurso(
            "Yo camine hasta la puerta y yo espere.", persona, "pasado", VT
        )
    assert not isinstance(fallo.value, KeyError), (
        f"KeyError sin tipar con persona={persona!r}: RF-CAL-14 pide error de dominio"
    )


# --- RF-CAL-13 aplicado a todos los validadores, no solo a los del hallazgo ---


def cierra_ante(llamada, etiqueta: str) -> str | None:
    """Devuelve la queja si la llamada **falla en abierto**, o None si cierra bien.

    Cerrar bien es una de dos: lanzar un error de dominio, o devolver defectos. Lo que
    RF-CAL-13 prohíbe es la tercera: devolver `[]`, que la puerta lee como «limpio».
    Un `KeyError` o un `ValidationError` tampoco valen — RF-CAL-14 pide error tipado.
    """
    try:
        return f"{etiqueta} -> []" if llamada() == [] else None
    except KeyError as error:
        return f"{etiqueta} -> KeyError({error}) sin tipar (RF-CAL-14)"
    except Exception as error:  # noqa: BLE001 — el tipo concreto lo juzga la línea de arriba
        tipo = type(error).__module__ + "." + type(error).__name__
        if "commons.errors" in tipo:
            return None
        return f"{etiqueta} -> {tipo}, que no es de commons/errors/ (RF-CAL-13)"


def test_rf_cal_13_todo_validador_declara_su_dominio() -> None:
    """Inventario explícito: qué validador tiene escala cerrada y si la comprueba.

    Falla mientras quede uno que, ante un valor fuera de su escala, devuelva lista
    vacía o lance algo sin tipar. Es la forma de que el requisito no se dé por
    cumplido arreglando solo los dos casos que un CA nombra — que es exactamente lo
    que ha pasado: el 2026-09-23 `validar_nivel_de_calor` pasó a lanzar
    `EntradaFueraDeDominio` y `validar_discurso` se quedó como estaba.
    """
    abiertos = [
        queja
        for queja in (
            cierra_ante(
                lambda: validar_nivel_de_calor(
                    "Se quito la ropa.", "NIVEL_INVALIDO", VT
                ),
                "validar_nivel_de_calor(nivel fuera de _ESCALA)",
            ),
            cierra_ante(
                lambda: validar_discurso(NARRACION, "tercera", "preterito", VT),
                "validar_discurso(tiempo fuera de _MARCAS_DE_TIEMPO)",
            ),
            cierra_ante(
                lambda: validar_discurso(NARRACION, "segunda", "pasado", VT),
                "validar_discurso(persona fuera de _MARCAS_DE_PERSONA)",
            ),
        )
        if queja
    ]

    assert not abiertos, "validadores que fallan en abierto:\n  " + "\n  ".join(
        abiertos
    )


# --- RF-CAL-15 sobre las colecciones que CA-4 no cubre -----------------------


afirmaciones_con_objeto = st.lists(
    st.builds(
        Afirmacion,
        cita=st.sampled_from(["la llave", "el farol", "la carpeta"]),
        sujeto=st.sampled_from(["Mara", "Iker"]),
        objeto=st.sampled_from(["llave", "farol", "carpeta"]),
    ),
    min_size=2,
    max_size=4,
)


@AJUSTE
@given(afirmaciones_con_objeto, st.randoms())
def test_rf_cal_15_objetos_no_depende_del_orden(afs: list[Afirmacion], rnd) -> None:
    """`validar_objetos` recibe una colección: su salida no puede depender del orden."""
    texto = "Mara tomo la llave, el farol y la carpeta del taller."
    estado = {"llave": "perdido", "farol": "roto", "carpeta": "disponible"}

    barajado = list(afs)
    rnd.shuffle(barajado)

    assert huella(validar_objetos(afs, estado, texto, VT)) == huella(
        validar_objetos(barajado, estado, texto, VT)
    )


@AJUSTE
@given(afirmaciones_con_objeto, st.randoms())
def test_rf_cal_15_conocimiento_no_depende_del_orden(
    afs: list[Afirmacion], rnd
) -> None:
    """Y `validar_conocimiento` recibe dos: las afirmaciones y los conocimientos."""
    texto = "Mara tomo la llave, el farol y la carpeta del taller."
    conocimientos = {"Mara": ["llave", "farol"], "Iker": ["carpeta"]}

    barajado = list(afs)
    rnd.shuffle(barajado)
    del_reves = {k: list(reversed(v)) for k, v in conocimientos.items()}

    assert huella(validar_conocimiento(afs, conocimientos, texto, VT)) == huella(
        validar_conocimiento(barajado, del_reves, texto, VT)
    )


# --- RF-CAL-17: las propiedades viven en la suite ----------------------------


def test_rf_cal_17_las_propiedades_estan_en_la_suite() -> None:
    """El requisito que ningún criterio comprueba.

    RF-CAL-17 pide que las seis propiedades vivan **en la suite** como tests basados en
    propiedades. CA-1 comprueba que la sonda *pasa*, no que esté dentro de `testpaths`.
    Se puede arreglar el código, dejar las dos sondas en verde aquí fuera, no migrar
    nada, y tener los siete criterios en verde con RF-CAL-17 incumplido.

    Esto lo detecta: busca `hypothesis` en los tests que `pytest` sí recoge.
    """
    tests = RAIZ / "src" / "backend" / "app" / "features" / "calidad" / "tests"
    assert tests.is_dir(), f"no existe {tests}"

    con_propiedades = [
        f.name
        for f in tests.glob("test_*.py")
        if "hypothesis" in f.read_text(encoding="utf-8")
    ]
    assert con_propiedades, (
        "ningún test de features/calidad/tests/ usa hypothesis: las propiedades siguen "
        "fuera de la suite y RF-CAL-17 no se cumple, por muy verdes que estén los CA"
    )


def test_rf_cal_17_las_sondas_siguen_fuera_de_testpaths() -> None:
    """La otra cara: mientras sean evidencia, `pytest` no debe recogerlas solo.

    Si un día `testpaths` las incluyera, la suite entera se pondría roja por diseño y
    se acabaría relajando la sonda para que pase — que es justo lo que CA-1 prohíbe.
    """
    recogidos = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
    ).stdout
    assert "sonda_invariantes" not in recogidos, (
        "la sonda está dentro de testpaths: o se migra a la suite (RF-CAL-17) o se "
        "deja fuera, pero no puede estar a medias"
    )
