"""La cobertura de la personalizacion: lo que el comprador pidio, ¿llego al texto?

RF-VAL-05, `CA-15` y la **regla de dominio 11**, que es el axioma 15 de
`definitions.md` §11: «Todo elemento de `Brief.elementos_obligatorios[]` aparece
en al menos un `Capitulo`, comprobado contra `HechoCanon.usado_en[]`. Un dato que
el comprador pidio y no esta no es una omision: es el producto sin entregar».

**Solo se puede comprobar con la novela entera**, y por eso este modulo no esta
en el `CATALOGO` de `validadores.py`: aquellos corren en el hook de capitulo y
miran un capitulo solo. Un capitulo suelto no demuestra nada sobre la cobertura
—que el elemento no este en el 3 no es un defecto si esta en el 8—, asi que un
validador de capitulo que lo comprobara solo sabria emitir falsos positivos.

**Contra la tabla de hechos, y no con un `in` sobre la prosa.** Esa diferencia no
es un detalle de implementacion: es el requisito. Con una busqueda de subcadena
sobre el texto, «el perro Luna» quedaria cubierto por un capitulo que dijera «el
perro de Luna Ruiz» sin que ningun hecho lo respaldara, y lo que se estaria
midiendo es la casualidad lexica. Lo que cuenta aqui es `usado_en[]`, la relacion
**hacia adelante** que escribe quien integra el capitulo (`definitions.md` §4.5):
no de donde salio el hecho, sino a donde fue. Por eso a esta funcion **no entra
prosa**, y hay un test sobre su firma que lo guarda.

**Las dos formas de que este validador siempre diga que si**, que son las dos que
lo convertirian en un adorno —«un validador que siempre pasa es peor que no
tenerlo: ocupa su sitio», R-6 de la Fase 1—:

1. El **elemento vacio**. Una cadena vacia es subcadena de cualquier capitulo, y
   tambien esta contenida en cualquier hecho: «todas sus palabras estan» es
   cierto de balde sobre un conjunto sin palabras. `BriefEntrada` ya la rechaza
   con `TextoNoVacio`, pero el agujero no estaba en el esquema ni en el
   validador sino **en la juntura**, asi que aqui se tapa otra vez: un elemento
   sin ninguna palabra con contenido se declara **ausente**, nunca cubierto.
2. El **hecho del brief que ningun capitulo usa**. Entra al canon en la
   entrevista (RF-ENT-06), antes de la primera linea de prosa. Si contara, la
   cobertura seria del 100 % con la novela sin empezar. Un hecho con `usado_en`
   vacio **no cubre nada**.

**Lo que esta comprobacion NO compra**, para que nadie lo ensanche al leerlo: no
dice que el elemento este bien traido. Un dato incrustado sin funcion narrativa
cubre igual, y eso es `PER-03`, que juzga otro. `definitions.md` §7 lo dice sin
rodeos: son dos metricas y no una, porque fallan en direcciones opuestas y medir
solo la cobertura premia el relleno.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.commons.domain.normalizacion import normalizar

_PALABRA = re.compile(r"\w+", re.UNICODE)

CODIGO_DE_ELEMENTO_AUSENTE = "PER-01"
"""De la taxonomia de `definitions.md` §8: «Elemento personalizado obligatorio
que no aparece en ningun capitulo». **No se inventa uno propio**: fuera de la
taxonomia no es un defecto, y `defectos.py` lo descartaria por forma."""

PALABRAS_SIN_CONTENIDO: frozenset[str] = frozenset(
    normalizar(palabra)
    for palabra in (
        "el",
        "la",
        "lo",
        "los",
        "las",
        "un",
        "una",
        "unos",
        "unas",
        "de",
        "del",
        "al",
        "a",
        "y",
        "e",
        "o",
        "u",
        "en",
        "con",
        "por",
        "para",
        "que",
        "su",
        "sus",
        "mi",
        "mis",
        "tu",
        "tus",
    )
)
"""Articulos, preposiciones y posesivos: se quitan del **elemento**, no del
hecho. Exigir que «de» este en el hecho haria fallar la cobertura por una
preposicion, y eso son falsos positivos que nadie puede reparar.

