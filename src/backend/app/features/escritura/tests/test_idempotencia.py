"""Idempotencia por `run_id`, tabla por tabla (T3 de la Fase 3).

**RF-ORQ-03 y R-4.** Lo que se prueba aqui no es que el ciclo entero repetido
deje la base igual: eso pasaria aunque un paso concreto duplicara, si otro lo
compensara. Se prueba **paso a paso**, y cada paso sobre la tabla en la que
escribe: `version_texto`, `ejecucion`, `evento` y `hecho_canon`.

Cada tabla lleva **dos** pruebas y no una, y la segunda es la que importa:

| Prueba | Que descarta |
| --- | --- |
| Repetir el paso no anade filas | Que la reanudacion duplique (R-4) |
| Otra corrida —u otra escena— **si** escribe | Que el guardia se limite a no escribir nunca |

Sin la segunda, un guardia que devolviera siempre «ya esta» pasaria la suite
entera y la reanudacion no escribiria nada. Es la diferencia entre «no duplico»
y «no escribio», y es la que el plan dice que en esta fase ya se colo tres
veces.

Ninguna prueba llama al proveedor (CA-4): aqui no hay modelo, solo escrituras.
"""

from collections.abc import Callable, Coroutine
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.conftest import ObraConOutline
from app.features.escena.modelos import Escena
from app.features.escritura.idempotencia import (
    Paso,
    RastroCompuesto,
    RastroEnEjecucion,
    RastroEnEvento,
    RastroEnHechoCanon,
    RastroEnVersionTexto,
    donde_ya_escribio,
    una_sola_vez,
)

RUN = "cap1-trb1"
OTRA_CORRIDA = "cap1-trb2"


# ---------------------------------------------------------------------------
# Escrituras de mentira, una por tabla, que cuentan cuantas veces se las llamo
# ---------------------------------------------------------------------------


class Contada:
    """Una escritura que ademas se deja contar.

    Contar las llamadas y no solo las filas es lo que distingue «el guardia
    evito la escritura» de «la escritura corrio y no llego a insertar»: lo
    segundo seguiria gastando la llamada al modelo que `architecture.md` §3.7
    dice que es el unico paso caro de repetir.
    """

    def __init__(self, escribir: Callable[[], Coroutine[Any, Any, int]]) -> None:
        self._escribir = escribir
        self.veces = 0

    async def __call__(self) -> int:
        self.veces += 1
        return await self._escribir()


def escritura_de_version_texto(sesion: AsyncSession, escena_id: int, run_id: str) -> Contada:
    async def escribir() -> int:
        siguiente = (
            await sesion.execute(
                text("SELECT COALESCE(MAX(numero), 0) + 1 FROM version_texto WHERE escena_id = :e"),
                {"e": escena_id},
            )
        ).scalar_one()
        await sesion.execute(
            text(
                "INSERT INTO version_texto (escena_id, numero, texto, vigente, run_id, creado_en) "
                "VALUES (:e, :n, 'prosa', 0, :r, CURRENT_TIMESTAMP)"
            ),
            {"e": escena_id, "n": siguiente, "r": run_id},
        )
        await sesion.flush()
        return int(siguiente)

    return Contada(escribir)


def escritura_de_ejecucion(sesion: AsyncSession, obra_id: int, run_id: str) -> Contada:
    async def escribir() -> int:
        await sesion.execute(
            text(
                "INSERT INTO ejecucion (run_id, obra_id, prompt_id, prompt_version, prompt_hash, "
                "modelo, semilla, parametros, tokens_por_capa, tokens_previstos, "
                "ids_recuperados, ids_canon, creado_en) "
                "VALUES (:r, :o, 'escritor', 'v1', 'h', 'doble', 0, '{}', '{}', 10, '[]', '[]', "
                "CURRENT_TIMESTAMP)"
            ),
            {"r": run_id, "o": obra_id},
        )
        await sesion.flush()
        return 1

    return Contada(escribir)


