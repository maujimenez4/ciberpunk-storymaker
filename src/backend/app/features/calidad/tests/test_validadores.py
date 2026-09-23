"""P-60 a P-66 y P-68: los validadores mecánicos y su cita.

RF-CAL-01 a RF-CAL-08 y RF-CAL-12. Cada uno tiene su caso que **falla** y su
caso que **pasa**: un validador que solo se prueba con el caso malo acaba
rechazando escenas correctas, y eso lo desactiva alguien en una semana.
"""

import pytest

from app.features.calidad import (
    Afirmacion,
    CodigoDeDefecto,
    HechoDeCanon,
    citar,
    solo_narracion,
    validar_canon,
    validar_conocimiento,
    validar_continuidad_fisica,
    validar_discurso,
    validar_giro_de_valor,
    validar_nivel_de_calor,
    validar_objetos,
)

VT = "vt1"


# --- P-66: la cita se ancla sobre el texto real ------------------------------


def test_la_cita_lleva_desplazamiento_y_literal() -> None:
    """D-06: los dos. Los desplazamientos son para el código; el literal, para
    el autor en `ESCALADA` y para el prompt de reparación."""
    texto = "La lluvia cortaba la red del taller."

    defecto = citar(texto, "cortaba la red", CodigoDeDefecto.CON_01, VT)

    assert defecto.cita == "cortaba la red"
    assert texto[defecto.desplazamiento_inicio : defecto.desplazamiento_fin] == (
        "cortaba la red"
    )


def test_no_se_puede_citar_lo_que_no_esta_en_el_texto() -> None:
    """Axioma 11 por construcción: un validador no puede emitir una cita
    inventada, que es la mitad de lo que comprueba RF-CAL-11."""
    with pytest.raises(ValueError):
        citar("La lluvia.", "el sol", CodigoDeDefecto.CON_01, VT)


def test_una_cita_vacia_se_rechaza() -> None:
    from app.features.calidad import Defecto

    with pytest.raises(ValueError):
        Defecto(
            codigo=CodigoDeDefecto.CON_01,
            version_texto_id=VT,
            cita="x",
            desplazamiento_inicio=5,
            desplazamiento_fin=5,
        )


# --- P-60: giro de valor (EST-01) -------------------------------------------


def test_una_ficha_sin_giro_da_est_01() -> None:
    defectos = validar_giro_de_valor("control", "control", "Texto cualquiera.", VT)

    assert [d.codigo for d in defectos] == [CodigoDeDefecto.EST_01]


def test_una_ficha_con_giro_no_da_defecto() -> None:
    assert validar_giro_de_valor("control", "amenaza", "Texto.", VT) == []


# --- P-61: nivel de calor (SEG-01) ------------------------------------------


def test_un_termino_por_encima_del_nivel_da_seg_01() -> None:
    texto = "Se quedaron desnudos bajo la lluvia."

    defectos = validar_nivel_de_calor(texto, "puerta_cerrada", VT)

    assert [d.codigo for d in defectos] == [CodigoDeDefecto.SEG_01]


def test_el_mismo_texto_es_valido_en_un_nivel_mas_alto() -> None:
    """Las listas son acumulativas y el nivel declarado es el que manda."""
    texto = "Se quedaron desnudos bajo la lluvia."

    assert validar_nivel_de_calor(texto, "abierto", VT) == []


def test_una_escena_casta_no_da_defecto() -> None:
    assert validar_nivel_de_calor("Se dieron la mano.", "puerta_cerrada", VT) == []


# --- P-62: continuidad física (CON-01) ---------------------------------------


def test_estar_en_dos_lugares_a_la_vez_da_con_01() -> None:
    afirmaciones = [
        Afirmacion(cita="en el taller", sujeto="Ada", lugar="taller", momento=0),
        Afirmacion(cita="en el puerto", sujeto="Ada", lugar="puerto", momento=0),
    ]
    texto = "Ada estaba en el taller y en el puerto."

    defectos = validar_continuidad_fisica(afirmaciones, {}, texto, VT)

    assert [d.codigo for d in defectos] == [CodigoDeDefecto.CON_01]


def test_llegar_antes_del_tiempo_de_viaje_da_con_01() -> None:
    """RG-04 contra los `tiempo_de_viaje` de la biblia: es lo único que hace
    detectable el teletransporte."""
    afirmaciones = [
        Afirmacion(cita="sale del taller", sujeto="Ada", lugar="taller", momento=0),
        Afirmacion(cita="llega al puerto", sujeto="Ada", lugar="puerto", momento=5),
    ]
    texto = "Ada sale del taller. Ada llega al puerto."

    defectos = validar_continuidad_fisica(
        afirmaciones, {("taller", "puerto"): 30}, texto, VT
    )

    assert len(defectos) == 1
    assert "30" in defectos[0].detalle


