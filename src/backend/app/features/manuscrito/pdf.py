"""El PDF de una tirada publicada. Plan 4, Tarea 10; `RI-11` y el encargo §2.

Dos piezas, separadas a proposito:

- **`componer_html`** es una funcion pura: recibe titulo, dedicatoria y los
  capitulos ya leidos, y devuelve un HTML autocontenido. Sin sesion, sin red,
  sin fichero que no sea la hoja de estilos que vive al lado. Es lo que la
  suite prueba, y por eso no toca Chromium.
- **`ImpresoraChromium`** convierte ese HTML en bytes con el navegador de
  Playwright. Va por `Depends()` como el cliente de modelo (`CLAUDE.md` §6):
  en la suite se sustituye por un doble que devuelve el HTML que recibio.

**El navegador no tiene red y no ejecuta nada.** JavaScript desactivado y una
ruta que aborta toda peticion que no sea `data:`. El motivo que decide no es la
reproducibilidad sino `CLAUDE.md` §4.3: la prosa y la dedicatoria **no salen
de la maquina**. Un `@import` olvidado en la hoja lo incumpliria sin que ningun
test lo viera; con la ruta, se aborta y se cuenta.

**Toda cadena se escapa.** La prosa la escribio un modelo y la dedicatoria el
comprador, que es texto no confiable (`CLAUDE.md` §11). Sin escapar, un `<` en
la prosa rompe la maqueta y un `<img src=...>` seria una peticion a un tercero.

**Regla de dominio 15.** La dedicatoria va en la portada, con `.dedicatoria`,
fuera de cualquier `<section class="capitulo">`. Hay tantas secciones de
capitulo como capitulos publicados y ni una mas.
"""

from __future__ import annotations

import html
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

ESTILOS = Path(__file__).with_name("impresion") / "impresion.css"

Capitulo = tuple[int, str | None, str, bool]
"""`(numero, titulo, texto, cambiado)`. Lo minimo que la maqueta necesita, y
en orden de lectura: quien compone no reordena."""


class ImpresoraNoDisponible(RuntimeError):
    """No se pudo arrancar el navegador que imprime.

    No hereda de `ErrorDeDominio`: que falte Chromium no es una regla de negocio
    incumplida sino una herramienta ausente, igual que `HerramientaNoDisponible`
    en `lean/`. La ruta la traduce a **503 con motivo** (`CLAUDE.md` §4.2, el
    mismo patron que `sqlite-vec`: se degrada y se dice).
    """


class Impresora(Protocol):
    """Lo unico que la ruta necesita de quien imprime."""

    async def a_pdf(self, html: str) -> bytes: ...


# --- La composicion --------------------------------------------------------


def componer_html(*, titulo: str, dedicatoria: str | None, capitulos: Sequence[Capitulo]) -> str:
    """El HTML autocontenido de la novela: portada, novedades, indice, capitulos.

    - **Portada**: el titulo de la obra y la dedicatoria, si la hay.
    - **Novedades**: solo si algun capitulo esta marcado `cambiado`, con un
      enlace interno a cada uno (encargo §2). Sin cambios no hay pagina: una
      hoja vacia que dijera «novedades» seria una afirmacion falsa en la
      primera hoja del regalo.
    - **Indice**: un enlace `#capitulo-N` por capitulo.
    - **Capitulos**: una `<section class="capitulo" id="capitulo-N">` cada uno,
      con la prosa partida en parrafos por linea en blanco, igual que la lee
      el frontend.
    """
    partes = [
        "<!DOCTYPE html>",
        '<html lang="es"><head><meta charset="utf-8">',
        f"<title>{_e(titulo)}</title>",
        f"<style>{ESTILOS.read_text('utf-8')}</style>",
        "</head><body>",
        _portada(titulo, dedicatoria),
    ]
    cambiados = [(n, t) for n, t, _, cambiado in capitulos if cambiado]
    if cambiados:
        partes.append(_novedades(cambiados))
    partes.append(_indice([(n, t) for n, t, _, _ in capitulos]))
    partes.extend(_capitulo(n, t, texto) for n, t, texto, _ in capitulos)
    partes.append("</body></html>")
    return "\n".join(partes)


