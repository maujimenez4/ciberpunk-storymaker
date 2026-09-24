"""CA-15 · RF-VAL-05 · R-5. Lo que el comprador pidio, ¿llego al texto?

La regla de dominio 11, y el axioma 15 de `definitions.md` §11: «Todo elemento
de `Brief.elementos_obligatorios[]` aparece en al menos un `Capitulo`,
comprobado contra `HechoCanon.usado_en[]`».

**Estos tests vigilan dos formas de que el validador siempre diga que si**, que
son la unica manera de que ocupe su sitio sin hacer su trabajo:

1. La **cadena vacia** contada como cubierta (R-6 de la Fase 1).
2. El **hecho del brief que ningun capitulo usa** contado como cubierto: si
   valiera, cada elemento estaria cubierto desde la entrevista y la novela
   entera no tendria que mencionar nada.
"""

import inspect

import pytest

from app.features.calidad import (
    CODIGO_DE_ELEMENTO_AUSENTE,
    CODIGOS_DE_LA_TAXONOMIA,
    Cobertura,
    HechoUsado,
    cobertura_de_obligatorios,
)

LUNA = HechoUsado(entidad="Luna", atributo="especie", valor="perro", usado_en=(3, 7))
ANILLO = HechoUsado(entidad="anillo", atributo="procedencia", valor="de la abuela", usado_en=(5,))


def test_un_elemento_que_un_hecho_recoge_esta_cubierto():
    """El caso feliz, y por si solo no demuestra nada: ver los de abajo."""
    resultado = cobertura_de_obligatorios(["el perro Luna"], [LUNA])

    assert resultado.completa
    assert resultado.ausentes == ()
    assert [(c.elemento, c.capitulos) for c in resultado.cubiertos] == [("el perro Luna", (3, 7))]


def test_un_elemento_que_ningun_hecho_recoge_se_senala_por_su_nombre():
    """R-5 · CA-15. «Falta algo» no permite arreglarlo: hay que decir cual.

    Y es el test que impide una funcion que devuelva siempre «todo bien».
    """
    resultado = cobertura_de_obligatorios(["el perro Luna", "el anillo de la abuela"], [ANILLO])

    assert not resultado.completa
    assert [a.elemento for a in resultado.ausentes] == ["el perro Luna"]
    assert [c.elemento for c in resultado.cubiertos] == ["el anillo de la abuela"]


def test_se_senalan_todos_los_ausentes_y_no_solo_el_primero():
    """Con dos que faltan, decir uno deja el segundo sin reparar."""
    resultado = cobertura_de_obligatorios(["el perro Luna", "el anillo de la abuela"], [])

    assert [a.elemento for a in resultado.ausentes] == ["el perro Luna", "el anillo de la abuela"]


def test_el_codigo_del_elemento_ausente_es_per_01_y_esta_en_la_taxonomia():
    """`definitions.md` §8: PER-01 es «elemento personalizado obligatorio que no
    aparece en ningun capitulo». Un codigo fuera de la taxonomia no es un
    defecto, y este validador no puede inventarse el suyo."""
    resultado = cobertura_de_obligatorios(["el perro Luna"], [])

    assert [a.codigo for a in resultado.ausentes] == ["PER-01"]
    assert CODIGO_DE_ELEMENTO_AUSENTE in CODIGOS_DE_LA_TAXONOMIA


@pytest.mark.parametrize("vacio", ["", "   ", "\t\n"])
def test_la_cadena_vacia_nunca_cuenta_como_cubierta(vacio: str):
    """**El agujero que R-6 de la Fase 1 existe para impedir.**

    Su motivo, literal: «una cadena vacia es subcadena de cualquier capitulo,
    asi que el validador de cobertura daria 100 %. Un validador que siempre pasa
    es peor que no tenerlo: ocupa su sitio». El esquema del brief ya la rechaza,
    y aqui se rechaza **otra vez**, porque la juntura es lo que fallaba: un
    elemento sin ninguna palabra con contenido no tiene nada que buscar en un
    hecho, y «todas sus palabras estan» sobre un conjunto vacio es cierto de
    balde. Se declara ausente, que es lo unico honesto.
    """
    resultado = cobertura_de_obligatorios([vacio], [LUNA, ANILLO])

    assert not resultado.completa
    assert [a.elemento for a in resultado.ausentes] == [vacio]


