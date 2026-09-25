"""Acceso a las tablas de la publicacion.

T1 deja aqui las dos lecturas que las demas tareas dan por hechas: por token,
que es como entra la lectura (T9), y por obra, que es como se sabe cual fue la
ultima tirada para encadenar la siguiente (T6, T7).

Escribir es de T6 -- publicar es atomico y se decide alli --, y por eso este
modulo no expone ningun `guardar`: media publicacion escrita desde dos sitios
distintos es exactamente lo que T6 existe para impedir.
"""

import json
from collections.abc import Mapping
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.manuscrito.modelos import (
    CapituloPublicado,
    Dedicatoria,
    FichaDeLectura,
    VersionPublicada,
)
from app.features.manuscrito.schemas import DedicatoriaEntrada


async def version_por_token(
    sesion: AsyncSession, identificador_publico: str
) -> VersionPublicada | None:
    """La tirada a la que apunta un enlace repartido.

    Devuelve `None` en vez de lanzar: un token que no existe y un token que
    expiro son lo mismo para quien lee, y quien llama decide que responder.
    Lanzar aqui obligaria a distinguirlos en el mensaje, que es justo lo que no
    conviene decirle a quien esta probando tokens.
    """
    resultado = await sesion.execute(
        select(VersionPublicada).where(
            VersionPublicada.identificador_publico == identificador_publico
        )
    )
    return resultado.scalar_one_or_none()


async def ultima_version(sesion: AsyncSession, obra_id: int) -> VersionPublicada | None:
    """La tirada de ordinal mas alto, o `None` si la obra no se ha publicado.

    Es lo que T6 necesita para dar ordinal a la siguiente y rellenar
    `sucede_a_id`, y lo que T7 compara para calcular `cambiado`.
    """
    resultado = await sesion.execute(
        select(VersionPublicada)
        .where(VersionPublicada.obra_id == obra_id)
        .order_by(VersionPublicada.ordinal.desc())
        .limit(1)
    )
    return resultado.scalar_one_or_none()


async def capitulos_de(sesion: AsyncSession, version_id: int) -> list[CapituloPublicado]:
    """Los capitulos de una tirada, en orden de lectura."""
    resultado = await sesion.execute(
        select(CapituloPublicado)
        .where(CapituloPublicado.version_id == version_id)
        .order_by(CapituloPublicado.numero)
    )
    return list(resultado.scalars())


async def dedicatoria_de(sesion: AsyncSession, obra_id: int) -> Dedicatoria | None:
    """La dedicatoria de la obra, que la portada necesita y puede no existir."""
    resultado = await sesion.execute(select(Dedicatoria).where(Dedicatoria.obra_id == obra_id))
    return resultado.scalar_one_or_none()


# --- T7 -----------------------------------------------------------------
# Anadido al final y sin tocar lo de arriba: T6 amplia este mismo modulo a la
# vez, y el plan reparte asi para que dos agentes no editen las mismas lineas.


def capitulos_cambiados(
    anteriores: Mapping[int, str] | None,
    nuevos: Mapping[int, str],
) -> list[int]:
    """Que capitulos lee distinto el destinatario. `RF-PUB-06`.

    **Diferencia de texto, no de identificador.** Una regeneracion crea una
    `VersionTexto` nueva con otro `id` y otro `run_id`; si el texto sale
    igual, para quien lee no ha cambiado nada y el indice no debe decir que
    si. Comparar `version_texto_id` marcaria el capitulo y mandaria al lector
    a buscar un cambio que no existe.

    **Recibe textos y no filas, y no es un descuido de capa.** `escritura`
    cierra `VersionTexto` en su puerta -- «quien necesite el texto recibe el
    texto, no la fila» --, asi que esta feature no puede leerla: los trae quien
    publica. Por eso la funcion no toca la base pese a vivir en `repository`,
    que es donde el plan de la Fase 4 la asigna para no partir el modulo entre
    dos agentes de la misma ola.

    Las claves son numeros de capitulo. Un capitulo **nuevo** cuenta como
    cambiado: hay algo que leer ahi que antes no estaba. Uno que **desaparece**
    no, porque no le queda entrada de indice que marcar.

    **`anteriores=None` es la primera tirada, y no es lo mismo que `{}`.** Sin
    tirada anterior no se marca nada: es la primera vez que se lee, y «todo
    cambiado» seria tan falso como «nada cambiado». Un diccionario vacio, en
    cambio, es una tirada anterior que existio y no tenia capitulos, y entonces
    los de ahora si son nuevos. El tipo obliga a decir cual de las dos es: era
    la unica forma de que la distincion no dependiera de recordarla.

    Devuelve los numeros **en orden de lectura**, que es como los pinta el
    indice; ordenarlos otra vez despues seria una de mas.
    """
    if anteriores is None:
        return []
    return sorted(numero for numero, texto in nuevos.items() if anteriores.get(numero) != texto)


