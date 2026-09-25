"""La revision humana con la **misma rubrica** que el juez, y la comparacion.

    uv run python evals/revision_humana.py rubrica
    uv run python evals/revision_humana.py puntuar --obra 12 --revisor maujimenez4
    uv run python evals/revision_humana.py puntuar --obra 12 --revisor maujimenez4 --desde notas.json
    uv run python evals/revision_humana.py comparar --obra 12 [--langfuse]

La rubrica sale de `rubrica_vigente()` —la **misma instancia** que recibe el
Critico, `CA-20`— y no de una copia: si alguien crea `v2`, este script la
presenta sin tocarlo.

**La revisa el Autor, no el Comprador** (P-05). La aceptacion del comprador no
entra aqui y no mueve la distancia (R-7).

Donde se guarda, **sin migracion nueva**: las tablas son del plan 6 T2.

- `rubrica` y `criterio_de_rubrica`: la vigente, si todavia no esta (nadie la
  sembraba). Se busca por `version`.
- `revision_humana`: una fila por pasada, con revisor y fecha.
- `puntuacion`: una por criterio, `origen='humana'`, `unidad='revision'`,
  `unidad_id=<revision_id>`, con su justificacion (el `CHECK` la exige).

Es un sustituto de los casos de uso de T9 (`registrar_revision_humana`,
`distancia_con_el_juez`), que no existen: la escritura va a mano sobre las
mismas tablas y con las mismas reglas. Cuando T9 exista, esto se retira.

Las puntuaciones del juez **no estan en la base** (ver `langfuse_juez.py`):
`comparar` las lee de `puntuacion` si alguna vez las hay, y si no de Langfuse.
"""

import argparse
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import comun
from app.features.calidad import rubrica_vigente

VALIDADOR = "revision_humana"


def mostrar_rubrica() -> None:
    rubrica = rubrica_vigente()
    minimo, maximo = rubrica.escala
    print(f"Rubrica {rubrica.version}, escala {minimo} a {maximo}\n")
    for criterio in rubrica.criterios:
        print(f"## {criterio.nombre}\n{criterio.definicion}")
        print(f"  {minimo} = {criterio.ancla_minimo}")
        print(f"  {maximo} = {criterio.ancla_maximo}\n")


def asegurar_rubrica(conexion: sqlite3.Connection) -> tuple[int, dict[str, int]]:
    """El id de la rubrica vigente y de sus criterios, sembrandolos si faltan."""
    rubrica = rubrica_vigente()
    fila = conexion.execute(
        "SELECT rubrica_id FROM rubrica WHERE version = ?", (rubrica.version,)
    ).fetchone()
    if fila is None:
        cursor = conexion.execute(
            "INSERT INTO rubrica (version, escala_minimo, escala_maximo) VALUES (?, ?, ?)",
            (rubrica.version, *rubrica.escala),
        )
        rubrica_id = int(cursor.lastrowid or 0)
    else:
        rubrica_id = int(fila["rubrica_id"])
    criterios: dict[str, int] = {}
    for criterio in rubrica.criterios:
        fila = conexion.execute(
            "SELECT criterio_id FROM criterio_de_rubrica WHERE rubrica_id = ? AND nombre = ?",
            (rubrica_id, criterio.nombre),
        ).fetchone()
        if fila is None:
            cursor = conexion.execute(
                "INSERT INTO criterio_de_rubrica"
                " (rubrica_id, nombre, definicion, ancla_minimo, ancla_maximo)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    rubrica_id,
                    criterio.nombre,
                    criterio.definicion,
                    criterio.ancla_minimo,
                    criterio.ancla_maximo,
                ),
            )
            criterios[criterio.nombre] = int(cursor.lastrowid or 0)
        else:
            criterios[criterio.nombre] = int(fila["criterio_id"])
    return rubrica_id, criterios


def validar(puntuaciones: dict[str, dict[str, Any]]) -> None:
    """Misma rubrica, entera y dentro de escala, con justificacion (R-4, R-5)."""
    rubrica = rubrica_vigente()
    esperados = {c.nombre for c in rubrica.criterios}
    if set(puntuaciones) != esperados:
        sobran = sorted(set(puntuaciones) - esperados)
        faltan = sorted(esperados - set(puntuaciones))
        raise ValueError(f"criterios distintos de la rubrica: sobran {sobran}, faltan {faltan}")
    minimo, maximo = rubrica.escala
    for nombre, p in puntuaciones.items():
        if not minimo <= int(p["valor"]) <= maximo:
            raise ValueError(f"{nombre}: {p['valor']} fuera de {minimo}..{maximo}")
        if not str(p.get("justificacion") or "").strip():
            raise ValueError(f"{nombre}: sin justificacion")


def registrar(
    conexion: sqlite3.Connection,
    *,
    obra_id: int,
    revisor: str,
    puntuaciones: dict[str, dict[str, Any]],
) -> int:
    validar(puntuaciones)
    rubrica_id, criterios = asegurar_rubrica(conexion)
    fecha = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S.%f")
    cursor = conexion.execute(
        "INSERT INTO revision_humana (obra_id, rubrica_id, revisor, fecha) VALUES (?, ?, ?, ?)",
        (obra_id, rubrica_id, revisor, fecha),
    )
    revision_id = int(cursor.lastrowid or 0)
    for nombre, p in puntuaciones.items():
        conexion.execute(
            "INSERT INTO puntuacion"
            " (validador, unidad, unidad_id, valor, criterio_id, justificacion, origen)"
            " VALUES (?, 'revision', ?, ?, ?, ?, 'humana')",
            (
                VALIDADOR,
                str(revision_id),
                float(p["valor"]),
                criterios[nombre],
                str(p["justificacion"]).strip(),
            ),
        )
    conexion.commit()
    return revision_id