@pytest.mark.parametrize("solo_vacias", ["el", "de la", "y el de la"])
def test_un_elemento_hecho_solo_de_palabras_sin_contenido_tampoco_cuenta(solo_vacias: str):
    """La misma puerta por el otro lado: «de la» no es menos vacio que «».

    Y «de la» esta elegido a proposito: son palabras que `ANILLO` **si** tiene,
    asi que sin la guarda quedaria cubierto, no ausente por casualidad.

    **El tercer caso decia «los unos y los otros» y pasaba por el motivo
    equivocado.** Lo destapo la mutacion de CA-6: al quitar la guarda ese caso
    seguia en verde, porque «otros» normaliza a «otro», que **no** es una
    palabra sin contenido —el elemento no estaba vacio— y ningun hecho la tiene.
    Comprobaba que un elemento inventado no esta, no que el vacio no cuenta.
    """
    resultado = cobertura_de_obligatorios([solo_vacias], [LUNA, ANILLO])

    assert [a.elemento for a in resultado.ausentes] == [solo_vacias]


def test_un_hecho_que_ningun_capitulo_usa_no_cubre_nada():
    """**La segunda forma de que el validador siempre diga que si.**

    El hecho del brief —«el perro se llama Luna»— entra al canon en la
    entrevista (RF-ENT-06) y esta en la tabla desde antes de escribir la primera
    linea. Si contara, la cobertura seria del 100 % con la novela sin empezar.
    Lo que cuenta es `usado_en[]`, que lo escribe **quien integra el capitulo**
    (`definitions.md` §4.5): la relacion hacia adelante, no la de origen.
    """
    del_brief = HechoUsado(entidad="Luna", atributo="especie", valor="perro", usado_en=())

    resultado = cobertura_de_obligatorios(["el perro Luna"], [del_brief])

    assert not resultado.completa
    assert [a.elemento for a in resultado.ausentes] == ["el perro Luna"]


def test_las_palabras_del_elemento_deben_estar_todas_en_el_mismo_hecho():
    """Un hecho sobre Luna que no la hace perro, y otro sobre un perro que no es
    Luna, no demuestran juntos que «el perro Luna» llegara a ningun capitulo.
    Sumar palabras sueltas de hechos distintos es inventarse la evidencia."""
    media_luna = HechoUsado(entidad="Luna", atributo="color", valor="blanco", usado_en=(2,))
    medio_perro = HechoUsado(entidad="Nala", atributo="especie", valor="perro", usado_en=(4,))

    resultado = cobertura_de_obligatorios(["el perro Luna"], [media_luna, medio_perro])

    assert [a.elemento for a in resultado.ausentes] == ["el perro Luna"]


def test_los_acentos_y_los_plurales_no_rompen_la_cobertura():
    """RF-GUA-02 usa el mismo `normalizar` de `commons`: «Ivan» cubre «Iván», y
    «cartas» cubre «carta». Sin esto la cobertura pediria literalidad al texto,
    que es justo lo que PER-02 —no este validador— vigila."""
    hecho = HechoUsado(entidad="Ivan", atributo="objeto", valor="carta", usado_en=(9,))

    resultado = cobertura_de_obligatorios(["las cartas de Iván"], [hecho])

    assert resultado.completa
    assert resultado.cubiertos[0].capitulos == (9,)


def test_los_capitulos_de_un_elemento_salen_ordenados_y_sin_repetir():
    """Se agregan los de todos los hechos que lo recogen: `usado_en[]` es por
    hecho, y un elemento puede estar en varios."""
    otro = HechoUsado(entidad="Luna", atributo="raza", valor="perro pastor", usado_en=(1, 3))

    resultado = cobertura_de_obligatorios(["el perro Luna"], [LUNA, otro])

    assert resultado.cubiertos[0].capitulos == (1, 3, 7)


def test_la_cobertura_no_recibe_el_texto_de_ningun_capitulo():
    """RF-VAL-05 dice «comprobado **contra la tabla de hechos**», y esa
    diferencia es el requisito. Con un `in` sobre la prosa, «el perro Luna»
    quedaria cubierto por un capitulo que dice «el perro de Luna Ruiz» sin que
    ningun hecho lo respalde, y la cobertura mediria la casualidad lexica.

    Lo que lo garantiza es la **firma**: aqui no entra prosa. Si alguien anade
    un parametro de texto, este test cae y tendra que decir por que.
    """
    parametros = inspect.signature(cobertura_de_obligatorios).parameters

    assert list(parametros) == ["elementos_obligatorios", "hechos"]


def test_sin_ausentes_la_cobertura_es_completa_y_con_uno_no():
    """`completa` es lo que mira la puerta; que se derive de `ausentes` y no de
    una bandera aparte evita el estado imposible «completa con ausentes»."""
    assert Cobertura(cubiertos=(), ausentes=()).completa
    assert not cobertura_de_obligatorios(["el perro Luna"], []).completa
