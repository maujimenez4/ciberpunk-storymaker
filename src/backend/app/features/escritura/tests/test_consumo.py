"""Fase 6 · T7 · Tokens, coste y latencia: por llamada, por capitulo y por novela.

**El agujero que esta tarea tapa.** Hasta hoy solo el Escritor dejaba fila en
`ejecucion`: el Entrevistador, el Arquitecto, el Planificador, el Extractor, el
Continuista y el Critico llamaban al modelo **sin dejar rastro de coste**. La
cifra de una novela se quedaba corta siempre, y `RF-OBS-03` la usa despues para
comparar plantillas.
"""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.llm.claude_code import (
    MODELO_ESCRITOR,
    MODELO_JUEZ,
    Consumo,
    TarifaDesconocida,
    coste_derivado,
)
from app.features.escritura.consumo import (
    cerrar_llamada,
    consumo_de_novela,
    registrar_llamada,
)
from app.features.escritura.modelos import Ejecucion
from app.features.obra.modelos import Obra


async def _llamada(
    sesion: AsyncSession,
    obra: Obra,
    *,
    prompt_id: str,
    modelo: str,
    entrada: int,
    salida: int,
    latencia_ms: int = 10,
    cache_leida: int = 0,
) -> int:
    ejecucion_id = await registrar_llamada(
        sesion,
        run_id="run-1",
        obra_id=obra.id,
        escena_id=None,
        prompt_id=prompt_id,
        prompt_version="v1",
        prompt_hash="h" * 64,
        modelo=modelo,
        semilla=7,
        tokens_previstos=entrada,
    )
    await cerrar_llamada(
        sesion,
        ejecucion_id,
        consumo=Consumo(
            modelo=modelo,
            semilla=7,
            tokens_entrada=entrada,
            tokens_salida=salida,
            coste_usd=coste_derivado(modelo, entrada, salida),
            cache_read_input_tokens=cache_leida,
        ),
        latencia_ms=latencia_ms,
        veredicto="aprobada",
    )
    return ejecucion_id


async def test_el_coste_de_la_novela_incluye_al_juez(sesion: AsyncSession, obra: Obra) -> None:
    """`R-9`. El test que abre la tarea.

    Si el juez no deja fila, el coste de una novela sale sistematicamente corto
    y nadie lo nota: no falla nada, solo es mas barata de lo que fue.
    """
    await _llamada(
        sesion, obra, prompt_id="escritor", modelo=MODELO_ESCRITOR, entrada=10_000, salida=1_500
    )
    await _llamada(
        sesion, obra, prompt_id="critico", modelo=MODELO_JUEZ, entrada=12_000, salida=800
    )

    resumen = await consumo_de_novela(sesion, obra_id=obra.id)

    assert resumen.llamadas == 2
    assert set(resumen.por_rol) == {"escritor", "critico"}
    assert resumen.coste_usd == (
        coste_derivado(MODELO_ESCRITOR, 10_000, 1_500) + coste_derivado(MODELO_JUEZ, 12_000, 800)
    )


async def test_el_desglose_por_rol_cuadra_con_el_total(sesion: AsyncSession, obra: Obra) -> None:
    """Un total que no es la suma de sus partes no se puede auditar."""
    await _llamada(
        sesion, obra, prompt_id="escritor", modelo=MODELO_ESCRITOR, entrada=1_000, salida=100
    )
    await _llamada(
        sesion, obra, prompt_id="escritor", modelo=MODELO_ESCRITOR, entrada=2_000, salida=200
    )
    await _llamada(
        sesion, obra, prompt_id="extractor", modelo=MODELO_ESCRITOR, entrada=500, salida=50
    )

    resumen = await consumo_de_novela(sesion, obra_id=obra.id)

    assert resumen.llamadas == 3
    assert resumen.por_rol["escritor"].llamadas == 2
    assert sum(r.llamadas for r in resumen.por_rol.values()) == resumen.llamadas
    assert sum(r.coste_usd for r in resumen.por_rol.values()) == resumen.coste_usd
    assert sum(r.tokens_entrada for r in resumen.por_rol.values()) == resumen.tokens_entrada
    assert sum(r.latencia_ms for r in resumen.por_rol.values()) == resumen.latencia_ms


