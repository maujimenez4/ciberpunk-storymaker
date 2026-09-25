"""El ciclo de escritura de un capitulo: escribir, validar, reparar, escalar.

Aqui vive lo que el Escritor **no** hace: guardar la version, cruzar la puerta
mecanica de `calidad`, contar los reintentos y detenerse. El agente no juzga su
propia prosa y no decide cuando parar; si lo hiciera, el mismo codigo que
escribe se estaria dando permiso.

Lo que se comprueba, por requisito:

- **RF-ESC-02** — cada version es inmutable: reparar crea otra y marca la vigente.
- **RF-ESC-03** — el reintento lleva el defecto concreto con su cita.
- **RF-GUA-03** — una palabra vetada devuelve el capitulo con el termino
  concreto; agotado el limite, la generacion se detiene y se informa.
- **RF-ORQ-04** — maximo dos reparaciones por capitulo, y el contador **solo
  crece dentro del capitulo**.
- **Regla de dominio 10** — la persona y el tiempo verbal se comprueban en el
  texto, con el validador de `calidad` y no con uno propio.
- **RF-OBS-06** — `ejecucion` se completa con tokens reales, coste y veredicto.

Ninguna prueba llama al proveedor (CA-4).
"""

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.commons.db.auditoria import leer_auditoria
from app.commons.llm.doble import DobleDeterminista
from app.features.calidad import (
    CODIGO_DE_PALABRA_PROHIBIDA,
    NombreDeCanon,
    RangoDeExtension,
    localizar_veto,
)
from app.features.contexto import ensamblar_capitulo
from app.features.escena import RestriccionesDeDiscurso
from app.features.escritura.agents import MARCA_DE_PLANTILLA, MARCA_DE_REPARACION, Escritor
from app.features.escritura.modelos import Ejecucion, VersionTexto
from app.features.escritura.service import (
    PERSONA_DE_LA_OBRA,
    TIEMPO_VERBAL_DE_LA_OBRA,
    escribir_capitulo,
)
from app.features.obra.modelos import HechoCanon

# Tercera limitada y pasado: dos marcas de pasado, ninguna de primera persona.
BUENA = "Nadia cerro el invernadero y miro la carta que estaba sobre la mesa."
# La misma escena con una palabra vetada dentro.
CON_VETO = "Nadia miro la sangre que estaba sobre la mesa del invernadero."
# Y la misma con el nombre del canon mal escrito: «Maria» por «María».
CON_NOMBRE_MAL = "Maria estaba en el invernadero y cerro la puerta."

RANGO_ANCHO = RangoDeExtension(minimo=1, maximo=10_000)
RANGO_DE_CAPITULO = RangoDeExtension(minimo=800, maximo=1200)
"""El rango real de un capitulo (`definitions.md` §4.1). Cualquiera de estos
textos de prueba se queda corto, asi que sirve de **palanca de rechazo sin
veto**: es lo que permite que los tests del limite de reparaciones no dependan
de que la deteccion de palabras vetadas funcione. Lo destapo una mutacion de
CA-6, con ocho tests cayendo por una sola regla."""

NOMBRES = (NombreDeCanon(forma_canonica="María"),)


class ContadorDePalabras:
    """El mismo de `conftest.py`: exacto, reproducible y sin red."""

    def contar(self, texto: str) -> int:
        return len(texto.split())


class DobleQueDeclaraConsumo(DobleDeterminista):
    """Un doble con `ultimo_consumo`, que es lo que el cliente real expone.

    `ClienteModelo` **no** declara ese atributo -- su fichero es de T1 y ya
    cerro -- asi que el servicio lo pregunta y sigue sin el. Las dos ramas
    tienen test, que es lo unico que impide que «se guarda el coste» sea cierto
    solo en la maquina de quien lo escribio.
    """

    class Consumo:
        tokens_entrada = 900
        tokens_salida = 120
        coste_usd = Decimal("0.0015")
        # P-18: el CLI usa cache de prompt y estos dos campos se perdian en el
        # momento. El doble los declara **porque el cliente real los expone**:
        # un doble sin ellos no podria distinguir que se guardan de que no.
        cache_read_input_tokens = 6835
        cache_creation_input_tokens = 0

    @property
    def ultimo_consumo(self) -> "DobleQueDeclaraConsumo.Consumo":
        return self.Consumo()


