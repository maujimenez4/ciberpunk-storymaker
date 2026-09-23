"""Sonda de invariantes sobre `validadores.py` — evidencia de la spec 005.

**No es parte de la suite.** `pyproject.toml` fija `testpaths = ["src/backend"]`,
así que `pytest` no la recoge. Vive aquí porque es la evidencia de los seis
hallazgos, y porque un hallazgo sin reproducción es una opinión.

Cómo correrla:

    uv run pytest specs/005-validadores-fallo-cerrado/sonda_invariantes.py -q

Hoy **falla**, y eso es lo que documenta. Cuando la spec se implemente, RF-CAL-17
la convierte en tests permanentes dentro de `features/calidad/tests/`; entonces
este fichero queda como registro, igual que el plan.

Las tres técnicas que produjeron estas invariantes están en
`.claude/skills/verification-methods/references/lenguajes-formales.md` §2:
alcance pequeño de Alloy, precondición declarada de Dafny y SPARK, y la
separación seguridad/vivacidad de TLA+ y Quint.
"""

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.commons.errors import EntradaFueraDeDominio
from app.features.calidad import (
    Afirmacion,
    HechoDeCanon,
    solo_narracion,
    validar_canon,
    validar_conocimiento,
    validar_continuidad_fisica,
    validar_discurso,
    validar_giro_de_valor,
    validar_nivel_de_calor,
)

VT = "vt1"
NIVELES = ("puerta_cerrada", "sensual", "abierto", "explicito")
AJUSTE = settings(max_examples=400, suppress_health_check=[HealthCheck.too_slow])


def huella(defectos):
    """Lo que debe ser estable: código, cita, anclaje y detalle."""
    return sorted(
        (d.codigo, d.cita, d.desplazamiento_inicio, d.detalle) for d in defectos
    )


# --- H-1: todo validador es total sobre `texto` (RF-CAL-14) ------------------


@AJUSTE
@given(st.text(min_size=0, max_size=60))
def test_h1_giro_de_valor_es_total(texto: str) -> None:
    """Una prosa vacía es un modo de fallo corriente del modelo. Debe producir
    EST-01 o un error de dominio, nunca un ValidationError de Pydantic.

    Resuelto el 2026-09-23 por la sesión Jose: con texto vacío o solo espacios
    se lanza `EntradaFueraDeDominio`, porque el axioma 11 exige que la cita
    ancle y sin texto no hay pasaje que citar. El cuerpo de este test se
    completa aquí para que siga diciendo la verdad; RF-CAL-14 ya lo permitía
    —«devuelve defectos o lanza un error de dominio»—, pero solo se comprobaba
    la mitad.
    """
    try:
        defectos = validar_giro_de_valor("duda", "duda", texto, VT)
    except EntradaFueraDeDominio:
        assert not texto.strip(), "solo la prosa vacia sale por aqui"
        return
    for d in defectos:
        assert texto[d.desplazamiento_inicio : d.desplazamiento_fin] == d.cita


# --- H-2: SEG-01 falla cerrado (RF-CAL-13) ----------------------------------


@AJUSTE
@given(st.text(min_size=1, max_size=12).filter(lambda n: n not in NIVELES))
def test_h2_calor_falla_cerrado(nivel: str) -> None:
    """Una errata en el nivel declarado no puede apagar el validador en silencio."""
    texto = "Se quito la ropa y quedo desnuda ante el."
    with pytest.raises(Exception):  # noqa: B017 — el tipo lo decide P-5
        validar_nivel_de_calor(texto, nivel, VT)


# --- H-3: el arbitraje de canon no depende del orden (RF-CAL-15) ------------

hechos = st.lists(
    st.builds(
        HechoDeCanon,
        hc_id=st.sampled_from(["h1", "h2", "h3"]),
        entidad=st.just("Mara"),
        atributo=st.just("ojos"),
        valor=st.sampled_from(["verdes", "negros"]),
        orden_discurso=st.sampled_from([1, 1, 2]),
    ),
    min_size=2,
    max_size=4,
)