def escritura_de_evento(sesion: AsyncSession, obra_id: int, escena_id: int) -> Contada:
    async def escribir() -> int:
        await sesion.execute(
            text(
                "INSERT INTO evento (obra_id, escena_id, descripcion, tiempo_historia, lugar, "
                "participantes, testigos, causa, consecuencia, excluye) "
                "VALUES (:o, :e, 'Nadia abre la carta', 'dia 1', 'El invernadero', "
                "'[]', '[\"Nadia\"]', '[]', '[]', '[]')"
            ),
            {"o": obra_id, "e": escena_id},
        )
        await sesion.flush()
        return 1

    return Contada(escribir)


def escritura_de_hecho_canon(sesion: AsyncSession, obra_id: int, escena_id: int) -> Contada:
    async def escribir() -> int:
        await sesion.execute(
            text(
                "INSERT INTO hecho_canon (obra_id, entidad, atributo, valor, confianza, origen, "
                "escena_de_origen) VALUES (:o, 'Nadia', 'oficio', 'botanica', 1.0, 'escena', :e)"
            ),
            {"o": obra_id, "e": str(escena_id)},
        )
        await sesion.flush()
        return 1

    return Contada(escribir)


async def cuenta(sesion: AsyncSession, consulta: str, **params: Any) -> int:
    return int((await sesion.execute(text(consulta), params)).scalar_one())


@pytest.fixture
async def segunda_escena(sesion: AsyncSession, obra_con_outline: ObraConOutline) -> Escena:
    """Otra escena de la misma obra, para probar que el guardia no es global."""
    escena = Escena(
        capitulo_id=obra_con_outline.capitulos[1].id,
        version_obra_id=obra_con_outline.version_obra.id,
        orden_discurso=2,
        tiempo_historia="dia 1, tarde",
        pov="Nadia",
        lugar="El muelle",
        presentes=["Nadia"],
        objetivo_del_pov="Encontrar la casa",
        obstaculo="Llueve",
        resultado="no-y-ademas",
        valor_entrada="sospecha",
        valor_salida="miedo",
        extension_objetivo=1200,
        densidad_de_dialogo_objetivo=0.4,
        distancia_psiquica=3,
    )
    sesion.add(escena)
    await sesion.flush()
    return escena


# ---------------------------------------------------------------------------
# La clave de idempotencia
# ---------------------------------------------------------------------------


def test_el_paso_se_identifica_por_corrida_nombre_y_ordinal() -> None:
    """`architecture.md` §3.2: el `run_id` es la clave de idempotencia.

    Y no basta el `run_id` solo: una corrida escribe hasta tres veces en
    `version_texto` —la primera vuelta y dos reparaciones (RF-ORQ-04)—, asi que
    la clave lleva tambien de que paso se trata y cual de sus vueltas.
    """
    primero = Paso(run_id=RUN, nombre="ESCRIBIENDO")
    assert primero.clave == f"{RUN}:ESCRIBIENDO:0"
    assert primero != Paso(run_id=RUN, nombre="ESCRIBIENDO", ordinal=1)
    assert primero != Paso(run_id=OTRA_CORRIDA, nombre="ESCRIBIENDO")
    assert primero != Paso(run_id=RUN, nombre="EXTRAYENDO")


def test_un_paso_sin_corrida_no_es_un_paso() -> None:
    """`CLAUDE.md` §15: no se guarda prosa generada sin `run_id`. Un guardia con
    la clave vacia acabaria dando por repetido lo que nadie escribio."""
    with pytest.raises(ValueError):
        Paso(run_id="", nombre="ESCRIBIENDO")
    with pytest.raises(ValueError):
        Paso(run_id=RUN, nombre="")
    with pytest.raises(ValueError):
        Paso(run_id=RUN, nombre="ESCRIBIENDO", ordinal=-1)


# ---------------------------------------------------------------------------
# `version_texto`
# ---------------------------------------------------------------------------


