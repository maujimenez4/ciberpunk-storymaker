"""El ciclo de un capitulo, de punta a punta (T11). **No anade comportamiento.**

Lo que aqui se comprueba es lo que ninguna tarea anterior podia comprobar sola:
que las piezas que cada una dejo probadas **se tocan entre si** donde el plan
decia que se tocarian. Las siete junturas que la fase dejo sin dueno tienen una
seccion cada una, y las cinco que se cierran aqui tienen su test:

| Juntura | Que dejaba abierto | Donde se cierra |
| --- | --- | --- |
| 1 | Quien instancia el `PresupuestoConcurrente` unico del proceso | `obtener_presupuesto` |
| 2 | Que los tokens del portero fueran los del Ensamblador | `ejecutar_ciclo` |
| 3 | Que el prompt del reintento volviera a presupuestarse | `test_presupuesto_del_reintento.py` |
| 5 | Que `sqlite-vec` se detectara **al levantar** | el *lifespan* de `main.py` |
| 6 y 7 | Que un rechazo real de la puerta no dejara rastro | `ejecutar_ciclo` |

La juntura 4 —el metodo de vectorizar de `ClienteModelo`— **no se cierra**, y el
motivo esta escrito en Desviaciones: el protocolo es de T1, `DobleDeterminista`
lo hereda por subclase explicita y anadirle un miembro sin implementar romperia
la suite entera. Lo que si existe aqui es el punto de conexion: `vectorizar`
llega por parametro y baja hasta el Extractor.

Ninguna prueba llama al proveedor (CA-4): el cliente es `DobleDeterminista`.
"""

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.commons.db.vectores import extension_disponible
from app.commons.jobs.turnos import CerrojoDeEscena, PresupuestoConcurrente
from app.commons.llm.doble import DobleDeterminista
from app.features.canon.agents import Extractor
from app.features.canon.modelos import Embedding, Evento, HiloNarrativo, ResumenCapitulo
from app.features.escena.agents import Planificador
from app.features.escena.modelos import Escena
from app.features.escritura.agents import Escritor
from app.features.escritura.ciclo import (
    Agentes,
    _codigos_bloqueantes,
    abrir_trabajo,
    ejecutar_ciclo,
)
from app.features.escritura.modelos import Ejecucion, Trabajo, VersionTexto
from app.features.escritura.router import obtener_presupuesto
from app.features.obra.modelos import HechoCanon
from app.features.outline.modelos import Capitulo
from app.features.outline.schemas import BeatDeGenero
from app.main import crear_app

# ---------------------------------------------------------------------------
# Lo que devuelve el doble, por rol
# ---------------------------------------------------------------------------

FRASE = "Nadia cerro el invernadero y miro la carta que estaba sobre la mesa."
"""Trece palabras, tercera limitada y pasado: ni una marca de primera persona."""

PROSA_BUENA = "\n\n".join(" ".join([FRASE] * 23) for _ in range(4))
"""1.196 palabras: dentro del rango 1.000-1.500 de `definitions.md` §4.1."""

PROSA_CORTA = FRASE
"""La palanca de rechazo **sin veto**: `EST-02`, extension fuera de rango.

Es la palanca que T8 separo al descubrir que la palabra vetada era la unica de
casi toda la suite. Aqui importa por lo mismo: lo que este modulo prueba es que
la puerta rechaza de verdad, no que la deteccion de vetos funcione."""

BIBLIA: dict[str, Any] = {
    "protagonista": "Nadia",
    "persona": "3ª limitada",
    "tiempo_verbal": "pasado",
    "nivel_de_calor": 2,
}

FICHA = json.dumps(
    {
        "tiempo_historia": "dia 1, manana",
        "elapsed_desde_anterior": None,
        "pov": "Nadia",
        "lugar": "El invernadero",
        "presentes": ["Nadia", "Teo"],
        "mencionados": ["la madre de Teo"],
        "objetivo_del_pov": "Que Teo confiese",
        "obstaculo": "Teo no habla de su madre",
        "resultado": "si-pero",
        "valor_entrada": "confianza",
        "valor_salida": "sospecha",
        "extension_objetivo": 1200,
        "densidad_de_dialogo_objetivo": 0.4,
        "distancia_psiquica": 3,
        "beat_de_genero": "Encuentro",
        "planta": ["la carta sin abrir"],
        "paga": [],
        "revela": [],
    }
)