@AJUSTE
@given(hechos, st.randoms())
def test_h3_canon_independiente_del_orden(canon: list[HechoDeCanon], rnd) -> None:
    """Alcance pequeño de Alloy: dos hechos, dos valores y dos órdenes bastan."""
    texto = "Mara tenia los ojos azules."
    afs = [
        Afirmacion(cita="ojos azules", sujeto="Mara", atributo="ojos", valor="azules")
    ]
    barajado = list(canon)
    rnd.shuffle(barajado)
    assert huella(validar_canon(afs, canon, texto, VT)) == huella(
        validar_canon(afs, barajado, texto, VT)
    )


# --- H-4: la continuidad tampoco (RF-CAL-15) --------------------------------

afirmaciones_de_lugar = st.lists(
    st.builds(
        Afirmacion,
        cita=st.sampled_from(["uno", "dos", "tres"]),
        sujeto=st.just("Mara"),
        lugar=st.sampled_from(["taller", "puerto"]),
        momento=st.sampled_from([0, 0, 1]),
    ),
    min_size=2,
    max_size=4,
)


@AJUSTE
@given(afirmaciones_de_lugar, st.randoms())
def test_h4_continuidad_independiente_del_orden(afs: list[Afirmacion], rnd) -> None:
    """El detalle llega al prompt de reparación: si cambia con el orden, el
    reintento deja de ser reproducible."""
    texto = "uno dos tres"
    barajado = list(afs)
    rnd.shuffle(barajado)
    assert huella(validar_continuidad_fisica(afs, {}, texto, VT)) == huella(
        validar_continuidad_fisica(barajado, {}, texto, VT)
    )


# --- H-5: CON-03 contrasta información, no objetos (RF-CAL-16) --------------


def test_h5_un_objeto_fisico_no_es_informacion() -> None:
    """Hallazgo de la sesión Nubia. `derivar_estado_en_t` llena `conocimientos`
    con `evento.descripcion` —texto libre del Extractor— y aquí se compara con
    `Afirmacion.objeto`, que el prompt define como «objetos que se usan»."""
    texto = "Mara abrio la carpeta y leyo el nombre del traidor."
    conocimientos = {"Mara": ["Mara presencia la confesion de Iker en el puerto"]}
    afs = [Afirmacion(cita="la carpeta", sujeto="Mara", objeto="la carpeta")]

    assert validar_conocimiento(afs, conocimientos, texto, VT) == [], (
        "un objeto fisico corriente produce CON-03. Desde el 2026-09-23 ya no "
        "bloquea G1a -maujimenez4 lo saco de BLOQUEANTES_EN_G1A-, pero el "
        "contraste sigue siendo igualdad exacta sobre texto libre"
    )


def test_h5_la_informacion_presenciada_no_exige_literalidad() -> None:
    """Dos llamadas independientes a un modelo no coinciden palabra por palabra."""
    texto = "Mara nombro la confesion de Iker sin levantar la vista."
    conocimientos = {"Mara": ["Mara presencia la confesion de Iker en el puerto"]}
    afs = [
        Afirmacion(
            cita="la confesion de Iker",
            sujeto="Mara",
            objeto="la confesion de Iker",
        )
    ]

    assert validar_conocimiento(afs, conocimientos, texto, VT) == []


# --- H-6: el diálogo no se traga la narración (RF-CAL-13) -------------------


def test_h6_la_narracion_sobrevive_al_dialogo() -> None:
    """En español la raya abre el diálogo y la narración sigue en la misma línea.
    `—[^\\n]*` se come todo lo que va detrás, y VOZ-03 se queda ciego."""
    texto = "—Yo no fui —dijo ella. Yo camine hasta la puerta y yo espere."

    narracion = solo_narracion(texto)

    assert "camine hasta la puerta" in narracion, (
        f"la narracion desaparecio entera: {narracion!r}"
    )
    assert validar_discurso(texto, "tercera", "pasado", VT), (
        "narracion en primera persona con la obra declarada en tercera y VOZ-03 calla"
    )