async def test_repetir_el_paso_no_duplica_la_version_de_texto(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    escena_id = obra_con_outline.escena.id
    paso = Paso(run_id=RUN, nombre="ESCRIBIENDO")
    rastro = RastroEnVersionTexto(escena_id=escena_id)
    escribir = escritura_de_version_texto(sesion, escena_id, RUN)

    primera = await una_sola_vez(sesion, paso, rastro, escribir)
    segunda = await una_sola_vez(sesion, paso, rastro, escribir)

    assert primera.repetido is False
    assert segunda.repetido is True
    assert segunda.tabla == "version_texto"
    assert escribir.veces == 1
    assert (
        await cuenta(
            sesion,
            "SELECT COUNT(*) FROM version_texto WHERE escena_id = :e AND run_id = :r",
            e=escena_id,
            r=RUN,
        )
        == 1
    )


async def test_otra_corrida_sobre_la_misma_escena_si_escribe(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """La prueba que distingue «no duplico» de «no escribio».

    Una regeneracion es otra corrida sobre la misma escena, y tiene que dejar su
    version. Un guardia que mirase solo la escena la daria por escrita y el
    capitulo se quedaria sin texto nuevo.
    """
    escena_id = obra_con_outline.escena.id
    rastro = RastroEnVersionTexto(escena_id=escena_id)
    await una_sola_vez(
        sesion,
        Paso(run_id=RUN, nombre="ESCRIBIENDO"),
        rastro,
        escritura_de_version_texto(sesion, escena_id, RUN),
    )

    otra = escritura_de_version_texto(sesion, escena_id, OTRA_CORRIDA)
    resultado = await una_sola_vez(
        sesion, Paso(run_id=OTRA_CORRIDA, nombre="ESCRIBIENDO"), rastro, otra
    )

    assert resultado.repetido is False
    assert otra.veces == 1
    assert (
        await cuenta(sesion, "SELECT COUNT(*) FROM version_texto WHERE escena_id = :e", e=escena_id)
        == 2
    )


async def test_la_reparacion_es_otro_paso_de_la_misma_corrida(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """RF-ORQ-04: hasta dos reparaciones dirigidas, cada una con su version.

    Las tres vuelta comparten `run_id`, asi que sin el ordinal la segunda seria
    indistinguible de una repeticion y el reintento no llegaria a escribirse.
    """
    escena_id = obra_con_outline.escena.id
    rastro = RastroEnVersionTexto(escena_id=escena_id)
    for ordinal in (0, 1, 2):
        escribir = escritura_de_version_texto(sesion, escena_id, RUN)
        resultado = await una_sola_vez(
            sesion, Paso(run_id=RUN, nombre="ESCRIBIENDO", ordinal=ordinal), rastro, escribir
        )
        assert resultado.repetido is False
        assert escribir.veces == 1

    repetida = escritura_de_version_texto(sesion, escena_id, RUN)
    ultima = await una_sola_vez(
        sesion, Paso(run_id=RUN, nombre="ESCRIBIENDO", ordinal=2), rastro, repetida
    )
    assert ultima.repetido is True
    assert repetida.veces == 0
    assert await cuenta(sesion, "SELECT COUNT(*) FROM version_texto WHERE run_id = :r", r=RUN) == 3


# ---------------------------------------------------------------------------
# `ejecucion`
# ---------------------------------------------------------------------------


async def test_repetir_el_paso_no_duplica_la_ejecucion(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """Regla de dominio 7: cada llamada al modelo deja una fila y solo una.

    Dos filas por una llamada no son un duplicado inofensivo: el coste y los
    tokens de la obra se leen sumando esta tabla (CU-07).
    """
    obra_id = obra_con_outline.obra.id
    paso = Paso(run_id=RUN, nombre="ESCRIBIENDO")
    rastro = RastroEnEjecucion()
    escribir = escritura_de_ejecucion(sesion, obra_id, RUN)

    await una_sola_vez(sesion, paso, rastro, escribir)
    segunda = await una_sola_vez(sesion, paso, rastro, escribir)

    assert segunda.repetido is True
    assert segunda.tabla == "ejecucion"
    assert escribir.veces == 1
    assert await cuenta(sesion, "SELECT COUNT(*) FROM ejecucion WHERE run_id = :r", r=RUN) == 1


async def test_otra_corrida_deja_su_propia_ejecucion(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    obra_id = obra_con_outline.obra.id
    rastro = RastroEnEjecucion()
    await una_sola_vez(
        sesion,
        Paso(run_id=RUN, nombre="ESCRIBIENDO"),
        rastro,
        escritura_de_ejecucion(sesion, obra_id, RUN),
    )

    otra = escritura_de_ejecucion(sesion, obra_id, OTRA_CORRIDA)
    resultado = await una_sola_vez(
        sesion, Paso(run_id=OTRA_CORRIDA, nombre="ESCRIBIENDO"), rastro, otra
    )

    assert resultado.repetido is False
    assert otra.veces == 1
    assert await cuenta(sesion, "SELECT COUNT(*) FROM ejecucion") == 2


# ---------------------------------------------------------------------------
# `evento` — el ledger, que no se puede limpiar despues
# ---------------------------------------------------------------------------


async def test_repetir_el_paso_no_duplica_eventos_del_ledger(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """`EXTRAYENDO` es reanudable «por idempotencia del `run_id`»
    (`architecture.md` §3.3), y esta es la tabla donde eso se nota: un evento
    duplicado duplica los testigos de `estado_en_t`, que es la vista de la que
    sale quien sabe que (regla de dominio 2)."""
    obra = obra_con_outline.obra.id
    escena_id = obra_con_outline.escena.id
    paso = Paso(run_id=RUN, nombre="EXTRAYENDO")
    rastro = RastroEnEvento(escena_id=escena_id)
    escribir = escritura_de_evento(sesion, obra, escena_id)

    await una_sola_vez(sesion, paso, rastro, escribir)
    segunda = await una_sola_vez(sesion, paso, rastro, escribir)

    assert segunda.repetido is True
    assert segunda.tabla == "evento"
    assert escribir.veces == 1
    assert (
        await cuenta(sesion, "SELECT COUNT(*) FROM evento WHERE escena_id = :e", e=escena_id) == 1
    )
    assert await cuenta(sesion, "SELECT COUNT(*) FROM estado_en_t WHERE personaje = 'Nadia'") == 1


async def test_el_ledger_de_otra_escena_no_bloquea_el_paso(
    sesion: AsyncSession, obra_con_outline: ObraConOutline, segunda_escena: Escena
) -> None:
    """La otra mitad: que el guardia no se convierta en «el ledger ya tiene algo,
    no escribas mas». El capitulo 2 tiene que poder dejar sus eventos aunque el
    1 ya dejara los suyos."""
    obra = obra_con_outline.obra.id
    await una_sola_vez(
        sesion,
        Paso(run_id=RUN, nombre="EXTRAYENDO"),
        RastroEnEvento(escena_id=obra_con_outline.escena.id),
        escritura_de_evento(sesion, obra, obra_con_outline.escena.id),
    )

    escribir = escritura_de_evento(sesion, obra, segunda_escena.id)
    resultado = await una_sola_vez(
        sesion,
        Paso(run_id=OTRA_CORRIDA, nombre="EXTRAYENDO"),
        RastroEnEvento(escena_id=segunda_escena.id),
        escribir,
    )

    assert resultado.repetido is False
    assert escribir.veces == 1
    assert await cuenta(sesion, "SELECT COUNT(*) FROM evento") == 2


async def test_la_idempotencia_no_puede_ser_borrar_y_reescribir(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """Por que el guardia decide **antes** y no limpia despues.

    El ledger es *append-only* y la Fase 2 lo sujeto en el esquema: borrar para
    reescribir no es una alternativa mas lenta, es una sentencia que el motor
    rechaza. Si este test dejara de fallar, el disparador habria desaparecido y
    la idempotencia podria implementarse mal sin que nada lo dijera.
    """
    await escritura_de_evento(sesion, obra_con_outline.obra.id, obra_con_outline.escena.id)()

    with pytest.raises(IntegrityError, match="append-only"):
        await sesion.execute(text("DELETE FROM evento"))
    await sesion.rollback()


# ---------------------------------------------------------------------------
# `hecho_canon`
# ---------------------------------------------------------------------------


async def test_repetir_el_paso_no_duplica_hechos_de_canon(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """Regla de dominio 4: un hecho de `origen: escena` cita la escena que lo
    establecio. Duplicarlo deja dos verdades sobre lo mismo con la misma cita."""
    obra = obra_con_outline.obra.id
    escena_id = obra_con_outline.escena.id
    paso = Paso(run_id=RUN, nombre="EXTRAYENDO")
    rastro = RastroEnHechoCanon(escena_id=escena_id)
    escribir = escritura_de_hecho_canon(sesion, obra, escena_id)

    await una_sola_vez(sesion, paso, rastro, escribir)
    segunda = await una_sola_vez(sesion, paso, rastro, escribir)

    assert segunda.repetido is True
    assert segunda.tabla == "hecho_canon"
    assert escribir.veces == 1
    assert (
        await cuenta(
            sesion, "SELECT COUNT(*) FROM hecho_canon WHERE escena_de_origen = :e", e=str(escena_id)
        )
        == 1
    )


async def test_los_hechos_del_brief_no_bloquean_los_de_la_escena(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """`obra_con_outline` trae ya un hecho de `origen: brief`, que **no tiene**
    escena de origen (regla de dominio 4). Si el guardia contara los hechos de
    la obra en vez de los de la escena, el primer capitulo no escribiria ni uno.
    """
    obra = obra_con_outline.obra.id
    escena_id = obra_con_outline.escena.id
    assert await cuenta(sesion, "SELECT COUNT(*) FROM hecho_canon WHERE obra_id = :o", o=obra) == 1

    escribir = escritura_de_hecho_canon(sesion, obra, escena_id)
    resultado = await una_sola_vez(
        sesion,
        Paso(run_id=RUN, nombre="EXTRAYENDO"),
        RastroEnHechoCanon(escena_id=escena_id),
        escribir,
    )

    assert resultado.repetido is False
    assert escribir.veces == 1
    assert await cuenta(sesion, "SELECT COUNT(*) FROM hecho_canon WHERE obra_id = :o", o=obra) == 2


# ---------------------------------------------------------------------------
# El paso que escribe en varias tablas a la vez
# ---------------------------------------------------------------------------


async def test_el_paso_de_varias_tablas_se_juzga_por_todas(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """`EXTRAYENDO` escribe canon y ledger dentro del mismo punto de guardado, y
    por eso basta con que **una** de las dos tenga rastro para saber que corrio.
    Exigir las dos daria por no ejecutado un paso que si lo fue."""
    obra = obra_con_outline.obra.id
    escena_id = obra_con_outline.escena.id
    rastro = RastroCompuesto(
        (RastroEnEvento(escena_id=escena_id), RastroEnHechoCanon(escena_id=escena_id))
    )
    paso = Paso(run_id=RUN, nombre="EXTRAYENDO")

    assert await donde_ya_escribio(sesion, paso, rastro) is None

    await escritura_de_evento(sesion, obra, escena_id)()
    assert await donde_ya_escribio(sesion, paso, rastro) == "evento"

    escribir = escritura_de_hecho_canon(sesion, obra, escena_id)
    resultado = await una_sola_vez(sesion, paso, rastro, escribir)
    assert resultado.repetido is True
    assert escribir.veces == 0


async def test_el_guardia_devuelve_lo_que_escribio_el_paso(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """Quien orqueste necesita el valor del paso, no solo saber que corrio; y en
    la repeticion no lo hay, porque el paso no volvio a correr."""
    escena_id = obra_con_outline.escena.id
    paso = Paso(run_id=RUN, nombre="ESCRIBIENDO")
    rastro = RastroEnVersionTexto(escena_id=escena_id)

    primera = await una_sola_vez(
        sesion, paso, rastro, escritura_de_version_texto(sesion, escena_id, RUN)
    )
    segunda = await una_sola_vez(
        sesion, paso, rastro, escritura_de_version_texto(sesion, escena_id, RUN)
    )

    assert primera.valor == 1
    assert primera.paso == paso
    assert primera.tabla is None
    assert segunda.valor is None


async def test_el_fallo_del_paso_no_se_traga(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """Un paso que revienta tiene que reventar: el guardia decide si corre, no
    si salio bien. Y al no dejar rastro, el siguiente intento vuelve a correrlo.
    """
    escena_id = obra_con_outline.escena.id

    async def revienta() -> int:
        raise RuntimeError("el proveedor no responde")

    with pytest.raises(RuntimeError):
        await una_sola_vez(
            sesion,
            Paso(run_id=RUN, nombre="ESCRIBIENDO"),
            RastroEnVersionTexto(escena_id=escena_id),
            revienta,
        )

    escribir = escritura_de_version_texto(sesion, escena_id, RUN)
    resultado = await una_sola_vez(
        sesion,
        Paso(run_id=RUN, nombre="ESCRIBIENDO"),
        RastroEnVersionTexto(escena_id=escena_id),
        escribir,
    )
    assert resultado.repetido is False
    assert escribir.veces == 1