Se normalizan al construirse porque `normalizar` recorta la `-s` final de las
palabras de mas de tres letras: «unas» normaliza a «una», y un conjunto sin
normalizar no casaria con lo que se compara contra el."""


@dataclass(frozen=True, slots=True)
class HechoUsado:
    """Un hecho del grafo **con los capitulos que se apoyan en el**.

    Es una proyeccion, no la tabla: `HechoCanon` vive en `features/obra` y una
    feature solo entra a otra por su `__init__.py` (`CLAUDE.md` §5.1). La misma
    decision que ya tomaron `puerta.py` y `agents.py`, y por el mismo motivo:
    asi esta feature se prueba sin base de datos.

    Lleva `entidad`, `atributo` y `valor` separados —como `HechoDeCanon`— porque
    eso es lo que hace comparable un hecho con otro, y `usado_en`, que es lo que
    el axioma 15 nombra. **`usado_en` no tiene valor por defecto a proposito:**
    un `()` implicito convertiria el olvido de quien construye la proyeccion en
    un elemento ausente silencioso, y la cobertura mediria el descuido.

    **`usado_en` lleva el `numero` del capitulo, no su `capitulo_id`**, y quien
    la construya tiene que hacer esa junta. La tabla es `hecho_usado_en`
    (`hecho_canon_id`, `capitulo_id`) y vive en `features/canon`; lo que sale de
    aqui lo lee una persona —«falta el perro Luna», «el anillo esta en el 5»— y
    una clave primaria no le dice nada. Pasar ids no rompe nada y produce un
    informe inutil, que es peor, porque parece que funciona.
    """

    entidad: str
    atributo: str
    valor: str
    usado_en: tuple[int, ...]

    @property
    def palabras(self) -> frozenset[str]:
        """Las tres partes juntas, normalizadas y por palabra. Por palabra y no
        por subcadena, igual que `contiene_veto`: «ana» no debe casar dentro de
        «manana»."""
        return _palabras(f"{self.entidad} {self.atributo} {self.valor}")


@dataclass(frozen=True, slots=True)
class ElementoCubierto:
    """El elemento, tal y como el comprador lo escribio, y **donde** aparece.

    Los capitulos no son decoracion: RF-PUB-05 los quiere en la `FichaDeLectura`,
    «tomados del uso registrado del hecho (RF-MEM-02)».
    """

    elemento: str
    capitulos: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ElementoAusente:
    """El que falta, **con su nombre** (R-5). «Falta algo» no permite arreglarlo.

    No es un `Defecto` y no es un olvido. Un `Defecto` lleva `version_texto_id`,
    `cita` y desplazamientos, y la regla de dominio 8 exige que la cita sea
    subcadena exacta del texto que senala: un PER-01 **senala una ausencia**, y
    no hay pasaje que citar ni version de texto a la que anclarlo. Fabricar una
    cita vacia para que encajara en la forma pasaria la comprobacion de
    `defectos.py` por la puerta de atras —la cadena vacia esta en cualquier
    desplazamiento— y es exactamente el vicio que este modulo evita en el otro
    extremo. El `codigo` si viaja, para no perder el enlace con la taxonomia.
    """

    elemento: str
    codigo: str = CODIGO_DE_ELEMENTO_AUSENTE


@dataclass(frozen=True, slots=True)
class Cobertura:
    """Los dos montones, y ambos presentes.

    Los cubiertos no sobran: sin ellos no se puede construir la ficha de lectura
    ni distinguir «no lo comprobo nadie» de «se comprobo y estaba».
    """

    cubiertos: tuple[ElementoCubierto, ...]
    ausentes: tuple[ElementoAusente, ...]

    @property
    def completa(self) -> bool:
        """Se **deriva** de `ausentes` y no es una bandera aparte: asi el estado
        «completa con ausentes» no se puede ni representar."""
        return not self.ausentes


def _palabras(texto: str) -> frozenset[str]:
    return frozenset(normalizar(hallazgo.group(0)) for hallazgo in _PALABRA.finditer(texto))


def _palabras_con_contenido(elemento: str) -> frozenset[str]:
    """Lo que hay que encontrar en un hecho. **Puede salir vacio**, y quien
    llama tiene que tratarlo: ese conjunto vacio es el agujero de R-6."""
    return _palabras(elemento) - PALABRAS_SIN_CONTENIDO


def cobertura_de_obligatorios(
    elementos_obligatorios: Sequence[str], hechos: Sequence[HechoUsado]
) -> Cobertura:
    """Que elementos del brief llegaron a un capitulo y cuales no (RF-VAL-05).

    Un elemento esta cubierto si **un solo** hecho usado en algun capitulo
    contiene todas sus palabras con contenido. Un solo hecho y no la suma de
    varios: un hecho sobre Luna que no la hace perro, mas otro sobre un perro
    que no es Luna, no demuestran juntos que «el perro Luna» llegara al texto.
    Sumar palabras sueltas de hechos distintos es inventarse la evidencia.

    El orden de salida es el del brief, en los dos montones: es el orden en que
    el comprador los pidio y el unico que le dice algo a quien lea el informe.
    """
    cubiertos: list[ElementoCubierto] = []
    ausentes: list[ElementoAusente] = []

    for elemento in elementos_obligatorios:
        buscadas = _palabras_con_contenido(elemento)
        if not buscadas:
            # El agujero de R-6. `issubset` sobre el conjunto vacio es cierto
            # contra cualquier hecho, asi que sin esta guarda un elemento vacio
            # quedaria cubierto por el primero que hubiera.
            ausentes.append(ElementoAusente(elemento=elemento))
            continue

        # **La decision se toma sobre los capitulos, no sobre los hechos que
        # casan**, y ahi vive la segunda guarda: un hecho con `usado_en` vacio
        # —el del brief, que entra en la entrevista— casa igual pero no aporta
        # ningun capitulo, asi que no cubre. Llevaba ademas un `hecho.usado_en
        # and` delante de la condicion; la mutacion de CA-6 lo quito y **no
        # cayo ningun test**, porque era codigo muerto: el bucle de dentro ya
        # no recorre nada sobre una tupla vacia. Se retira en vez de dejarlo
        # como adorno. Lo que sostiene la propiedad es este `if capitulos:`, y
        # eso si esta probado: cambiarlo por `if algun hecho casa` tumba
        # `test_un_hecho_que_ningun_capitulo_usa_no_cubre_nada`.
        capitulos = sorted(
            {
                capitulo
                for hecho in hechos
                if buscadas <= hecho.palabras
                for capitulo in hecho.usado_en
            }
        )
        if capitulos:
            cubiertos.append(ElementoCubierto(elemento=elemento, capitulos=tuple(capitulos)))
        else:
            ausentes.append(ElementoAusente(elemento=elemento))

    return Cobertura(cubiertos=tuple(cubiertos), ausentes=tuple(ausentes))