EXTRACCION = json.dumps(
    {
        "hechos": [{"entidad": "Teo", "atributo": "oficio", "valor": "relojero"}],
        "eventos": [
            {
                "descripcion": "Nadia cierra el invernadero",
                "tiempo_historia": "dia 1, manana",
                "testigos": ["Nadia"],
            }
        ],
        "resumen": "Nadia cierra el invernadero y encuentra una carta.",
        "hilos": [{"pregunta": "quien escribio la carta"}],
    }
)


def _capitulos_del_outline() -> list[dict[str, Any]]:
    return [
        {
            "numero": n,
            "titulo": f"Capitulo {n}",
            "pov_dominante": "Nadia",
            "lugar": "El invernadero",
            "objetivo": "Que Teo confiese",
            "obstaculo": "Teo no habla de su madre",
            "valor_entrada": "confianza",
            "valor_salida": "sospecha",
            "gancho_de_apertura": "La puerta estaba abierta",
            "tipo_de_corte_final": "pregunta",
            "extension_objetivo": 1200,
            "beat_de_genero": beat.value,
        }
        for n, beat in enumerate(BeatDeGenero, start=1)
    ]


def _respuestas(prosa: str = PROSA_BUENA) -> dict[str, str]:
    """Las cuatro plantillas, elegidas por su marca. **El orden importa:** el
    doble devuelve la primera clave que sea subcadena del prompt."""
    return {
        "# Arquitecto": json.dumps({"biblia": BIBLIA, "capitulos": _capitulos_del_outline()}),
        "PLANIFICADOR DE ESCENA": FICHA,
        "# Extractor · v1": EXTRACCION,
        "ESCRITOR · v1": prosa,
        # P-17: el Continuista **corre de verdad** desde que `Agentes` lo
        # lleva. Sin esta clave el doble lanza `RespuestaNoPreparada`, y eso
        # es buena noticia: el rol dejo de estar escrito y sin llamar.
        "# Continuista": '{"defectos": []}',
    }


class ContadorDePalabras:
    """El mismo de `conftest.py`: exacto, reproducible y sin red."""

    def contar(self, texto: str) -> int:
        return len(texto.split())


class PresupuestoEspia(PresupuestoConcurrente):
    """Un portero que apunta **con cuantos tokens** se le pidio cada turno.

    Sin esto, «el portero recibe los tokens del Ensamblador» no es comprobable:
    `turno(0)` pasa todas las puertas y el contador vuelve a cero al salir.
    """

    def __init__(self) -> None:
        super().__init__()
        self.pedidos: list[int] = []

    async def _pedir(self, tokens: int, plazo: float | None, paso: str) -> None:
        self.pedidos.append(tokens)
        await super()._pedir(tokens, plazo, paso)


def _agentes(respuestas: dict[str, str]) -> Agentes:
    doble = DobleDeterminista(respuestas)
    return Agentes(
        planificador=Planificador(doble),
        escritor=Escritor(doble),
        extractor=Extractor(doble),
    )


@pytest.fixture
async def obra_lista(sesion, obra_con_outline):
    """La obra planificada **con canon sobre quien sale en la ficha**.

    `obra_con_outline` solo trae el hecho del perro, que la ficha no nombra: la
    capa de canon saldria vacia con el grafo lleno y el ensamblado fallaria con
    `CapaVacia` (R-3). Que haga falta anadirlo es la senal de que la regla vive.

    Va con `origen: brief` y **sin escena de origen** a proposito: asi el test
    de R-7 puede contar los hechos que vienen de una escena y exigir cero.

    Y se le anaden a la biblia `persona` y `tiempo_verbal`, que es lo que el
    Arquitecto escribe de verdad (RF-PLA-01) y lo que el ciclo relee para
    reconstruir las restricciones de la escena. La fixture compartida no los
    trae porque las tareas anteriores pasaban las restricciones a mano; el ciclo
    no puede, porque no hay nadie por encima que se las de.
    """
    obra_con_outline.version_obra.biblia = {
        **obra_con_outline.version_obra.biblia,
        "persona": "3ª limitada",
        "tiempo_verbal": "pasado",
    }
    sesion.add(
        HechoCanon(
            obra_id=obra_con_outline.obra.id,
            entidad="Nadia",
            atributo="oficio",
            valor="botanica",
            origen="brief",
        )
    )
    await sesion.flush()
    return obra_con_outline


