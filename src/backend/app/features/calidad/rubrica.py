"""La rubrica con la que se juzga un capitulo (RF-JUZ-01, RF-JUZ-02, `CA-20`).

Es el **instrumento compartido** entre el juez automatico y la revision humana
(`definitions.md` §8). Ahi esta todo su valor: si cada uno puntuara con su propio
criterio, la distancia de `RF-JUZ-05` no mediria la calidad del juez, mediria que
dos personas distintas miran cosas distintas.

**Una rubrica sin anclajes descritos no es una rubrica, es una escala.** Por eso
cada criterio dice que se ve en el texto cuando vale 1 y que se ve cuando vale 5,
y no se conforma con nombrarlo. Un criterio sin anclaje es una opinion con un
numero delante.

**Los anclajes describen lo observable, no lo deseable**, y desde la revision de
P-02 eso importa mas: el juez corre en el **mismo Haiku 4.5** que escribio el
capitulo. Un juez que comparte modelo y entrenamiento con el autor tiende a
aprobar su propio estilo, asi que la distancia saldra mejor de lo que el sistema
merece —queda declarado en la spec y no lo arregla este fichero—. Lo que si puede
hacer la rubrica es no empeorarlo: un ancla que dice «la prosa es elegante» invita
a concederselo; una que dice «si se quitara la frase, habria que reescribir lo que
pasa» obliga a mirar el texto.

**Aqui no se puntua.** El Critico puntua y no repara (`CLAUDE.md` §9.1); la
rubrica ni siquiera puntua. Es un modulo sin base de datos y sin modelo, como
`schemas.py`: si tuviera un metodo que decidiera, el instrumento de medida y quien
mide serian el mismo objeto.
"""

import json
from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True, slots=True)
class Criterio:
    """Un eje de juicio, con sus dos extremos descritos."""

    nombre: str
    definicion: str
    ancla_minimo: str
    """Que se ve en el texto cuando este criterio vale 1."""
    ancla_maximo: str
    """Que se ve en el texto cuando vale 5."""


@dataclass(frozen=True, slots=True)
class Rubrica:
    """Version, escala y criterios. Inmutable, porque se versiona con su hash."""

    version: str
    escala: tuple[int, int]
    criterios: tuple[Criterio, ...]


def hash_de_rubrica(rubrica: Rubrica) -> str:
    """Ata una puntuacion a la rubrica exacta con que se obtuvo.

    `definitions.md` §8: cambiar un criterio **invalida la comparacion con
    puntuaciones anteriores**. Sin el hash eso ocurre en silencio, y el *tuning*
    de T11 compararia numeros de dos rubricas distintas creyendo que son de la
    misma. Es el mismo mecanismo que `HASH_DE_PLANTILLA_V1` en `agents.py`, y por
    la misma razon: `CLAUDE.md` §10 prohibe editar en sitio lo versionado.

    El orden de los criterios entra en el hash a proposito: la lista es cerrada y
    reordenarla cambia que se le presenta primero a quien puntua.
    """
    contenido = json.dumps(
        {
            "version": rubrica.version,
            "escala": list(rubrica.escala),
            "criterios": [
                {
                    "nombre": c.nombre,
                    "definicion": c.definicion,
                    "ancla_minimo": c.ancla_minimo,
                    "ancla_maximo": c.ancla_maximo,
                }
                for c in rubrica.criterios
            ],
        },
        ensure_ascii=False,
        sort_keys=False,
        separators=(",", ":"),
    )
    return sha256(contenido.encode("utf-8")).hexdigest()


