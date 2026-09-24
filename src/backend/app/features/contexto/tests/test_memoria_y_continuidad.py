"""R-7: lo unico que esta fase anade de verdad sobre la Fase 2.

La frase del plan no admite dos lecturas: «el resumen del capitulo 3 alimenta el
contexto del 4… sin esto los diez capitulos son diez cuentos».

**La capa es la de memoria recuperada y no la de continuidad local.** Lo dice
`architecture.md` §4.8 fila a fila: la continuidad son «escenas N-1 y N-2», con
su prosa entera; la memoria es «indice vectorial **+ resumenes**». Un resumen no
es una escena anterior -- es el rastro largo de un capitulo ya cerrado -- y por
eso comparte capa y tope con lo recuperado.

**Y la capa pasa a tener dos almacenes, que es lo que obliga a revisar el
censo.** Mientras el indice estuvo vacio, el cuarto caso de RF-CTX-06 -- hay
escenas indexadas y el almacen no devuelve nada -- se veia porque la capa entera
quedaba vacia. Con los resumenes dentro, la capa sale llena por el otro almacen
y esa averia pasaria inadvertida: el aviso que la ola 1 dejo escrito era
exactamente ese, y aqui tiene test.

**Sobre el corpus, dicho antes de leerlo:** la busqueda es **lexica**
(`CLAUDE.md` §4.2), no semantica. Dos fragmentos que dicen lo mismo con otras
palabras no se reconocen, asi que un corpus montado esperando semantica pasaria
por el motivo equivocado. Quien trae la pertinencia aqui es el filtro
estructural; el vector solo ordena lo que el filtro dejo.
"""

from collections.abc import Sequence

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.db.vectores import desempaquetar_vector
from app.commons.llm.cliente import vectorizar_texto
from app.commons.llm.doble import DobleDeterminista
from app.conftest import ContadorDePalabras, ObraConOutline
from app.features.canon import Extraccion, consolidar_escena, vectorizador_de
from app.features.contexto.almacenes import AlmacenFuerzaBruta, Vecino
from app.features.contexto.capas import CapaVacia, Surtido
from app.features.contexto.presupuesto import Capa
from app.features.contexto.service import ensamblar_capitulo, surtir_capitulo
from app.features.escena.modelos import Escena
from app.features.escritura.modelos import VersionTexto
from app.features.obra.modelos import HechoCanon


class AlmacenMudo:
    """Tiene con que responder y no responde. Es el fallo del almacen de R-3."""

    modo = "mudo"

    async def vecinos(
        self, consulta: Sequence[float], candidatos: Sequence[int], limite: int
    ) -> list[Vecino]:
        return []


async def _escena_en(
    sesion: AsyncSession, base: ObraConOutline, capitulo: int, **campos: object
) -> Escena:
    """La escena del capitulo `capitulo`, con `orden_discurso` = `capitulo` (P-C, 1:1).

    La del capitulo 1 la trae la fixture: la cardinalidad es 1:1 y crear otra
    choca contra la restriccion que la sostiene.
    """
    if capitulo == 1 and not campos:
        return base.escena
    valores: dict[str, object] = {
        "capitulo_id": base.capitulos[capitulo - 1].id,
        "version_obra_id": base.version_obra.id,
        "orden_discurso": capitulo,
        "tiempo_historia": f"dia {capitulo}",
        "pov": "Nadia",
        "lugar": "El invernadero",
        "presentes": ["Nadia", "Teo"],
        "objetivo_del_pov": "Que Teo confiese",
        "obstaculo": "Teo no habla",
        "resultado": "si-pero",
        "valor_entrada": "confianza",
        "valor_salida": "sospecha",
        "extension_objetivo": 1200,
        "densidad_de_dialogo_objetivo": 0.4,
        "distancia_psiquica": 3,
    }
    valores.update(campos)
    escena = Escena(**valores)  # type: ignore[arg-type]
    sesion.add(escena)
    await sesion.flush()
    return escena


async def _escribir_capitulo(
    sesion: AsyncSession, base: ObraConOutline, capitulo: int, texto: str
) -> VersionTexto:
    """Un capitulo con su escena y su version de texto **vigente**: aprobado."""
    escena = await _escena_en(sesion, base, capitulo)
    version = VersionTexto(
        escena_id=escena.id, numero=1, texto=texto, vigente=True, run_id=f"run-{capitulo}"
    )
    sesion.add(version)
    await sesion.flush()
    return version