def preguntar() -> dict[str, dict[str, Any]]:
    rubrica = rubrica_vigente()
    minimo, maximo = rubrica.escala
    salida: dict[str, dict[str, Any]] = {}
    for criterio in rubrica.criterios:
        print(f"\n## {criterio.nombre}\n{criterio.definicion}")
        print(f"  {minimo} = {criterio.ancla_minimo}\n  {maximo} = {criterio.ancla_maximo}")
        while True:
            crudo = input(f"Puntuacion ({minimo}-{maximo}): ").strip()
            if crudo.isdigit() and minimo <= int(crudo) <= maximo:
                break
        justificacion = ""
        while not justificacion:
            justificacion = input("Justificacion (obligatoria): ").strip()
        salida[criterio.nombre] = {"valor": int(crudo), "justificacion": justificacion}
    return salida


def humana(conexion: sqlite3.Connection, obra_id: int) -> dict[str, float]:
    """La ultima revision del Autor sobre la obra, criterio a criterio."""
    fila = conexion.execute(
        "SELECT revision_id FROM revision_humana WHERE obra_id = ? ORDER BY revision_id DESC",
        (obra_id,),
    ).fetchone()
    if fila is None:
        return {}
    filas = conexion.execute(
        "SELECT c.nombre, p.valor FROM puntuacion p"
        " JOIN criterio_de_rubrica c ON c.criterio_id = p.criterio_id"
        " WHERE p.origen = 'humana' AND p.unidad = 'revision' AND p.unidad_id = ?",
        (str(fila["revision_id"]),),
    ).fetchall()
    return {f["nombre"]: float(f["valor"]) for f in filas}


def distancia(humano: dict[str, float], juez: dict[str, list[float]]) -> dict[str, Any]:
    """|humana - media del juez| **criterio a criterio**; la media va aparte."""
    por_criterio = {}
    for nombre, valor in humano.items():
        valores = juez.get(nombre) or []
        if valores:
            media = sum(valores) / len(valores)
            por_criterio[nombre] = {
                "humana": valor,
                "juez": round(media, 2),
                "n_juez": len(valores),
                "distancia": round(abs(valor - media), 2),
            }
    distancias = [d["distancia"] for d in por_criterio.values()]
    return {
        "por_criterio": por_criterio,
        "media": round(sum(distancias) / len(distancias), 2) if distancias else None,
        "criterios_comparados": len(distancias),
    }


def comparar(obra_id: int, *, db: str | None, langfuse: bool) -> dict[str, Any]:
    with comun.conectar(comun.ruta_db(db)) as conexion:
        humano = humana(conexion, obra_id)
        juez: dict[str, list[float]] = {}
        for f in conexion.execute(
            "SELECT c.nombre, p.valor FROM puntuacion p"
            " JOIN criterio_de_rubrica c ON c.criterio_id = p.criterio_id"
            " WHERE p.origen = 'juez'"
        ).fetchall():  # hoy vacio: el juez no persiste (langfuse_juez.py)
            juez.setdefault(f["nombre"], []).append(float(f["valor"]))
    if not juez and langfuse:
        import langfuse_juez

        juez = langfuse_juez.medias_del_juez(obra_id)
    resultado = distancia(humano, juez)
    lineas = [
        f"# Juez contra Autor, obra {obra_id}",
        "",
        "| criterio | Autor | juez (media) | n juez | distancia |",
        "| --- | --- | --- | --- | --- |",
    ]
    for nombre, d in resultado["por_criterio"].items():
        lineas.append(
            f"| {nombre} | {d['humana']:.0f} | {d['juez']} | {d['n_juez']} | {d['distancia']} |"
        )
    lineas += [
        "",
        (
            f"Distancia media: {resultado['media']} sobre "
            f"{resultado['criterios_comparados']} criterios. El juez **sigue sin bloquear** "
            "(RF-JUZ-06): una novela no es un conjunto."
        ),
        "",
    ]
    texto = "\n".join(lineas)
    print(texto)
    if not humano:
        print("No hay revision humana de esta obra: `puntuar` primero.", file=sys.stderr)
    if not juez:
        print(
            "No hay puntuaciones del juez: usa --langfuse con las credenciales en el entorno.",
            file=sys.stderr,
        )
    salida = comun.RESULTADOS / f"distancia-obra-{obra_id}.md"
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(texto, encoding="utf-8")
    return resultado


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Revision humana con la rubrica del juez")
    sub = parser.add_subparsers(dest="orden", required=True)
    sub.add_parser("rubrica")
    p = sub.add_parser("puntuar")
    p.add_argument("--obra", type=int, required=True)
    p.add_argument("--revisor", required=True)
    p.add_argument("--desde", help='JSON {"criterio": {"valor": 4, "justificacion": "..."}}')
    p.add_argument("--db")
    c = sub.add_parser("comparar")
    c.add_argument("--obra", type=int, required=True)
    c.add_argument("--langfuse", action="store_true")
    c.add_argument("--db")
    args = parser.parse_args(argv)

    if args.orden == "rubrica":
        mostrar_rubrica()
        return 0
    if args.orden == "puntuar":
        puntuaciones = (
            json.loads(Path(args.desde).read_text(encoding="utf-8")) if args.desde else preguntar()
        )
        with comun.conectar(comun.ruta_db(args.db), solo_lectura=False) as conexion:
            revision_id = registrar(
                conexion, obra_id=args.obra, revisor=args.revisor, puntuaciones=puntuaciones
            )
        print(f"Revision {revision_id} guardada para la obra {args.obra}.")
        return 0
    comparar(args.obra, db=args.db, langfuse=args.langfuse)
    return 0


if __name__ == "__main__":
    sys.exit(main())
