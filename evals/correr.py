"""Corredor de las evals: lleva cada brief por el backend **que ya esta corriendo**.

    uv run python evals/correr.py                     # los cinco, segun el manifiesto
    uv run python evals/correr.py --solo b1-jubilacion b3-trampa-temporal
    uv run python evals/correr.py --modo b5-cobertura-imposible=capitulo_1
    uv run python evals/correr.py --reanudar          # sigue donde se quedo cada brief

**Habla HTTP con el mismo proceso** (http://127.0.0.1:8000 por defecto) y no
monta ningun agente propio: asi los cinco comparten el techo concurrente de
100.000 tokens (`CLAUDE.md` §4.1), que vive en ese proceso. Un corredor que
compusiera su propia app tendria su propio portero, y el techo sumado dejaria de
ser uno.

**Gasta cuota.** Solo lo lanza una persona. Los tests usan un transporte falso.

Por brief, en orden: `POST /entrevistas` -> `/respuestas` -> `/cerrar` ->
`POST /obras/{id}/outline`, y despues:

- `completa`: `POST /obras/{id}/novela`, sondeo de `GET /obras/{id}/novela`
  hasta `terminada` o `detenida`, y `POST /obras/{id}/publicar` (Lean y G4).
- `capitulo_1`: **no usa `/novela`**, porque no hay endpoint de cancelar y la
  tarea de fondo seguiria con los nueve restantes. Usa
  `POST /capitulos/{capitulo_id}/escribir`, que escribe **ese** capitulo y para,
  y sondea `GET /trabajos/{id}`. El `capitulo_id` del numero 1 se lee de la base
  (solo lectura): `OutlineCreado` no lo devuelve.

R-3: un brief que revienta **no se lleva a los demas**. Cada paso se guarda en
`evals/resultados/corridas.json` en cuanto termina, asi que una caida del
corredor no pierde lo hecho y `--reanudar` sigue.

**Nada de prosa en `corridas.json`**: ids, estados, codigos HTTP y el `detail`
de los errores de dominio, que nombra validadores y elementos del brief.
"""

import argparse
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

import comun

Transporte = Callable[[str, str, dict[str, Any] | None, float], tuple[int, Any]]
"""(metodo, url, cuerpo, timeout) -> (status, json). Se inyecta para los tests."""

ESTADOS_FINALES_DE_TRABAJO = {"INTEGRADA", "ESCALADA", "FALLIDA", "CANCELADA"}
ESTADOS_FINALES_DE_NOVELA = {"terminada", "detenida", "sin_outline"}


def transporte_http(metodo: str, url: str, cuerpo: dict[str, Any] | None, timeout: float):
    datos = None if cuerpo is None else json.dumps(cuerpo).encode("utf-8")
    peticion = urllib.request.Request(url, data=datos, method=metodo)
    peticion.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
            crudo = respuesta.read().decode("utf-8")
            return respuesta.status, (json.loads(crudo) if crudo else None)
    except urllib.error.HTTPError as error:
        crudo = error.read().decode("utf-8", errors="replace")
        try:
            return error.code, json.loads(crudo)
        except json.JSONDecodeError:
            return error.code, {"detail": crudo[:500]}