async def _contexto(sesion, obra_con_outline):
    """El contexto del capitulo 1, ensamblado de verdad.

    Trae el hecho de canon sobre Nadia por el mismo motivo que la fixture
    `paquete`: sin el, la capa de canon sale vacia con el grafo lleno y el
    ensamblado falla con `CapaVacia`.
    """
    sesion.add(
        HechoCanon(
            obra_id=obra_con_outline.obra.id,
            entidad="Nadia",
            atributo="oficio",
            valor="botanica",
            origen="escena",
            escena_de_origen=str(obra_con_outline.escena.id),
        )
    )
    await sesion.flush()
    return await ensamblar_capitulo(sesion, obra_con_outline.capitulos[0].id, ContadorDePalabras())


def _escritor(respuestas: dict[str, str], cliente=None) -> Escritor:
    return Escritor(DobleDeterminista(respuestas) if cliente is None else cliente)


async def _escribir(sesion, obra_con_outline, escritor, **cambios):
    contexto = cambios.pop("contexto", None) or await _contexto(sesion, obra_con_outline)
    parametros = {
        # El contador entra con T11: el prompt del reintento se vuelve a
        # presupuestar contra la reserva, y sin contador no habria con que.
        "contador": ContadorDePalabras(),
        "run_id": "run-1",
        "modelo": "doble",
        "restricciones": RestriccionesDeDiscurso(
            persona="3ª limitada", tiempo_verbal="pasado", nivel_de_calor=2
        ),
        "rango_de_extension": RANGO_ANCHO,
    }
    parametros.update(cambios)
    return await escribir_capitulo(sesion, escritor, contexto=contexto, **parametros)


# ---------------------------------------------------------------------------
# El camino que aprueba
# ---------------------------------------------------------------------------


async def test_una_prosa_que_cumple_pasa_a_la_primera(sesion, obra_con_outline):
    escritura = await _escribir(sesion, obra_con_outline, _escritor({MARCA_DE_PLANTILLA: BUENA}))

    assert escritura.aprobado
    assert escritura.texto == BUENA
    assert len(escritura.intentos) == 1
    assert escritura.motivo_de_escalado is None


# ---------------------------------------------------------------------------
# RF-ESC-02 · la version es inmutable
# ---------------------------------------------------------------------------


async def test_reparar_crea_otra_version_y_marca_la_vigente(sesion, obra_con_outline):
    """RF-ESC-02: editar no modifica. La descartada se conserva entera.

    No se borra, y es deliberado: R-7 nombra canon, ledger e indice, no el
    manuscrito, y el disparador de T2 prohibe el `UPDATE` del texto justo para
    que lo entregado siga siendo recuperable.
    """
    escritura = await _escribir(
        sesion,
        obra_con_outline,
        _escritor({MARCA_DE_REPARACION: BUENA, MARCA_DE_PLANTILLA: CON_NOMBRE_MAL}),
        nombres_del_canon=NOMBRES,
    )

    versiones = (
        (await sesion.execute(select(VersionTexto).order_by(VersionTexto.numero))).scalars().all()
    )
    assert [(v.numero, v.vigente) for v in versiones] == [(1, False), (2, True)]
    assert versiones[0].texto == CON_NOMBRE_MAL
    assert versiones[1].texto == BUENA
    assert escritura.version_texto_id == versiones[1].id
    assert all(v.run_id == "run-1" for v in versiones)


# ---------------------------------------------------------------------------
# RF-GUA-03 · la palabra vetada
# ---------------------------------------------------------------------------


def test_localizar_veto_devuelve_el_termino_y_donde_esta():
    """`contiene_veto` da el termino; la puerta necesita ademas el pasaje.

    El desplazamiento no es un adorno: sin el, la cita del defecto no seria
    subcadena exacta en su desplazamiento (regla de dominio 8) y el defecto
    saldria **mal formado**, que es no bloquear.
    """
    encontrado = localizar_veto("Habia sangres en el suelo", ["sangre"])

    assert encontrado is not None
    veto, inicio, fin = encontrado
    assert veto == "sangre"
    assert "Habia sangres en el suelo"[inicio:fin] == "sangres"


def test_localizar_veto_no_ve_lo_que_no_esta():
    assert localizar_veto("Nadia cerro la puerta", ["sangre"]) is None


async def test_una_palabra_vetada_devuelve_el_capitulo_con_el_termino_concreto(
    sesion, obra_con_outline
):
    """RF-GUA-03. El segundo prompt nombra «sangre», no «hay algo prohibido»."""
    doble = DobleDeterminista({MARCA_DE_REPARACION: BUENA, MARCA_DE_PLANTILLA: CON_VETO})
    escritura = await _escribir(sesion, obra_con_outline, Escritor(doble), vetos=["sangre"])

    segundo_prompt, _ = doble.llamadas[1]
    assert CODIGO_DE_PALABRA_PROHIBIDA in segundo_prompt
    assert "sangre" in segundo_prompt
    assert escritura.aprobado
    assert escritura.intentos[0].termino_vetado == "sangre"