# --- lecturas que cruzan de feature, y por que van en SQL -------------------
#
# Las tres consultas de abajo leen `capitulo`, `trabajo`, `version_texto`,
# `escena` y `hecho_canon`, que son de `outline`, `escritura`, `escena` y
# `canon`. **No se importan sus modelos**: el contrato de import-linter prohibe
# entrar a `app.features.*.modelos`, y entrar por el `__init__` de `escritura`
# **crea un ciclo** -- `obra/service.py` ya tuvo que diferir su import de
# `manuscrito` dentro de una funcion por lo mismo.
#
# Asi que se lee en SQL contra la base compartida, que es lo que ya hace
# `escritura/novela.py` con `hecho_canon`. Es una sola base por decision P-07, y
# estas son proyecciones de solo lectura: ninguna escribe fuera de `manuscrito`.


async def capitulos_con_su_puerta(sesion: AsyncSession, obra_id: int) -> list[dict[str, Any]]:
    """Los capitulos de la obra con el estado de su trabajo y su texto vigente.

    `LEFT JOIN` desde `capitulo` y no desde `trabajo`: un capitulo **sin
    trabajo** tiene que aparecer con el estado a nulo en vez de desaparecer de
    la consulta. Partiendo de `trabajo` se quedaria fuera, y un capitulo que
    nadie valido se publicaria por no figurar -- que es la regla de dominio 14
    incumplida en silencio.
    """
    filas = (
        await sesion.execute(
            text(
                "SELECT c.numero AS numero, c.titulo AS titulo, "
                "       t.estado AS estado, v.id AS version_texto_id, v.texto AS texto "
                "FROM capitulo AS c "
                "LEFT JOIN trabajo AS t "
                "       ON t.capitulo_id = c.id AND t.tipo = 'escribir_escena' "
                "LEFT JOIN version_texto AS v "
                "       ON v.escena_id = t.escena_id AND v.vigente = 1 "
                "WHERE c.obra_id = :obra_id "
                "ORDER BY c.numero"
            ),
            {"obra_id": obra_id},
        )
    ).mappings()
    return [dict(f) for f in filas]


async def presentes_por_capitulo(sesion: AsyncSession, obra_id: int) -> list[dict[str, Any]]:
    """Quien esta presente en cada capitulo aprobado, para la ficha (RF-PUB-05)."""
    filas = (
        await sesion.execute(
            text(
                "SELECT c.numero AS numero, e.presentes AS presentes "
                "FROM capitulo AS c "
                "JOIN trabajo AS t ON t.capitulo_id = c.id AND t.estado = 'INTEGRADA' "
                "JOIN escena AS e ON e.id = t.escena_id "
                "WHERE c.obra_id = :obra_id "
                "ORDER BY c.numero"
            ),
            {"obra_id": obra_id},
        )
    ).mappings()
    return [dict(f) for f in filas]


async def hechos_vivos(sesion: AsyncSession, obra_id: int) -> list[dict[str, Any]]:
    """Los hechos de canon de la obra que **ningun otro sustituye**.

    Son los que la ficha puede ofrecer para corregir: pedir un cambio sobre un
    hecho ya sustituido se rechaza (plan-5 R-5).
    """
    filas = (
        await sesion.execute(
            text(
                "SELECT h.id AS id, h.entidad AS entidad, h.atributo AS atributo "
                "FROM hecho_canon AS h "
                "WHERE h.obra_id = :obra_id AND NOT EXISTS ("
                "  SELECT 1 FROM hecho_canon AS s WHERE s.sustituye_a = h.id) "
                "ORDER BY h.id"
            ),
            {"obra_id": obra_id},
        )
    ).mappings()
    return [dict(f) for f in filas]


async def hechos_con_sus_capitulos(sesion: AsyncSession, obra_id: int) -> list[dict[str, Any]]:
    """El grafo de canon con los capitulos que se apoyan en cada hecho.

    **Segundo uso de esta consulta**; el primero es `escritura/novela.py`. §5.1
    regla 4 dice que se duplica primero y sube a `commons/` al tercero, asi que
    aqui se duplica **a proposito** y queda anotado para quien traiga el tercero.

    El `LEFT JOIN` no es indiferencia: un hecho que ningun capitulo usa -- los
    del brief -- tiene que llegar a la cobertura igual, porque justo esos son
    los que pueden faltar en la novela.
    """
    filas = (
        await sesion.execute(
            text(
                "SELECT h.id AS id, h.entidad AS entidad, h.atributo AS atributo, "
                "       h.valor AS valor, c.numero AS numero "
                "FROM hecho_canon AS h "
                "LEFT JOIN hecho_usado_en AS u ON u.hecho_canon_id = h.id "
                "LEFT JOIN capitulo AS c ON c.id = u.capitulo_id "
                "WHERE h.obra_id = :obra_id "
                "ORDER BY h.id, c.numero"
            ),
            {"obra_id": obra_id},
        )
    ).mappings()
    return [dict(f) for f in filas]