def _e(texto: str | None) -> str:
    return html.escape(texto or "", quote=True)


def _portada(titulo: str, dedicatoria: str | None) -> str:
    dedicatoria_html = (
        f'<p class="dedicatoria">{_e(dedicatoria)}</p>'
        if dedicatoria and dedicatoria.strip()
        else ""
    )
    return (
        '<section class="portada">'
        f'<h1 class="portada__titulo">{_e(titulo)}</h1>'
        f"{dedicatoria_html}"
        "</section>"
    )


def _entrada(numero: int, titulo: str | None) -> str:
    return (
        f'<li><a href="#capitulo-{numero}">'
        f'<span class="indice__numero">Capítulo {numero}</span>'
        f'<span class="indice__titulo">{_e(titulo)}</span></a></li>'
    )


def _novedades(cambiados: Sequence[tuple[int, str | None]]) -> str:
    return (
        '<section class="novedades">'
        "<h2>Novedades</h2>"
        "<p>Capítulos que han cambiado desde la tirada anterior.</p>"
        "<ol>" + "".join(_entrada(n, t) for n, t in cambiados) + "</ol>"
        "</section>"
    )


def _indice(entradas: Sequence[tuple[int, str | None]]) -> str:
    return (
        '<nav class="indice" aria-label="Índice">'
        "<h2>Índice</h2>"
        "<ol>" + "".join(_entrada(n, t) for n, t in entradas) + "</ol>"
        "</nav>"
    )


def _capitulo(numero: int, titulo: str | None, texto: str) -> str:
    parrafos = "".join(f"<p>{_e(p.strip())}</p>" for p in texto.split("\n\n") if p.strip())
    return (
        f'<section class="capitulo" id="capitulo-{numero}">'
        '<h2 class="capitulo__titulo">'
        f'<span class="capitulo__numero">Capítulo {numero}</span>{_e(titulo)}</h2>'
        f"{parrafos}"
        "</section>"
    )


# --- La impresora ----------------------------------------------------------


class ImpresoraChromium:
    """Imprime con el Chromium de Playwright, sin red y sin JavaScript.

    `peticiones_bloqueadas` cuenta lo que la ruta tuvo que abortar. Si el HTML
    es autocontenido de verdad, es cero; si alguna vez no lo es, el PDF sale
    igual y el contador lo delata. Es la diferencia entre «no salio» y «no
    intento salir».
    """

    def __init__(self) -> None:
        self.peticiones_bloqueadas = 0

    async def a_pdf(self, html: str) -> bytes:
        from playwright.async_api import Error as ErrorDePlaywright
        from playwright.async_api import Route, async_playwright

        async def bloquear(ruta: Route) -> None:
            if ruta.request.url.startswith("data:"):
                await ruta.continue_()
                return
            self.peticiones_bloqueadas += 1
            await ruta.abort()

        try:
            async with async_playwright() as p:
                navegador = await p.chromium.launch()
                try:
                    contexto = await navegador.new_context(java_script_enabled=False)
                    await contexto.route("**/*", bloquear)
                    pagina = await contexto.new_page()
                    await pagina.set_content(html, wait_until="load")
                    return await pagina.pdf(prefer_css_page_size=True, print_background=True)
                finally:
                    await navegador.close()
        except ErrorDePlaywright as error:
            # El mensaje de Playwright dice que ejecutable falta y como
            # instalarlo; no lleva prosa, asi que puede viajar en el 503.
            raise ImpresoraNoDisponible(str(error).splitlines()[0]) from error


def obtener_impresora() -> Impresora:
    """La dependencia que la ruta pide por `Depends()`. La suite la sobrescribe."""
    return ImpresoraChromium()