async def _integrar_capitulo(
    sesion: AsyncSession, base: ObraConOutline, capitulo: int, *, texto: str, resumen: str
) -> None:
    """Escribe el capitulo y lo consolida **por la puerta de `canon`**.

    El resumen no se inserta a mano: pasa por `consolidar_escena`, que es quien
    lo escribe en produccion, con el `vectorizar` del cliente. Asi el test
    ejerce la juntura entera -- resumen e indice -- y no una maqueta de ella.
    """
    version = await _escribir_capitulo(sesion, base, capitulo, texto)
    await consolidar_escena(
        sesion,
        obra_id=base.obra.id,
        escena_id=version.escena_id,
        capitulo_id=base.capitulos[capitulo - 1].id,
        extraccion=Extraccion.model_validate(
            {
                "hechos": [{"entidad": "Nadia", "atributo": "oficio", "valor": "botanica"}],
                "eventos": [],
                "resumen": resumen,
                "hilos": [],
            }
        ),
        prosa=texto,
        version_texto_id=version.id,
        vectorizar=vectorizador_de(DobleDeterminista({})),
    )


async def _hecho_de(sesion: AsyncSession, base: ObraConOutline, entidad: str) -> HechoCanon:
    """Un hecho sobre alguien que la ficha **si** nombra, o la capa de canon falla."""
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


def _consulta_lexica(texto: str) -> list[float]:
    """El vector de consulta, con **el mismo vectorizador** que indexa."""
    return desempaquetar_vector(vectorizar_texto(texto).datos)


# ---------------------------------------------------------------------------
# 1. El resumen alimenta el contexto de los siguientes (RF-MEM-04 aplicado)
# ---------------------------------------------------------------------------


