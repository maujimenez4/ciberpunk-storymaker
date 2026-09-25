"""La superficie de lectura: cinco rutas, y se entra por el token.

`RI-08`, `RI-11`, y el contrato con la spec 002.

**El token es la llave de entrada, no un campo del cuerpo.** La 002 lo dice
literal: «ninguna ruta lleva el identificador de la obra en claro; el `token`
es lo unico que protege la lectura». El frontend abre `/l/{token}` y no conoce
`obra_id` ni el ordinal. Devolver el identificador en el cuerpo lo pondria a
proteger **lo que se devuelve** en vez de **lo que se pide**, que es al reves.

**Y la portada no trae prosa.** Los diez capitulos embebidos son unas doce mil
palabras cargadas donde no se lee ni una. Hay un test en negativo que lo fija,
porque es la clase de cosa que se cuela sin que nadie lo note.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.conftest import ObraConOutline
from app.features.escena.modelos import Escena
from app.features.escritura.modelos import Trabajo, VersionTexto
from app.features.manuscrito import publicar
from app.features.manuscrito.modelos import Dedicatoria, VersionPublicada
from app.features.manuscrito.tests.ayudas import cubrir_los_obligatorios

CAPITULOS = 10
DEDICATORIA = "Para Marta, que nunca se rinde."

# Mas de 500 caracteres: el test de prosa comprueba que llega el capitulo
# entero y no un resumen ni un recorte.
TEXTO_LARGO = (
    "El faro llevaba anos apagado y aun asi Marta subia cada tarde. "
    "Contaba los escalones en voz baja, como si el numero fuera a cambiar, "
    "y al llegar arriba se sentaba en el suelo de piedra a mirar el agua. "
    "Habia aprendido que el mar no responde, pero tampoco interrumpe, y eso "
    "ya era mas de lo que le ofrecia nadie en el pueblo. "
    "Aquella tarde, sin embargo, la puerta de abajo estaba abierta, y en el "
    "primer rellano habia una taza todavia tibia que ella no habia dejado. "
) * 2


async def _integrar(sesion: AsyncSession, obra: ObraConOutline) -> None:
    """Diez capitulos con su texto vigente y su trabajo cerrado.

    Misma forma que en `test_publicar.py`: publicar exige que los diez hayan
    pasado su puerta (regla de dominio 14), asi que sin esto no hay tirada.
    """
    for numero, capitulo in enumerate(obra.capitulos, start=1):
        if capitulo.id == obra.escena.capitulo_id:
            escena = obra.escena
        else:
            escena = Escena(
                capitulo_id=capitulo.id,
                version_obra_id=obra.version_obra.id,
                orden_discurso=numero,
                tiempo_historia=f"dia {numero}",
                pov="Nadia",
                lugar="El invernadero",
                presentes=["Nadia", "Teo"],
                objetivo_del_pov="Que Teo confiese",
                obstaculo="Teo no habla",
                resultado="si-pero",
                valor_entrada="confianza",
                valor_salida="sospecha",
                extension_objetivo=1200,
                densidad_de_dialogo_objetivo=0.4,
                distancia_psiquica=3,
            )
            sesion.add(escena)
            await sesion.flush()

        sesion.add(
            VersionTexto(
                escena_id=escena.id,
                numero=1,
                texto=f"Capitulo {numero}. {TEXTO_LARGO}",
                vigente=True,
                run_id=f"run-{numero}",
            )
        )
        sesion.add(
            Trabajo(
                obra_id=obra.obra.id,
                escena_id=escena.id,
                capitulo_id=capitulo.id,
                tipo="escribir_escena",
                estado="INTEGRADA",
                run_id=f"run-{numero}",
            )
        )
    await sesion.flush()
    await cubrir_los_obligatorios(sesion, obra.obra.id)


@pytest.fixture
async def version(sesion: AsyncSession, obra_con_outline: ObraConOutline) -> VersionPublicada:
    """Una tirada publicada de verdad, con dedicatoria y diez capitulos."""
    await _integrar(sesion, obra_con_outline)
    sesion.add(Dedicatoria(obra_id=obra_con_outline.obra.id, texto=DEDICATORIA))
    await sesion.flush()
    publicada = await publicar(sesion, obra_con_outline.obra.id)
    await sesion.commit()
    return publicada


# --- El contrato con la spec 002 ----------------------------------------


def test_la_lectura_se_indexa_por_token_y_no_por_obra_id(cliente: TestClient) -> None:
    """La 002: «ninguna ruta lleva el identificador de la obra en claro»."""
    rutas = cliente.get("/openapi.json").json()["paths"]

    de_lectura = [r for r in rutas if r.startswith("/lectura/")]

    # Cinco de la Fase 4 y tres de la peticion (plan-5 T8), las tres por token.
    assert len(de_lectura) == 8
    assert not any("obra_id" in r for r in de_lectura)


def test_las_cinco_rutas_de_lectura_estan_publicadas(cliente: TestClient) -> None:
    rutas = set(cliente.get("/openapi.json").json()["paths"])

    assert {
        "/lectura/{token}",
        "/lectura/{token}/capitulos/{numero}",
        "/lectura/{token}/ficha",
        "/lectura/{token}/pdf",
        "/lectura/{token}/versiones",
    } <= rutas


def test_el_openapi_publica_los_esquemas_que_el_frontend_deriva(cliente: TestClient) -> None:
    """Sin esto, `pnpm gen:api` de la 002 produce un `schema.d.ts` sin un solo
    tipo util. Es el contrato entre las dos specs y no lo comprueba nada mas."""
    esquemas = set(cliente.get("/openapi.json").json()["components"]["schemas"])

    assert {"VersionPublicada", "CapituloPublicado", "FichaDeLectura"} <= esquemas


# --- La portada ---------------------------------------------------------


async def test_la_portada_trae_la_dedicatoria_y_los_capitulos_con_titulo(
    cliente: TestClient, version: VersionPublicada
) -> None:
    cuerpo = cliente.get(f"/lectura/{version.identificador_publico}").json()

    assert cuerpo["dedicatoria"] == DEDICATORIA
    assert len(cuerpo["capitulos"]) == CAPITULOS
    assert cuerpo["capitulos"][0]["titulo"]
    assert "cambiado" in cuerpo["capitulos"][0]


async def test_la_portada_trae_el_titulo_de_la_obra(
    cliente: TestClient, version: VersionPublicada
) -> None:
    """`RF-POR-01` pide «el titulo de la obra **y** la dedicatoria», y la
    portada solo servia la segunda.

    Lo encontro el frontend al pintar: con el esquema como estaba, **la novela
    no podia llevar su nombre en la pagina donde se abre**. Es la clase de hueco
    que no rompe ningun test del backend -nadie echa en falta un campo que nunca
    estuvo- y que se ve en cuanto alguien intenta usarlo.
    """
    cuerpo = cliente.get(f"/lectura/{version.identificador_publico}").json()

    assert cuerpo["titulo"], "la portada no trae el titulo de la obra (RF-POR-01)"


async def test_la_portada_no_trae_la_prosa_de_los_diez(
    cliente: TestClient, version: VersionPublicada
) -> None:
    """Doce mil palabras al abrir la portada, donde no se lee ni una."""
    cuerpo = cliente.get(f"/lectura/{version.identificador_publico}").json()

    assert all("texto" not in capitulo for capitulo in cuerpo["capitulos"])


async def test_leer_no_expone_el_modelo_de_base_de_datos(
    cliente: TestClient, version: VersionPublicada
) -> None:
    """`CLAUDE.md` §6. Y aqui hay un motivo extra: `id` y `obra_id` son
    internos, y el identificador publico es **la credencial**."""
    respuesta = cliente.get(f"/lectura/{version.identificador_publico}")

    # Sin esto el test pasa por vacio: un 404 tampoco trae `id` ni `obra_id`.
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert "id" not in cuerpo
    assert "obra_id" not in cuerpo


# --- El capitulo --------------------------------------------------------


async def test_un_capitulo_devuelve_su_prosa(
    cliente: TestClient, version: VersionPublicada
) -> None:
    cuerpo = cliente.get(f"/lectura/{version.identificador_publico}/capitulos/3").json()

    assert len(cuerpo["texto"]) > 500
    assert cuerpo["numero"] == 3


# --- El token que no vale -----------------------------------------------


def test_un_token_que_no_existe_da_404_y_no_dice_por_que(cliente: TestClient) -> None:
    """El caso mas probable de todos: el enlace se comparte por mensajeria y
    se corta. Y la respuesta **no puede decir por que** fallo: distinguir «esa
    obra no existe» de «ese token no vale» filtraria la existencia de obras
    ajenas, que es lo unico que el token protege."""
    # La ruta tiene que **existir** para que el 404 signifique algo: si no,
    # este test pasa con el 404 que da FastAPI cuando no hay endpoint.
    assert "/lectura/{token}" in cliente.get("/openapi.json").json()["paths"]

    respuesta = cliente.get("/lectura/noexiste")

    assert respuesta.status_code == 404
    assert "obra" not in respuesta.text.lower()


async def test_el_texto_que_se_lee_es_el_fijado_y_no_el_vigente(
    cliente: TestClient, sesion: AsyncSession, version: VersionPublicada
) -> None:
    """`RF-PUB-01`, y es el punto que sostiene toda la tirada inmutable.

    Se publica, se reescribe el capitulo 3 -- version nueva y vigente -- y se
    vuelve a leer por el mismo token. Tiene que salir **el viejo**. Si saliera
    el nuevo, un enlace ya repartido habria cambiado de contenido sin que nadie
    lo tocara, que es lo que fijar `version_texto_id` existe para impedir.
    """
    antes = cliente.get(f"/lectura/{version.identificador_publico}/capitulos/3").json()["texto"]

    fijada = (
        await sesion.execute(
            text(
                "SELECT v.id AS id, v.escena_id AS escena_id "
                "FROM capitulo_publicado AS c "
                "JOIN version_texto AS v ON v.id = c.version_texto_id "
                "WHERE c.version_id = :version_id AND c.numero = 3"
            ),
            {"version_id": version.id},
        )
    ).one()
    await sesion.execute(
        text("UPDATE version_texto SET vigente = 0 WHERE id = :id"), {"id": fijada.id}
    )
    sesion.add(
        VersionTexto(
            escena_id=fijada.escena_id,
            numero=2,
            texto=f"REESCRITO. {TEXTO_LARGO}",
            vigente=True,
            run_id="run-3-bis",
        )
    )
    await sesion.commit()

    despues = cliente.get(f"/lectura/{version.identificador_publico}/capitulos/3").json()["texto"]

    assert despues == antes
    assert "REESCRITO" not in despues


# --- La publicacion por HTTP -------------------------------------------------
#
# `publicar` existia en el servicio desde T6 y **no tenia ruta**, asi que desde
# el navegador no habia forma de publicar ni de saber cuando una novela se puede
# leer. El frontend llegaba hasta «se esta escribiendo» y ahi se cortaba: no es
# que faltara una pantalla, es que faltaba el dato.


@pytest.fixture
async def integrada(sesion: AsyncSession, obra_con_outline: ObraConOutline) -> ObraConOutline:
    """Los diez capitulos listos, **sin publicar todavia**.

    `version` publica; esta no, porque lo que se prueba aqui es justamente el
    acto de publicar por HTTP.
    """
    await _integrar(sesion, obra_con_outline)
    sesion.add(Dedicatoria(obra_id=obra_con_outline.obra.id, texto=DEDICATORIA))
    await sesion.commit()
    return obra_con_outline


def test_la_ruta_de_publicacion_existe_en_el_openapi(cliente: TestClient) -> None:
    """**Este test es el guardia de los tres siguientes.**

    Sin el, `test_publicar_una_obra_sin_capitulos_listos_no_da_500` pasaba
    **con la ruta sin escribir**: un 404 tambien es `>= 400` y tambien trae
    `detail`. Es la familia de fallo que este repositorio lleva el dia entero
    cazando -- un test con el nombre correcto que no puede fallar -- y aparecio
    escribiendo justo estos tests.
    """
    rutas = cliente.get("/openapi.json").json()["paths"]

    assert "/obras/{obra_id}/publicar" in rutas


async def test_publicar_devuelve_el_token_con_el_que_se_lee(
    cliente: TestClient, integrada: ObraConOutline
) -> None:
    """**El campo que cierra la cadena.**

    Es la unica ruta que devuelve el `identificador_publico`, y tiene que
    hacerlo: quien publica es el Autor y todavia no lo tiene. Las de lectura no
    lo devuelven a proposito -- quien lee ya entro con el -- y esa asimetria es
    deliberada, no un descuido de una de las dos.
    """
    respuesta = cliente.post(f"/obras/{integrada.obra.id}/publicar")

    assert respuesta.status_code == 200, respuesta.text
    token = respuesta.json()["token"]
    assert token, "publicar no devuelve el token, y sin el no se puede leer"

    # Y el token sirve de verdad: se entra con el sin tocar nada mas.
    assert cliente.get(f"/lectura/{token}").status_code == 200


async def test_publicar_dos_veces_sin_cambios_da_el_mismo_token(
    cliente: TestClient, integrada: ObraConOutline
) -> None:
    """R-1 visto desde la API. Dos tiradas identicas serian dos enlaces al mismo
    contenido, y ni el comprador sabria cual mandar de regalo."""
    primero = cliente.post(f"/obras/{integrada.obra.id}/publicar").json()["token"]
    segundo = cliente.post(f"/obras/{integrada.obra.id}/publicar").json()["token"]

    assert primero == segundo


async def test_publicar_una_obra_sin_capitulos_listos_no_da_500(
    cliente: TestClient, obra_con_outline: ObraConOutline
) -> None:
    """Regla de dominio 14 desde el borde: **publicar es afirmar que paso la
    puerta**, y una obra a medias no puede.

    Lo que se comprueba no es solo que falle: es que falle **con un motivo
    legible**. `CLAUDE.md` §6 dice que los errores de dominio los traduce el
    handler central, y un 500 aqui dejaria al frontend sin nada que contarle a
    quien acaba de pagar.
    """
    respuesta = cliente.post(f"/obras/{obra_con_outline.obra.id}/publicar")

    assert respuesta.status_code != 500, "un capitulo sin puerta revienta en vez de explicarse"
    assert respuesta.status_code >= 400
    assert respuesta.json().get("detail"), "falla sin decir por que"
