"""`rutas_estables` e `inspeccion_visual` (plan 7 T9, `RF-VAL-08`, `CA-27`).

Contra un navegador **doble**: la logica no importa Playwright, y por eso esta
suite corre sin Chromium. El conductor real tiene su propio test, marcado
`chromium`, que sirve una pagina fija por intercepcion y no toca la red.
"""

from dataclasses import replace
from pathlib import Path

import pytest

from app.features.calidad import (
    CapituloVisto,
    PaginaLeida,
    RutasDeLectura,
    inspeccionar_lectura,
)

RUTAS = RutasDeLectura(base="http://127.0.0.1:5173", token="t0ken")


def doble(paginas: dict[str, PaginaLeida]):
    async def abrir(url: str) -> PaginaLeida:
        return paginas[url]

    return abrir


def leer_bien(capitulos: int = 10) -> PaginaLeida:
    return PaginaLeida(
        url=RUTAS.leer(),
        estado=200,
        titulo="Tu novela",
        texto_visible="Capitulo 1",
        nodos=120,
        vista_activa="leer",
        h1=1,
        hay_dedicatoria=True,
        indice=tuple(range(1, capitulos + 1)),
        capitulos=tuple(
            CapituloVisto(numero=n, parrafos=8, con_error=False, alcanzable=True)
            for n in range(1, capitulos + 1)
        ),
        enlace_pdf=True,
    )


def ficha_bien() -> PaginaLeida:
    return PaginaLeida(
        url=RUTAS.quien_es_quien(),
        estado=200,
        titulo="Tu novela",
        texto_visible="Quien viaja contigo",
        nodos=40,
        vista_activa="quien-es-quien",
        h1=1,
        hay_ficha=True,
    )


def todas_bien() -> dict[str, PaginaLeida]:
    return {RUTAS.leer(): leer_bien(), RUTAS.quien_es_quien(): ficha_bien()}


def test_las_rutas_llevan_el_token_como_parametro_y_la_vista_pedida() -> None:
    assert RUTAS.leer() == "http://127.0.0.1:5173/?token=t0ken&vista=leer"
    assert RUTAS.quien_es_quien() == "http://127.0.0.1:5173/?token=t0ken&vista=quien-es-quien"
    assert RUTAS.todas() == (RUTAS.leer(), RUTAS.quien_es_quien())


async def test_la_lectura_entera_bien_pasa_y_puntua_los_dos() -> None:
    informe = await inspeccionar_lectura(RUTAS, abrir=doble(todas_bien()))
    assert informe.aprobado
    assert not informe.defectos
    assert {(p.nombre, p.valor) for p in informe.puntuaciones()} == {
        ("rutas_estables", 1.0),
        ("inspeccion_visual", 1.0),
    }


async def test_una_ruta_que_no_responde_es_REN_01_y_dice_cual() -> None:
    paginas = todas_bien()
    paginas[RUTAS.quien_es_quien()] = replace(ficha_bien(), estado=404, nodos=0)
    informe = await inspeccionar_lectura(RUTAS, abrir=doble(paginas))
    assert not informe.aprobado
    (defecto,) = informe.defectos
    assert defecto.codigo == "REN-01"
    assert defecto.validador == "rutas_estables"
    assert "quien-es-quien" in defecto.cita


async def test_si_abre_otra_vista_falla_rutas_estables_y_no_se_inspecciona() -> None:
    """R-8: la pagina responde 200 pero la vista activa no es la pedida. Mirarla
    daria verde sobre la pantalla equivocada."""
    paginas = todas_bien()
    paginas[RUTAS.quien_es_quien()] = replace(ficha_bien(), vista_activa="leer", hay_ficha=False)
    informe = await inspeccionar_lectura(RUTAS, abrir=doble(paginas))
    assert [d.validador for d in informe.defectos] == ["rutas_estables"]
    assert {p.nombre: p.valor for p in informe.puntuaciones()}["rutas_estables"] == 0.0


async def test_una_pagina_vacia_no_pasa_por_responder_200() -> None:
    paginas = todas_bien()
    paginas[RUTAS.leer()] = replace(
        leer_bien(), texto_visible="", nodos=1, indice=(), capitulos=(), h1=0
    )
    informe = await inspeccionar_lectura(RUTAS, abrir=doble(paginas))
    assert not informe.aprobado
    assert all(d.codigo == "REN-01" for d in informe.defectos)