async def test_agotado_el_limite_por_veto_la_generacion_se_detiene_y_se_informa(
    sesion, obra_con_outline
):
    """RF-GUA-03, segunda mitad. Tres llamadas y para: ni una cuarta, ni bucle."""
    doble = DobleDeterminista({MARCA_DE_PLANTILLA: CON_VETO})
    escritura = await _escribir(sesion, obra_con_outline, Escritor(doble), vetos=["sangre"])

    assert not escritura.aprobado
    assert len(doble.llamadas) == 3
    assert escritura.motivo_de_escalado is not None
    assert "sangre" in escritura.motivo_de_escalado


async def test_la_coincidencia_queda_en_el_registro_de_auditoria(sesion, obra_con_outline):
    """RF-GUA-04 y `definitions.md` §8, `SEG-02`: «se cuenta en el registro».

    Y se anota tambien lo permitido: un registro que solo guarda los bloqueos
    responde «que salio mal» y no «por que aquella novela salio como salio»
    (`commons/db/auditoria.py`).

    **Desde la Fase 7 el motivo lleva delante el nombre de la regla.** No es
    cosmetica: el encargo §7 pide «un audit log de las **decisiones del policy
    engine**», y una decision sin la regla que la tomo no se puede atribuir
    cuando el catalogo tenga mas de una (RF-GUA-07).
    """
    await _escribir(
        sesion,
        obra_con_outline,
        _escritor({MARCA_DE_REPARACION: BUENA, MARCA_DE_PLANTILLA: CON_VETO}),
        vetos=["sangre"],
    )

    anotado = await leer_auditoria(sesion, obra_con_outline.obra.id)
    decisiones = [(f.decision, f.motivo) for f in anotado]
    assert ("bloqueado", "palabras_vetadas: veto: sangre") in decisiones
    assert any(d == "permitido" for d, _ in decisiones)
    assert all(m.startswith("palabras_vetadas: ") for _, m in decisiones)


# ---------------------------------------------------------------------------
# RF-ORQ-04 · dos reparaciones y no mas
# ---------------------------------------------------------------------------


async def test_a_la_tercera_se_escala_y_no_se_entra_en_bucle(sesion, obra_con_outline):
    """RF-ORQ-04 y CA-9: **maximo dos reparaciones dirigidas** por capitulo.

    **Sin vetos**, y a proposito: el bloqueo lo da la extension. Con la palabra
    vetada como unica palanca, este test caia tambien al mutar la deteccion de
    vetos, y entonces no distinguia «el limite funciona» de «el veto funciona».
    """
    doble = DobleDeterminista({MARCA_DE_PLANTILLA: BUENA})
    escritura = await _escribir(
        sesion, obra_con_outline, Escritor(doble), rango_de_extension=RANGO_DE_CAPITULO
    )

    assert len(escritura.intentos) == 3
    assert escritura.reparaciones_gastadas == 2
    assert not escritura.aprobado
    assert escritura.motivo_de_escalado is not None
    assert "EST-02" in escritura.motivo_de_escalado


async def test_el_contador_de_reparaciones_no_sobrevive_a_la_llamada(sesion, obra_con_outline):
    """RF-ORQ-04: «el contador **solo crece dentro del capitulo**».

    Un contador que sobreviviera al capitulo dejaria el segundo con un solo
    intento y el tercero con ninguno, y el manuscrito acabaria escalado entero
    sin que nada fallara. El mecanismo que lo impide es que el contador sea una
    variable local de `escribir_capitulo` y no un campo del Escritor, asi que lo
    que hay que ejercer son **dos llamadas con el mismo agente**: el segundo
    capitulo del outline no tiene escena planificada todavia y ensamblarlo
    fallaria por otro motivo, que es el que no se quiere probar aqui.
    """
    primero = await _contexto(sesion, obra_con_outline)
    doble = DobleDeterminista({MARCA_DE_REPARACION: BUENA, MARCA_DE_PLANTILLA: CON_NOMBRE_MAL})
    escritor = Escritor(doble)

    uno = await _escribir(
        sesion, obra_con_outline, escritor, contexto=primero, nombres_del_canon=NOMBRES
    )
    dos = await _escribir(
        sesion, obra_con_outline, escritor, contexto=primero, nombres_del_canon=NOMBRES
    )

    assert uno.aprobado and dos.aprobado
    assert uno.reparaciones_gastadas == 1
    assert dos.reparaciones_gastadas == 1


