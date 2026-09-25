"""De la vista `cronologia` a un fichero Lean que T5 compila. `RF-FOR-01`, R-4.

**Por que indices y no cadenas.** En Lean las pruebas de §5c se cierran con
`decide`, que evalua por fuerza bruta: con `n` filas, `sinUbicuidad` compara
`n²` pares. Comparar dos `Nat` es una instruccion; comparar dos `String` recorre
caracteres. Los nombres viajan una sola vez, en su tabla, y los eventos llevan
enteros. Lo midio quien instalo la herramienta sobre el proyecto de ejemplo.

**Una fila por participante, no por evento.** `sinUbicuidad` compara pares de
filas preguntando «mismo personaje, mismo momento, distinto lugar». Un evento
con tres participantes son tres filas: emitirlo como una fila con una lista
dentro dejaria al invariante sin nada que comparar.

**Y lo que este generador NO puede dar, que conviene leer antes de escribir el
invariante 1.** El encargo §5c pide comprobar que los eventos respetan el orden
temporal, y en el esquema **no hay ninguna magnitud ordenable de tiempo de
historia**: `evento.tiempo_historia` es `String(120)` y lleva cosas como «dia 1,
manana». El indice que se emite aqui ordena por **aparicion**, que es orden de
discurso; en un salto atras el discurso avanza y el tiempo de historia
retrocede. Un `ordenTemporal` sobre este campo comprobaria que el discurso
avanza, que es cierto por construccion. El fichero generado lo dice en su
cabecera para que la advertencia viaje con el dato y no se quede aqui.
"""

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

CABECERA = """\
/-
  GENERADO. No editar a mano: lo reescribe `generar_lean` en cada publicacion.

  Obra {obra_id}. {filas} filas, una por participante y evento.

  **`momento` es un orden de aparicion y no es tiempo de historia.**
  `evento.tiempo_historia` es texto libre -- «dia 1, manana» --, asi que no hay
  con que ordenar el tiempo de la historia. Este indice sigue el orden del
  discurso, y en un salto atras el discurso avanza mientras la historia
  retrocede. Sirve para preguntar **si dos filas comparten momento**, que es lo
  que necesita «nadie en dos lugares a la vez»; no sirve para preguntar si el
  tiempo avanza.
-/
"""


def escapar(valor: str) -> str:
    """Un nombre del brief dentro de una cadena de Lean.

    Solo la barra invertida y la comilla doble: en Lean la apostrofe no delimita
    nada, asi que «O'Shea» entra tal cual, y los acentos tampoco se tocan porque
    Lean 4 lee UTF-8 y «Begoña» es un literal valido.

    La barra va primero. Escapar la comilla antes duplicaria despues la barra
    que se acaba de introducir, y «el "bar"» saldria con una barra de mas.
    """
    return valor.replace("\\", "\\\\").replace('"', '\\"')


def _lista_de_nombres(nombre: str, valores: list[str]) -> str:
    cuerpo = ", ".join(f'"{escapar(v)}"' for v in valores)
    return f"def {nombre} : List String := [{cuerpo}]"


def _participantes_de(crudo: Any) -> list[str]:
    """La columna JSON, venga como lista o como el texto que SQLite guardo.

    Segun por donde entre la fila -- el ORM o un `insert()` directo -- la vista
    devuelve una lista o la cadena `'["Marta"]'`. Sin esta normalizacion, iterar
    la cadena emite **una fila por caracter**: compila, y es basura.
    """
    if isinstance(crudo, str):
        try:
            crudo = json.loads(crudo)
        except json.JSONDecodeError:
            return []
    if not isinstance(crudo, list):
        return []
    return [str(v) for v in crudo if str(v).strip()]


def momento_de(tiempo_historia: str, evento_id: object) -> str:
    """El instante que un evento declara, **solo si lo declara**.

    Corrida real, obra 3: el Extractor anota «madrugada», «presente» o
    «amanecer» en capitulos distintos, y tomar el texto como instante puso a la
    protagonista en nueve sitios a la vez. Ni acotando por capitulo bastaba:
    dentro de una madrugada se pasa de la cocina a la escalera. **Un texto sin
    cifra no identifica un instante**, y cada evento vago es el suyo propio.

    «San Juan de 1996» o «dia 1, manana» si lo identifican, y siguen
    emparejandose: es lo que B3 necesita. El punto ciego, en
    `verification.md`: dos sitios en la misma «madrugada» ya no se ven.
    """
    if any(caracter.isdigit() for caracter in tiempo_historia):
        return tiempo_historia
    return f"{tiempo_historia} · evento {evento_id}"