async def elementos_obligatorios_de(sesion: AsyncSession, obra_id: int) -> list[str]:
    """Lo que el comprador pidio que apareciera, de su columna propia (P-2)."""
    crudo = (
        await sesion.execute(
            text("SELECT elementos_obligatorios FROM obra WHERE id = :obra_id"),
            {"obra_id": obra_id},
        )
    ).scalar_one_or_none()
    if isinstance(crudo, str):
        try:
            crudo = json.loads(crudo)
        except json.JSONDecodeError:
            return []
    return [str(v) for v in crudo or []]


async def titulo_de_obra(sesion: AsyncSession, obra_id: int) -> str:
    """El titulo de la novela, para la portada (`RF-POR-01`).

    Por SQL crudo y no por el modelo `Obra`, igual que
    `elementos_obligatorios_de` justo encima y por el mismo motivo: `Obra` vive
    en la feature `obra` y una feature solo entra a otra por su `__init__.py`
    (`CLAUDE.md` §5.1). Leer una columna por nombre no cruza esa frontera; su
    modelo, si.

    Devuelve cadena vacia si la obra no esta, y no lanza: la portada ya decidio
    que existe -- llego por un token valido -- y un titulo ausente no es motivo
    para negarle la novela a nadie.
    """
    titulo = (
        await sesion.execute(
            text("SELECT titulo FROM obra WHERE id = :obra_id"), {"obra_id": obra_id}
        )
    ).scalar_one_or_none()
    return str(titulo or "")


async def texto_publicado(sesion: AsyncSession, version_id: int, numero: int) -> str | None:
    """El texto **fijado** de un capitulo publicado, no el vigente de hoy.

    Es la lectura que sostiene `RF-PUB-01`, y la distincion lo es todo:
    `capitulo_publicado.version_texto_id` apunta a una fila concreta de
    `version_texto`, y esta consulta va por ahi. Resolver la version vigente
    de la escena daria el texto de hoy, y entonces **un enlace ya repartido
    cambiaria de contenido sin que nadie lo tocara** -- que es exactamente lo
    que la tirada inmutable existe para impedir.

    Por `text()` y no por el modelo: `VersionTexto` es de `escritura` y no
    cruza su puerta (`CLAUDE.md` §5.1). Misma via que `capitulos_con_su_puerta`.
    """
    fila = (
        await sesion.execute(
            text(
                "SELECT v.texto AS texto "
                "FROM capitulo_publicado AS c "
                "JOIN version_texto AS v ON v.id = c.version_texto_id "
                "WHERE c.version_id = :version_id AND c.numero = :numero"
            ),
            {"version_id": version_id, "numero": numero},
        )
    ).first()
    return str(fila.texto) if fila else None


async def ficha_de(sesion: AsyncSession, version_id: int) -> FichaDeLectura | None:
    """La ficha de lectura de una tirada. Puede no existir en tiradas viejas."""
    resultado = await sesion.execute(
        select(FichaDeLectura).where(FichaDeLectura.version_id == version_id)
    )
    return resultado.scalar_one_or_none()


async def versiones_de(sesion: AsyncSession, obra_id: int) -> list[VersionPublicada]:
    """Todas las tiradas de la obra, de la mas reciente a la primera.

    De mas nueva a mas vieja porque la lectura entra por la ultima: quien
    abre el enlace quiere lo de ahora, y las anteriores son el historial.
    """
    resultado = await sesion.execute(
        select(VersionPublicada)
        .where(VersionPublicada.obra_id == obra_id)
        .order_by(VersionPublicada.ordinal.desc())
    )
    return list(resultado.scalars())


async def guardar_dedicatoria(sesion: AsyncSession, obra_id: int, texto: str | None) -> None:
    """Guarda la dedicatoria de una obra, o no guarda nada si esta vacia.

    **Vive aqui y no en `obra` aunque la recoja la entrevista.** Es la juntura
    que T2 declaro entera, y desde el otro lado solo se puede cruzar por esta
    puerta: `obra` no puede tocar `Dedicatoria`, porque el modelo de base de
    datos no sale de la feature (`CLAUDE.md` §6) y una feature no importa los
    ficheros internos de otra (§5.1). Pedir la escritura es lo correcto;
    construir la fila desde fuera, no.

    Los tres vacios -- `None`, `""` y `"   "` -- se tratan igual y no dejan
    fila. Guardar una con tres espacios obligaria a la portada a distinguirla
    de una dedicatoria de verdad, y ese `if` acabaria escrito en dos sitios.
    """
    limpia = DedicatoriaEntrada(texto=texto).limpia()
    if limpia is None:
        return
    sesion.add(Dedicatoria(obra_id=obra_id, texto=limpia))
