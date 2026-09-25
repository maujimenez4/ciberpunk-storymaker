"""El PDF: la tirada publicada, impresa, sin red. Plan 4, Tarea 10.

`RI-11`, el encargo §2 para PDF y las reglas de dominio 14 y 15.

**Casi toda la suite no arranca Chromium.** La impresora se inyecta y el doble
devuelve el HTML que recibio: lo que se prueba es **que** se imprime. El unico
test que imprime de verdad esta marcado `chromium` y se salta si el navegador
no esta instalado; aun asi corre sin red, porque es la red lo que comprueba.
"""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.escritura.modelos import VersionTexto
from app.features.manuscrito import modelos
from app.features.manuscrito.pdf import (
    ImpresoraNoDisponible,
    componer_html,
    obtener_impresora,
)
from app.features.manuscrito.tests.test_lectura import CAPITULOS, DEDICATORIA

# La fixture `version` llega por el `conftest.py` de esta carpeta.

REPO = Path(__file__).resolve().parents[6]
ESTILOS_LECTURA = REPO / "src/frontend/src/app/estilos.css"
ESTILOS_PDF = Path(__file__).resolve().parents[1] / "impresion/impresion.css"


class DobleDeImpresora:
    """Guarda el HTML que le llega y devuelve un PDF de mentira."""

    def __init__(self) -> None:
        self.html: str | None = None

    async def a_pdf(self, html: str) -> bytes:
        self.html = html
        return b"%PDF-1.7 doble"


@pytest.fixture
def impresora(cliente: TestClient) -> DobleDeImpresora:
    doble = DobleDeImpresora()
    cliente.app.dependency_overrides[obtener_impresora] = lambda: doble
    return doble


def _pdf(version: modelos.VersionPublicada) -> str:
    return f"/lectura/{version.identificador_publico}/pdf"


# --- La ruta ------------------------------------------------------------


async def test_la_ruta_devuelve_un_pdf_para_descargar(
    cliente: TestClient, version: modelos.VersionPublicada, impresora: DobleDeImpresora
) -> None:
    respuesta = cliente.get(_pdf(version))

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/pdf"
    assert respuesta.headers["content-disposition"].startswith("attachment;")
    assert respuesta.content.startswith(b"%PDF")


def test_un_token_que_no_existe_da_404_tambien_en_el_pdf(
    cliente: TestClient, impresora: DobleDeImpresora
) -> None:
    """Guardia de regresion: ya pasaba con el 501, y se queda para que la
    implementacion no componga nada antes de validar el token."""
    respuesta = cliente.get("/lectura/noexiste/pdf")

    assert respuesta.status_code == 404
    assert impresora.html is None


async def test_sin_navegador_es_503_con_motivo_y_no_500(
    cliente: TestClient, version: modelos.VersionPublicada
) -> None:
    class SinNavegador:
        async def a_pdf(self, html: str) -> bytes:
            raise ImpresoraNoDisponible("chromium no esta instalado")

    cliente.app.dependency_overrides[obtener_impresora] = lambda: SinNavegador()

    respuesta = cliente.get(_pdf(version))

    assert respuesta.status_code == 503
    assert "pdf" in respuesta.json()["detail"].lower()


# --- Lo que lleva: reglas 14 y 15 ---------------------------------------


async def test_lleva_la_portada_con_titulo_y_dedicatoria_y_los_diez_capitulos(
    cliente: TestClient,
    sesion: AsyncSession,
    version: modelos.VersionPublicada,
    impresora: DobleDeImpresora,
) -> None:
    """Regla 15: diez secciones de capitulo, ni una mas, y la dedicatoria en
    la portada, **fuera** de todas ellas. Y el titulo de la obra delante."""
    titulo = (
        await sesion.execute(text("SELECT titulo FROM obra WHERE id = :o"), {"o": version.obra_id})
    ).scalar_one()

    cliente.get(_pdf(version))
    html = impresora.html or ""

    assert len(re.findall(r'<section class="capitulo"', html)) == CAPITULOS
    for numero in range(1, CAPITULOS + 1):
        assert f"Capitulo {numero}. " in html  # la prosa fijada de cada uno
    assert html.count('class="dedicatoria"') == 1
    portada = html.split('<section class="capitulo"', 1)[0]
    assert DEDICATORIA in portada
    assert titulo and titulo in portada