class _Indice:
    """Nombre -> entero, por orden de primera aparicion.

    Por aparicion y no alfabetico a proposito: asi el fichero de una obra que
    crece solo **anade** al final de la tabla, y dos generaciones seguidas de
    los mismos datos dan el mismo texto, que es lo que `CLAUDE.md` §3 punto 6
    pide. Ordenar alfabeticamente renumeraria medio fichero al aparecer un
    nombre nuevo.
    """

    def __init__(self) -> None:
        self._por_nombre: dict[str, int] = {}

    def de(self, nombre: str) -> int:
        if nombre not in self._por_nombre:
            self._por_nombre[nombre] = len(self._por_nombre)
        return self._por_nombre[nombre]

    @property
    def nombres(self) -> list[str]:
        return list(self._por_nombre)


async def generar_lean(sesion: AsyncSession, obra_id: int) -> str:
    """El fichero Lean de una obra, listo para que T5 lo compile.

    Lee la vista `cronologia` y no la tabla `evento`: la vista es la proyeccion
    que `definitions.md` §4.4 declara como entrada del validador formal, y
    leerla deja al generador indiferente a como se derive.

    El orden es `orden_discurso` y luego `evento_id`. Los eventos del brief no
    tienen escena, asi que su `orden_discurso` es nulo y van primero: existieron
    antes del texto. El desempate por `evento_id` no es adorno -- sin el, dos
    eventos del mismo capitulo saldrian en el orden que quisiera SQLite y el
    fichero dejaria de ser reproducible.
    """
    filas = (
        (
            await sesion.execute(
                text(
                    "SELECT evento_id, tiempo_historia, lugar, participantes, excluye"
                    " FROM cronologia WHERE obra_id = :obra"
                    " ORDER BY orden_discurso IS NULL DESC, orden_discurso, evento_id"
                ),
                {"obra": obra_id},
            )
        )
        .mappings()
        .all()
    )

    momentos, lugares, personajes = _Indice(), _Indice(), _Indice()
    eventos: list[str] = []
    exclusiones: list[str] = []

    for fila in filas:
        instante = momento_de(str(fila["tiempo_historia"]), fila["evento_id"])
        # `excluye[]` se lee **aunque el evento no tenga participantes**: una
        # muerte o una partida definitiva puede no tener a nadie «presente», y
        # perderla dejaria el invariante 2 sin nada contra que comparar.
        for excluido in _participantes_de(fila.get("excluye")):
            exclusiones.append(f"⟨{momentos.de(instante)}, {personajes.de(excluido)}⟩")

        participantes = _participantes_de(fila["participantes"])
        if not participantes:
            # Un evento sin participantes no dice de nadie donde estaba. No hay
            # fila que emitir, y emitir una con un hueco no compilaria.
            continue
        momento = momentos.de(instante)
        lugar = lugares.de(str(fila["lugar"] or ""))
        eventos.extend(f"⟨{momento}, {personajes.de(p)}, {lugar}⟩" for p in participantes)

    return "\n".join(
        [
            CABECERA.format(obra_id=obra_id, filas=len(eventos)),
            _lista_de_nombres("momentos", momentos.nombres),
            _lista_de_nombres("lugares", lugares.nombres),
            _lista_de_nombres("personajes", personajes.nombres),
            "",
            _lista_de_registros("eventos", "Evento", eventos),
            "",
            _lista_de_registros("exclusiones", "Exclusion", exclusiones),
            "",
        ]
    )


def _lista_de_registros(nombre: str, tipo: str, filas: list[str]) -> str:
    """`def <nombre> : List <tipo> := [...]`, vacia o en varias lineas.

    La lista vacia se emite en una sola linea a proposito: es la forma que R-3
    busca en el fichero para distinguir «paso por vacio» de «paso comprobando».
    """
    if not filas:
        return f"def {nombre} : List {tipo} := []"
    cuerpo = "\n".join(f"    {f}," for f in filas)
    return f"def {nombre} : List {tipo} := [\n{cuerpo}\n  ]"