def test_un_viaje_con_tiempo_suficiente_no_da_defecto() -> None:
    afirmaciones = [
        Afirmacion(cita="sale del taller", sujeto="Ada", lugar="taller", momento=0),
        Afirmacion(cita="llega al puerto", sujeto="Ada", lugar="puerto", momento=45),
    ]
    texto = "Ada sale del taller. Ada llega al puerto."

    assert (
        validar_continuidad_fisica(afirmaciones, {("taller", "puerto"): 30}, texto, VT)
        == []
    )


# --- P-63: conocimiento (CON-03) --------------------------------------------


def test_usar_lo_que_no_se_sabe_da_con_03() -> None:
    afirmaciones = [
        Afirmacion(cita="menciona el incendio", sujeto="Noe", objeto="el incendio")
    ]
    texto = "Noe menciona el incendio."

    defectos = validar_conocimiento(afirmaciones, {"Ada": ["el incendio"]}, texto, VT)

    assert [d.codigo for d in defectos] == [CodigoDeDefecto.CON_03]


def test_usar_lo_que_si_se_sabe_no_da_defecto() -> None:
    afirmaciones = [
        Afirmacion(cita="menciona el incendio", sujeto="Ada", objeto="el incendio")
    ]
    texto = "Ada menciona el incendio."

    assert validar_conocimiento(afirmaciones, {"Ada": ["el incendio"]}, texto, VT) == []


# --- P-64: canon (CAN-01) ----------------------------------------------------


def test_contradecir_el_canon_da_can_01_y_cita_el_hecho() -> None:
    """Axioma 12: un CAN-01 declara con qué hecho choca. Sin eso, el prompt de
    reparación no sabe cuál es el valor correcto."""
    canon = [
        HechoDeCanon(
            hc_id="hc1",
            entidad="Ada",
            atributo="ojos",
            valor="verdes",
            orden_discurso=3,
        )
    ]
    afirmaciones = [
        Afirmacion(cita="ojos grises", sujeto="Ada", atributo="ojos", valor="grises")
    ]
    texto = "Los ojos grises de Ada."

    defectos = validar_canon(afirmaciones, canon, texto, VT)

    assert defectos[0].codigo is CodigoDeDefecto.CAN_01
    assert defectos[0].hecho_canon_id == "hc1"


def test_prevalece_el_hecho_de_menor_orden_discurso() -> None:
    """RG-03. Lo escrito antes gana: el lector ya lo leyó y no se le puede
    desmentir sin pagarlo."""
    canon = [
        HechoDeCanon(
            hc_id="tardio",
            entidad="Ada",
            atributo="ojos",
            valor="grises",
            orden_discurso=9,
        ),
        HechoDeCanon(
            hc_id="temprano",
            entidad="Ada",
            atributo="ojos",
            valor="verdes",
            orden_discurso=2,
        ),
    ]
    afirmaciones = [
        Afirmacion(cita="ojos grises", sujeto="Ada", atributo="ojos", valor="grises")
    ]

    defectos = validar_canon(afirmaciones, canon, "Los ojos grises.", VT)

    assert defectos[0].hecho_canon_id == "temprano"


def test_coincidir_con_el_canon_no_da_defecto() -> None:
    canon = [
        HechoDeCanon(
            hc_id="hc1",
            entidad="Ada",
            atributo="ojos",
            valor="verdes",
            orden_discurso=3,
        )
    ]
    afirmaciones = [
        Afirmacion(cita="ojos verdes", sujeto="Ada", atributo="ojos", valor="verdes")
    ]

    assert validar_canon(afirmaciones, canon, "Los ojos verdes.", VT) == []


# --- P-65: objetos (CON-02) --------------------------------------------------


@pytest.mark.parametrize("estado", ["perdido", "roto", "destruido"])
def test_usar_un_objeto_no_disponible_da_con_02(estado: str) -> None:
    afirmaciones = [Afirmacion(cita="abrio la caja", objeto="caja")]

    defectos = validar_objetos(afirmaciones, {"caja": estado}, "Ada abrio la caja.", VT)

    assert [d.codigo for d in defectos] == [CodigoDeDefecto.CON_02]


@pytest.mark.parametrize("estado", ["intacto", "oculto"])
def test_un_objeto_disponible_no_da_defecto(estado: str) -> None:
    """`oculto` no es indisponible: se puede encontrar, y rechazarlo impediría
    escribir la escena en que aparece."""
    afirmaciones = [Afirmacion(cita="abrio la caja", objeto="caja")]

    assert (
        validar_objetos(afirmaciones, {"caja": estado}, "Ada abrio la caja.", VT) == []
    )


