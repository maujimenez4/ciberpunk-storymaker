"""La validacion visual: codigo que conduce un navegador (plan 7 T9, `RF-VAL-08`).

**No es un agente** (`architecture.md` §3.5.1). No recibe prompt, no llama al
modelo, no decide: abre la lectura publicada, recorre el indice y mira si lo que
el `Destinatario` recibe **se pinta**. Dos validadores, con los nombres de
`verification.md` §8.1:

- `rutas_estables`, **primero**: que cada vista responda y que la pantalla que
  se abre sea **la pedida**. Existe para que el otro no mienta (R-8).
- `inspeccion_visual`, despues, solo sobre las vistas que pasaron el primero:
  portada con un `h1`, dedicatoria, indice con tantas entradas como capitulos,
  cada capitulo con prosa y alcanzable desde el indice, enlace al PDF, y la
  ficha de «Quien es quien» pintada.

La direccion es **una** (D-07): `/?token=<t>&vista=<v>`. `?vista=` es la
superficie de inspeccion que `router.ts` declara para esto.

**La logica no importa Playwright.** `inspeccionar_lectura` recibe `abrir` ya
construido; el conductor real vive en `abrir_con_playwright` y el `import` es
perezoso. Si la logica lo importara, la suite necesitaria un navegador.

**Nada de prosa sale de aqui.** Las citas de los defectos son estructurales
(«capitulo 3 sin prosa»), nunca texto del manuscrito (`CLAUDE.md` §15). Las
capturas si contienen prosa: por eso van a un directorio fuera del repositorio.

Uso, contra una version publicada y con la lectura levantada::

    uv run python -m app.features.calidad.visual --token <token>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import tempfile
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote

from app.commons.observabilidad import Puntuacion, obtener_observador
from app.features.calidad.scores import FALLA, PASA, emitir

CODIGO = "REN-01"
RUTAS_ESTABLES = "rutas_estables"
INSPECCION_VISUAL = "inspeccion_visual"
VISTA_LEER = "leer"
VISTA_FICHA = "quien-es-quien"
NODOS_MINIMOS = 15
"""Por debajo, la SPA no monto: el contenedor raiz y poco mas."""


@dataclass(frozen=True, slots=True)
class RutasDeLectura:
    """Las dos vistas de la lectura publicada, en la direccion unica de D-07."""

    base: str
    token: str

    def _vista(self, vista: str) -> str:
        return f"{self.base.rstrip('/')}/?token={quote(self.token, safe='')}&vista={vista}"

    def leer(self) -> str:
        return self._vista(VISTA_LEER)

    def quien_es_quien(self) -> str:
        return self._vista(VISTA_FICHA)

    def todas(self) -> tuple[str, ...]:
        return (self.leer(), self.quien_es_quien())


@dataclass(frozen=True, slots=True)
class CapituloVisto:
    """Un capitulo tal como se pinto. Sin su texto: solo cuanto hay."""

    numero: int
    parrafos: int
    con_error: bool
    alcanzable: bool
    """Pulsar su entrada del indice lo trae a la vista."""


@dataclass(frozen=True, slots=True)
class PaginaLeida:
    """Lo **unico** que el validador mira de una pagina."""

    url: str
    estado: int
    titulo: str
    texto_visible: str
    nodos: int
    vista_activa: str | None = None
    h1: int = 0
    hay_dedicatoria: bool = False
    indice: tuple[int, ...] = ()
    capitulos: tuple[CapituloVisto, ...] = ()
    enlace_pdf: bool = False
    hay_ficha: bool = False
    entradas_de_ficha: int = 0
    avisos_de_error: tuple[str, ...] = ()
    errores_de_consola: tuple[str, ...] = ()
    capturas: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DefectoVisual:
    codigo: str
    validador: str
    cita: str
    """Estructural: la vista y lo que falla. Nunca prosa."""


@dataclass(frozen=True, slots=True)
class InformeVisual:
    paginas: tuple[PaginaLeida, ...]
    defectos: tuple[DefectoVisual, ...]
    validadores_ejecutados: tuple[str, ...] = (RUTAS_ESTABLES, INSPECCION_VISUAL)

    @property
    def aprobado(self) -> bool:
        return not self.defectos

    def puntuaciones(self) -> tuple[Puntuacion, ...]:
        """Paso o no paso, uno por validador ejecutado (la escala de `scores`)."""
        fallidos = {d.validador for d in self.defectos}
        return tuple(
            Puntuacion(nombre=v, valor=FALLA if v in fallidos else PASA)
            for v in self.validadores_ejecutados
        )


Abrir = Callable[[str], Awaitable[PaginaLeida]]


def _vista_de(url: str) -> str:
    encontrada = re.search(r"[?&]vista=([^&#]+)", url)
    return encontrada.group(1) if encontrada else "?"


def _rutas_estables(url: str, pagina: PaginaLeida | None, fallo: str | None) -> list[str]:
    vista = _vista_de(url)
    if pagina is None:
        return [f"vista={vista}: no abre ({fallo})"]
    problemas = []
    if pagina.estado != 200:
        problemas.append(f"vista={vista}: HTTP {pagina.estado}")
    elif pagina.vista_activa != vista:
        problemas.append(f"vista={vista}: se abrio la vista {pagina.vista_activa!r}")
    return problemas


def _comunes(vista: str, pagina: PaginaLeida) -> list[str]:
    problemas = []
    if pagina.nodos < NODOS_MINIMOS or not pagina.texto_visible.strip():
        problemas.append(f"vista={vista}: pagina vacia ({pagina.nodos} nodos)")
    if pagina.h1 != 1:
        problemas.append(f"vista={vista}: portada con {pagina.h1} h1, se espera 1")
    for aviso in pagina.avisos_de_error:
        problemas.append(f"vista={vista}: aviso de error visible «{aviso[:80]}»")
    return problemas


def _leer(pagina: PaginaLeida, esperados: int, exigir_dedicatoria: bool) -> list[str]:
    problemas = _comunes(VISTA_LEER, pagina)
    if exigir_dedicatoria and not pagina.hay_dedicatoria:
        problemas.append("vista=leer: portada sin dedicatoria")
    if pagina.indice != tuple(range(1, esperados + 1)):
        problemas.append(
            f"vista=leer: indice con {len(pagina.indice)} entradas {list(pagina.indice)}, "
            f"se esperan {esperados}"
        )
    numeros = tuple(c.numero for c in pagina.capitulos)
    if numeros != pagina.indice:
        problemas.append(f"vista=leer: capitulos pintados {list(numeros)} no casan con el indice")
    for c in pagina.capitulos:
        if c.con_error or c.parrafos == 0:
            problemas.append(f"vista=leer: capitulo {c.numero} sin prosa")
        if not c.alcanzable:
            problemas.append(f"vista=leer: capitulo {c.numero} no se alcanza desde el indice")
    if not pagina.enlace_pdf:
        problemas.append("vista=leer: sin enlace al PDF")
    return problemas


def _ficha(pagina: PaginaLeida) -> list[str]:
    problemas = _comunes(VISTA_FICHA, pagina)
    if not pagina.hay_ficha:
        problemas.append("vista=quien-es-quien: la ficha no se pinta")
    return problemas


async def inspeccionar_lectura(
    rutas: RutasDeLectura,
    *,
    abrir: Abrir,
    capitulos_esperados: int = 10,
    exigir_dedicatoria: bool = True,
) -> InformeVisual:
    """Corre `rutas_estables` y, sobre lo que lo pasa, `inspeccion_visual`.

    Un navegador que revienta **no lanza**: es un `REN-01` de `rutas_estables`
    con el motivo, porque la pregunta era si la lectura se ve y la respuesta es no.
    """
    paginas: list[PaginaLeida] = []
    defectos: list[DefectoVisual] = []
    inspeccionadas = 0
    for url in rutas.todas():
        pagina: PaginaLeida | None = None
        fallo: str | None = None
        try:
            pagina = await abrir(url)
        except Exception as error:  # noqa: BLE001 -- se convierte en defecto, no se oculta
            fallo = type(error).__name__
        estables = _rutas_estables(url, pagina, fallo)
        defectos += [DefectoVisual(CODIGO, RUTAS_ESTABLES, c) for c in estables]
        if pagina is None:
            continue
        paginas.append(pagina)
        if estables:
            continue  # R-8: mirar la pantalla equivocada daria verde
        inspeccionadas += 1
        vista = _vista_de(url)
        visuales = (
            _leer(pagina, capitulos_esperados, exigir_dedicatoria)
            if vista == VISTA_LEER
            else _ficha(pagina)
        )
        defectos += [DefectoVisual(CODIGO, INSPECCION_VISUAL, c) for c in visuales]
    # Si no se pudo mirar ninguna, `inspeccion_visual` no corrio: no puntua.
    ejecutados = (RUTAS_ESTABLES, INSPECCION_VISUAL) if inspeccionadas else (RUTAS_ESTABLES,)
    return InformeVisual(
        paginas=tuple(paginas), defectos=tuple(defectos), validadores_ejecutados=ejecutados
    )


# --- El conductor real. Lo unico que sabe de selectores y de Playwright. ------

_EXTRAER = """() => {
  const q = (s, r = document) => Array.from(r.querySelectorAll(s));
  const activa = document.querySelector('[role=tab][aria-selected=true]');
  return {
    titulo: document.title,
    texto_visible: (document.body.innerText || '').trim(),
    nodos: document.querySelectorAll('body *').length,
    vista_activa: activa ? activa.id.replace(/^pestana-/, '') : null,
    h1: q('h1').length,
    hay_dedicatoria: !!document.querySelector('.dedicatoria'),
    indice: q('nav [data-testid^="sumario-"]').map(a => parseInt(a.dataset.testid.split('-')[1], 10)),
    capitulos: q('section.capitulo').map(s => ({
      id: s.id,
      numero: parseInt((s.id.match(/\\d+/) || ['0'])[0], 10),
      parrafos: q('p.prosa', s).filter(p => p.textContent.trim() !== '…').length,
      con_error: !!s.querySelector('[role=alert]'),
    })),
    enlace_pdf: q('a[href*="/pdf"]').length > 0,
    hay_ficha: !!document.querySelector('section.viajeros'),
    entradas_de_ficha: q('.viajeros__lista article.etiqueta').length,
    avisos_de_error: q('[role=alert]').filter(e => !e.closest('section.capitulo'))
      .map(e => (e.textContent || '').trim()),
  };
}"""

_CARGADO = """() => !document.body.innerText.includes('Abriendo tu novela')
  && !document.body.innerText.includes('Buscando qui')
  && !Array.from(document.querySelectorAll('section.capitulo p.prosa'))
       .some(p => p.textContent.trim() === '…')"""

_EN_VISTA = """(id) => { const s = document.getElementById(id); if (!s) return false;
  const r = s.getBoundingClientRect();
  return location.hash === '#' + id && r.top < window.innerHeight && r.bottom > 0; }"""


@asynccontextmanager
async def abrir_con_playwright(
    *,
    capturas: Path | None = None,
    html_fijo: str | None = None,
    espera_ms: int = 20_000,
) -> AsyncIterator[Abrir]:
    """Construye el `abrir` real sobre el Chromium de Playwright.

    `html_fijo` sirve esa pagina a cualquier peticion, sin red: es para el test
    del conductor, no para la corrida.
    """
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        navegador = await p.chromium.launch()
        try:
            contexto = await navegador.new_context(viewport={"width": 1280, "height": 900})
            if html_fijo is not None:
                html = html_fijo

                async def servir(ruta: Any) -> None:
                    await ruta.fulfill(status=200, content_type="text/html", body=html)

                await contexto.route("**/*", servir)

            async def abrir(url: str) -> PaginaLeida:
                pagina = await contexto.new_page()
                consola: list[str] = []
                pagina.on(
                    "console", lambda m: consola.append(m.type) if m.type == "error" else None
                )
                try:
                    respuesta = await pagina.goto(url, wait_until="networkidle")
                    try:
                        await pagina.wait_for_function(_CARGADO, timeout=espera_ms)
                    except Exception:  # noqa: BLE001, S110 -- lo que falte, lo dira la extraccion
                        pass
                    datos: dict[str, Any] = await pagina.evaluate(_EXTRAER)
                    fotos: list[str] = []
                    vista = _vista_de(url)
                    if capturas is not None:
                        capturas.mkdir(parents=True, exist_ok=True)
                        destino = capturas / f"{vista}.png"
                        await pagina.screenshot(path=str(destino), full_page=False)
                        fotos.append(str(destino))
                    capitulos: list[CapituloVisto] = []
                    for c in datos["capitulos"]:
                        alcanzable = False
                        enlace = pagina.locator(f'[data-testid="sumario-{c["numero"]}"]')
                        if await enlace.count():
                            await enlace.first.click()
                            await pagina.wait_for_timeout(250)
                            alcanzable = bool(await pagina.evaluate(_EN_VISTA, c["id"]))
                            if capturas is not None:
                                destino = capturas / f"{vista}-capitulo-{c['numero']:02d}.png"
                                await pagina.screenshot(path=str(destino))
                                fotos.append(str(destino))
                        capitulos.append(
                            CapituloVisto(
                                numero=c["numero"],
                                parrafos=c["parrafos"],
                                con_error=c["con_error"],
                                alcanzable=alcanzable,
                            )
                        )
                    return PaginaLeida(
                        url=url,
                        estado=respuesta.status if respuesta else 0,
                        titulo=datos["titulo"],
                        texto_visible=datos["texto_visible"],
                        nodos=datos["nodos"],
                        vista_activa=datos["vista_activa"],
                        h1=datos["h1"],
                        hay_dedicatoria=datos["hay_dedicatoria"],
                        indice=tuple(datos["indice"]),
                        capitulos=tuple(capitulos),
                        enlace_pdf=datos["enlace_pdf"],
                        hay_ficha=datos["hay_ficha"],
                        entradas_de_ficha=datos["entradas_de_ficha"],
                        avisos_de_error=tuple(datos["avisos_de_error"]),
                        errores_de_consola=tuple(consola),
                        capturas=tuple(fotos),
                    )
                finally:
                    await pagina.close()

            yield abrir
        finally:
            await navegador.close()


# --- La linea de ordenes. -----------------------------------------------------


@dataclass
class _Opciones:
    base: str
    token: str
    capitulos: int
    sin_dedicatoria: bool
    capturas: Path
    obra_id: int | None
    json: bool = field(default=False)


def _opciones(argv: list[str] | None) -> _Opciones:
    lector = argparse.ArgumentParser(prog="python -m app.features.calidad.visual")
    lector.add_argument("--base", default="http://127.0.0.1:5173")
    lector.add_argument("--token", required=True)
    lector.add_argument("--capitulos", type=int, default=10)
    lector.add_argument("--sin-dedicatoria", action="store_true")
    lector.add_argument(
        "--capturas",
        type=Path,
        default=Path(tempfile.gettempdir()) / "validacion-visual",
        help="Fuera del repositorio: las capturas contienen prosa (CLAUDE.md §16).",
    )
    lector.add_argument("--obra-id", type=int, default=None, help="Emite los scores a su sesion")
    lector.add_argument("--json", action="store_true")
    a = lector.parse_args(argv)
    return _Opciones(a.base, a.token, a.capitulos, a.sin_dedicatoria, a.capturas, a.obra_id, a.json)


async def _correr(o: _Opciones) -> InformeVisual:
    rutas = RutasDeLectura(base=o.base, token=o.token)
    async with abrir_con_playwright(capturas=o.capturas) as abrir:
        informe = await inspeccionar_lectura(
            rutas,
            abrir=abrir,
            capitulos_esperados=o.capitulos,
            exigir_dedicatoria=not o.sin_dedicatoria,
        )
    if o.obra_id is not None:
        observador = obtener_observador()
        async with (
            observador.traza(obra_id=o.obra_id, nombre="validacion_visual") as traza,
            traza.span(INSPECCION_VISUAL) as span,
        ):
            emitir(span, informe.puntuaciones())
        observador.cerrar()
    return informe


def main(argv: list[str] | None = None) -> int:
    o = _opciones(argv)
    informe = asyncio.run(_correr(o))
    resumen = {
        "aprobado": informe.aprobado,
        "scores": {p.nombre: p.valor for p in informe.puntuaciones()},
        "defectos": [
            {"codigo": d.codigo, "validador": d.validador, "cita": d.cita} for d in informe.defectos
        ],
        "paginas": [
            {
                "vista": _vista_de(p.url),
                "estado": p.estado,
                "nodos": p.nodos,
                "indice": len(p.indice),
                "capitulos": len(p.capitulos),
                "entradas_de_ficha": p.entradas_de_ficha,
                "errores_de_consola": len(p.errores_de_consola),
                "capturas": list(p.capturas),
            }
            for p in informe.paginas
        ],
    }
    if o.json:
        print(json.dumps(resumen, ensure_ascii=False, indent=2))
    else:
        print("APROBADO" if informe.aprobado else "SUSPENDIDO")
        for p in informe.puntuaciones():
            print(f"  {p.nombre}: {p.valor}")
        for d in informe.defectos:
            print(f"  {d.codigo} [{d.validador}] {d.cita}")
        print(f"  capturas en {o.capturas}")
    return 0 if informe.aprobado else 1


if __name__ == "__main__":
    sys.exit(main())
