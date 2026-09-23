"""RF-CAL-13 a RF-CAL-17: las invariantes de los validadores, como propiedades.

**Por que propiedades y no ejemplos.** Los seis defectos que estos tests fijan
los encontro la sesion Gustavo sondeando invariantes en alcance pequeno, no
leyendo el codigo, y ninguno lo habria cazado un test de ejemplo: cada funcion
tenia su caso bueno y su caso malo en verde desde la fase 6. Un ejemplo
arreglado protege ese ejemplo; una propiedad protege la funcion.

La sonda original vive en `specs/005-validadores-fallo-cerrado/` como registro
de los hallazgos. Esto es lo que queda vigilandolos.
"""

from random import Random

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.commons.errors import EntradaFueraDeDominio
from app.features.calidad import (
    Afirmacion,
    CodigoDeDefecto,
    Defecto,
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
AJUSTE = settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])


def huella(defectos: list[Defecto]) -> list[tuple[CodigoDeDefecto, str, int, str]]:
    """Lo que debe ser estable: codigo, cita, anclaje y detalle."""
    return sorted(
        (d.codigo, d.cita, d.desplazamiento_inicio, d.detalle) for d in defectos
    )


# --- RF-CAL-14: total sobre `texto` -----------------------------------------


@AJUSTE
@given(st.text(min_size=0, max_size=60))
def test_el_giro_de_valor_nunca_revienta_con_un_validation_error(texto: str) -> None:
    """Prosa vacia es un modo de fallo corriente del modelo.

    O emite EST-01 con su cita anclada, o dice que no puede evaluar. Lo que no
    puede es reventar con un `ValidationError` de Pydantic, que el orquestador
    no sabe distinguir de un fallo tecnico y acaba en `FALLIDA` en vez de en el
    defecto que era.
    """
    try:
        defectos = validar_giro_de_valor("duda", "duda", texto, VT)
    except EntradaFueraDeDominio:
        assert not texto.strip()
        return
    for defecto in defectos:
        trozo = texto[defecto.desplazamiento_inicio : defecto.desplazamiento_fin]
        assert trozo == defecto.cita


# --- RF-CAL-13: los guardarrailes fallan cerrados ---------------------------


@AJUSTE
@given(st.text(min_size=1, max_size=12).filter(lambda n: n not in NIVELES))
def test_un_nivel_de_calor_desconocido_no_apaga_el_validador(nivel: str) -> None:
    """Regla 5 de §8 y SEG-01.

    Devolver `[]` ante un nivel fuera de la escala era decir «no he encontrado
    nada malo»: una errata en el `nivel_de_calor` de la obra desactivaba el
    guardarrail entero sin una linea de aviso.
    """
    texto = "Se quito la ropa y quedo desnuda ante el."

    with pytest.raises(EntradaFueraDeDominio):
        validar_nivel_de_calor(texto, nivel, VT)


@pytest.mark.parametrize("nivel", NIVELES)
def test_los_niveles_de_la_escala_siguen_evaluandose(nivel: str) -> None:
    """El control negativo: fallar cerrado no puede volverse fallar siempre."""
    validar_nivel_de_calor("Cruzo el taller sin mirarlo.", nivel, VT)


# --- RF-CAL-15: la salida no depende del orden de la entrada ----------------