async def _ciclo(sesion, capitulo_id: int, *, prosa: str = PROSA_BUENA, **cambios: Any):
    """Abre el trabajo y lo ejecuta entero, con los dobles de los tres roles."""
    trabajo = await abrir_trabajo(sesion, capitulo_id=capitulo_id)
    parametros: dict[str, Any] = {
        "capitulo_id": capitulo_id,
        "agentes": _agentes(_respuestas(prosa)),
        "contador": ContadorDePalabras(),
        "presupuesto": PresupuestoConcurrente(),
        "cerrojo": CerrojoDeEscena(),
    }
    parametros.update(cambios)
    return await ejecutar_ciclo(sesion, trabajo, **parametros)


# ---------------------------------------------------------------------------
# Juntura 1 · el presupuesto concurrente es UNO por proceso, y se inyecta
# ---------------------------------------------------------------------------


def test_el_presupuesto_concurrente_es_uno_por_proceso():
    """Si fuera uno por trabajo, el techo se cumpliria «por consecuencia y no
    por regla» —el fallo que la spec dedica un parrafo a denunciar— y con los
    dieciseis tests de T10 en verde, porque ninguno mira quien lo instancia."""
    assert obtener_presupuesto() is obtener_presupuesto()


async def test_dos_trabajos_distintos_comparten_la_misma_instancia(sesion, obra_lista):
    """Y se **inyecta**: el ciclo usa el que le dan, no uno que se fabrique.

    Dos capitulos distintos, un solo portero, dos turnos apuntados. Si el ciclo
    construyera el suyo, el espia no veria ninguno.
    """
    espia = PresupuestoEspia()

    for capitulo in obra_lista.capitulos[:2]:
        await _ciclo(sesion, capitulo.id, presupuesto=espia)

    assert len(espia.pedidos) == 2


# ---------------------------------------------------------------------------
# Juntura 2 · los tokens del portero son los que conto el Ensamblador
# ---------------------------------------------------------------------------


async def test_el_portero_recibe_los_tokens_que_conto_el_ensamblador(sesion, obra_lista):
    """La union T5-T6-T10. Hoy `turno(0)` pasa todas las puertas.

    Se compara contra la fila de `ejecucion`, que es donde el Ensamblador dejo
    su recuento: si el ciclo pidiera turno por cualquier otra cifra —cero, una
    constante, la longitud del texto— las dos no coincidirian.
    """
    espia = PresupuestoEspia()

    resultado = await _ciclo(sesion, obra_lista.capitulos[0].id, presupuesto=espia)

    previstos = (
        (
            await sesion.execute(
                select(Ejecucion.tokens_previstos).where(Ejecucion.run_id == resultado.run_id)
            )
        )
        .scalars()
        .all()
    )
    assert espia.pedidos == [previstos[0]]
    assert espia.pedidos[0] > 0


# ---------------------------------------------------------------------------
# De una obra sale un capitulo integrado
# ---------------------------------------------------------------------------