# ---------------------------------------------------------------------------
# Regla de dominio 10 · la persona y el tiempo verbal, en el texto
# ---------------------------------------------------------------------------


async def test_la_prosa_en_otra_persona_vuelve_al_escritor(sesion, obra_con_outline):
    """Regla de dominio 10, y con el validador de `calidad`, no con uno propio.

    La obra declara primera persona y la prosa no tiene una sola marca de
    primera: es `VOZ-03`, y bloquea. Pedirlo en el prompt no lo comprueba nadie
    -- eso ya se hacia, y es justo lo que el axioma 13 vino a cerrar.
    """
    doble = DobleDeterminista({MARCA_DE_PLANTILLA: BUENA})
    escritura = await _escribir(
        sesion,
        obra_con_outline,
        Escritor(doble),
        restricciones=RestriccionesDeDiscurso(
            persona="1ª", tiempo_verbal="pasado", nivel_de_calor=2
        ),
    )

    assert not escritura.aprobado
    assert [d.codigo for d in escritura.intentos[0].resultado.bloqueantes] == ["VOZ-03"]


def test_las_personas_de_la_obra_tienen_traduccion_a_la_de_calidad():
    """La obra dice `3ª limitada` y `calidad` dice `tercera_limitada`.

    Son el mismo concepto con dos grafias, y las dos existen hoy en el
    repositorio (ver Desviaciones). La traduccion vive en un sitio y este test
    la guarda: una persona nueva sin traducir haria que el validador de la
    regla de dominio 10 no se pudiera construir, y eso tiene que doler aqui y
    no en produccion.
    """
    from app.features.escena.schemas import PERSONAS, TIEMPOS_VERBALES

    assert set(PERSONA_DE_LA_OBRA) == set(PERSONAS)
    assert set(TIEMPO_VERBAL_DE_LA_OBRA) == set(TIEMPOS_VERBALES)


async def test_un_capitulo_fuera_del_rango_vuelve_al_escritor(sesion, obra_con_outline):
    """CA-35 desde este lado: el rango declarado llega al validador de verdad."""
    doble = DobleDeterminista({MARCA_DE_PLANTILLA: BUENA})
    escritura = await _escribir(
        sesion,
        obra_con_outline,
        Escritor(doble),
        rango_de_extension=RangoDeExtension(minimo=800, maximo=1200),
    )

    assert not escritura.aprobado
    assert "EST-02" in [d.codigo for d in escritura.intentos[0].resultado.bloqueantes]


async def test_un_nombre_mal_escrito_vuelve_al_escritor(sesion, obra_con_outline):
    """CA-16 desde este lado: los nombres del canon llegan al validador.

    «Maria» por «María» es la grafia equivocada del mismo nombre, que es lo que
    `PER-02` senala. Un nombre que se parece sin normalizar igual —«Nadya» por
    «Nadia»— **no** lo caza nadie, y es el punto ciego que `calidad` declara.
    """
    doble = DobleDeterminista({MARCA_DE_PLANTILLA: "Maria estaba en el invernadero."})
    escritura = await _escribir(
        sesion,
        obra_con_outline,
        Escritor(doble),
        nombres_del_canon=(NombreDeCanon(forma_canonica="María"),),
    )

    assert not escritura.aprobado
    assert "PER-02" in [d.codigo for d in escritura.intentos[0].resultado.bloqueantes]


# ---------------------------------------------------------------------------
# RF-OBS-06 · la ejecucion se completa
# ---------------------------------------------------------------------------


async def test_la_ejecucion_nace_con_el_recuento_previo_y_se_completa(sesion, obra_con_outline):
    """P-A: `tokens_previstos` antes de llamar, `tokens_reales` y coste despues."""
    escritura = await _escribir(
        sesion,
        obra_con_outline,
        Escritor(DobleQueDeclaraConsumo({MARCA_DE_PLANTILLA: BUENA})),
    )

    fila = (await sesion.execute(select(Ejecucion))).scalars().one()
    assert fila.tokens_previstos > 0
    assert fila.tokens_reales == 1020
    assert fila.coste == pytest.approx(0.0015)
    assert fila.veredicto == "aprobada"
    assert fila.prompt_id == "escritor"
    assert fila.prompt_version == "v1"
    assert escritura.aprobado