async def test_un_consumo_ausente_deja_nulo_y_no_cero(sesion: AsyncSession, obra: Obra) -> None:
    """«Un cero se guarda, se suma y se publica sin que nadie note que el dato
    no estaba; un nulo se ve.»

    Que la latencia **si** se guarde con el consumo ausente no es incoherencia:
    la llamada tardo lo que tardo aunque el proveedor no dijera cuanto gasto.
    """
    ejecucion_id = await registrar_llamada(
        sesion,
        run_id="run-1",
        obra_id=obra.id,
        escena_id=None,
        prompt_id="escritor",
        prompt_version="v1",
        prompt_hash="h" * 64,
        modelo=MODELO_ESCRITOR,
        semilla=7,
        tokens_previstos=900,
    )

    await cerrar_llamada(sesion, ejecucion_id, consumo=None, latencia_ms=12, veredicto="aprobada")

    fila = await sesion.get(Ejecucion, ejecucion_id)
    assert fila is not None
    assert fila.tokens_reales is None
    assert fila.coste is None
    assert fila.latencia_ms == 12


async def test_una_llamada_sin_cerrar_no_cuenta_como_gratis(
    sesion: AsyncSession, obra: Obra
) -> None:
    """Una llamada registrada y no cerrada -- el proceso murio a mitad -- tiene
    coste nulo, y **nulo no es cero**: entra en el recuento de llamadas y no
    baja el coste medio."""
    await registrar_llamada(
        sesion,
        run_id="run-1",
        obra_id=obra.id,
        escena_id=None,
        prompt_id="escritor",
        prompt_version="v1",
        prompt_hash="h" * 64,
        modelo=MODELO_ESCRITOR,
        semilla=7,
        tokens_previstos=900,
    )

    resumen = await consumo_de_novela(sesion, obra_id=obra.id)

    assert resumen.llamadas == 1
    assert resumen.coste_usd == Decimal(0)
    assert resumen.llamadas_sin_consumo == 1


async def test_un_modelo_sin_tarifa_no_imputa_cero(sesion: AsyncSession, obra: Obra) -> None:
    """Ya es asi en `coste_derivado`; el test lo fija **desde este lado**, que es
    donde se usaria por descuido. Un modelo nuevo sin tarifa saldria gratis."""
    with pytest.raises(TarifaDesconocida):
        coste_derivado("un-modelo-que-nadie-tarifo", 1_000, 100)


async def test_la_cache_leida_se_ve_aunque_no_se_impute(sesion: AsyncSession, obra: Obra) -> None:
    """`P-18`, y esta es la mitad que si toca aqui.

    **A que precio se imputa la cache es una tarifa, y una tarifa la firma una
    persona** (`claude_code.py`): esta tarea no la inventa. Lo que si hace es
    que el hueco **se vea**. Medido en produccion, un prompt de 5.012 tokens
    devolvio `input_tokens=10` y `cache_read=6.835`: imputar solo el primero
    deja el coste corto por un factor de ~680, y hoy esa diferencia no aparece
    en ningun numero.

    Con `tokens_de_cache_no_imputados` en el resumen, quien lea el coste ve al
    lado el volumen que no esta dentro. Sigue sin imputarse, y deja de ser
    invisible.
    """
    await _llamada(
        sesion,
        obra,
        prompt_id="escritor",
        modelo=MODELO_ESCRITOR,
        entrada=10,
        salida=100,
        cache_leida=6_835,
    )

    resumen = await consumo_de_novela(sesion, obra_id=obra.id)

    assert resumen.tokens_entrada == 10
    assert resumen.tokens_de_cache_no_imputados == 6_835
    assert resumen.coste_usd == coste_derivado(MODELO_ESCRITOR, 10, 100)


async def test_una_novela_sin_llamadas_da_cero_y_no_revienta(
    sesion: AsyncSession, obra: Obra
) -> None:
    resumen = await consumo_de_novela(sesion, obra_id=obra.id)

    assert resumen.llamadas == 0
    assert resumen.coste_usd == Decimal(0)
    assert resumen.por_rol == {}


async def test_el_consumo_de_una_obra_no_suma_el_de_otra(sesion: AsyncSession, obra: Obra) -> None:
    """Sin esto, el coste por novela seria el coste del servidor."""
    otra = Obra(
        titulo="Otra",
        genero=obra.genero,
        tono=obra.tono,
        nivel_de_calor=obra.nivel_de_calor,
        elementos_obligatorios=obra.elementos_obligatorios,
    )
    sesion.add(otra)
    await sesion.flush()
    await _llamada(
        sesion, obra, prompt_id="escritor", modelo=MODELO_ESCRITOR, entrada=1_000, salida=100
    )
    await _llamada(
        sesion, otra, prompt_id="escritor", modelo=MODELO_ESCRITOR, entrada=9_999, salida=999
    )

    resumen = await consumo_de_novela(sesion, obra_id=obra.id)

    assert resumen.llamadas == 1
    assert resumen.tokens_entrada == 1_000