async def test_de_una_obra_planificada_sale_un_capitulo_integrado(sesion, obra_lista):
    """La fase entera en un test: ficha, paquete, prosa, puerta, canon."""
    resultado = await _ciclo(sesion, obra_lista.capitulos[1].id)

    assert resultado.estado == "INTEGRADA"
    assert resultado.escritura is not None
    assert resultado.escritura.aprobado
    assert resultado.consolidacion is not None
    assert not resultado.consolidacion.vacia

    capitulo_id = obra_lista.capitulos[1].id
    assert (
        await sesion.execute(
            select(func.count()).select_from(Escena).where(Escena.capitulo_id == capitulo_id)
        )
    ).scalar_one() == 1
    assert (
        await sesion.execute(
            select(func.count())
            .select_from(ResumenCapitulo)
            .where(ResumenCapitulo.capitulo_id == capitulo_id)
        )
    ).scalar_one() == 1


async def test_la_ejecucion_queda_escrita_con_todo_lo_que_la_hace_auditable(sesion, obra_lista):
    """RF-OBS-06 y regla de dominio 7, campo a campo."""
    resultado = await _ciclo(sesion, obra_lista.capitulos[0].id)

    fila = (
        (await sesion.execute(select(Ejecucion).where(Ejecucion.run_id == resultado.run_id)))
        .scalars()
        .one()
    )
    assert fila.prompt_id == "escritor"
    assert len(fila.prompt_hash) == 64
    assert fila.version_obra_id == obra_lista.version_obra.id
    assert fila.modelo
    assert fila.semilla == 0
    assert fila.tokens_por_capa
    assert fila.tokens_previstos > 0
    assert fila.veredicto == "aprobada"
    # RF-CTX-09 en su columna, desde la Fase 3. Vivia dentro de `parametros`.
    assert fila.ids_por_capa


# ---------------------------------------------------------------------------
# Junturas 6 y 7 · R-7 y CA-10, ahora de punta a punta
# ---------------------------------------------------------------------------


async def test_un_capitulo_rechazado_no_deja_rastro_en_ningun_almacen(sesion, obra_lista):
    """R-7 · CA-10. Y lo rechaza **la puerta de verdad**, no un dato de entrada.

    Hasta ahora R-7 probaba que `canon` obedece un veredicto que el test le
    daba hecho: T9 recibia los codigos como parametro y T12 los producia, y
    nadie unia las dos cosas. Aqui el rechazo lo emite `extension_de_capitulo`
    sobre prosa de trece palabras, y lo que se comprueba es que **ni el
    manuscrito** queda sucio: la `version_texto` descartada se retira, que es lo
    unico que R-7 nombraba y nadie hacia.
    """
    capitulo_id = obra_lista.capitulos[0].id

    resultado = await _ciclo(sesion, capitulo_id, prosa=PROSA_CORTA)

    assert resultado.estado == "ESCALADA"
    assert "EST-02" in (resultado.causa_fallo or "")
    for tabla in (HechoCanon, Evento, ResumenCapitulo, HiloNarrativo, Embedding, VersionTexto):
        # `HechoCanon` trae el del brief de la fixture: lo que no puede haber es
        # ninguno **de esta escena**.
        condicion = (
            select(func.count()).select_from(tabla).where(tabla.escena_de_origen.isnot(None))
            if tabla is HechoCanon
            else select(func.count()).select_from(tabla)
        )
        assert (await sesion.execute(condicion)).scalar_one() == 0, tabla.__name__


async def test_el_veredicto_que_va_a_canon_es_el_que_emitio_la_puerta(sesion, obra_lista):
    """La otra mitad de la juntura 6, y hace falta decir por que es aparte.

    Que un capitulo rechazado no deje rastro lo sostienen **dos paredes**: el
    ciclo no llama al Extractor, y `consolidar_escena` no escribe si recibe un
    codigo bloqueante. Quitar una sola no tumba ningun test —lo comprobe
    mutandola—, porque la otra sigue en pie: es defensa redundante y no una rama
    muerta, y conviene que este escrito en vez de descubrirse mutando.

    Lo que **si** se puede comprobar aparte es que lo que el ciclo le pasa a
    `canon` son los codigos que emitio la puerta de T12, y no una lista vacia
    que haria pasar por aprobado lo que se rechazo.
    """
    resultado = await _ciclo(sesion, obra_lista.capitulos[0].id, prosa=PROSA_CORTA)

    assert resultado.escritura is not None
    assert _codigos_bloqueantes(resultado.escritura) == ("EST-02",)