def _ahora() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Corredor:
    def __init__(
        self,
        *,
        base: str,
        transporte: Transporte = transporte_http,
        capitulo_uno: Callable[[int], int] | None = None,
        sondeo_s: float = 30.0,
        espera_maxima_s: float = 4 * 3600,
        corridas: dict[str, Any] | None = None,
        guardar: Callable[[dict[str, Any]], None] = comun.guardar_corridas,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        self.base = base.rstrip("/")
        self.transporte = transporte
        self.capitulo_uno = capitulo_uno or _capitulo_uno_de_la_base
        self.sondeo_s = sondeo_s
        self.espera_maxima_s = espera_maxima_s
        self.datos = corridas if corridas is not None else {"corridas": {}}
        self._guardar = guardar
        self._dormir = dormir
        self._cerrojo = threading.Lock()

    # --- persistencia ------------------------------------------------------

    def _registro(self, brief_id: str) -> dict[str, Any]:
        with self._cerrojo:
            return self.datos["corridas"].setdefault(brief_id, {"pasos": {}})

    def _anotar(self, brief_id: str, paso: str, **valores: Any) -> None:
        with self._cerrojo:
            registro = self.datos["corridas"].setdefault(brief_id, {"pasos": {}})
            registro["pasos"][paso] = {"en": _ahora(), **valores}
            for clave in ("obra_id", "llego_a", "error", "modo"):
                if clave in valores:
                    registro[clave] = valores[clave]
            self._guardar(self.datos)

    def _hecho(self, brief_id: str, paso: str) -> dict[str, Any] | None:
        paso_hecho: dict[str, Any] | None = self._registro(brief_id)["pasos"].get(paso)
        if paso_hecho and paso_hecho.get("ok"):
            return paso_hecho
        return None

    # --- HTTP --------------------------------------------------------------

    def _llamar(
        self, metodo: str, ruta: str, cuerpo: dict[str, Any] | None = None, timeout: float = 1800.0
    ) -> tuple[int, Any]:
        return self.transporte(metodo, f"{self.base}{ruta}", cuerpo, timeout)

    # --- un brief ----------------------------------------------------------

    def correr_brief(self, entrada: dict[str, Any], modo: str, reanudar: bool) -> None:
        brief_id = entrada["id"]
        try:
            self._correr(entrada, modo, reanudar)
        except Exception as error:  # noqa: BLE001 -- R-3: el brief cae, el corredor no
            self._anotar(brief_id, "error", ok=False, error=f"{type(error).__name__}: {error}")

    def _correr(self, entrada: dict[str, Any], modo: str, reanudar: bool) -> None:
        brief_id = entrada["id"]
        if not reanudar:
            with self._cerrojo:
                self.datos["corridas"][brief_id] = {"pasos": {}}
        self._anotar(brief_id, "inicio", ok=True, modo=modo)
        obra_id = self._registro(brief_id).get("obra_id")

        if obra_id is None:
            obra_id = self._entrevista(entrada)
            if obra_id is None:
                return

        if not self._hecho(brief_id, "outline"):
            t0 = time.monotonic()
            status, cuerpo = self._llamar("POST", f"/obras/{obra_id}/outline")
            ok = status == 201
            self._anotar(
                brief_id,
                "outline",
                ok=ok,
                status=status,
                segundos=round(time.monotonic() - t0),
                **({} if ok else {"detail": _detalle(cuerpo), "llego_a": "outline"}),
            )
            if not ok:
                return

        if modo == "capitulo_1":
            self._capitulo_uno(brief_id, obra_id)
        else:
            self._novela(brief_id, obra_id)

    def _entrevista(self, entrada: dict[str, Any]) -> int | None:
        brief_id = entrada["id"]
        status, cuerpo = self._llamar("POST", "/entrevistas", timeout=60)
        if status != 201:
            self._anotar(
                brief_id,
                "entrevista",
                ok=False,
                status=status,
                detail=_detalle(cuerpo),
                llego_a="entrevista",
            )
            return None
        entrevista_id = cuerpo["id"]

        t0 = time.monotonic()
        status, evaluacion = self._llamar(
            "POST",
            f"/entrevistas/{entrevista_id}/respuestas",
            {
                "respuestas": comun.brief(entrada),
                "texto_aportado": entrada.get("texto_aportado", ""),
            },
        )
        self._anotar(
            brief_id,
            "respuestas",
            ok=status == 200,
            status=status,
            entrevista_id=entrevista_id,
            segundos=round(time.monotonic() - t0),
            faltantes=(evaluacion or {}).get("faltantes"),
            contradicciones=len((evaluacion or {}).get("contradicciones") or []),
        )

        t0 = time.monotonic()
        status, cierre = self._llamar("POST", f"/entrevistas/{entrevista_id}/cerrar")
        if status not in (200, 201):
            self._anotar(
                brief_id,
                "cerrar",
                ok=False,
                status=status,
                detail=_detalle(cierre),
                faltantes=(cierre or {}).get("faltantes"),
                contradicciones=(cierre or {}).get("contradicciones"),
                llego_a="entrevista",
                segundos=round(time.monotonic() - t0),
            )
            return None
        obra_id = int(cierre["obra_id"])
        self._anotar(
            brief_id,
            "cerrar",
            ok=True,
            status=status,
            obra_id=obra_id,
            segundos=round(time.monotonic() - t0),
        )
        return obra_id

    def _novela(self, brief_id: str, obra_id: int) -> None:
        if not self._hecho(brief_id, "novela"):
            status, lanzada = self._llamar("POST", f"/obras/{obra_id}/novela", timeout=120)
            if status != 202:
                self._anotar(
                    brief_id,
                    "novela",
                    ok=False,
                    status=status,
                    detail=_detalle(lanzada),
                    llego_a="novela",
                )
                return
            t0 = time.monotonic()
            estado = self._sondear(f"/obras/{obra_id}/novela", "estado", ESTADOS_FINALES_DE_NOVELA)
            self._anotar(
                brief_id,
                "novela",
                ok=estado.get("estado") == "terminada",
                estado=estado.get("estado"),
                integrados=estado.get("integrados"),
                total=estado.get("total"),
                motivo=estado.get("motivo"),
                segundos=round(time.monotonic() - t0),
                **({} if estado.get("estado") == "terminada" else {"llego_a": "novela"}),
            )
            if estado.get("estado") != "terminada":
                return

        status, publicada = self._llamar("POST", f"/obras/{obra_id}/publicar", timeout=900)
        if status == 200:
            # El token no se guarda: es la llave de lectura. Se imprime y ya.
            print(
                f"[{brief_id}] publicada, ordinal {publicada.get('ordinal')}, "
                f"token {publicada.get('token')}",
                flush=True,
            )
            self._anotar(
                brief_id,
                "publicar",
                ok=True,
                status=status,
                ordinal=publicada.get("ordinal"),
                llego_a="publicada",
            )
        else:
            self._anotar(
                brief_id,
                "publicar",
                ok=False,
                status=status,
                detail=_detalle(publicada),
                llego_a="G4",
            )

    def _capitulo_uno(self, brief_id: str, obra_id: int) -> None:
        if self._hecho(brief_id, "capitulo_1"):
            return
        capitulo_id = self.capitulo_uno(obra_id)
        status, lanzado = self._llamar("POST", f"/capitulos/{capitulo_id}/escribir", timeout=120)
        if status != 202:
            self._anotar(
                brief_id,
                "capitulo_1",
                ok=False,
                status=status,
                detail=_detalle(lanzado),
                llego_a="capitulo_1",
            )
            return
        t0 = time.monotonic()
        trabajo = self._sondear(f"/trabajos/{lanzado['id']}", "estado", ESTADOS_FINALES_DE_TRABAJO)
        self._anotar(
            brief_id,
            "capitulo_1",
            ok=trabajo.get("estado") == "INTEGRADA",
            trabajo_id=lanzado["id"],
            capitulo_id=capitulo_id,
            estado=trabajo.get("estado"),
            causa_fallo=trabajo.get("causa_fallo"),
            segundos=round(time.monotonic() - t0),
            llego_a="capitulo_1",
        )

    def _sondear(self, ruta: str, campo: str, finales: set[str]) -> dict[str, Any]:
        limite = time.monotonic() + self.espera_maxima_s
        while True:
            status, cuerpo = self._llamar("GET", ruta, timeout=60)
            if status == 200 and cuerpo.get(campo) in finales:
                result: dict[str, Any] = cuerpo
                return result
            if time.monotonic() > limite:
                return {campo: "sin_terminar", "motivo": f"sondeo agotado en {ruta}"}
            self._dormir(self.sondeo_s)

    # --- todos -------------------------------------------------------------

    def correr(
        self,
        entradas: list[dict[str, Any]],
        modos: dict[str, str],
        *,
        reanudar: bool,
        en_paralelo: bool,
    ) -> dict[str, Any]:
        if en_paralelo:
            # Hilos y no procesos: lo que se paraleliza es esperar. El techo de
            # tokens lo aplica el backend, no este corredor.
            with ThreadPoolExecutor(max_workers=len(entradas) or 1) as grupo:
                for entrada in entradas:
                    grupo.submit(self.correr_brief, entrada, modos[entrada["id"]], reanudar)
        else:
            for entrada in entradas:
                self.correr_brief(entrada, modos[entrada["id"]], reanudar)
        return self.datos


def _detalle(cuerpo: Any) -> str | None:
    if isinstance(cuerpo, dict):
        detalle = cuerpo.get("detail")
        return None if detalle is None else str(detalle)[:500]
    return None


def _capitulo_uno_de_la_base(obra_id: int) -> int:
    with comun.conectar(comun.ruta_db()) as conexion:
        fila = conexion.execute(
            "SELECT id FROM capitulo WHERE obra_id = ? AND numero = 1 ORDER BY id DESC LIMIT 1",
            (obra_id,),
        ).fetchone()
    if fila is None:
        raise RuntimeError(f"la obra {obra_id} no tiene capitulo 1 en la base")
    return int(fila["id"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--solo", nargs="*", help="ids del manifiesto a correr")
    parser.add_argument("--modo", nargs="*", default=[], help="id=completa|capitulo_1")
    parser.add_argument("--reanudar", action="store_true")
    parser.add_argument("--en-serie", action="store_true", help="un brief detras de otro")
    parser.add_argument("--sondeo", type=float, default=30.0, help="segundos entre consultas")
    args = parser.parse_args(argv)

    entradas = [e for e in comun.manifiesto() if not args.solo or e["id"] in args.solo]
    modos = {e["id"]: e["modo"] for e in entradas}
    for cambio in args.modo:
        clave, _, valor = cambio.partition("=")
        if valor not in ("completa", "capitulo_1"):
            parser.error(f"modo invalido: {cambio}")
        modos[clave] = valor

    corredor = Corredor(base=args.base, sondeo_s=args.sondeo, corridas=comun.leer_corridas())
    datos = corredor.correr(entradas, modos, reanudar=args.reanudar, en_paralelo=not args.en_serie)
    for brief_id, registro in datos["corridas"].items():
        print(
            f"{brief_id}: obra {registro.get('obra_id')} -> {registro.get('llego_a')}"
            f"{'  ERROR ' + registro['error'] if registro.get('error') else ''}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