_hechos = st.lists(
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
@given(_hechos, st.randoms())
def test_el_arbitraje_de_canon_no_depende_del_orden(
    canon: list[HechoDeCanon], rnd: Random
) -> None:
    """El `hecho_canon_id` que sale es el que exige el axioma 12 y el que viaja
    al prompt de reparacion: si cambia con el orden de la lista, la ejecucion
    deja de ser reproducible (`CLAUDE.md` §3, punto 6)."""
    afirmaciones = [
        Afirmacion(cita="ojos azules", sujeto="Mara", atributo="ojos", valor="azules")
    ]
    barajado = list(canon)
    rnd.shuffle(barajado)

    assert huella(
        validar_canon(afirmaciones, canon, "Mara tenia los ojos azules.", VT)
    ) == huella(
        validar_canon(afirmaciones, barajado, "Mara tenia los ojos azules.", VT)
    )


_lugares = st.lists(
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
@given(_lugares, st.randoms())
def test_la_continuidad_fisica_no_depende_del_orden(
    afirmaciones: list[Afirmacion], rnd: Random
) -> None:
    barajado = list(afirmaciones)
    rnd.shuffle(barajado)

    assert huella(
        validar_continuidad_fisica(afirmaciones, {}, "uno dos tres", VT)
    ) == huella(validar_continuidad_fisica(barajado, {}, "uno dos tres", VT))


# --- RF-CAL-16: CON-03 contrasta informacion, no objetos --------------------


def test_un_objeto_fisico_no_se_contrasta_contra_lo_que_alguien_sabe() -> None:
    """`objeto` y `informacion` eran el mismo campo, asi que una carpeta se
    buscaba en la lista de lo que el personaje sabe y nunca estaba."""
    afirmaciones = [Afirmacion(cita="la carpeta", sujeto="Mara", objeto="la carpeta")]

    defectos = validar_conocimiento(
        afirmaciones,
        {"Mara": ["Mara presencia la confesion de Iker en el puerto"]},
        "Mara abrio la carpeta y leyo el nombre del traidor.",
        VT,
    )

    assert defectos == []


def test_la_informacion_presenciada_no_exige_coincidencia_literal() -> None:
    """El Extractor y el Continuista son dos llamadas independientes: no
    redactan igual. Exigir literalidad convertia cada sinonimo en CON-03."""
    afirmaciones = [
        Afirmacion(
            cita="la confesion de Iker",
            sujeto="Mara",
            informacion="la confesion de Iker",
        )
    ]

    defectos = validar_conocimiento(
        afirmaciones,
        {"Mara": ["Mara presencia la confesion de Iker en el puerto"]},
        "Mara nombro la confesion de Iker sin levantar la vista.",
        VT,
    )

    assert defectos == []


def test_lo_que_nadie_presencio_sigue_dando_con_03() -> None:
    """El control negativo: bajar el falso positivo no puede apagar la regla."""
    afirmaciones = [
        Afirmacion(
            cita="el incendio del puerto",
            sujeto="Mara",
            informacion="el incendio del puerto",
        )
    ]

    defectos = validar_conocimiento(
        afirmaciones,
        {"Mara": ["Mara presencia la confesion de Iker"]},
        "Mara hablo del incendio del puerto como si lo hubiera visto.",
        VT,
    )

    assert [d.codigo.value for d in defectos] == ["CON-03"]


# --- RF-CAL-13: la narracion sobrevive al dialogo ---------------------------


def test_la_narracion_detras_de_la_raya_no_desaparece() -> None:
    """En espanol la raya abre el dialogo y el inciso del narrador lo reabre.

    VOZ-03 llevaba ciego desde que existe, y en romance el dialogo es casi toda
    la escena: la regla 10 de §8 la sostenia solo el prompt.
    """
    texto = "—Yo no fui —dijo ella. Yo camine hasta la puerta y yo espere."

    narracion = solo_narracion(texto)

    assert "camine hasta la puerta" in narracion
    assert "Yo no fui" not in narracion
    assert validar_discurso(texto, "tercera", "pasado", VT)


def test_el_dialogo_en_primera_sigue_sin_disparar_voz_03() -> None:
    """El control negativo que ya existia, con la regla nueva: un personaje
    habla en primera dentro de una narracion en tercera y eso es correcto."""
    texto = "Ada cruzó el taller. —Yo no pienso firmar —dijo ella, y lo miró."

    assert validar_discurso(texto, "tercera", "pasado", VT) == []


# --- RF-CAL-13, H-7: VOZ-03 tampoco se apaga en silencio --------------------


@pytest.mark.parametrize(
    ("persona", "tiempo"),
    [
        ("PASADO", "pasado"),
        ("segunda", "pasado"),
        ("tercera", "PASADO"),
        ("tercera", "preterito"),
    ],
)
def test_un_discurso_fuera_de_dominio_no_apaga_voz_03(
    persona: str, tiempo: str
) -> None:
    """Lo encontro la sesion Hernan con los seis arreglos ya dentro.

    `_MARCAS_DE_TIEMPO.get(...)` devolvia `None` y la comprobacion se saltaba
    entera, asi que «PASADO» apagaba media regla 10 de §8 sin una linea de
    aviso; y `_MARCAS_DE_PERSONA[persona]` subia un `KeyError` pelado, que es
    peor que el `ValidationError` de H-1 porque ni siquiera esta tipado.
    """
    with pytest.raises(EntradaFueraDeDominio):
        validar_discurso("Ada cruzó el taller.", persona, tiempo, VT)


@pytest.mark.parametrize("persona", ["primera", "tercera"])
@pytest.mark.parametrize("tiempo", ["pasado", "presente"])
def test_el_discurso_declarado_en_la_escala_sigue_evaluandose(
    persona: str, tiempo: str
) -> None:
    """El control negativo: fallar cerrado no puede volverse fallar siempre."""
    validar_discurso("Ada cruzó el taller sin mirarlo.", persona, tiempo, VT)