async def test_el_resumen_del_capitulo_anterior_entra_en_la_capa_de_memoria(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """RF-MEM-04 aplicado: el resumen deja de ser una tabla que nadie consulta."""
    await _integrar_capitulo(
        sesion,
        obra_con_outline,
        1,
        texto="Nadia encontro la carta en el invernadero",
        resumen="Nadia encuentra una carta sin firma",
    )
    await _escena_en(sesion, obra_con_outline, 2)

    surtidos = await surtir_capitulo(sesion, obra_con_outline.capitulos[1].id)

    piezas = surtidos[Capa.MEMORIA].piezas
    assert any("Nadia encuentra una carta sin firma" in p.texto for p in piezas)
    assert piezas[0].identificador == f"rc:{obra_con_outline.capitulos[0].id}"


async def test_r7_el_resumen_del_capitulo_3_alimenta_el_contexto_del_4(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """R-7 entero, con el indice lleno de verdad y por la puerta de produccion.

    Tres capitulos integrados con el `vectorizar` del cliente -- el mismo que
    usara produccion, porque el doble y el real comparten implementacion (T1) --
    y el cuarto ensamblandose. Lo que se afirma es la frase del plan sin
    rodeos: **el resumen del 3 esta en el paquete del 4**.
    """
    for numero in (1, 2, 3):
        await _integrar_capitulo(
            sesion,
            obra_con_outline,
            numero,
            texto=f"Capitulo {numero}. Nadia volvio al invernadero y cerro la puerta.",
            resumen=f"En el capitulo {numero} Nadia vuelve al invernadero",
        )
    await _escena_en(sesion, obra_con_outline, 4)

    contexto = await ensamblar_capitulo(
        sesion,
        obra_con_outline.capitulos[3].id,
        ContadorDePalabras(),
        consulta=_consulta_lexica("Nadia invernadero puerta"),
        almacen=AlmacenFuerzaBruta(sesion),
    )

    assert "En el capitulo 3 Nadia vuelve al invernadero" in contexto.paquete.texto
    ids = contexto.paquete.ids_por_capa[Capa.MEMORIA]
    assert f"rc:{obra_con_outline.capitulos[2].id}" in ids
    assert any(i.startswith("emb:") for i in ids), "y el indice tambien surte la capa"


async def test_los_resumenes_van_delante_de_los_fragmentos_recuperados(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """El recorte quita por el final, asi que el orden decide que se pierde.

    Un fragmento es un parrafo entre muchos del mismo capitulo; un resumen es lo
    unico que representa al capitulo entero. Perder el resumen es perder el
    capitulo, y por eso va delante aunque no traiga puntuacion.
    """
    await _integrar_capitulo(
        sesion,
        obra_con_outline,
        1,
        texto="Nadia volvio al invernadero y cerro la puerta.",
        resumen="Nadia vuelve al invernadero",
    )
    await _escena_en(sesion, obra_con_outline, 2)

    surtidos = await surtir_capitulo(
        sesion,
        obra_con_outline.capitulos[1].id,
        consulta=_consulta_lexica("Nadia invernadero puerta"),
        almacen=AlmacenFuerzaBruta(sesion),
    )

    prefijos = [(p.identificador or "").split(":")[0] for p in surtidos[Capa.MEMORIA].piezas]
    assert prefijos.count("rc") == 1
    assert prefijos.count("emb") >= 1
    assert prefijos.index("rc") < prefijos.index("emb")


async def test_el_resumen_de_otra_obra_no_alimenta_esta(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """La capa se acota por obra, y no por casualidad de identificadores."""
    await _integrar_capitulo(
        sesion,
        obra_con_outline,
        1,
        texto="Nadia encontro la carta",
        resumen="Nadia encuentra una carta",
    )
    await _escena_en(sesion, obra_con_outline, 2)

    surtidos = await surtir_capitulo(sesion, obra_con_outline.capitulos[1].id)
    ajenos = [
        p
        for p in surtidos[Capa.MEMORIA].piezas
        if (p.identificador or "").startswith("rc:")
        and p.identificador != f"rc:{obra_con_outline.capitulos[0].id}"
    ]

    assert ajenos == []


# ---------------------------------------------------------------------------
# 2. El censo de la capa, con dos almacenes dentro
# ---------------------------------------------------------------------------


async def test_el_capitulo_escrito_que_no_dejo_resumen_es_fallo_del_almacen(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """El censo de los resumenes, y la mitad que lo hace alcanzable.

    El capitulo 1 esta escrito y aprobado -- tiene texto vigente -- y no dejo
    resumen. La capa de memoria llega vacia **teniendo con que llenarse**, que
    es RF-CTX-06: la consolidacion escribe el resumen en la misma transaccion
    que los hechos, asi que un capitulo integrado sin resumen es un almacen que
    no surtio, no un capitulo sin memoria pertinente.
    """
    await _escribir_capitulo(sesion, obra_con_outline, 1, "Nadia cerro el invernadero")
    await _escena_en(sesion, obra_con_outline, 2)
    await _hecho_de(sesion, obra_con_outline, "Nadia")

    with pytest.raises(CapaVacia) as caida:
        await ensamblar_capitulo(sesion, obra_con_outline.capitulos[1].id, ContadorDePalabras())

    assert caida.value.capa == Capa.MEMORIA.value
    assert caida.value.disponibles == 1


async def test_el_capitulo_planificado_y_aun_sin_escribir_no_cuenta_en_el_censo(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """La pareja del anterior, y la que impide la restriccion inalcanzable.

    Si el censo contara los capitulos del outline en vez de los escritos,
    **toda obra fallaria desde el capitulo 2**, que es el caso mas normal que
    hay. Aqui el capitulo 1 tiene escena y no tiene texto: censo 0.
    """
    await _escena_en(sesion, obra_con_outline, 2)
    await _hecho_de(sesion, obra_con_outline, "Nadia")

    surtidos = await surtir_capitulo(sesion, obra_con_outline.capitulos[1].id)

    assert surtidos[Capa.MEMORIA] == Surtido(piezas=(), disponibles=0)


async def test_con_el_indice_lleno_el_almacen_mudo_sigue_siendo_averia(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """**El encargo que la ola 1 dejo: que el censo siga diciendo la verdad.**

    Capitulo integrado, resumen escrito, indice lleno y almacen mudo. La capa
    **no** esta vacia -- el resumen la surte -- y aun asi tiene que fallar: si
    solo se mirara la capa entera, la averia del indice se escondería detras del
    otro almacen y RF-CTX-06 volveria a cumplirse por consecuencia.
    """
    await _integrar_capitulo(
        sesion,
        obra_con_outline,
        1,
        texto="Nadia volvio al invernadero y cerro la puerta.",
        resumen="Nadia vuelve al invernadero",
    )
    await _escena_en(sesion, obra_con_outline, 2)

    with pytest.raises(CapaVacia) as caida:
        await ensamblar_capitulo(
            sesion,
            obra_con_outline.capitulos[1].id,
            ContadorDePalabras(),
            consulta=_consulta_lexica("Nadia invernadero"),
            almacen=AlmacenMudo(),
        )

    assert caida.value.capa == Capa.MEMORIA.value
    assert caida.value.disponibles == 1


# ---------------------------------------------------------------------------
# 3. La continuidad local, y el orden que `CLAUDE.md` §4.1 declara
# ---------------------------------------------------------------------------


async def test_la_continuidad_trae_la_escena_n_1_antes_que_la_n_2(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """«Escena N-2 antes que N-1» es la columna de recorte de `CLAUDE.md` §4.1.

    El recorte quita **por el final**, asi que esa frase solo es ejecutable si
    la N-1 va primera: al reves, lo que se perderia al apretar el tope seria la
    escena inmediatamente anterior, que es la unica que el Escritor no puede
    contradecir sin que se note.

    La regla estaba escrita en el SQL y **no la guardaba ningun test**: los dos
    que habia comprueban el capitulo 1 y la version vigente, y los dos siguen
    en verde con el orden invertido.
    """
    await _escribir_capitulo(sesion, obra_con_outline, 1, "Primera: la puerta estaba abierta")
    await _escribir_capitulo(sesion, obra_con_outline, 2, "Segunda: Teo no estaba")
    await _escena_en(sesion, obra_con_outline, 3)

    surtidos = await surtir_capitulo(sesion, obra_con_outline.capitulos[2].id)

    textos = [p.texto for p in surtidos[Capa.CONTINUIDAD].piezas]
    assert len(textos) == 2, "la N-1 y la N-2, no una sola"
    assert "Segunda: Teo no estaba" in textos[0], "la N-1 va primera"
    assert "Primera: la puerta estaba abierta" in textos[1], "la N-2 detras"
