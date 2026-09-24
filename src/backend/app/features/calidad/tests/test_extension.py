"""CA-35 · RF-VAL-04. Por los tres lados: corto, largo y dentro."""

from app.features.calidad import (
    CapituloAValidar,
    NombreDeCanon,
    ParametrosDeDiscurso,
    Persona,
    RangoDeExtension,
    TiempoVerbal,
    extension_de_capitulo,
)

RANGO = RangoDeExtension(minimo=10, maximo=20)
DISCURSO = ParametrosDeDiscurso(persona=Persona.TERCERA_LIMITADA, tiempo_verbal=TiempoVerbal.PASADO)


def capitulo(texto: str) -> CapituloAValidar:
    return CapituloAValidar(
        version_texto_id="vt-1",
        texto=texto,
        rango_de_extension=RANGO,
        discurso=DISCURSO,
        nombres_del_canon=(NombreDeCanon(forma_canonica="Marta"),),
    )


def palabras(n: int) -> str:
    return " ".join(["palabra"] * n)


def test_un_capitulo_por_debajo_del_rango_es_defecto_est_02():
    defectos = extension_de_capitulo(capitulo(palabras(5)))

    assert [d.codigo for d in defectos] == ["EST-02"]


def test_un_capitulo_por_encima_del_rango_es_defecto_est_02():
    defectos = extension_de_capitulo(capitulo(palabras(30)))

    assert [d.codigo for d in defectos] == ["EST-02"]


def test_un_capitulo_dentro_del_rango_pasa():
    assert extension_de_capitulo(capitulo(palabras(15))) == []


def test_los_extremos_del_rango_estan_dentro():
    """«Dentro del rango declarado» incluye el rango. Una frontera mal puesta
    devuelve al escritor un capitulo que cumple."""
    assert extension_de_capitulo(capitulo(palabras(10))) == []
    assert extension_de_capitulo(capitulo(palabras(20))) == []


def test_el_defecto_de_extension_cita_el_capitulo_entero_en_su_desplazamiento():
    texto = palabras(5)
    (defecto,) = extension_de_capitulo(capitulo(texto))

    assert texto[defecto.desplazamiento_inicio : defecto.desplazamiento_fin] == defecto.cita
