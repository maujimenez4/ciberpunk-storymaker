"""De los almacenes a las capas: la tabla de `architecture.md` §4.8, ejecutable.

Aqui vive el aviso que la ola 2 dejo escrito y que decide si R-3 vale algo:
**`recuperar` devuelve `[]` tanto si el filtro no deja nada como si el indice
esta vacio, y son dos cosas distintas.** Si no se distinguen, la comprobacion
de RF-CTX-06 se cumple *por consecuencia* — nunca hay censo, nunca falla — y su
test pasaria sin comprobar nada.

Los cuatro casos de la capa de memoria tienen test, y **solo el ultimo falla**:

| Caso | Censo | Que es |
| --- | --- | --- |
| Nadie trajo vector de consulta | 0 | Hoy nadie puede: `ClienteModelo` no vectoriza (Desviaciones, ola 2) |
| El filtro no deja nada pertinente | 0 | Capitulo sin memoria que venga a cuento. Normal |
| Hay escenas pertinentes y **ninguna indexada** | 0 | Indice sin llenar, no almacen roto |
| Hay pertinentes **e indexadas** y no sale nada | >0 | **Fallo del almacen** |
"""

from collections.abc import Sequence

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.db.vectores import empaquetar_vector
from app.conftest import ObraConOutline
from app.features.canon import Embedding
from app.features.contexto.almacenes import AlmacenFuerzaBruta, Vecino
from app.features.contexto.capas import CAPAS_CON_ORIGEN, CapaVacia, Paquete, Surtido
from app.features.contexto.presupuesto import TOPES, Capa
from app.features.contexto.service import (
    CapituloDesconocido,
    CapituloSinEscena,
    DatosDeLlamada,
    ensamblar_capitulo,
    registrar_ejecucion,
    surtir_capitulo,
)
from app.features.escena.modelos import Escena
from app.features.escritura.modelos import VersionTexto
from app.features.obra.modelos import HechoCanon

CONSULTA = [1.0, 0.0, 0.0]


class ContadorDePalabras:
    """El mismo doble del resto de la feature: exacto y reproducible."""

    def contar(self, texto: str) -> int:
        return len(texto.split())


class AlmacenMudo:
    """Tiene con que responder y no responde. Es el fallo del almacen de R-3."""

    modo = "mudo"

    async def vecinos(
        self, consulta: Sequence[float], candidatos: Sequence[int], limite: int
    ) -> list[Vecino]:
        return []


def _llamada() -> DatosDeLlamada:
    return DatosDeLlamada(
        run_id="run-1",
        prompt_id="escritor",
        prompt_version="v1",
        prompt_hash="0" * 64,
        modelo="doble",
        semilla=7,
    )


async def _hecho_de(sesion: AsyncSession, base: ObraConOutline, entidad: str) -> HechoCanon:
    """Un hecho del grafo sobre una entidad que la ficha **si** nombra."""
    hecho = HechoCanon(
        obra_id=base.obra.id,
        entidad=entidad,
        atributo="oficio",
        valor="botanica",
        origen="escena",
        escena_de_origen=str(base.escena.id),
    )
    sesion.add(hecho)
    await sesion.flush()
    return hecho


# ---------------------------------------------------------------------------
# 1. La tabla de `architecture.md` §4.8: cada capa, de su almacen
# ---------------------------------------------------------------------------


