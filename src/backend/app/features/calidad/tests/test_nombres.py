"""CA-16 · RF-VAL-03. La diferencia esta en el canon, no en la astucia del validador."""

from app.features.calidad import (
    CapituloAValidar,
    NombreDeCanon,
    ParametrosDeDiscurso,
    Persona,
    RangoDeExtension,
    TiempoVerbal,
    nombres_literales,
)

DISCURSO = ParametrosDeDiscurso(persona=Persona.TERCERA_LIMITADA, tiempo_verbal=TiempoVerbal.PASADO)


def capitulo(texto: str, *nombres: NombreDeCanon) -> CapituloAValidar:
    return CapituloAValidar(
        version_texto_id="vt-1",
        texto=texto,
        rango_de_extension=RangoDeExtension(minimo=0, maximo=10_000),
        discurso=DISCURSO,
        nombres_del_canon=nombres,
    )


MARIA = NombreDeCanon(forma_canonica="María", variantes=("Mari",))
IVAN = NombreDeCanon(forma_canonica="Iván", variantes=("Ivan",))


def test_maria_sin_tilde_es_defecto_per_02():
    defectos = nombres_literales(capitulo("Aquella tarde Maria cerró la puerta.", MARIA))

    assert [(d.codigo, d.cita) for d in defectos] == [("PER-02", "Maria")]


def test_una_variante_declarada_no_es_defecto():
    """«Mari» por «María» NO es defecto si el canon la declara (CA-16).

    **Y este test solo, por si solo, no demuestra que `variantes` sirva de
    algo.** Se comprobo quitando `variantes` del conjunto aceptado: sigue en
    verde, porque «Mari» ni siquiera se parece a «María» para `normalizar` —no
    comparten forma normalizada— y el validador no la habria mirado de todas
    formas. Es el caso de CA-16 y hay que tenerlo, pero pasa por un motivo que
    no es el que el criterio quiere proteger. Quien lo protege es el de abajo.
    """
    assert nombres_literales(capitulo("Aquella tarde Mari cerró la puerta.", MARIA)) == []


def test_una_variante_declarada_que_si_colisiona_con_la_forma_canonica_no_es_defecto():
    """La declaracion del canon **gana** a la sospecha del validador.

    «Ivan» sin tilde es exactamente lo que `nombres_literales` senalaria como
    `PER-02`: misma forma normalizada que «Iván», otra grafia. Si el canon la
    declara variante —porque asi lo escribe quien encarga la novela—, deja de
    serlo. Quitar `variantes` del conjunto aceptado pone **este** test en rojo,
    que es lo que hace comprobable la mitad de CA-16 que el de arriba no alcanza.
    """
    assert nombres_literales(capitulo("Aquella tarde Ivan cerró la puerta.", IVAN)) == []


def test_la_forma_canonica_no_es_defecto():
    assert nombres_literales(capitulo("Aquella tarde María cerró la puerta.", MARIA)) == []


def test_una_variante_no_declarada_no_se_persigue():
    """Punto ciego declarado (`verification.md` §8.1): si el canon no declara la
    variante, no hay contra que comparar y el validador calla. Perseguirla es
    justo lo que CA-16 prohibe."""
    solo_maria = NombreDeCanon(forma_canonica="María")

    assert nombres_literales(capitulo("Aquella tarde Mari cerró la puerta.", solo_maria)) == []


def test_la_minuscula_es_otra_grafia_y_es_defecto():
    defectos = nombres_literales(capitulo("Aquella tarde maría cerró la puerta.", MARIA))

    assert [d.cita for d in defectos] == ["maría"]


def test_el_nombre_no_salta_dentro_de_otra_palabra():
    nala = NombreDeCanon(forma_canonica="Nala")

    assert nombres_literales(capitulo("La sala estaba vacía.", nala)) == []


def test_el_defecto_de_nombre_cita_la_palabra_en_su_desplazamiento():
    texto = "Aquella tarde Maria cerró la puerta."
    (defecto,) = nombres_literales(capitulo(texto, MARIA))

    assert texto[defecto.desplazamiento_inicio : defecto.desplazamiento_fin] == defecto.cita