async def test_el_pdf_lleva_el_texto_fijado_y_no_el_vigente(
    cliente: TestClient,
    sesion: AsyncSession,
    version: modelos.VersionPublicada,
    impresora: DobleDeImpresora,
) -> None:
    """Regla 14. Se publica, se reescribe el capitulo 3 y se imprime: sale
    **el viejo**. Si saliera el nuevo, el PDF llevaria un capitulo que no paso
    por ninguna puerta."""
    fijada = (
        await sesion.execute(
            text(
                "SELECT v.id AS id, v.escena_id AS escena_id FROM capitulo_publicado AS c "
                "JOIN version_texto AS v ON v.id = c.version_texto_id "
                "WHERE c.version_id = :v AND c.numero = 3"
            ),
            {"v": version.id},
        )
    ).one()
    await sesion.execute(
        text("UPDATE version_texto SET vigente = 0 WHERE id = :id"), {"id": fijada.id}
    )
    sesion.add(
        VersionTexto(
            escena_id=fijada.escena_id,
            numero=2,
            texto="TEXTO QUE NUNCA PASO SU PUERTA",
            vigente=True,
            run_id="run-nuevo",
        )
    )
    await sesion.commit()

    cliente.get(_pdf(version))

    assert impresora.html is not None
    assert "TEXTO QUE NUNCA PASO SU PUERTA" not in impresora.html
    assert "Capitulo 3. " in impresora.html


# --- La composicion, que es una funcion pura ----------------------------


def test_el_indice_enlaza_a_los_diez_y_las_novedades_solo_a_los_cambiados() -> None:
    """El encargo §2: indice navegable y una pagina de «novedades» con enlaces
    internos a los capitulos que cambiaron. Y sin cambios, sin pagina: una
    hoja vacia que dice «novedades» seria una afirmacion falsa."""
    html = componer_html(
        titulo="T",
        dedicatoria=None,
        capitulos=[(n, f"Titulo {n}", "texto", n in (3, 7)) for n in range(1, 11)],
    )
    for n in range(1, 11):
        assert f'id="capitulo-{n}"' in html
        assert f'href="#capitulo-{n}"' in html
    novedades = html.split('class="novedades"', 1)[1].split("</section>", 1)[0]
    assert 'href="#capitulo-3"' in novedades
    assert 'href="#capitulo-7"' in novedades
    assert 'href="#capitulo-4"' not in novedades

    sin_cambios = componer_html(
        titulo="T",
        dedicatoria=None,
        capitulos=[(n, None, "texto", False) for n in range(1, 11)],
    )
    assert 'class="novedades"' not in sin_cambios


def test_toda_cadena_se_escapa_y_el_html_no_pide_nada_fuera() -> None:
    """La prosa la escribio un modelo y la dedicatoria el comprador: ninguna
    puede meter una etiqueta, y menos una que pida algo a la red
    (`CLAUDE.md` §4.3 y §11)."""
    html = componer_html(
        titulo="<i>t</i>",
        dedicatoria='<img src="https://tercero.example/x.png">',
        capitulos=[(1, "<b>t</b>", "a < b y <script>alert(1)</script>", False)],
    )
    assert "<img" not in html
    assert "<script>" not in html
    assert "<b>t</b>" not in html
    assert "<i>t</i>" not in html
    assert "&lt;script&gt;" in html
    assert "@import" not in html
    assert not re.search(r"(src|href)=[\"']?https?://", html)
    assert not re.search(r"url\(\s*[\"']?https?://", html)


def test_los_tokens_del_pdf_son_los_de_la_lectura() -> None:
    """`CLAUDE.md` §5.1 regla 4, «se duplica primero», con alguien que vigila la
    copia. Lee el frontend a proposito, y si falta el fichero **revienta**: un
    skip aqui volveria verde el test por no encontrar lo que tenia que comparar."""

    def tokens(css: str) -> dict[str, str]:
        # La **primera** definicion de cada token: en la lectura es el tema
        # Papel, el de defecto; los temas Sepia y Noche vienen despues.
        primeros: dict[str, str] = {}
        for nombre, valor in re.findall(r"(--[a-z-]+):\s*([^;]+);", css):
            primeros.setdefault(nombre, valor)
        return primeros

    lectura = tokens(ESTILOS_LECTURA.read_text("utf-8"))
    pdf = tokens(ESTILOS_PDF.read_text("utf-8"))
    for nombre in ("--papel", "--tinta", "--acento", "--tinta-suave"):
        assert pdf[nombre] == lectura[nombre], nombre


# --- La impresora real --------------------------------------------------


@pytest.mark.chromium
async def test_chromium_imprime_sin_una_sola_peticion() -> None:
    """El unico test que arranca el navegador. Se salta si no esta instalado
    -- por su ejecutable, no por capturar el fallo --, y aun asi no toca la
    red: comprueba justo eso."""
    from playwright.async_api import async_playwright

    from app.features.manuscrito.pdf import ImpresoraChromium

    async with async_playwright() as p:
        if not Path(p.chromium.executable_path).exists():
            pytest.skip("Chromium de Playwright no instalado")

    impresora = ImpresoraChromium()
    html = componer_html(
        titulo="Titulo de prueba",
        dedicatoria="Dedicatoria de prueba",
        capitulos=[(n, f"Titulo {n}", "Texto de prueba. " * 300, n == 2) for n in range(1, 11)],
    )

    pdf = await impresora.a_pdf(html)

    assert pdf.startswith(b"%PDF")
    assert impresora.peticiones_bloqueadas == 0