async def test_las_siete_capas_con_origen_se_surten_de_su_almacen(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """§4.8, fila a fila. Constitucional de la biblia, estructural del outline…

    La capa de canon se surte con un hecho sobre **Nadia**, que es quien la
    ficha nombra: el hecho que trae la fixture es sobre el perro y por eso no
    entra (ver el test de R-3, donde eso es justo lo que falla).
    """
    await _hecho_de(sesion, obra_con_outline, "Nadia")

    surtidos = await surtir_capitulo(sesion, obra_con_outline.capitulos[0].id)

    assert surtidos[Capa.CONSTITUCIONAL].piezas, "la biblia surte la constitucional"
    assert surtidos[Capa.ESTRUCTURAL].piezas, "el outline surte la estructural"
    assert surtidos[Capa.CANON].piezas, "el grafo de canon surte la de canon"
    assert surtidos[Capa.INSTRUCCION].piezas, "la ficha surte la instruccion"
    assert Capa.RESERVA not in surtidos, "la reserva no tiene almacen de origen"
    assert set(surtidos) == CAPAS_CON_ORIGEN


async def test_el_capitulo_que_no_existe_no_se_ensambla(sesion: AsyncSession) -> None:
    with pytest.raises(CapituloDesconocido):
        await surtir_capitulo(sesion, 9999)


async def test_el_capitulo_sin_escena_planificada_no_se_ensambla(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """Sin ficha no hay capa de instruccion, y un paquete sin ella no se pide."""
    with pytest.raises(CapituloSinEscena):
        await surtir_capitulo(sesion, obra_con_outline.capitulos[5].id)


# ---------------------------------------------------------------------------
# 2. R-3 · la capa de canon vacia en un capitulo que tiene hechos
# ---------------------------------------------------------------------------


async def test_el_canon_vacio_con_hechos_en_el_grafo_falla_antes_de_llamar(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """R-3, tal y como lo enuncia el plan.

    La obra **tiene** un hecho —el perro se llama Luna— y la ficha nombra a
    Nadia y a Teo, asi que el filtro por ficha deja la capa vacia. El censo dice
    que habia con que surtirla, y eso es lo que hace que falle en vez de salir
    un paquete sin canon que el Escritor contradiria sin saberlo.
    """
    with pytest.raises(CapaVacia) as caida:
        await ensamblar_capitulo(sesion, obra_con_outline.capitulos[0].id, ContadorDePalabras())

    assert caida.value.capa == Capa.CANON.value
    assert caida.value.disponibles == 1


async def test_el_canon_con_un_hecho_de_la_ficha_si_sale_y_va_etiquetado_por_hc_id(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """La pareja del anterior: con un hecho pertinente el paquete sale.

    Sin este test, endurecer la regla hasta fallar siempre pasaria inadvertido.
    """
    hecho = await _hecho_de(sesion, obra_con_outline, "Nadia")

    contexto = await ensamblar_capitulo(
        sesion, obra_con_outline.capitulos[0].id, ContadorDePalabras()
    )

    assert f"hc:{hecho.id}" in contexto.paquete.ids_por_capa[Capa.CANON]


async def test_una_obra_sin_ningun_hecho_de_canon_no_falla(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """Censo 0: no hay canon que enviar porque no hay canon. No es averia."""
    await sesion.execute(
        text("DELETE FROM hecho_canon WHERE obra_id = :o"), {"o": obra_con_outline.obra.id}
    )

    contexto = await ensamblar_capitulo(
        sesion, obra_con_outline.capitulos[0].id, ContadorDePalabras()
    )

    assert contexto.paquete.ids_por_capa[Capa.CANON] == ()


# ---------------------------------------------------------------------------
# 3. El aviso de la ola 2: los cuatro casos de la capa de memoria
# ---------------------------------------------------------------------------

# Se surte **el capitulo 2** y no el 1: el filtro estructural acota por rango de
# capitulos, asi que para el capitulo 1 no hay nada anterior que recuperar y los
# cuatro casos darian censo 0 por el mismo motivo. Un montaje asi pasaria los
# tests sin distinguir nada, que es justo el fallo que el aviso advierte.


async def _escena_actual(sesion: AsyncSession, base: ObraConOutline, **campos: object) -> Escena:
    """La escena del capitulo 2, que es la que se esta ensamblando."""
    valores: dict[str, object] = {
        "capitulo_id": base.capitulos[1].id,
        "version_obra_id": base.version_obra.id,
        "orden_discurso": 2,
        "tiempo_historia": "dia 2",
        "pov": "Nadia",
        "lugar": "El invernadero",
        "presentes": ["Nadia", "Teo"],
        "objetivo_del_pov": "Insistir",
        "obstaculo": "Teo calla",
        "resultado": "no",
        "valor_entrada": "calma",
        "valor_salida": "miedo",
        "extension_objetivo": 1200,
        "densidad_de_dialogo_objetivo": 0.4,
        "distancia_psiquica": 3,
    }
    valores.update(campos)
    escena = Escena(**valores)  # type: ignore[arg-type]
    sesion.add(escena)
    await sesion.flush()
    return escena


async def _indexar(sesion: AsyncSession, base: ObraConOutline, escena_id: int) -> Embedding:
    embedding = Embedding(
        obra_id=base.obra.id,
        escena_id=escena_id,
        fragmento="Nadia cerro el invernadero con llave",
        vector=empaquetar_vector(CONSULTA),
        dimension=3,
        modelo="doble",
    )
    sesion.add(embedding)
    await sesion.flush()
    return embedding


async def test_sin_vector_de_consulta_la_memoria_queda_vacia_y_no_es_averia(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """Hoy nadie puede traerlo: `ClienteModelo` no vectoriza (Desviaciones).

    El indice esta lleno **y la escena anterior es pertinente**, asi que este
    caso no se confunde con los otros tres: lo que falta es el vector.
    """
    await _escena_actual(sesion, obra_con_outline)
    await _indexar(sesion, obra_con_outline, obra_con_outline.escena.id)

    surtidos = await surtir_capitulo(sesion, obra_con_outline.capitulos[1].id)

    assert surtidos[Capa.MEMORIA] == Surtido(piezas=(), disponibles=0)


async def test_memoria_vacia_porque_el_filtro_no_deja_nada_pertinente(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """Primer caso del aviso: no hay escena pertinente que recuperar.

    La escena anterior esta **indexada** y no viene a cuento: otro lugar, otros
    personajes, ningun hilo abierto que la traiga. El censo tiene que ser 0.
    Contar el indice sin pasar por el filtro convertiria este caso normal en un
    fallo del almacen, y es la mutacion que este test caza.
    """
    await _escena_actual(
        sesion, obra_con_outline, lugar="La azotea", pov="Bruno", presentes=["Bruno"]
    )
    await _indexar(sesion, obra_con_outline, obra_con_outline.escena.id)

    surtidos = await surtir_capitulo(
        sesion,
        obra_con_outline.capitulos[1].id,
        consulta=CONSULTA,
        almacen=AlmacenFuerzaBruta(sesion),
    )

    assert surtidos[Capa.MEMORIA] == Surtido(piezas=(), disponibles=0)


async def test_la_escena_en_curso_no_es_candidata_de_su_propio_filtro(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """El caso anterior pasaba por el motivo equivocado, y lo destapo CA-6.

    Una escena comparte lugar y presentes **consigo misma**, asi que si el rango
    de capitulos llegara hasta el suyo seria siempre candidata y «el filtro no
    deja nada» no ocurriria nunca: el test de al lado quedaba verde porque la
    escena en curso no estaba indexada, no porque el filtro la descartara.

    Aqui se indexa **la escena en curso y solo ella**. Si entrara en su propio
    filtro, el censo seria 1 y el ensamblado fallaria por un fragmento que
    todavia no se ha escrito.
    """
    actual = await _escena_actual(sesion, obra_con_outline)
    await _indexar(sesion, obra_con_outline, actual.id)

    surtidos = await surtir_capitulo(
        sesion,
        obra_con_outline.capitulos[1].id,
        consulta=CONSULTA,
        almacen=AlmacenFuerzaBruta(sesion),
    )

    assert surtidos[Capa.MEMORIA] == Surtido(piezas=(), disponibles=0)


async def test_memoria_vacia_porque_lo_pertinente_no_esta_indexado(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """Segundo caso del aviso, y el que el aviso 2 explica: nadie ha indexado.

    La escena anterior **si** es pertinente y no tiene embedding. El censo tiene
    que ser 0: contar los candidatos del filtro en vez de los indexados haria
    fallar un sistema en el que simplemente todavia no se ha vectorizado nada, y
    hoy no se ha vectorizado nada porque `ClienteModelo` no sabe.
    """
    await _escena_actual(sesion, obra_con_outline)

    surtidos = await surtir_capitulo(
        sesion,
        obra_con_outline.capitulos[1].id,
        consulta=CONSULTA,
        almacen=AlmacenFuerzaBruta(sesion),
    )

    assert surtidos[Capa.MEMORIA] == Surtido(piezas=(), disponibles=0)


async def test_memoria_vacia_con_lo_pertinente_indexado_si_es_fallo_del_almacen(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """Tercer caso, y el unico que falla: habia con que surtirla y no salio nada.

    Es el que distingue de verdad. Si los tres casos anteriores se contaran
    igual que este, RF-CTX-06 se cumpliria por consecuencia y no por regla.
    """
    await _escena_actual(sesion, obra_con_outline)
    await _indexar(sesion, obra_con_outline, obra_con_outline.escena.id)
    await _hecho_de(sesion, obra_con_outline, "Nadia")

    with pytest.raises(CapaVacia) as caida:
        await ensamblar_capitulo(
            sesion,
            obra_con_outline.capitulos[1].id,
            ContadorDePalabras(),
            consulta=CONSULTA,
            almacen=AlmacenMudo(),
        )

    assert caida.value.capa == Capa.MEMORIA.value
    assert caida.value.disponibles == 1


async def test_con_el_almacen_de_verdad_la_memoria_sale_y_va_etiquetada(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """La pareja: el mismo montaje con un almacen que si responde."""
    await _escena_actual(sesion, obra_con_outline)
    embedding = await _indexar(sesion, obra_con_outline, obra_con_outline.escena.id)
    await _hecho_de(sesion, obra_con_outline, "Nadia")

    contexto = await ensamblar_capitulo(
        sesion,
        obra_con_outline.capitulos[1].id,
        ContadorDePalabras(),
        consulta=CONSULTA,
        almacen=AlmacenFuerzaBruta(sesion),
    )

    assert contexto.paquete.ids_por_capa[Capa.MEMORIA] == (f"emb:{embedding.id}",)


# ---------------------------------------------------------------------------
# 4. La continuidad local, y por que el capitulo 1 no falla
# ---------------------------------------------------------------------------


async def test_la_continuidad_del_primer_capitulo_esta_vacia_y_no_es_averia(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """No hay escena N-1 escrita, asi que no hay censo: es el caso normal."""
    await _hecho_de(sesion, obra_con_outline, "Nadia")

    surtidos = await surtir_capitulo(sesion, obra_con_outline.capitulos[0].id)

    assert surtidos[Capa.CONTINUIDAD] == Surtido(piezas=(), disponibles=0)


async def test_la_continuidad_trae_el_texto_vigente_de_la_escena_anterior(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """Y solo el vigente: una version antigua no es el manuscrito (RF-ESC-02)."""
    anterior = obra_con_outline.escena
    segunda = Escena(
        capitulo_id=obra_con_outline.capitulos[1].id,
        version_obra_id=obra_con_outline.version_obra.id,
        orden_discurso=2,
        tiempo_historia="dia 2",
        pov="Nadia",
        lugar="El invernadero",
        presentes=["Nadia", "Teo"],
        objetivo_del_pov="Insistir",
        obstaculo="Teo calla",
        resultado="no",
        valor_entrada="calma",
        valor_salida="miedo",
        extension_objetivo=1200,
        densidad_de_dialogo_objetivo=0.4,
        distancia_psiquica=3,
    )
    sesion.add(segunda)
    await sesion.flush()
    sesion.add_all(
        [
            VersionTexto(
                escena_id=anterior.id,
                numero=1,
                texto="la version vieja",
                vigente=False,
                run_id="r0",
            ),
            VersionTexto(
                escena_id=anterior.id,
                numero=2,
                texto="la puerta estaba abierta",
                vigente=True,
                run_id="r1",
            ),
        ]
    )
    await sesion.flush()
    await _hecho_de(sesion, obra_con_outline, "Nadia")

    surtidos = await surtir_capitulo(sesion, obra_con_outline.capitulos[1].id)

    textos = " ".join(p.texto for p in surtidos[Capa.CONTINUIDAD].piezas)
    assert "la puerta estaba abierta" in textos
    assert "la version vieja" not in textos


# ---------------------------------------------------------------------------
# 5. CA-12 · desde `ejecucion` se reconstruye el paquete
# ---------------------------------------------------------------------------


async def test_la_ejecucion_guarda_el_desglose_los_ids_y_el_recuento_previo(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """RF-CTX-09 y RF-OBS-06: por capa, con su capa, y el previsto de P-A."""
    hecho = await _hecho_de(sesion, obra_con_outline, "Nadia")

    contexto = await ensamblar_capitulo(
        sesion, obra_con_outline.capitulos[0].id, ContadorDePalabras()
    )
    ejecucion_id = await registrar_ejecucion(sesion, contexto, _llamada())

    fila = (
        await sesion.execute(
            text(
                "SELECT tokens_por_capa, tokens_previstos, tokens_reales, "
                "ids_canon, ids_recuperados, parametros "
                "FROM ejecucion WHERE id = :id"
            ),
            {"id": ejecucion_id},
        )
    ).one()
    import json

    assert json.loads(fila.tokens_por_capa) == contexto.paquete.tokens_por_capa
    assert fila.tokens_previstos == contexto.paquete.tokens_previstos
    assert fila.tokens_reales is None, "el real lo pone el proveedor, despues"
    assert json.loads(fila.ids_canon) == [hecho.id]
    assert json.loads(fila.ids_recuperados) == []
    # RF-CTX-09 pide **todas** las capas que tienen ids, con su capa, y el
    # esquema de T2 solo trae dos columnas de ids (ver Desviaciones).
    por_capa = json.loads(fila.parametros)["ids_por_capa"]
    assert set(por_capa) == {capa.value for capa in CAPAS_CON_ORIGEN}
    assert por_capa[Capa.CANON.value] == [f"hc:{hecho.id}"]


async def test_ca_12_desde_la_ejecucion_y_los_almacenes_sale_el_mismo_paquete(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """CA-12, y es una demostracion, no una afirmacion.

    Se ensambla, se persiste, se vuelve a ensamblar **desde los almacenes** y se
    compara con lo que la fila guardo: mismo desglose, mismos ids, mismos hechos
    de canon. Es lo que hace que CU-07 se pueda responder sin preguntarle a
    nadie, y lo que se perderia si el paquete lo ensamblara un modelo.
    """
    hecho = await _hecho_de(sesion, obra_con_outline, "Nadia")
    capitulo_id = obra_con_outline.capitulos[0].id

    primero = await ensamblar_capitulo(sesion, capitulo_id, ContadorDePalabras())
    ejecucion_id = await registrar_ejecucion(sesion, primero, _llamada())

    segundo = await ensamblar_capitulo(sesion, capitulo_id, ContadorDePalabras())

    fila = (
        await sesion.execute(
            text("SELECT tokens_por_capa, ids_canon FROM ejecucion WHERE id = :id"),
            {"id": ejecucion_id},
        )
    ).one()
    import json

    assert segundo.paquete.texto == primero.paquete.texto
    assert segundo.paquete.tokens_por_capa == json.loads(fila.tokens_por_capa)
    assert json.loads(fila.ids_canon) == [hecho.id]
    assert segundo.paquete.ids_por_capa[Capa.CANON] == (f"hc:{hecho.id}",)


# ---------------------------------------------------------------------------
# 6. La fixture `paquete`, que es lo que recibe quien escribe
# ---------------------------------------------------------------------------


def test_la_fixture_paquete_trae_las_siete_capas_surtidas(paquete: Paquete) -> None:
    """Una fixture que nadie ejerce se rompe en silencio, y esta es para T8.

    El Escritor **solo ve lo que hay en el paquete** (`CLAUDE.md` §9.1): si la
    fixture llegara con una capa sin surtir, T8 escribiria sus tests contra un
    paquete incompleto y los defectos dejarian de ser atribuibles al ensamblado.
    """
    assert set(paquete.ids_por_capa) == CAPAS_CON_ORIGEN
    assert paquete.ids_por_capa[Capa.CANON], "la capa de canon no puede llegar vacia"
    assert paquete.ids_por_capa[Capa.INSTRUCCION], "sin ficha no hay que escribir"
    assert paquete.tokens_previstos == paquete.desglose.total
    assert paquete.desglose.reserva_libre == TOPES[Capa.RESERVA]
