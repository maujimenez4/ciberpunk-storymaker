"""Exportacion del manuscrito: Markdown y PDF (`CLAUDE.md` §5.1, segmento service).

El manuscrito se ensambla en memoria (`repository.py`) y hay que poder sacarlo
de la maquina. Hasta ahora salia a un `.txt` suelto en la raiz del repositorio:
sin titulo, sin cortes de escena y en un formato que nadie abre para leer.

**Exportar no reescribe.** El texto de cada fragmento viaja caracter a caracter;
lo unico que anade esta capa es el titulo, el corte entre escenas y el paginado.
Si el formato tocara la prosa, el fichero dejaria de ser el manuscrito y pasaria
a ser otra version sin `run_id` que la explique (§14).

**El PDF se escribe a mano, sin dependencias.** Son unas cien lineas de PDF 1.4
con Helvetica, una de las catorce fuentes que todo lector trae: no hay que
incrustar nada. Se prefirio a `reportlab` para no meter un paquete -y su arbol
de dependencias- por una salida de demostracion. El precio esta declarado abajo:
el ajuste de linea usa las anchuras reales de Helvetica solo para ASCII y
aproxima el resto.
"""

from dataclasses import dataclass
from pathlib import Path

from app.features.manuscrito.repository import Manuscrito

SEPARADOR_DE_ESCENA = "* * *"

# --- geometria de la pagina (puntos PostScript; A4) ---------------------------
ANCHO, ALTO = 595.0, 842.0
MARGEN = 72.0
CUERPO, INTERLINEA = 11.0, 15.5
TAMANO_TITULO = 20.0

# Anchuras de Helvetica en milesimas de em, codigos 32..126, del AFM de la
# fuente base 14. Sin ellas el corte de linea se hace a ojo y un parrafo con
# muchas mayusculas se sale del margen sin que nada avise.
# fmt: off
_ANCHURAS = (
    278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278,
    278, 556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584,
    584, 556, 1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556,
    833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278,
    278, 278, 469, 556, 333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222,
    500, 222, 833, 556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500,
    500, 334, 260, 334, 584,
)
# fmt: on
# La raya de dialogo abre casi todos los parrafos de esta novela: merece su
# anchura real. El resto de lo no-ASCII (vocales acentuadas, ene, comillas
# latinas) ronda la de la `o`, y ese es el error que se acepta.
_ANCHURA_POR_DEFECTO = 556
_ANCHURAS_ESPECIALES = {"—": 1000, "–": 556, "…": 1000, "«": 556, "»": 556}


def a_markdown(manuscrito: Manuscrito, titulo: str) -> str:
    """El manuscrito como un solo `.md`: titulo, escenas y sus cortes."""
    partes: list[str] = [f"# {titulo}", ""]
    for posicion, fragmento in enumerate(manuscrito.fragmentos):
        if posicion:
            partes += [SEPARADOR_DE_ESCENA, ""]
        partes += [fragmento.texto.strip(), ""]
    return "\n".join(partes)


def a_pdf(manuscrito: Manuscrito, titulo: str) -> bytes:
    """El mismo manuscrito, paginado en A4."""
    return _ensamblar(_paginar(_componer(manuscrito, titulo)))


def exportar(
    manuscrito: Manuscrito, carpeta: Path, nombre: str, titulo: str
) -> list[Path]:
    """Deja `<nombre>.md` y `<nombre>.pdf` juntos en `carpeta`.

    La carpeta esta ignorada por git (§15: la prosa no entra en el
    repositorio), asi que en un clon limpio no existe y hay que crearla.
    """
    carpeta.mkdir(parents=True, exist_ok=True)
    md = carpeta / f"{nombre}.md"
    pdf = carpeta / f"{nombre}.pdf"
    md.write_text(a_markdown(manuscrito, titulo), encoding="utf-8")
    pdf.write_bytes(a_pdf(manuscrito, titulo))
    return [md, pdf]


# --- composicion: de fragmentos a lineas ya medidas ---------------------------


@dataclass(frozen=True)
class _Linea:
    texto: str
    fuente: str
    tamano: float
    alto: float
    centrada: bool = False


def _anchura(texto: str, tamano: float) -> float:
    total = 0
    for caracter in texto:
        codigo = ord(caracter)
        if 32 <= codigo <= 126:
            total += _ANCHURAS[codigo - 32]
        else:
            total += _ANCHURAS_ESPECIALES.get(caracter, _ANCHURA_POR_DEFECTO)
    return total * tamano / 1000


