"""Validador estructural de una spec, contra `CLAUDE.md` §3.2.

No juzga si la spec es *buena*: comprueba que es **evaluable**. Trece invariantes
mecánicas, todas con contraejemplo posible, ninguna que dependa de leer prosa.

Falla cerrado, igual que pide la spec 005 de los validadores de G1a: si no puede
evaluar una invariante —falta la sección, el enlace no resuelve, el frontmatter no
parsea— **eso es un fallo**, no un «no aplica». Un validador de specs que calla
cuando no entiende lo que lee no sirve para abrir una puerta.

Cómo correrlo:

    uv run python specs/005-validadores-fallo-cerrado/validar_spec.py
    uv run python specs/005-validadores-fallo-cerrado/validar_spec.py \
        --spec specs/001-backend-v1/spec.md

Salida: una línea por invariante, y código de salida 1 si alguna falla.

**Fuera de `testpaths`**, como la sonda: es evidencia y herramienta de la spec 005,
no parte de la suite. Si la spec se aprueba, el plan decide si se promueve a
`verificar_spec.py` en la raíz, junto a `verificar_ca4.py`.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
POR_DEFECTO = Path(__file__).resolve().parent / "spec.md"

ESTADOS = ("borrador", "en-revision", "aprobada", "implementada")
ESTADOS_FIRMADOS = ("aprobada", "implementada")

SECCIONES = (
    "Problema",
    "Alcance",
    "Fuera de alcance",
    "Requisitos",
    "Criterios de aceptación",
    "Reglas de dominio afectadas",
    "Impacto técnico",
    "Vocabulario",
)

# `Preguntas abiertas` se renombra a `Decisiones` al cerrarse todas (§3.2), así que
# vale cualquiera de las dos, pero no ninguna.
SECCIONES_ALTERNATIVAS = (("Preguntas abiertas", "Decisiones"),)

MARCAS_DE_VERIFICACION = (
    "Test",
    "Análisis",
    "Inspección",
    "Demostración",
    "Unverifiable",
)
# La marca se escribe entera —`*(Test)*`, como la 001 y la 003— o abreviada
# —`*(T)*`, como escribia la 003 hasta las 17:30—. Reconocer solo una forma
# acusa a la otra de no declararla, y este validador llego a reportar veinte
# criterios sin marca que si la tenian. Lo encontro la sesion Mario.
RE_MARCA_BREVE = re.compile(r"\*?\([TAIDU]\)\*?")

# Los requisitos se declaran en tabla (`| RF-LEC-01 | …`) o en negrita
# (`- **RF-CAL-13** — …`). Capturar solo la negrita dejaba fuera specs enteras:
# la 003 declara los suyos en tabla y este validador veía **cero**, que es el
# fallo en abierto que esta misma spec persigue. Se busca el identificador, no
# su adorno.
PREFIJOS = ("CU", "RI", "RF", "RD", "RNF")
RE_REQUISITO = re.compile(
    r"\b((?:" + "|".join(PREFIJOS) + r")-(?:[A-Z]{2,4}-)?\d{2,3})\b"
)
RE_CRITERIO = re.compile(r"\*\*(CA-\d+)\*\*")
RE_DECLARACION_CA = re.compile(r"^\s*-\s*\[[ xX]\]\s*\*\*(CA-\d+)\*\*", re.MULTILINE)
RE_HALLAZGO = re.compile(r"^###\s+(H-\d+)", re.MULTILINE)
RE_PREGUNTA = re.compile(r"\*\*(P-\d+)[^*]*\*\*")
RE_ENLACE = re.compile(r"\[[^\]]+\]\(([^)#]+\.(?:md|py))\)")
RE_CASILLA_MARCADA = re.compile(r"^\s*-\s*\[x\]", re.MULTILINE | re.IGNORECASE)


class Resultado:
    def __init__(self) -> None:
        self.fallos: list[tuple[str, str]] = []
        self.pasadas: list[str] = []
        self.avisos: list[str] = []

    def comprobar(self, ident: str, condicion: bool, queja: str) -> None:
        if condicion:
            self.pasadas.append(ident)
        else:
            self.fallos.append((ident, queja))


def partir_frontmatter(texto: str) -> tuple[dict[str, str], str]:
    """Devuelve (campos, cuerpo). Un frontmatter ilegible es un fallo, no un vacío."""
    if not texto.startswith("---"):
        raise ValueError("la spec no empieza por un frontmatter `---`")
    cierre = texto.find("\n---", 3)
    if cierre < 0:
        raise ValueError("el frontmatter no se cierra con `---`")
    campos: dict[str, str] = {}
    for linea in texto[3:cierre].splitlines():
        if not linea.strip() or linea.lstrip().startswith("#"):
            continue
        if ":" not in linea:
            raise ValueError(f"linea de frontmatter sin `:`: {linea!r}")
        clave, valor = linea.split(":", 1)
        campos[clave.strip()] = valor.split("#", 1)[0].strip()
    return campos, texto[cierre + 4 :]


def seccion(cuerpo: str, titulo: str) -> str | None:
    """El texto de una sección `## Titulo` hasta el siguiente `## `."""
    patron = re.compile(
        r"^##\s+" + re.escape(titulo) + r"\s*$(.*?)(?=^##\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    hallada = patron.search(cuerpo)
    return hallada.group(1) if hallada else None


def validar(ruta: Path) -> Resultado:
    r = Resultado()
    texto = ruta.read_text(encoding="utf-8")

    campos, cuerpo = partir_frontmatter(texto)

    # V-1 — el frontmatter lleva los cinco campos de la spec de referencia.
    faltan = [
        c
        for c in ("id", "titulo", "estado", "aprobada_por", "fecha")
        if c not in campos
    ]
    r.comprobar("V-1  frontmatter completo", not faltan, f"faltan campos: {faltan}")

    # V-2 — el `id` coincide con la carpeta: un id que miente rompe toda cita
    # `specs/NNN`.
    r.comprobar(
        "V-2  id == carpeta",
        campos.get("id") == ruta.parent.name,
        f"id={campos.get('id')!r} pero la carpeta es {ruta.parent.name!r}",
    )

    estado = campos.get("estado", "")
    # V-3 — el estado es uno de los cuatro de §3.2.
    r.comprobar(
        "V-3  estado válido",
        estado in ESTADOS,
        f"estado={estado!r} no está en {ESTADOS}",
    )

    # V-4 — §14: nadie da por aprobado lo que nadie ha firmado.
    firmada = bool(campos.get("aprobada_por"))
    r.comprobar(
        "V-4  firma si está aprobada",
        estado not in ESTADOS_FIRMADOS or firmada,
        f"estado={estado!r} sin `aprobada_por`: un agente no aprueba por una persona",
    )

    # V-5 — §3.2: mientras quede una pregunta abierta, la spec no se aprueba.
    abiertas_txt = seccion(cuerpo, "Preguntas abiertas")
    preguntas = RE_PREGUNTA.findall(abiertas_txt) if abiertas_txt else []
    r.comprobar(
        "V-5  sin preguntas si está aprobada",
        not (estado in ESTADOS_FIRMADOS and preguntas),
        f"estado={estado!r} con {len(preguntas)} preguntas abiertas: {preguntas}",
    )

    # V-6 — las secciones que §3.2 declara obligatorias.
    ausentes = [s for s in SECCIONES if seccion(cuerpo, s) is None]
    for alternativas in SECCIONES_ALTERNATIVAS:
        if all(seccion(cuerpo, s) is None for s in alternativas):
            ausentes.append(" | ".join(alternativas))
    r.comprobar(
        "V-6  secciones obligatorias", not ausentes, f"faltan secciones: {ausentes}"
    )

    req_txt = seccion(cuerpo, "Requisitos") or ""
    ca_txt = seccion(cuerpo, "Criterios de aceptación") or ""
    # Un requisito es **propio** si la seccion lo declara: como identificador de
    # fila (`| RF-LEC-01 | …`) o en negrita (`- **RF-CAL-13** — …`). Si solo
    # aparece suelto en prosa es una cita a otra spec —la de validadores menciona
    # `RF-CAL-07`, que es de la 001— y contarlo como propio acusa en falso.
    # Regla propuesta por la sesion Mario el 2026-09-23.
    declarados: set[str] = set()
    for linea in req_txt.splitlines():
        limpia = linea.strip()
        if limpia.startswith("|"):
            celda = limpia.strip("| ").split("|")[0]
            declarados.update(RE_REQUISITO.findall(celda))
        for negrita in re.findall(r"\*\*([^*]+)\*\*", limpia):
            declarados.update(RE_REQUISITO.findall(negrita))
    requisitos = sorted(declarados)
    ajenos = sorted(set(RE_REQUISITO.findall(req_txt)) - declarados)
    criterios = sorted(set(RE_CRITERIO.findall(ca_txt)))

    # V-7 — hay requisitos y hay criterios. Sin ninguno de los dos no es una spec.
    r.comprobar(
        "V-7  hay requisitos y criterios",
        bool(requisitos) and bool(criterios),
        f"requisitos={len(requisitos)} criterios={len(criterios)}",
    )

    # V-8 — §3.2 punto 3: un requisito que nadie comprueba no se comprobará nunca.
    #
    # No exige un CA: la 001 cubre RF-CAL-02 y RF-CAL-03 por **Inspección** firmada
    # por el autor (D-09), y eso es cobertura legítima — T/A/I/D/U, no solo T. Lo
    # que no es
    # legítimo es que el identificador no aparezca en ninguna otra parte de la spec: ahí
    # nadie se ha comprometido a nada. Los que solo tienen cobertura fuera de los
    # criterios se avisan, no se bloquean.
    fuera_de_requisitos = cuerpo.replace(req_txt, "")
    sin_cobertura = [q for q in requisitos if q not in fuera_de_requisitos]
    sin_criterio = [q for q in requisitos if q not in ca_txt]

    # Es aviso, no fallo, y el motivo es una limitacion real: la seccion de
    # requisitos tambien cita identificadores de OTRAS specs —la de validadores
    # menciona
    # `RF-CAL-07`, que es de la 001— y desde el texto no hay forma mecanica de
    # distinguir el requisito propio del ajeno. Un fallo binario sobre ese dato
    # acusaria a specs correctas, y un validador que acusa en falso se acaba
    # ignorando. La cifra sigue siendo util: mide la deuda de trazabilidad.
    r.pasadas.append("V-8  trazabilidad requisito -> criterio (aviso)")
    if sin_criterio:
        r.avisos.append(
            f"V-8  {len(sin_criterio)} de {len(requisitos)} identificadores de "
            f"requisito propio no los cita ningun CA. Citas a otras specs "
            f"descartadas: {len(ajenos)}. De ellos, {len(sin_cobertura)} no "
            f"aparecen en ninguna otra seccion: {sin_cobertura[:8]}"
        )

    # V-9 — cada criterio declara cómo se comprueba (T/A/I/D/U de
    # `docs/verification.md`).
    # Se mira el ítem entero, no la línea: la marca suele caer en la línea siguiente.
    sin_marca = []
    for bloque in re.split(r"^\s*-\s*\[[ xX]\]", ca_txt, flags=re.MULTILINE)[1:]:
        hallado = RE_CRITERIO.search(bloque)
        entera = any(m in bloque for m in MARCAS_DE_VERIFICACION)
        breve = RE_MARCA_BREVE.search(bloque) is not None
        if hallado and not entera and not breve:
            sin_marca.append(hallado.group(1))
    r.comprobar(
        "V-9  cada criterio dice cómo se verifica",
        not sin_marca,
        f"criterios sin marca T/A/I/D/U: {sorted(set(sin_marca))}",
    )

    # V-10 — todo hallazgo está recogido por algún requisito: si no, es un defecto
    # documentado que nadie se ha comprometido a arreglar.
    hallazgos = RE_HALLAZGO.findall(cuerpo)
    huerfanos = [h for h in hallazgos if h not in req_txt]
    r.comprobar(
        "V-10 todo hallazgo tiene requisito",
        not huerfanos,
        f"hallazgos que ningún requisito cita: {huerfanos}",
    )

    # V-11 — los enlaces relativos resuelven: un enlace roto es una cita falsa.
    rotos = []
    for destino in set(RE_ENLACE.findall(cuerpo)):
        if (ruta.parent / destino).resolve().exists():
            continue
        if (RAIZ / destino.lstrip("./")).exists():
            continue
        rotos.append(destino)
    r.comprobar(
        "V-11 enlaces relativos resuelven", not rotos, f"enlaces rotos: {rotos}"
    )

    # V-12 — ningún criterio se marca cumplido antes de estar implementada: la casilla
    # `[x]` es la afirmación más fácil de hacer y la más cara de creer.
    marcadas = len(RE_CASILLA_MARCADA.findall(ca_txt))
    r.comprobar(
        "V-12 sin criterios dados por buenos",
        estado == "implementada" or marcadas == 0,
        f"{marcadas} criterios marcados [x] con estado={estado!r}",
    )

    # V-13 — ningun criterio se declara dos veces. Lo propuso la sesion Mario el
    # 2026-09-23 tras encontrar **dos** `CA-14` distintos en la 001, y es la mas
    # solida de las trece: decidible sin heuristica de formato, sin falso positivo
    # posible, y arregla de paso el recuento —contar identificadores unicos sobre
    # un documento con duplicados desplaza la cifra hacia abajo sin avisar—.
    #
    # Solo sobre criterios, no sobre requisitos: la 001 explica `RF-CAL-02` en una
    # nota en negrita bajo su tabla, y eso es una aclaracion, no una segunda
    # declaracion. Aplicarlo alli daria el tercer falso positivo del dia.
    declaraciones = RE_DECLARACION_CA.findall(cuerpo)
    repetidos = sorted({c for c in declaraciones if declaraciones.count(c) > 1})
    r.comprobar(
        "V-13 ningun criterio declarado dos veces",
        not repetidos,
        f"criterios declarados mas de una vez: {repetidos}. "
        f"Una cita cruzada a ese identificador no senala nada",
    )

    return r


def main() -> int:
    partes = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    partes.add_argument("--spec", type=Path, default=POR_DEFECTO)
    argumentos = partes.parse_args()

    ruta = argumentos.spec if argumentos.spec.is_absolute() else RAIZ / argumentos.spec
    if not ruta.exists():
        print(f"no existe: {ruta}", file=sys.stderr)
        return 2

    try:
        r = validar(ruta)
    except ValueError as error:
        # Fallo cerrado: no poder leer la spec no es «sin defectos».
        print(f"FALLO  no se pudo evaluar la spec: {error}", file=sys.stderr)
        return 2

    print(f"spec: {ruta.relative_to(RAIZ)}\n")
    for ident in r.pasadas:
        print(f"  ok    {ident}")
    for aviso in r.avisos:
        print(f"  aviso {aviso}")
    for ident, queja in r.fallos:
        print(f"  FALLO {ident} — {queja}")

    total = len(r.pasadas) + len(r.fallos)
    print(f"\n{len(r.pasadas)}/{total} invariantes pasan")
    return 1 if r.fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
