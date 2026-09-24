"""Regla de dominio 10 (axioma 13). Se comprueba EN EL TEXTO, no en el prompt."""

from app.features.calidad import (
    CapituloAValidar,
    NombreDeCanon,
    ParametrosDeDiscurso,
    Persona,
    RangoDeExtension,
    TiempoVerbal,
    discurso,
)


def capitulo(texto: str, persona: Persona, tiempo: TiempoVerbal) -> CapituloAValidar:
    return CapituloAValidar(
        version_texto_id="vt-1",
        texto=texto,
        rango_de_extension=RangoDeExtension(minimo=0, maximo=10_000),
        discurso=ParametrosDeDiscurso(persona=persona, tiempo_verbal=tiempo),
        nombres_del_canon=(NombreDeCanon(forma_canonica="Marta"),),
    )


EN_TERCERA_Y_PASADO = "Marta cerró la puerta. Estaba cansada y no dijo nada."
EN_PRIMERA_Y_PASADO = "Yo cerré la puerta. Estaba cansada y no dije nada."
EN_TERCERA_Y_PRESENTE = "Marta cierra la puerta. Está cansada y no dice nada."


def test_narracion_en_primera_con_tercera_declarada_es_defecto_voz_03():
    defectos = discurso(
        capitulo(EN_PRIMERA_Y_PASADO, Persona.TERCERA_LIMITADA, TiempoVerbal.PASADO)
    )

    assert [d.codigo for d in defectos] == ["VOZ-03"]


def test_narracion_en_tercera_con_tercera_declarada_pasa():
    assert (
        discurso(capitulo(EN_TERCERA_Y_PASADO, Persona.TERCERA_LIMITADA, TiempoVerbal.PASADO)) == []
    )


def test_narracion_sin_marcas_de_primera_con_primera_declarada_es_defecto_voz_03():
    defectos = discurso(capitulo(EN_TERCERA_Y_PASADO, Persona.PRIMERA, TiempoVerbal.PASADO))

    assert [d.codigo for d in defectos] == ["VOZ-03"]


def test_narracion_en_primera_con_primera_declarada_pasa():
    assert discurso(capitulo(EN_PRIMERA_Y_PASADO, Persona.PRIMERA, TiempoVerbal.PASADO)) == []


def test_narracion_en_presente_con_pasado_declarado_es_defecto_voz_03():
    defectos = discurso(
        capitulo(EN_TERCERA_Y_PRESENTE, Persona.TERCERA_LIMITADA, TiempoVerbal.PASADO)
    )

    assert [d.codigo for d in defectos] == ["VOZ-03"]


def test_narracion_en_presente_con_presente_declarado_pasa():
    capi = capitulo(EN_TERCERA_Y_PRESENTE, Persona.TERCERA_LIMITADA, TiempoVerbal.PRESENTE)

    assert discurso(capi) == []


def test_el_dialogo_no_dispara_el_defecto_de_persona():
    """`verification.md` §8.1: el validador de discurso EXCLUYE el dialogo a
    proposito. Un personaje habla en primera persona en una novela escrita en
    tercera, y eso no es un defecto: es una novela."""
    texto = "Marta cerró la puerta.\n—Yo no dije nada —murmuró ella.\nLa casa estaba en silencio."

    assert discurso(capitulo(texto, Persona.TERCERA_LIMITADA, TiempoVerbal.PASADO)) == []


def test_el_dialogo_no_dispara_el_defecto_de_tiempo_verbal():
    """El presente vive en el dialogo **mas veces que el pasado en la
    narracion**, que es lo unico que hace caer este test si la exclusion se
    rompe: la comparacion es por dominancia, asi que una linea de dialogo corta
    no bastaria y el test pasaria sin comprobar nada."""
    texto = (
        "Marta cerró la puerta.\n"
        "—Ahora es tarde, no hay nadie y todo está cerrado; nadie responde —murmuró.\n"
        "No dijo más."
    )

    assert discurso(capitulo(texto, Persona.TERCERA_LIMITADA, TiempoVerbal.PASADO)) == []


def test_el_defecto_de_discurso_cita_el_pasaje_en_su_desplazamiento():
    texto = EN_PRIMERA_Y_PASADO
    (defecto,) = discurso(capitulo(texto, Persona.TERCERA_LIMITADA, TiempoVerbal.PASADO))

    assert texto[defecto.desplazamiento_inicio : defecto.desplazamiento_fin] == defecto.cita