RUBRICA_V1 = Rubrica(
    version="v1",
    escala=(1, 5),
    criterios=(
        Criterio(
            nombre="continuidad",
            definicion=(
                "Que nada de este capitulo contradiga lo establecido antes. Mide el "
                "**fondo**, no la forma: los validadores mecanicos ya contrastan "
                "hechos contra el grafo, y lo que queda aqui es la contradiccion que "
                "ningun campo captura."
            ),
            ancla_minimo=(
                "Algo del capitulo desmiente lo anterior y el texto no se da por "
                "enterado: un personaje usa un dato que nadie le dijo, o un objeto "
                "que se perdio en el capitulo 3 vuelve a estar en una mano sin que "
                "medie explicacion."
            ),
            ancla_maximo=(
                "Cada referencia a algo anterior coincide con lo establecido, y "
                "cuando algo ha cambiado el propio capitulo dice cuando cambio. Un "
                "lector que volviera atras no encontraria ninguna frase que "
                "corregir."
            ),
        ),
        Criterio(
            nombre="tono",
            definicion=(
                "Que el registro sea el que el brief pidio, y que sea el mismo de "
                "principio a fin del capitulo."
            ),
            ancla_minimo=(
                "El registro es el contrario del pedido —se pidio calido y el "
                "capitulo es seco y administrativo—, o cambia de parrafo a parrafo "
                "sin que pase nada en la historia que lo justifique."
            ),
            ancla_maximo=(
                "Alguien que leyera solo este capitulo, sin ver el brief, "
                "describiria su tono con las mismas palabras que uso el comprador."
            ),
        ),
        Criterio(
            nombre="arco",
            definicion=(
                "Que la historia vaya a algun sitio **dentro de este capitulo**: que "
                "entre con un valor y salga con otro."
            ),
            ancla_minimo=(
                "Al terminar, la situacion es la misma que al empezar: nadie quiere "
                "algo distinto, nadie ha ganado ni perdido nada, y el capitulo se "
                "podria suprimir sin tocar el siguiente."
            ),
            ancla_maximo=(
                "El capitulo entra con un valor y sale con el contrario, y lo que "
                "produce el cambio ocurre dentro del capitulo y no se cuenta como "
                "algo que paso fuera."
            ),
        ),
        Criterio(
            nombre="coherencia_de_personajes",
            definicion=(
                "Que actuen como quienes son: que cada decision se explique por lo "
                "que ya sabiamos de ellos, o que el capitulo muestre que les hizo "
                "cambiar."
            ),
            ancla_minimo=(
                "Un personaje hace lo contrario de lo que se ha dicho de el y el "
                "texto no lo nota: la que el brief describe como terca cede a la "
                "primera, y nadie —ni ella— lo comenta."
            ),
            ancla_maximo=(
                "Cada decision se sigue de lo establecido sobre quien la toma; y "
                "donde alguien actua fuera de su caracter, el capitulo ensena la "
                "presion que lo explica."
            ),
        ),
        Criterio(
            nombre="ritmo",
            definicion=(
                "**Entre capitulos, no dentro de uno.** Que este capitulo ocupe un "
                "lugar que ningun otro ocupa en la novela."
            ),
            ancla_minimo=(
                "Repite la funcion del capitulo anterior —otra conversacion que "
                "vuelve a plantear lo mismo sin moverlo— o mete de golpe lo que dos "
                "capitulos venian preparando y lo resuelve en un parrafo."
            ),
            ancla_maximo=(
                "Quitarlo dejaria un hueco que se nota: lo que aqui se planta o se "
                "paga no esta en ningun otro capitulo, y la velocidad a la que "
                "avanza corresponde a donde esta en la novela."
            ),
        ),
        Criterio(
            nombre="naturalidad_de_la_personalizacion",
            definicion=(
                "Que el destinatario este **integrado** en la historia y no "
                "**incrustado** en ella (`definitions.md` §7). Es el unico de los "
                "seis que mide la mitad del producto que ningun validador mecanico "
                "alcanza: uno mecanico comprueba que el dato **aparece**, y "
                "aparecer no es estar narrado."
            ),
            ancla_minimo=(
                "El dato esta nombrado y no hace nada: se puede borrar la frase que "
                "lo menciona y el capitulo sigue funcionando igual. La bufanda roja "
                "se cita y nadie la usa, la ata nadie, no abriga a nadie."
            ),
            ancla_maximo=(
                "El dato sostiene algo que pasa: si se quitara, habria que "
                "reescribir la escena y no solo tachar una linea. El recuerdo "
                "aportado es lo que hace que un personaje diga que si, y sin el la "
                "decision no se entiende."
            ),
        ),
    ),
)
"""La vigente. Cambiar un criterio exige `v2` y un hash nuevo, no editar esto."""

HASH_DE_RUBRICA_V1 = hash_de_rubrica(RUBRICA_V1)


def rubrica_vigente() -> Rubrica:
    """La que usa el juez **y** la que se le presenta al Autor: la misma instancia.

    `CA-20` pide que sean la misma rubrica. Devolver una copia bastaria para
    cumplir la letra y romper el motivo: dos objetos iguales pueden dejar de
    serlo, y entonces la distancia de `RF-JUZ-05` compararia dos medidas tomadas
    con reglas distintas sin que nada avisara.
    """
    return RUBRICA_V1
