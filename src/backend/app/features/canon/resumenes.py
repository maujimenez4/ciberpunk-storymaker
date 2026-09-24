"""RF-MEM-04 por el lado que faltaba: **leer** el resumen de un capitulo.

El requisito tiene dos mitades y la Fase 2 solo dejo escrita la primera:
«resumen por capitulo, derivado del texto aprobado, **que alimenta el contexto
de los siguientes**». Escribirlo lo hace `service.consolidar_escena`, detras del
Extractor y solo si la escena fue aprobada; leerlo no lo hacia nadie, y sin
lector el resumen es una tabla que crece y no se consulta. Es literalmente lo
que separa diez capitulos de diez cuentos (R-7).

**Quien lo lee es la capa de memoria recuperada**, no la de continuidad:
`architecture.md` §4.8 pone en esa fila «indice vectorial **+ resumenes**». La
continuidad local es otra cosa y esta acotada -- las escenas N-1 y N-2, con su
prosa entera --; los resumenes son el rastro largo, y por eso comparten capa y
tope con lo recuperado.

**Las tablas de otras features se leen por SQL con su nombre** (`CLAUDE.md`
§5.1): `capitulo` es de `outline`, `escena` de `escena` y `version_texto` de
`escritura`. Es el mismo trato que `contexto/service.py` da a las suyas y que
`outline/repository.py` da a `obra`.

**Dos funciones y no una, porque son dos preguntas distintas.** Una devuelve los
resumenes que hay; la otra cuenta los capitulos que **deberian** tener uno. Si
la segunda contara lo que devuelve la primera, coincidirian siempre y
RF-CTX-06 se cumpliria por consecuencia: nunca habria censo mayor que piezas y
ningun test podria caer. Es la trampa que `capas.py` nombra por su nombre.
"""

import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class ResumenDeCapitulo:
    """Un resumen ya derivado del texto aprobado, con de donde sale.

    `version_texto_id` no es opcional aqui aunque la columna lo admita: lo que
    no cita el texto del que salio no es un resumen derivado sino una segunda
    verdad sobre el capitulo, y esas no entran en el contexto de nadie.
    """

    capitulo_id: int
    numero: int
    texto: str
    hechos_establecidos: tuple[str, ...]
    hilos_abiertos: tuple[str, ...]
    version_texto_id: int


async def leer_resumenes_anteriores(
    sesion: AsyncSession, *, obra_id: int, antes_de: int
) -> list[ResumenDeCapitulo]:
    """Los resumenes de los capitulos anteriores al `antes_de`, del mas reciente al mas antiguo.

    Tres decisiones, y ninguna es de estilo:

    - **`antes_de` es estricto.** Un capitulo que se resumiera a si mismo
      tendria en su contexto el resumen de la prosa que aun no ha escrito. Es
      el mismo error que el filtro estructural evita con la escena en curso, y
      alli lo destapo una mutacion de CA-6.
    - **Se exige `version_texto` vigente.** Es lo que hace ejecutable el
      «derivado del texto aprobado» de RF-MEM-04: un resumen sin cita no se
      puede rehacer desde el manuscrito, y uno que cita una version descartada
      describe prosa que el manuscrito ya no tiene. Meter cualquiera de los dos
      en el contexto del capitulo siguiente es como una novela se contradice a
      si misma.
    - **Orden descendente por numero.** El recorte de la capa quita por el
      final (`presupuesto.py`), asi que lo ultimo es lo primero que se pierde;
      lo que no puede perderse es el capitulo inmediatamente anterior.
    """
    if antes_de <= 1:
        return []

    filas = (
        (
            await sesion.execute(
                text(
                    """
                    SELECT rc.capitulo_id AS capitulo_id, c.numero AS numero,
                           rc.texto AS texto, rc.hechos_establecidos AS hechos,
                           rc.hilos_abiertos AS hilos, rc.version_texto_id AS version_texto_id
                    FROM resumen_capitulo AS rc
                    JOIN capitulo AS c ON c.id = rc.capitulo_id
                    JOIN version_texto AS vt
                      ON vt.id = rc.version_texto_id AND vt.vigente = 1
                    WHERE c.obra_id = :obra_id AND c.numero < :antes_de
                    ORDER BY c.numero DESC
                    """
                ),
                {"obra_id": obra_id, "antes_de": antes_de},
            )
        )
        .mappings()
        .all()
    )

    return [
        ResumenDeCapitulo(
            capitulo_id=int(f["capitulo_id"]),
            numero=int(f["numero"]),
            texto=str(f["texto"]),
            hechos_establecidos=tuple(_lista(f["hechos"])),
            hilos_abiertos=tuple(_lista(f["hilos"])),
            version_texto_id=int(f["version_texto_id"]),
        )
        for f in filas
    ]


async def contar_capitulos_con_texto_aprobado(
    sesion: AsyncSession, *, obra_id: int, antes_de: int
) -> int:
    """El censo: cuantos capitulos anteriores **deberian** haber dejado resumen.

    Un capitulo con texto vigente es un capitulo aprobado e integrado, y la
    consolidacion escribe su resumen en la misma transaccion que sus hechos
    (`service.consolidar_escena`). Asi que censo mayor que resumenes significa
    una cosa concreta: un capitulo escrito cuyo resumen no esta, que es el
    «almacen que tenia con que surtir y no surtio» de R-3.

    Lo que **no** se cuenta: capitulos planificados y aun sin escribir. Contar
    esos haria fallar el caso mas normal que hay -- una obra recien empezada --
    y convertiria la regla en una restriccion inalcanzable por el otro lado.
    """
    if antes_de <= 1:
        return 0

    resultado = await sesion.execute(
        text(
            """
            SELECT COUNT(DISTINCT c.id)
            FROM capitulo AS c
            JOIN escena AS e ON e.capitulo_id = c.id
            JOIN version_texto AS vt ON vt.escena_id = e.id AND vt.vigente = 1
            WHERE c.obra_id = :obra_id AND c.numero < :antes_de
            """
        ),
        {"obra_id": obra_id, "antes_de": antes_de},
    )
    return int(resultado.scalar_one())


def _lista(valor: Any) -> list[str]:
    """SQLAlchemy Core devuelve las columnas JSON en crudo; el ORM ya las decodifica."""
    decodificado = json.loads(valor) if isinstance(valor, str | bytes) else valor
    return [str(elemento) for elemento in (decodificado or ())]