async def test_el_rechazo_deja_el_trabajo_escalado_y_con_los_dos_intentos_gastados(
    sesion, obra_lista
):
    """RF-ORQ-04 visto desde el trabajo: dos reparaciones y ni una mas."""
    resultado = await _ciclo(sesion, obra_lista.capitulos[0].id, prosa=PROSA_CORTA)

    trabajo = (
        (await sesion.execute(select(Trabajo).where(Trabajo.id == resultado.trabajo_id)))
        .scalars()
        .one()
    )
    assert trabajo.estado == "ESCALADA"
    assert trabajo.intento == 2


# ---------------------------------------------------------------------------
# RI-05 y RI-06 · los dos endpoints
# ---------------------------------------------------------------------------


@pytest.fixture
def respuestas_del_modelo() -> dict[str, str]:
    return _respuestas()


async def test_post_capitulos_escribir_lanza_el_ciclo_y_get_trabajos_lo_cuenta(
    cliente, sesion, obra
):
    """RI-05 y RI-06, sobre una `Obra` de la Fase 1 y nada mas.

    Es la fase entera por HTTP: se encarga el outline (RI-04), se escribe el
    primer capitulo (RI-05) y se consulta el trabajo (RI-06).
    """
    assert cliente.post(f"/obras/{obra.id}/outline").status_code == 201
    capitulo_id = (
        await sesion.execute(
            select(Capitulo.id).where(Capitulo.obra_id == obra.id, Capitulo.numero == 1)
        )
    ).scalar_one()

    lanzado = cliente.post(f"/capitulos/{capitulo_id}/escribir")
    assert lanzado.status_code == 202
    trabajo_id = lanzado.json()["id"]

    consulta = cliente.get(f"/trabajos/{trabajo_id}")
    assert consulta.status_code == 200
    assert consulta.json()["estado"] == "INTEGRADA"
    assert consulta.json()["tipo"] == "escribir_escena"


async def test_escribir_un_capitulo_inexistente_responde_404(cliente):
    """Y con **el mensaje del dominio**, no con el «Not Found» de la ruta ausente.

    La distincion no es cosmetica: los dos primeros rojos de este modulo dieron
    404 con los endpoints todavia sin escribir. Un test que no mira el cuerpo no
    sabe distinguir «no existe ese capitulo» de «no existe ese endpoint».
    """
    respuesta = cliente.post("/capitulos/9999/escribir")

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "No existe el capitulo 9999"


async def test_consultar_un_trabajo_inexistente_responde_404(cliente):
    respuesta = cliente.get("/trabajos/9999")

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "No existe el trabajo 9999"


async def test_los_dos_endpoints_estan_en_el_openapi(cliente):
    """RI-05 y RI-06 son contrato: la spec 002 genera su cliente del OpenAPI."""
    rutas = cliente.get("/openapi.json").json()["paths"]

    assert "post" in rutas["/capitulos/{capitulo_id}/escribir"]
    assert "get" in rutas["/trabajos/{trabajo_id}"]


# ---------------------------------------------------------------------------
# Juntura 5 · la extension vectorial se detecta AL LEVANTAR
# ---------------------------------------------------------------------------


def test_la_aplicacion_detecta_la_extension_vectorial_al_arrancar():
    """R-6: «el sistema arranca y **avisa**». Hoy el aviso salia en la primera
    recuperacion, que es mas tarde de lo que la frase promete.

    Se mira la cache de `extension_disponible`, que es de proceso y se llena la
    primera vez que alguien pregunta. Se vacia antes a proposito: sin eso, otro
    test del proceso ya la habria llenado y este pasaria sin comprobar nada.

    No usa la fixture `cliente`, que sustituye dependencias: lo que se prueba es
    la aplicacion tal y como la levanta `uvicorn`.
    """
    extension_disponible.cache_clear()
    assert extension_disponible.cache_info().currsize == 0

    with TestClient(crear_app()):
        assert extension_disponible.cache_info().currsize == 1