def _cortar(texto: str, tamano: float, disponible: float) -> list[str]:
    """Corta por palabras; una palabra que no cabe entera se parte por letras.

    Sin la segunda mitad, una URL o un `AAAA...` se sale de la pagina en
    silencio: el PDF no tiene margen que lo detenga.
    """
    lineas: list[str] = []
    actual = ""
    for bruta in texto.split():
        palabra = bruta
        candidata = f"{actual} {palabra}".strip()
        if _anchura(candidata, tamano) <= disponible:
            actual = candidata
            continue
        if actual:
            lineas.append(actual)
            actual = ""
        while _anchura(palabra, tamano) > disponible:
            corte = 1
            while (
                corte < len(palabra)
                and _anchura(palabra[: corte + 1], tamano) <= disponible
            ):
                corte += 1
            lineas.append(palabra[:corte])
            palabra = palabra[corte:]
        actual = palabra
    if actual:
        lineas.append(actual)
    return lineas or [""]


def _componer(manuscrito: Manuscrito, titulo: str) -> list[_Linea]:
    disponible = ANCHO - 2 * MARGEN
    lineas: list[_Linea] = [
        _Linea(texto, "F2", TAMANO_TITULO, TAMANO_TITULO * 1.4, centrada=True)
        for texto in _cortar(titulo, TAMANO_TITULO, disponible)
    ]
    lineas.append(_Linea("", "F1", CUERPO, INTERLINEA))
    for posicion, fragmento in enumerate(manuscrito.fragmentos):
        if posicion:
            lineas.append(_Linea("", "F1", CUERPO, INTERLINEA))
            lineas.append(
                _Linea(SEPARADOR_DE_ESCENA, "F1", CUERPO, INTERLINEA, centrada=True)
            )
            lineas.append(_Linea("", "F1", CUERPO, INTERLINEA))
        for parrafo in fragmento.texto.splitlines():
            if not parrafo.strip():
                lineas.append(_Linea("", "F1", CUERPO, INTERLINEA / 2))
                continue
            lineas += [
                _Linea(corte, "F1", CUERPO, INTERLINEA)
                for corte in _cortar(parrafo, CUERPO, disponible)
            ]
    return lineas


def _paginar(lineas: list[_Linea]) -> list[list[tuple[_Linea, float]]]:
    """Reparte las lineas en paginas y le fija a cada una su linea base."""
    paginas: list[list[tuple[_Linea, float]]] = [[]]
    y = ALTO - MARGEN
    for linea in lineas:
        y -= linea.alto
        if y < MARGEN:
            paginas.append([])
            y = ALTO - MARGEN - linea.alto
        paginas[-1].append((linea, y))
    return paginas


# --- ensamblado del fichero PDF -----------------------------------------------


def _texto_pdf(texto: str) -> bytes:
    """Cadena literal de PDF: cp1252 -lo que entiende WinAnsiEncoding- con los
    tres caracteres que la sintaxis reserva, escapados."""
    crudo = texto.encode("cp1252", errors="replace")
    for viejo, nuevo in ((b"\\", b"\\\\"), (b"(", b"\\("), (b")", b"\\)")):
        crudo = crudo.replace(viejo, nuevo)
    return crudo


def _contenido(pagina: list[tuple[_Linea, float]]) -> bytes:
    partes: list[bytes] = []
    for linea, y in pagina:
        if not linea.texto:
            continue
        x = MARGEN
        if linea.centrada:
            x = (ANCHO - _anchura(linea.texto, linea.tamano)) / 2
        partes.append(
            b"BT /%s %.1f Tf 1 0 0 1 %.2f %.2f Tm (%s) Tj ET\n"
            % (linea.fuente.encode(), linea.tamano, x, y, _texto_pdf(linea.texto))
        )
    return b"".join(partes)


def _ensamblar(paginas: list[list[tuple[_Linea, float]]]) -> bytes:
    """PDF 1.4 minimo: catalogo, nodo de paginas, dos fuentes base 14 y, por
    pagina, su objeto y su flujo de contenido.

    Las posiciones de la tabla `xref` se calculan sobre los bytes ya escritos:
    es lo unico del formato que no perdona un error de uno.
    """
    total = len(paginas)
    ids = [5 + 2 * i for i in range(total)]
    objetos: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [%s] /Count %d >>"
        % (b" ".join(b"%d 0 R" % i for i in ids), total),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica"
        b" /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold"
        b" /Encoding /WinAnsiEncoding >>",
    ]
    for indice, pagina in enumerate(paginas):
        flujo = _contenido(pagina)
        objetos.append(
            b"<< /Type /Page\n/Parent 2 0 R /MediaBox [0 0 %.0f %.0f]"
            b" /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >>"
            b" /Contents %d 0 R >>" % (ANCHO, ALTO, ids[indice] + 1)
        )
        objetos.append(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(flujo), flujo))

    salida = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    posiciones: list[int] = []
    for numero, cuerpo in enumerate(objetos, start=1):
        posiciones.append(len(salida))
        salida += b"%d 0 obj\n%s\nendobj\n" % (numero, cuerpo)
    inicio_xref = len(salida)
    salida += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1)
    for posicion in posiciones:
        salida += b"%010d 00000 n \n" % posicion
    salida += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objetos) + 1,
        inicio_xref,
    )
    return bytes(salida)