async def test_los_tokens_de_cache_quedan_en_la_ejecucion(sesion, obra_con_outline):
    """P-18. Se guardan **aparte** de `tokens_reales`, y esa separacion es el punto.

    `tokens_reales` es lo que hoy alimenta el coste imputado, y sumarle la cache
    cambiaria la cifra sin que nadie hubiera decidido a que precio. En columna
    propia, el dato queda para rehacer el calculo cuando esa tarifa se declare,
    y mientras tanto **no mueve ningun numero publicado**.

    Lo que esto compra: una corrida de hoy se podra recalcular manana. Sin la
    columna, cada llamada que hacemos es una medicion que se pierde.
    """
    await _escribir(
        sesion,
        obra_con_outline,
        Escritor(DobleQueDeclaraConsumo({MARCA_DE_PLANTILLA: BUENA})),
    )

    fila = (await sesion.execute(select(Ejecucion))).scalars().one()
    assert fila.cache_read_input_tokens == 6835
    assert fila.cache_creation_input_tokens == 0
    assert fila.tokens_reales == 1020, "la cache no se suma a los tokens imputados"
    assert fila.coste == pytest.approx(0.0015), "el coste no cambia: P-18 no lo imputa"


async def test_un_cliente_que_no_declara_consumo_no_impide_el_veredicto(sesion, obra_con_outline):
    """La otra rama: sin consumo declarado, la fila queda con el veredicto y
    los dos campos del proveedor nulos. No se imputa cero, que es lo que se
    guarda, se suma y se publica sin que nadie note que no habia dato."""
    await _escribir(sesion, obra_con_outline, _escritor({MARCA_DE_PLANTILLA: BUENA}))

    fila = (await sesion.execute(select(Ejecucion))).scalars().one()
    assert fila.tokens_reales is None
    assert fila.coste is None
    assert fila.veredicto == "aprobada"


class DobleConConsumoPorLlamada(DobleDeterminista):
    """`ultimo_consumo` cambia en cada llamada, como el cliente real (P-31).

    El Escritor y los jueces comparten cliente: leer el consumo al cerrar la
    fila devolvia el de la ultima llamada de juez, no el del Escritor.
    """

    class Consumo:
        def __init__(self, entrada: int, salida: int, coste: str) -> None:
            self.tokens_entrada = entrada
            self.tokens_salida = salida
            self.coste_usd = Decimal(coste)
            self.cache_read_input_tokens = 0
            self.cache_creation_input_tokens = 0

    def __init__(self, respuestas: dict[str, str]) -> None:
        super().__init__(respuestas)
        self.ultimo_consumo: DobleConConsumoPorLlamada.Consumo | None = None

    async def completar(self, prompt: str, semilla: int, modelo: str | None = None) -> str:
        respuesta = await super().completar(prompt, semilla, modelo)
        if MARCA_DE_PLANTILLA in prompt:
            self.ultimo_consumo = self.Consumo(900, 120, "0.0015")
        else:
            self.ultimo_consumo = self.Consumo(5000, 50, "0.0400")
        return respuesta


async def test_la_ejecucion_del_escritor_no_guarda_el_consumo_del_juez(sesion, obra_con_outline):
    """P-31: la foto del consumo se toma justo despues de `escritor.escribir`."""
    from app.features.calidad import Continuista

    doble = DobleConConsumoPorLlamada(
        {MARCA_DE_PLANTILLA: BUENA, "# Continuista": '{"defectos": []}'}
    )
    await _escribir(sesion, obra_con_outline, Escritor(doble), continuista=Continuista(doble))

    assert len(doble.llamadas) == 2, "el juez tiene que haber usado el cliente despues"
    fila = (await sesion.execute(select(Ejecucion))).scalars().one()
    assert fila.tokens_reales == 1020
    assert fila.coste == pytest.approx(0.0015)


async def test_cada_llamada_deja_su_ejecucion(sesion, obra_con_outline):
    """Regla de dominio 7: **cada** ejecucion, no la primera de cada capitulo."""
    await _escribir(
        sesion,
        obra_con_outline,
        _escritor({MARCA_DE_PLANTILLA: BUENA}),
        rango_de_extension=RANGO_DE_CAPITULO,
    )

    filas = (await sesion.execute(select(Ejecucion).order_by(Ejecucion.id))).scalars().all()
    assert len(filas) == 3
    assert [f.veredicto for f in filas] == ["rechazada", "rechazada", "escalada"]
