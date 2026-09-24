"""El checkpoint por capitulo y el contador que no se hereda (T5).

**RF-ORQ-05, RF-ORQ-04 sobre diez capitulos, R-3 y el cableado de R-6.**

Lo que este modulo prueba son dos frases de `architecture.md` §3.9 que hasta
ahora no tenian codigo detras:

| Frase del documento | Donde se prueba |
| --- | --- |
| «Al integrar un capitulo se persiste el avance, de modo que una caida reanuda desde **el ultimo capitulo completado**» | `test_al_integrar_un_capitulo_se_persiste_el_checkpoint`, que lee **por otro motor** |
| «`SiguienteCapitulo` … **No.** Cada capitulo empieza con su propio contador» | los dos lados de R-3: `test_a_la_tercera_reparacion_del_mismo_capitulo_se_escala` y `test_el_capitulo_siguiente_empieza_con_el_contador_a_cero` |

Y la tercera, que es la que la ola 1 dejo encargada: `exigir_que_la_novela_siga`
existia sin que nadie la llamara, asi que R-6 estaba **probado y sin efecto**.
Aqui se llama antes de empezar cada capitulo, y hay un test que lo exige
(`test_un_capitulo_escalado_impide_empezar_el_siguiente`).

Ninguna prueba llama al proveedor (CA-4): en este fichero no hay modelo que
llamar, y ese es el punto — el checkpoint es codigo determinista.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.commons.domain.errores import ErrorDeDominio
from app.conftest import ObraConOutline
from app.features.contexto import CapituloDesconocido
from app.features.escritura.checkpoint import (
    Arranque,
    CapituloAnteriorSinIntegrar,
    CapituloYaIntegrado,
    Checkpoint,
    CheckpointPrematuro,
    TrabajoSinCapitulo,
    empezar_capitulo,
    registrar_checkpoint,
    reparaciones_del_capitulo,
    siguiente_capitulo,
    ultimo_capitulo_completado,
)
from app.features.escritura.maquina import Estado, NovelaDetenida, Senal, transitar
from app.features.escritura.modelos import INTENTOS_MAXIMOS, Trabajo
from app.features.obra.modelos import Obra
from app.features.outline.modelos import Capitulo  # el outline de la segunda obra


async def _trabajo(
    sesion: AsyncSession,
    *,
    obra_id: int,
    capitulo_id: int | None,
    estado: Estado,
    intento: int = 0,
) -> Trabajo:
    """Un trabajo ya atado a su capitulo, que es como los abre el orquestador."""
    trabajo = Trabajo(
        obra_id=obra_id,
        escena_id=None,
        capitulo_id=capitulo_id,
        tipo="escribir_escena",
        estado=estado.value,
        intento=intento,
        run_id=f"cap{capitulo_id}-trb",
    )
    sesion.add(trabajo)
    await sesion.flush()
    return trabajo


async def _integrar(
    sesion: AsyncSession, plan: ObraConOutline, numero: int, *, intento: int = 0
) -> Checkpoint:
    """Lleva un capitulo hasta `INTEGRADA` y anota su checkpoint."""
    capitulo = next(c for c in plan.capitulos if c.numero == numero)
    trabajo = await _trabajo(
        sesion,
        obra_id=plan.obra.id,
        capitulo_id=capitulo.id,
        estado=Estado.INTEGRADA,
        intento=intento,
    )
    return await registrar_checkpoint(sesion, trabajo)


# ---------------------------------------------------------------------------
# RF-ORQ-05: al integrar un capitulo se persiste el avance
# ---------------------------------------------------------------------------


async def test_al_integrar_un_capitulo_se_persiste_el_checkpoint(
    motor: AsyncEngine, sesion: AsyncSession, obra_con_outline: ObraConOutline
):
    """**Otro motor, sobre el mismo fichero.**

    Releer por la misma sesion devolveria lo que su mapa de identidad ya tiene
    en memoria, y el test pasaria con un checkpoint que no escribe nada. Lo que
    importa es lo que vera el orquestador **despues de la caida** (§3.7).
    """
    capitulo = obra_con_outline.capitulos[0]
    checkpoint = await _integrar(sesion, obra_con_outline, capitulo.numero)

    assert checkpoint.capitulo_id == capitulo.id
    assert checkpoint.numero == capitulo.numero

    async with AsyncSession(motor) as otra:
        recuperado = await ultimo_capitulo_completado(otra, obra_id=obra_con_outline.obra.id)
    assert recuperado.capitulo_id == capitulo.id
    assert recuperado.numero == capitulo.numero
    assert recuperado.hay_avance is True


async def test_una_obra_sin_capitulos_integrados_no_tiene_avance(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
):
    """Y no se inventa el capitulo cero: reanudar desde el principio es correcto."""
    checkpoint = await ultimo_capitulo_completado(sesion, obra_id=obra_con_outline.obra.id)
    assert checkpoint.hay_avance is False
    assert checkpoint.capitulo_id is None
    assert checkpoint.numero is None


async def test_el_checkpoint_es_el_ultimo_por_numero_y_no_el_ultimo_escrito(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
):
    """El avance se mide en el outline, no en el orden en que se escribio.

    Se integra el 2 y **despues** el 1. Un checkpoint que ordenara por `id` de
    trabajo diria «vas por el 1» y la reanudacion reescribiria el 2.
    """
    await _integrar(sesion, obra_con_outline, 2)
    await _integrar(sesion, obra_con_outline, 1)

    checkpoint = await ultimo_capitulo_completado(sesion, obra_id=obra_con_outline.obra.id)
    assert checkpoint.numero == 2


async def test_el_checkpoint_es_por_obra(sesion: AsyncSession, obra_con_outline: ObraConOutline):
    """§3.8: varias obras a la vez, y el avance de una no es el de la otra."""
    await _integrar(sesion, obra_con_outline, 1)
    otra = Obra(
        titulo="Otra",
        genero="romance",
        tono="calido",
        nivel_de_calor=2,
        elementos_obligatorios=["un elemento que el comprador pidio"],
    )
    sesion.add(otra)
    await sesion.flush()

    checkpoint = await ultimo_capitulo_completado(sesion, obra_id=otra.id)
    assert checkpoint.hay_avance is False


async def test_no_hay_checkpoint_de_un_trabajo_que_no_esta_integrado(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
):
    """«Al **integrar**» no es «al terminar». Un capitulo escalado o fallido no
    es avance, y anotarlo haria que la reanudacion lo diera por hecho."""
    trabajo = await _trabajo(
        sesion,
        obra_id=obra_con_outline.obra.id,
        capitulo_id=obra_con_outline.capitulos[0].id,
        estado=Estado.VALIDANDO,
    )
    with pytest.raises(CheckpointPrematuro):
        await registrar_checkpoint(sesion, trabajo)


async def test_no_hay_checkpoint_de_un_trabajo_sin_capitulo(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
):
    """Un checkpoint sin capitulo no dice desde donde reanudar: es un `None`
    silencioso, que es la forma de fallar que esta tarea existe para evitar."""
    trabajo = await _trabajo(
        sesion,
        obra_id=obra_con_outline.obra.id,
        capitulo_id=None,
        estado=Estado.INTEGRADA,
    )
    with pytest.raises(TrabajoSinCapitulo):
        await registrar_checkpoint(sesion, trabajo)


# ---------------------------------------------------------------------------
# R-3: el contador de reparaciones solo crece dentro del capitulo
# ---------------------------------------------------------------------------


async def test_a_la_tercera_reparacion_del_mismo_capitulo_se_escala(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
):
    """Un lado de R-3. Dos reparaciones gastadas **en este capitulo** y la
    siguiente salida de `REPARANDO` es `ESCALADA` (`CLAUDE.md` §9.1)."""
    capitulo = obra_con_outline.capitulos[0]
    await _trabajo(
        sesion,
        obra_id=obra_con_outline.obra.id,
        capitulo_id=capitulo.id,
        estado=Estado.REPARANDO,
        intento=INTENTOS_MAXIMOS,
    )
    gastadas = await reparaciones_del_capitulo(
        sesion, obra_id=obra_con_outline.obra.id, capitulo_id=capitulo.id
    )
    assert gastadas == INTENTOS_MAXIMOS
    assert transitar(Estado.REPARANDO, Senal.PASO_COMPLETADO, intento=gastadas) is Estado.ESCALADA


async def test_el_capitulo_siguiente_empieza_con_el_contador_a_cero(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
):
    """El otro lado de R-3, y el que un contador global rompe.

    El capitulo 1 gasta sus dos reparaciones y **se integra**: es un capitulo
    sano que costo dos vueltas. Si el contador fuera de la obra, el 2 empezaria
    en dos y **el primer defecto lo escalaria** sin que hubiera fallado nada
    (`architecture.md` §3.9).
    """
    await _integrar(sesion, obra_con_outline, 1, intento=INTENTOS_MAXIMOS)

    arranque = await empezar_capitulo(
        sesion,
        obra_id=obra_con_outline.obra.id,
        capitulo_id=obra_con_outline.capitulos[1].id,
    )
    assert isinstance(arranque, Arranque)
    assert arranque.intento == 0
    assert arranque.anterior.numero == 1
    assert (
        transitar(Estado.REPARANDO, Senal.PASO_COMPLETADO, intento=arranque.intento)
        is Estado.ESCRIBIENDO
    )


async def test_el_contador_es_del_capitulo_y_sobrevive_al_relanzamiento(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
):
    """`FALLIDA` «se relanza como **trabajo nuevo**» (§3.3), y el contador es
    del capitulo: un relanzamiento que empezara de cero daria reparaciones
    infinitas y el limite de dos dejaria de ser un limite."""
    capitulo = obra_con_outline.capitulos[0]
    await _trabajo(
        sesion,
        obra_id=obra_con_outline.obra.id,
        capitulo_id=capitulo.id,
        estado=Estado.FALLIDA,
        intento=INTENTOS_MAXIMOS,
    )
    await _trabajo(
        sesion,
        obra_id=obra_con_outline.obra.id,
        capitulo_id=capitulo.id,
        estado=Estado.ESCRIBIENDO,
        intento=0,
    )
    gastadas = await reparaciones_del_capitulo(
        sesion, obra_id=obra_con_outline.obra.id, capitulo_id=capitulo.id
    )
    assert gastadas == INTENTOS_MAXIMOS


async def test_las_reparaciones_de_otro_capitulo_no_cuentan(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
):
    """La mutacion que borra el `capitulo_id` del filtro cae aqui."""
    await _trabajo(
        sesion,
        obra_id=obra_con_outline.obra.id,
        capitulo_id=obra_con_outline.capitulos[0].id,
        estado=Estado.INTEGRADA,
        intento=INTENTOS_MAXIMOS,
    )
    gastadas = await reparaciones_del_capitulo(
        sesion,
        obra_id=obra_con_outline.obra.id,
        capitulo_id=obra_con_outline.capitulos[1].id,
    )
    assert gastadas == 0


# ---------------------------------------------------------------------------
# R-6, cableado: un capitulo que detiene la novela impide empezar el siguiente
# ---------------------------------------------------------------------------


async def test_un_capitulo_escalado_impide_empezar_el_siguiente(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
):
    """**El encargo de la ola 1.** `exigir_que_la_novela_siga` existia y nadie
    la llamaba: R-6 estaba probado y sin efecto en produccion."""
    await _integrar(sesion, obra_con_outline, 1)
    await _trabajo(
        sesion,
        obra_id=obra_con_outline.obra.id,
        capitulo_id=obra_con_outline.capitulos[1].id,
        estado=Estado.ESCALADA,
    )

    with pytest.raises(NovelaDetenida):
        await empezar_capitulo(
            sesion,
            obra_id=obra_con_outline.obra.id,
            capitulo_id=obra_con_outline.capitulos[2].id,
        )


async def test_un_escalado_de_otra_obra_no_detiene_esta(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
):
    """§3.8: que una obra se detenga no para a las demas."""
    otra = Obra(
        titulo="Otra",
        genero="romance",
        tono="calido",
        nivel_de_calor=2,
        elementos_obligatorios=["un elemento que el comprador pidio"],
    )
    sesion.add(otra)
    await sesion.flush()
    await _trabajo(sesion, obra_id=otra.id, capitulo_id=None, estado=Estado.ESCALADA)

    arranque = await empezar_capitulo(
        sesion,
        obra_id=obra_con_outline.obra.id,
        capitulo_id=obra_con_outline.capitulos[0].id,
    )
    assert arranque.numero == 1


async def test_un_capitulo_fallido_no_detiene_la_novela_pero_bloquea_el_siguiente(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
):
    """La pregunta que T2 dejo abierta, contestada en las dos mitades.

    `FALLIDA` **no** entra en `DETIENEN_LA_NOVELA` —§3.6 lo declara relanzable,
    y frenar la obra convertiria un remedio automatico en una decision
    humana— y aun asi **no se escribe encima**: lo que habilita el capitulo N+1
    no es «que N no este escalado», es «que N este integrado».
    """
    await _trabajo(
        sesion,
        obra_id=obra_con_outline.obra.id,
        capitulo_id=obra_con_outline.capitulos[0].id,
        estado=Estado.FALLIDA,
    )

    with pytest.raises(CapituloAnteriorSinIntegrar) as fallo:
        await empezar_capitulo(
            sesion,
            obra_id=obra_con_outline.obra.id,
            capitulo_id=obra_con_outline.capitulos[1].id,
        )
    assert not isinstance(fallo.value, NovelaDetenida)
    assert fallo.value.numero_pendiente == 1


async def test_relanzado_e_integrado_el_fallido_desbloquea_el_siguiente(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
):
    """La otra mitad: el remedio de §3.6 funciona sin intervencion humana."""
    await _trabajo(
        sesion,
        obra_id=obra_con_outline.obra.id,
        capitulo_id=obra_con_outline.capitulos[0].id,
        estado=Estado.FALLIDA,
    )
    await _integrar(sesion, obra_con_outline, 1)

    arranque = await empezar_capitulo(
        sesion,
        obra_id=obra_con_outline.obra.id,
        capitulo_id=obra_con_outline.capitulos[1].id,
    )
    assert arranque.numero == 2


async def test_no_se_vuelve_a_empezar_un_capitulo_ya_integrado(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
):
    """R-2: la reanudacion **no duplica**. Un capitulo integrado no se rehace."""
    await _integrar(sesion, obra_con_outline, 1)
    with pytest.raises(CapituloYaIntegrado):
        await empezar_capitulo(
            sesion,
            obra_id=obra_con_outline.obra.id,
            capitulo_id=obra_con_outline.capitulos[0].id,
        )


async def test_no_se_empieza_un_capitulo_de_otra_obra(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
):
    """Sin el `obra_id` en el filtro, el capitulo de otra obra pasaria las tres
    comprobaciones contra un outline que no es el suyo."""
    otra = Obra(
        titulo="Otra",
        genero="romance",
        tono="calido",
        nivel_de_calor=2,
        elementos_obligatorios=["un elemento que el comprador pidio"],
    )
    sesion.add(otra)
    await sesion.flush()

    with pytest.raises(CapituloDesconocido):
        await empezar_capitulo(
            sesion, obra_id=otra.id, capitulo_id=obra_con_outline.capitulos[0].id
        )


async def test_los_errores_del_checkpoint_son_de_dominio():
    """`commons/errors/` los traduce a HTTP: ninguno sale como 500."""
    for clase in (
        CapituloAnteriorSinIntegrar,
        CapituloYaIntegrado,
        CheckpointPrematuro,
        TrabajoSinCapitulo,
    ):
        assert issubclass(clase, ErrorDeDominio)


# ---------------------------------------------------------------------------
# Cual es el capitulo siguiente: lo que T5 sabe y la maquina no
# ---------------------------------------------------------------------------


async def test_el_siguiente_capitulo_es_el_primero_sin_integrar(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
):
    await _integrar(sesion, obra_con_outline, 1)
    await _integrar(sesion, obra_con_outline, 2)

    siguiente = await siguiente_capitulo(sesion, obra_id=obra_con_outline.obra.id)
    assert siguiente is not None
    assert siguiente.numero == 3


async def test_el_siguiente_capitulo_no_es_el_de_otra_obra(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
):
    """La mutacion que quita el `obra_id` del filtro **no tumbaba nada** hasta
    este test, porque las otras obras de la suite no tenian outline.

    Con dos obras planificadas a la vez —que es §3.8— un `siguiente_capitulo`
    sin filtro devolveria el capitulo 1 de la otra: el orquestador escribiria
    la novela equivocada, o se negaria a avanzar en la suya por un hueco ajeno.
    """
    otra = Obra(
        titulo="Otra",
        genero="romance",
        tono="calido",
        nivel_de_calor=2,
        elementos_obligatorios=["un elemento que el comprador pidio"],
    )
    sesion.add(otra)
    await sesion.flush()
    sesion.add(
        Capitulo(
            obra_id=otra.id,
            numero=1,
            titulo="El primero de la otra obra",
            pov_dominante="Nadia",
            gancho_de_apertura="La puerta estaba abierta",
            tipo_de_corte_final="pregunta",
            extension_objetivo=1200,
            lugar="Cadiz, el muelle",
            objetivo="Encontrar a quien escribio la carta",
            obstaculo="Nadie recuerda el nombre",
            giro_de_valor_previsto="esperanza -> sospecha",
        )
    )
    await sesion.flush()
    await _integrar(sesion, obra_con_outline, 1)

    siguiente = await siguiente_capitulo(sesion, obra_id=obra_con_outline.obra.id)
    assert siguiente is not None
    assert siguiente.capitulo_id == obra_con_outline.capitulos[1].id
    assert siguiente.numero == 2


async def test_no_hay_siguiente_cuando_los_diez_estan_integrados(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
):
    """RF-PLA-02: son diez. Terminar es que no quede ninguno, no contar hasta diez."""
    for capitulo in obra_con_outline.capitulos:
        await _integrar(sesion, obra_con_outline, capitulo.numero)

    assert await siguiente_capitulo(sesion, obra_id=obra_con_outline.obra.id) is None