async def test_once_entradas_para_diez_capitulos_renderiza_y_falla() -> None:
    """`verification.md` §8.1: «un indice con once entradas para diez capitulos
    renderiza perfectamente». Aqui no pasa."""
    paginas = todas_bien()
    paginas[RUTAS.leer()] = replace(leer_bien(), indice=tuple(range(1, 12)))
    informe = await inspeccionar_lectura(RUTAS, abrir=doble(paginas), capitulos_esperados=10)
    assert not informe.aprobado
    assert any("indice" in d.cita for d in informe.defectos)


async def test_sin_dedicatoria_falla_salvo_que_se_diga_que_no_la_hay() -> None:
    paginas = todas_bien()
    paginas[RUTAS.leer()] = replace(leer_bien(), hay_dedicatoria=False)
    assert not (await inspeccionar_lectura(RUTAS, abrir=doble(paginas))).aprobado
    informe = await inspeccionar_lectura(RUTAS, abrir=doble(paginas), exigir_dedicatoria=False)
    assert informe.aprobado


async def test_un_capitulo_sin_prosa_o_inalcanzable_desde_el_indice_dice_cual() -> None:
    capitulos = list(leer_bien().capitulos)
    capitulos[2] = CapituloVisto(numero=3, parrafos=0, con_error=True, alcanzable=True)
    capitulos[6] = CapituloVisto(numero=7, parrafos=5, con_error=False, alcanzable=False)
    paginas = todas_bien()
    paginas[RUTAS.leer()] = replace(leer_bien(), capitulos=tuple(capitulos))
    informe = await inspeccionar_lectura(RUTAS, abrir=doble(paginas))
    citas = " | ".join(d.cita for d in informe.defectos)
    assert "capitulo 3" in citas
    assert "capitulo 7" in citas
    assert {p.nombre: p.valor for p in informe.puntuaciones()}["inspeccion_visual"] == 0.0


async def test_la_ficha_que_no_pinta_o_avisa_de_error_falla() -> None:
    paginas = todas_bien()
    paginas[RUTAS.quien_es_quien()] = replace(
        ficha_bien(), hay_ficha=False, avisos_de_error=("No se pudo cargar la ficha.",)
    )
    informe = await inspeccionar_lectura(RUTAS, abrir=doble(paginas))
    assert not informe.aprobado
    assert all("quien-es-quien" in d.cita for d in informe.defectos)


async def test_un_navegador_que_revienta_es_un_defecto_y_no_una_excepcion() -> None:
    async def abrir(url: str) -> PaginaLeida:
        raise ConnectionError("ECONNREFUSED")

    informe = await inspeccionar_lectura(RUTAS, abrir=abrir)
    assert not informe.aprobado
    assert {d.validador for d in informe.defectos} == {"rutas_estables"}
    # Si no se pudo mirar ninguna pagina, `inspeccion_visual` no corrio: un 1.0
    # suyo seria un numero inventado (`scores.py`).
    assert [p.nombre for p in informe.puntuaciones()] == ["rutas_estables"]


_PAGINA_FIJA = """<!doctype html><html><head><title>Tu novela</title></head><body>
<main><h1>Tu novela</h1>
<div role="tablist"><button role="tab" id="pestana-leer" aria-selected="true">Leer</button></div>
<article class="lectura"><p class="dedicatoria">Para alguien</p>
<nav aria-label="Capitulos"><ol class="indice">
<li><a href="#capitulo-1" data-testid="sumario-1">Capitulo 1</a></li>
<li><a href="#capitulo-2" data-testid="sumario-2">Capitulo 2</a></li></ol></nav>
<section id="capitulo-1" class="capitulo"><h2>Capitulo 1.</h2><p class="prosa">Uno.</p></section>
<div style="height:3000px"></div>
<section id="capitulo-2" class="capitulo"><h2>Capitulo 2.</h2><p class="prosa">Dos.</p></section>
<p><a href="/api/lectura/t0ken/pdf">PDF</a></p></article></main></body></html>"""


@pytest.mark.chromium
async def test_el_conductor_real_lee_la_pagina_y_navega_el_indice(tmp_path: Path) -> None:
    from playwright.async_api import async_playwright

    from app.features.calidad import abrir_con_playwright

    async with async_playwright() as p:
        if not Path(p.chromium.executable_path).exists():
            pytest.skip("chromium no esta instalado")

    async with abrir_con_playwright(capturas=tmp_path, html_fijo=_PAGINA_FIJA) as abrir:
        pagina = await abrir(RUTAS.leer())

    assert pagina.estado == 200
    assert pagina.vista_activa == "leer"
    assert pagina.hay_dedicatoria
    assert pagina.indice == (1, 2)
    assert [c.numero for c in pagina.capitulos] == [1, 2]
    assert all(c.alcanzable and c.parrafos == 1 for c in pagina.capitulos)
    assert pagina.enlace_pdf
    assert any(tmp_path.iterdir())