# --- P-68: persona y tiempo verbal (VOZ-03) ---------------------------------


def test_narrar_en_primera_cuando_la_obra_es_en_tercera_da_voz_03() -> None:
    texto = "Yo crucé el taller y me quedé mirando la grieta."

    defectos = validar_discurso(texto, "tercera", "pasado", VT)

    assert CodigoDeDefecto.VOZ_03 in [d.codigo for d in defectos]


def test_el_dialogo_en_primera_no_dispara_voz_03() -> None:
    """El caso que hace útil al validador en vez de insufrible: un personaje
    habla en primera dentro de una narración en tercera, y eso es correcto."""
    texto = "Ada cruzó el taller. —Yo no pienso firmar —dijo ella, y lo miró."

    assert validar_discurso(texto, "tercera", "pasado", VT) == []


def test_solo_narracion_quita_el_dialogo() -> None:
    texto = "Ada miró. «Yo no voy» dijo. —Yo tampoco— añadió."

    limpio = solo_narracion(texto)

    assert "Ada miró" in limpio
    assert "Yo no voy" not in limpio


def test_una_narracion_en_el_tiempo_declarado_no_da_defecto() -> None:
    assert validar_discurso("Ada cruzó el taller.", "tercera", "pasado", VT) == []


# --- El limite conocido del contraste: igualdad exacta de texto libre -------
#
# Estos cuatro tests no comprueban que el validador acierte: comprueban que
# **falla de la forma que sabemos**, y son la razon por la que CAN-01 y CON-03
# no bloquean G1a (`defectos.py`). Si alguien arregla el contraste, se pondran
# en rojo, y eso es lo que se busca: obligan a volver a mirar la decision de
# bloqueo en vez de dejarla enterrada.
#
# El fondo: `conocimientos` lo llena el Extractor con `evento.descripcion`, y
# `Afirmacion` la llena el Continuista. Dos llamadas independientes al modelo,
# las dos en texto libre.


def test_con_03_se_dispara_con_un_objeto_fisico_cualquiera() -> None:
    """`objeto` significa dos cosas a la vez en `continuista.v1.md`.

    Para CON-02 es un objeto fisico; para CON-03, la informacion que alguien
    usa. El mismo campo lleva las dos, asi que una carpeta se contrasta contra
    la lista de lo que el personaje sabe y nunca esta ahi.
    """
    afirmacion = Afirmacion(cita="la carpeta", sujeto="pj-ada", objeto="la carpeta")

    defectos = validar_conocimiento(
        [afirmacion], {"pj-ada": ["Noe se niega a firmar"]}, "la carpeta", VT
    )

    assert [d.codigo for d in defectos] == [CodigoDeDefecto.CON_03]


def test_con_03_se_dispara_aunque_el_personaje_lo_presenciara() -> None:
    """Lo presencio, pero el Continuista lo dice con otras palabras."""
    afirmacion = Afirmacion(
        cita="Noe no quiere firmar", sujeto="pj-ada", objeto="Noe no quiere firmar"
    )

    defectos = validar_conocimiento(
        [afirmacion], {"pj-ada": ["Noe se niega a firmar"]}, "Noe no quiere firmar", VT
    )

    assert [d.codigo for d in defectos] == [CodigoDeDefecto.CON_03]


def test_con_03_solo_queda_limpio_si_la_cadena_coincide_palabra_por_palabra() -> None:
    afirmacion = Afirmacion(
        cita="Noe no quiere firmar", sujeto="pj-ada", objeto="Noe se niega a firmar"
    )

    assert (
        validar_conocimiento(
            [afirmacion],
            {"pj-ada": ["Noe se niega a firmar"]},
            "Noe no quiere firmar",
            VT,
        )
        == []
    )


def test_can_01_se_dispara_con_el_mismo_hecho_dicho_de_otra_forma() -> None:
    """El arbitraje de RG-03 es correcto; lo fragil es comparar los valores.

    `establecido.valor != a.valor` sobre texto libre convierte un sinonimo en
    una contradiccion de canon.
    """
    canon = [
        HechoDeCanon(
            hc_id="hc1",
            entidad="pj-noe",
            atributo="postura",
            valor="se niega a firmar",
            orden_discurso=1,
        )
    ]
    afirmacion = Afirmacion(
        cita="Noe no quiere firmar",
        sujeto="pj-noe",
        atributo="postura",
        valor="no quiere firmar",
    )

    defectos = validar_canon([afirmacion], canon, "Noe no quiere firmar", VT)

    assert [d.codigo for d in defectos] == [CodigoDeDefecto.CAN_01]
