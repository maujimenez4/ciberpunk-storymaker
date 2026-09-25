---
id: 001-backend-v1 / plan-8-corrida-real
titulo: "Fase 8 — Lo que falta para que la primera novela real sirva y se pueda leer por dentro"
estado: aprobado          # borrador | en-revision | aprobado | completado
aprobado_por: maujimenez4 # firmado el 2026-09-24 («Lo firmo asi»); rigen D-1 a D-5 como recomendadas, y vale como firma de la enmienda de spec de T2 (campo `trato`) y de los términos *marcador del destinatario* y *trato*
fecha: 2026-09-24
spec: specs/001-backend-v1/spec.md
hereda_de: specs/001-backend-v1/plan-7-harness.md
---

# Fase 8 — Lo que falta para que la primera novela real sirva

> **Para agentes:** este plan se ejecuta tarea a tarea con TDD (`CLAUDE.md` §3.4): cada paso de código empieza por un test que se ve en rojo. Los pasos van con casillas (`- [ ]`).

**Objetivo:** que la primera corrida real produzca **una novela entregable** (con el nombre de quien la recibe), que si un capítulo escala **quede evidencia para saber por qué**, que la corrida sea **más corta**, y que sus trazas de Langfuse **sirvan para el *tuning*** del plan 6.

**Por qué es un plan nuevo y no una tarea de otro.** Lo que bloquea la novela de ejemplo —P-19, P-20, P-21 y P-22 de [`problemas-abiertos.md`](../problemas-abiertos.md)— no estaba en ningún plan: salió al intentar la primera corrida real el 2026-09-24. **No es el último plan**: lo que queda después ya tiene plan firmado (plan 4 T10 el PDF, plan 5 la petición del lector, plan 6 T9–T11 las evals, plan 7 T9–T11 la validación visual y el PDF de ejemplo). Ver [`hoja-de-ruta.md`](../hoja-de-ruta.md).

**Spec:** [`spec.md`](spec.md), `aprobada`. **Este plan la enmienda en un punto** (T2: el campo `trato` del brief) y por eso su firma vale también como firma de esa enmienda; se dice en la tarea.

**Stack:** FastAPI + Pydantic v2 + SQLAlchemy async + Alembic (backend); React + TanStack Query (el campo nuevo del formulario); Claude Agent SDK; Langfuse v3.

---

## Global Constraints

- Ninguna llamada al modelo en los tests: el cliente es `DobleDeterminista` (`CLAUDE.md` §3.5).
- Nunca se llama al modelo sin contar sus tokens; el techo concurrente es **100.000 tokens en vuelo, contados en tokens y no en llamadas** (`CLAUDE.md` §4.1, `commons/jobs/turnos.py` `TECHO_CONCURRENTE = 100_000`).
- Todo esquema nuevo lleva migración de Alembic que funciona con y sin `sqlite-vec` (`CLAUDE.md` §16).
- Fronteras: una feature solo importa de `commons/` y del `__init__.py` de otra (`lint-imports`).
- Vocabulario: ningún término nuevo sin entrada en `docs/definitions.md` (`CLAUDE.md` §2). Este plan introduce **dos**: *marcador del destinatario* y *trato*.
- Commits: `git add <rutas>` + `git commit -F <fichero> -- <rutas>`; mensaje sin BOM.
- Puertas de cada tarea: `uv run pytest <features tocadas>`, `ruff check`, `mypy` de los ficheros tocados, `lint-imports`; si toca el frontend, `vitest`, `tsc`, `eslint`.

## Review Focus

Lo que ningún test de tarea ejercita y más probablemente muerda a quien use esto:

1. **Un nombre que es también palabra común** («Rosa», «Luz», «Blanca»): la sustitución de salida no puede convertir «una rosa» en «una María». → T3 sustituye **solo el marcador**, que es un nombre inventado; el nombre real nunca se busca en la prosa. Test en T3.
2. **El marcador aparece en un texto que el comprador escribió** (rasgos, recuerdos, elementos): el nombre real dentro de «el verano en Cádiz con Marta» también se enmascara al entrar. Test en T2.
3. **Un veto que coincide con el marcador** (el comprador veta «Oriana»): el marcador se elige de una lista y salta al siguiente. Test en T2.
4. **Dos obras escribiendo a la vez con los jueces en paralelo**: nadie se bloquea esperando turno mientras retiene el suyo. Test en T6.
5. **Langfuse caído durante la corrida**: el `flush` al apagar no puede tumbar el apagado. Test en T7.

---

## Decisiones que se toman al firmar

Van con recomendación. Si se firma sin decir nada, rige la recomendada.

| # | Decisión | Recomendación |
| --- | --- | --- |
| **D-1** | **¿Se hace el marcador aunque la cuenta nueva no anonimice?** El anonimizado apareció con la cuenta de trabajo, y hay indicios de que es una política de esa cuenta —en esta misma sesión se añadió una «nota de privacidad» a una respuesta—, no del modelo. | **Sondear primero (T1)** y hacer T2–T3 **solo si la cuenta de la corrida anonimiza**. Si no anonimiza, T2–T3 quedan escritas y sin ejecutar, y la corrida sale antes. |
| **D-2** | **Cómo es el marcador.** Un token raro (`DESTINATARIO_1`) lo reproduce el modelo, pero escribe mal alrededor de él y no sabe si es ella o él. | **Un nombre inventado, poco común y del trato correcto** (p. ej. «Oriana» / «Anselmo» / «Alix»), elegido por código de una lista. El modelo escribe natural, y `nombres_literales` caza sus variantes como con cualquier personaje. |
| **D-3** | **El trato.** Con el nombre oculto, el modelo pierde la única pista de género que tenía. | **Una pregunta más en la entrevista**: «¿Cómo nos referimos a esta persona? Ella / Él / Sin género», guardada en `destinatario.trato`. Enmienda de spec (T2). |
| **D-4** | **Qué compara `nombres_literales` y los vetos.** | **El texto almacenado, con el marcador.** El canon guarda el marcador, así que la comparación es la de siempre; R-8 ya garantiza que ningún veto choca con el nombre real, y T2 añade la misma garantía para el marcador. |
| **D-5** | **Entrevistador en Langfuse** (P-22.4). | **Fuera de esta fase, declarado.** Su sesión no existe aún y no aporta al *tuning*. Queda como está en `architecture.md` §9.2.1. |

---

## Las tareas y cómo se reparten

| # | Tarea | Depende de | Paralelizable con |
| --- | --- | --- | --- |
| **T1** | Sonda: ¿anonimiza la cuenta de la corrida? | — | todas |
| **T2** | Marcador de entrada: `trato`, elección del marcador, enmascarado del brief | T1 (si anonimiza) | T4, T5, T7 |
| **T3** | Marcador de salida: sustitución al servir | T2 | T4, T5, T7 |
| **T4** | Evidencia de la escalada: `intento_descartado` y su endpoint | — | T2, T3, T5, T7 |
| **T5** | Medir la sobrecarga del CLI | — | T2, T3, T4, T7 |
| **T6** | Continuista y Crítico en paralelo, contados | T5 | T2, T3, T7 |
| **T7** | Langfuse: criterio, `flush`, prompt versionado en cada span | — | todas salvo T6 (ver juntura) |

**Junturas con dueño (P-16):** `features/escritura/service.py` lo tocan T4 (devolver `juicio` al escalar) y T6 (el paralelo): **T6 va después de T4** en ese fichero. `commons/observabilidad/cliente.py` lo toca solo T7; T6 usa `Observacion.span` tal como esté. El `__init__.py` de `escritura` lo edita solo T4.

---

## Tarea 1 · Sonda: ¿anonimiza la cuenta de la corrida?

**Qué entrega:** una respuesta medida, no una suposición, a D-1. **No escribe código de producción.**

**Files:**
- Create: `src/backend/scripts/sonda_nombre.py` (fuera de `app/`: no es producto)
- Modify: `specs/problemas-abiertos.md` (P-19, con el resultado)

- [ ] **Paso 1: el script.** Llama **una vez** al Arquitecto real con `ejemplos/brief-marta.json` y cuenta apariciones.

```python
"""Sonda de P-19: ¿el modelo, con ESTA cuenta, conserva el nombre del destinatario?

Una llamada real al Arquitecto (unos 3 minutos). No se ejecuta en la suite.
Uso: uv run python src/backend/scripts/sonda_nombre.py
"""

import asyncio
import json
from pathlib import Path

from app.commons.llm.claude_code import ClienteClaudeCode
from app.features.outline.agents import PLANTILLA_V2, render_arquitecto

BRIEF = json.loads(Path("ejemplos/brief-marta.json").read_text(encoding="utf-8"))


async def main() -> None:
    nombre = BRIEF["destinatario"]["nombre"]
    prompt = render_arquitecto(PLANTILLA_V2, {"titulo": f"Novela para {nombre}", **BRIEF})
    salida = await ClienteClaudeCode().completar(prompt, semilla=0)
    print(json.dumps({
        "nombre": nombre,
        "apariciones_del_nombre": salida.count(nombre),
        "anonimizado": "ANONIMIZADO" in salida.upper(),
    }, ensure_ascii=False))


asyncio.run(main())
```

- [ ] **Paso 2: ejecutarla** con la cuenta con la que se hará la corrida. Esperado: una línea JSON.
- [ ] **Paso 3: anotar el resultado en P-19** (fecha, cuenta usada, las tres cifras) y **decidir**: `anonimizado: true` → se ejecutan T2 y T3; `false` y el nombre aparece → T2 y T3 quedan sin ejecutar y P-19 pasa a «depende de la cuenta».
- [ ] **Paso 4: commit** del script y de P-19.

---

## Tarea 2 · Marcador de entrada: el trato, la elección del marcador y el enmascarado

**Qué entrega:** ningún prompt posterior a la entrevista lleva el nombre real. Todo lo que se guarda después de cerrar la entrevista —título de la obra, biblia, canon, prosa— lleva el **marcador**. `destinatario.nombre` sigue guardando el real, y es el único sitio.

**Enmienda de spec que esta tarea introduce, y que la firma del plan aprueba:** el brief gana un campo obligatorio `trato ∈ {ella, el, neutro}`; el Entrevistador lo cuenta entre los datos obligatorios (`RF-ENT-03`).

**Files:**
- Modify: `docs/definitions.md` (entradas *marcador del destinatario* y *trato*, en la tabla de `Destinatario`)
- Modify: `src/backend/app/features/obra/schemas.py` (`DestinatarioEntrada.trato`)
- Modify: `src/backend/app/features/obra/modelos.py` (`Destinatario.trato`, `Destinatario.marcador`)
- Create: `src/backend/alembic/versions/<rev>_trato_y_marcador_del_destinatario.py`
- Create: `src/backend/app/commons/domain/marcador.py` (elección y enmascarado: dominio puro, sin FastAPI ni SQLAlchemy)
- Modify: `src/backend/app/features/obra/repository.py:129-176` (`crear_obra_desde_brief`: guarda trato y marcador; `titulo=f"Novela para {marcador}"`)
- Modify: `src/backend/app/features/outline/repository.py:101-150` (`leer_obra` / `como_brief`: enmascara)
- Modify: `src/backend/app/features/obra/prompts/` → `entrevistador.v3.md` (añade `trato` a obligatorios) y la constante en `obra/agents.py`
- Modify: `src/frontend/src/features/entrevista/components/Entrevista.tsx` (pregunta «¿Cómo nos referimos a esta persona?»)
- Test: `src/backend/app/commons/domain/tests/test_marcador.py`, `src/backend/app/features/outline/tests/test_brief_enmascarado.py`, `src/frontend/.../Entrevista.test.tsx`

**Interfaces:**
- Produces: `commons.domain.marcador`:
  - `Trato = Literal["ella", "el", "neutro"]`
  - `elegir_marcador(trato: Trato, *, evitar: Iterable[str]) -> str` — primer nombre de la lista del trato que no choca (por `contiene_veto`) con `evitar` (vetos + nombre real).
  - `enmascarar(texto: str, *, nombre: str, marcador: str) -> str` — sustituye el nombre real por el marcador, **palabra entera y sin distinguir mayúsculas ni acentos**.
  - `desenmascarar(texto: str, *, marcador: str, nombre: str) -> str` — la inversa, palabra entera, **solo el marcador**.

- [ ] **Paso 1: vocabulario.** Añadir a `docs/definitions.md`, junto a `Destinatario`:
  - **Marcador del destinatario** — nombre inventado que sustituye al nombre real del destinatario en todo lo que ve un modelo y en todo lo que se guarda tras cerrar la entrevista. Se sustituye por el nombre real **solo al servir** la lectura. Uno por obra.
  - **Trato** — cómo se nombra gramaticalmente al destinatario: `ella`, `el` o `neutro`. Lo declara el comprador.

- [ ] **Paso 2: test rojo del dominio.**

```python
from app.commons.domain.marcador import desenmascarar, elegir_marcador, enmascarar


def test_el_marcador_respeta_el_trato():
    assert elegir_marcador("ella", evitar=[]) == "Oriana"
    assert elegir_marcador("el", evitar=[]) == "Anselmo"


def test_un_veto_que_coincide_con_el_marcador_salta_al_siguiente():
    assert elegir_marcador("ella", evitar=["oriana"]) != "Oriana"


def test_el_marcador_nunca_es_el_nombre_real():
    assert elegir_marcador("ella", evitar=["Oriana"]) != "Oriana"


def test_enmascarar_cambia_el_nombre_como_palabra_entera_y_sin_mayusculas():
    texto = "El verano en Cádiz con MARTA; martanita no es ella."
    assert enmascarar(texto, nombre="Marta", marcador="Oriana") == (
        "El verano en Cádiz con Oriana; martanita no es ella."
    )


def test_desenmascarar_solo_toca_el_marcador_y_nunca_una_palabra_comun():
    # Review Focus 1: «Rosa» es nombre y es flor. Solo se busca el marcador.
    texto = "Oriana dejó una rosa en la mesa."
    assert desenmascarar(texto, marcador="Oriana", nombre="Rosa") == "Rosa dejó una rosa en la mesa."
```

- [ ] **Paso 3: verlo en rojo** — `uv run pytest src/backend/app/commons/domain/tests/test_marcador.py -q` → `ModuleNotFoundError`; luego, con el módulo vacío, fallos de aserción.

- [ ] **Paso 4: implementación mínima.**

```python
"""El marcador del destinatario (`docs/definitions.md`): dominio puro."""

import re
from collections.abc import Iterable
from typing import Literal

from app.commons.domain.normalizacion import contiene_veto, normalizar

Trato = Literal["ella", "el", "neutro"]

# Nombres poco comunes en la ficción española actual, para que no choquen con un
# personaje que el Arquitecto invente. El orden es el de preferencia.
_CANDIDATOS: dict[Trato, tuple[str, ...]] = {
    "ella": ("Oriana", "Casilda", "Leocadia", "Ximena"),
    "el": ("Anselmo", "Leandro", "Eusebio", "Fermín"),
    "neutro": ("Alix", "Noa", "Ariel", "Eli"),
}


def elegir_marcador(trato: Trato, *, evitar: Iterable[str]) -> str:
    evitar = list(evitar)
    for candidato in _CANDIDATOS[trato]:
        if contiene_veto(candidato, evitar) is None:
            return candidato
    raise ValueError(f"ningun marcador libre para el trato {trato!r}")


def _palabra(forma: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){re.escape(forma)}(?!\w)", re.IGNORECASE)


def enmascarar(texto: str, *, nombre: str, marcador: str) -> str:
    # Sin acentos: se compara sobre la forma normalizada palabra a palabra.
    objetivo = normalizar(nombre)
    return re.sub(r"\w+", lambda m: marcador if normalizar(m.group()) == objetivo else m.group(), texto)


def desenmascarar(texto: str, *, marcador: str, nombre: str) -> str:
    return _palabra(marcador).sub(nombre, texto)
```

  *(Si `normalizar` quita la -s final y eso hace que «Martas» cuente como «Marta», se acepta: es el nombre en plural, no otra palabra.)*

- [ ] **Paso 5: verde** del paso 3.

- [ ] **Paso 6: esquema, test rojo.** En `features/obra/tests/test_endpoints.py`, cerrar una entrevista con `trato: "ella"` crea `destinatario.trato == "ella"`, `destinatario.marcador == "Oriana"` y `obra.titulo == "Novela para Oriana"`; sin `trato`, `cerrar` devuelve 422 con `destinatario.trato` entre los faltantes. Verlo en rojo.

- [ ] **Paso 7: migración y modelo.** `Destinatario.trato: Mapped[str] = mapped_column(String(10))` y `Destinatario.marcador: Mapped[str] = mapped_column(String(40))`; migración con `server_default` `'neutro'` y marcador `'Alix'` para las filas existentes (hoy hay dos obras de prueba y ninguna novela). `DestinatarioEntrada.trato: Literal["ella", "el", "neutro"]`. En `crear_obra_desde_brief`: `marcador = elegir_marcador(brief.destinatario.trato, evitar=[*brief.vetos, brief.destinatario.nombre])` y `titulo=f"Novela para {marcador}"`. `uv run alembic upgrade head`, y después `downgrade -1` y otra vez `upgrade`, en limpio. Verde.

- [ ] **Paso 8: `como_brief` enmascarado, test rojo.** `test_brief_enmascarado.py`: con una obra de Marta cuyo recuerdo es «el verano en Cádiz con Marta», `como_brief()` **no contiene «Marta» en ningún valor** y contiene «Oriana» en `destinatario.nombre` y en el recuerdo; además lleva `destinatario.trato == "ella"`. **Y el test viejo `test_brief_del_arquitecto.py:83`, que afirma `nombre == "Marta"`, se cambia a propósito a «Oriana»**, citando esta tarea. Ver rojo; implementar aplicando `enmascarar` a cada valor de texto de `destinatario`, `elementos_obligatorios` y `titulo` en `leer_obra`; verde.

- [ ] **Paso 9: el Entrevistador pide el trato.** `entrevistador.v3.md` = v2 + `trato` en la lista de obligatorios; la constante pasa a `PLANTILLA_V3` apuntando a v3 (se corrige de paso el nombre engañoso `PLANTILLA_V1`, P-26). El test `test_prompt_y_esquema.py` que cruza obligatorios del prompt con el esquema debe ponerse en rojo con v2 y en verde con v3.

- [ ] **Paso 10: el formulario.** Test rojo en `Entrevista.test.tsx`: el cuerpo de `/respuestas` lleva `trato: "ella"` al elegir «Ella» en un `<select>` etiquetado «¿Cómo nos referimos a esta persona?», y **no lleva `trato`** si no se elige (se cuenta como faltante en el backend). Implementar en el bloque «Quién es». Verde en `vitest`, `tsc`, `eslint`.

- [ ] **Paso 11: commits** — uno para dominio + definiciones, uno para esquema + migración + repositorios, uno para el Entrevistador, uno para el frontend.

---

## Tarea 3 · Marcador de salida: la sustitución al servir

**Qué entrega:** quien lee ve el nombre real en el título, en cada capítulo y en la ficha, y **en ningún otro sitio** se deshace el marcador.

**Files:**
- Modify: `src/backend/app/features/manuscrito/service.py` (una función `servir(texto, obra_id)` que llama a `desenmascarar`)
- Modify: `src/backend/app/features/manuscrito/router.py:103-166` (portada: `titulo` y títulos de capítulo; capítulo: `texto`; ficha: `nombre` y `descripcion`)
- Test: `src/backend/app/features/manuscrito/tests/test_marcador_al_servir.py`

- [ ] **Paso 1: test rojo.** Publicar una obra cuyo `destinatario` es Marta con marcador Oriana, cuyo capítulo 1 dice «Oriana abrió la ventana» y cuya ficha tiene la entrada «Oriana». Esperado en la API de lectura: portada `titulo == "Novela para Marta"`, capítulo `texto == "Marta abrió la ventana"`, ficha con `nombre == "Marta"`. **Y en base de datos sigue «Oriana»** (la sustitución es de salida, no de escritura).
- [ ] **Paso 2: rojo.**
- [ ] **Paso 3: implementar** un único punto `desenmascarar_para(obra_id)` en `manuscrito/service.py` que lee `destinatario.nombre` y `destinatario.marcador` una vez por petición y se aplica en los tres endpoints. La dedicatoria **no pasa por aquí**: es texto del comprador y ya lleva el nombre real (regla de dominio 15).
- [ ] **Paso 4: verde**, y un test de que la dedicatoria sale intacta aunque contenga la palabra del marcador.
- [ ] **Paso 5: commit.**

*Fuera de esta tarea, declarado:* el PDF (plan 4 T10) debe usar el mismo `desenmascarar_para` cuando exista; se anota en P-19.

---

## Tarea 4 · Evidencia de la escalada

**Qué entrega:** tras cualquier capítulo con intentos rechazados —escale o no—, queda **cada intento con su texto y sus defectos**, fuera de lo vigente, y se puede consultar. Distingue «el modelo escribió mal tres veces» de «un validador rechaza siempre».

**Por qué una tabla aparte y no dejar de borrar:** `_retirar_lo_descartado` borra por R-7 —que la prosa descartada no contamine el paquete del capítulo siguiente vía `vigente = 1`—, y tres lectores dependen de esa semántica (`contexto/service.py:448`, `canon/resumenes.py:88,137`, `manuscrito/repository.py:152`). Guardar la evidencia **en otra tabla** no toca ninguno.

**Files:**
- Modify: `src/backend/app/features/escritura/modelos.py` (modelo `IntentoDescartado`)
- Create: `src/backend/alembic/versions/<rev>_intentos_descartados.py`
- Modify: `src/backend/app/features/escritura/ciclo.py:358-373` (antes de `_retirar_lo_descartado`, guardar)
- Modify: `src/backend/app/features/escritura/service.py:500-508` (el retorno escalado lleva `juicio=juicio`)
- Modify: `src/backend/app/features/escritura/router.py` (`GET /trabajos/{trabajo_id}/intentos`)
- Modify: `openapi.json` (regenerado desde la app)
- Test: `src/backend/app/features/escritura/tests/test_evidencia_de_escalada.py`

**Interfaces:**
- Produces: tabla `intento_descartado(id, trabajo_id FK, run_id, escena_id FK, numero, texto, defectos JSON, termino_vetado NULL, creado_en)`; endpoint `GET /trabajos/{trabajo_id}/intentos -> list[IntentoDescartadoSalida]` con `numero, texto, defectos: list[{codigo, cita}], termino_vetado`.

- [ ] **Paso 1: test rojo.**

```python
async def test_un_capitulo_escalado_deja_sus_tres_intentos_con_sus_defectos(cliente, sesion, ...):
    # Preparado para que la puerta rechace siempre con EST-02 (el mismo doble que
    # usa test_ciclo.py::test_el_rechazo_deja_el_trabajo_escalado_y_con_los_dos_intentos_gastados).
    trabajo = await lanzar_capitulo_que_escala(cliente)

    intentos = cliente.get(f"/trabajos/{trabajo.id}/intentos").json()

    assert [i["numero"] for i in intentos] == [1, 2, 3]
    assert all(i["texto"] for i in intentos)
    assert all("EST-02" in [d["codigo"] for d in i["defectos"]] for i in intentos)


async def test_la_evidencia_no_es_vigente_y_no_contamina_el_capitulo_siguiente(sesion, ...):
    # R-7 sigue en pie: version_texto de ese run_id queda a cero.
    ...
    assert await contar(sesion, VersionTexto, run_id=trabajo.run_id) == 0
```

- [ ] **Paso 2: rojo** (404 en el endpoint; tabla inexistente).
- [ ] **Paso 3: modelo, migración** (`upgrade`/`downgrade`/`upgrade` en limpio) **y escritura** en `ciclo.py` justo antes de `_retirar_lo_descartado`, a partir de `escritura.intentos` (ya trae `texto`, `resultado.bloqueantes` y `termino_vetado`). En el caso aprobado también se guardan los intentos previos rechazados, si los hubo: son la misma evidencia y el *tuning* la necesita.
- [ ] **Paso 4: el test viejo** `test_ciclo.py::test_un_capitulo_rechazado_no_deja_rastro_en_ningun_almacen` **sigue verde sin tocarlo**: no cuenta `intento_descartado` entre los almacenes, y es correcto —la evidencia no es un almacén de lectura—. Se añade una línea al docstring diciendo por qué.
- [ ] **Paso 5: endpoint** sin lógica (`CLAUDE.md` §6), servicio en `escritura/service.py`, y `openapi.json` regenerado con el comando que dejó el plan 4 (`json.dumps(crear_app().openapi(), indent=1, ensure_ascii=False)`).
- [ ] **Paso 6: el juicio al escalar.** Test rojo: el `Escritura` escalado trae `juicio` no nulo cuando hay Crítico. Una línea en `service.py:500-508`. Verde.
- [ ] **Paso 7: `causa_fallo` cabe.** `String(60)` y el motivo mide ~63: test rojo que lee el motivo tras un `commit` real y **no truncado**; migración a `String(200)`. SQLite no lo impone hoy, pero la columna miente.
- [ ] **Paso 8: commits** (modelo+migración+escritura; endpoint+openapi; juicio; causa_fallo).

---

## Tarea 5 · Medir la sobrecarga del CLI

**Qué entrega:** **una cifra medida** de cuántos tokens añade cada llamada por encima del prompt que contamos, que resuelve la contradicción de P-21 (~1.800 frente a 33.000–49.000) y que T6 necesita para reservar turno.

**Files:**
- Create: `src/backend/scripts/medir_sobrecarga.py`
- Modify: `src/backend/app/commons/jobs/turnos.py` (constante `SOBRECARGA_POR_LLAMADA`, con el valor medido y la fecha)
- Modify: `specs/problemas-abiertos.md` (P-21 con la medida) y `docs/verification.md` (el número y cómo se midió)
- Test: `src/backend/app/commons/jobs/tests/test_turnos.py` (la constante existe y es positiva; no mide nada)

- [ ] **Paso 1: script.** Tres llamadas reales con prompts de ~50, ~2.000 y ~8.000 tokens contados con `ContadorTiktoken`; para cada una imprime `contados`, `input_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens` y `sobrecarga = (input + cache_read + cache_creation) - contados`. Dos rondas seguidas, para ver el efecto de la caché.
- [ ] **Paso 2: ejecutarlo** (unos minutos, gasta poca cuota). Anotar la tabla en `docs/verification.md` y en P-21.
- [ ] **Paso 3: test rojo** de que `SOBRECARGA_POR_LLAMADA` existe y es `> 0`; constante con el **máximo observado** redondeado hacia arriba y un comentario con la fecha y el fichero donde está la medida. Verde.
- [ ] **Paso 4: commit.**

*Si la medida da ~33.000–49.000:* T6 sigue siendo posible —dos jueces con paquetes de ~10.000 más dos sobrecargas caben bajo 100.000—, pero el techo pasa a ser la restricción real y hay que decirlo en `CLAUDE.md` §4.1. Ese cambio de documento **lo firma una persona**; la tarea lo propone y para.

---

## Tarea 6 · Continuista y Crítico en paralelo, contados

**Qué entrega:** en cada intento, el Crítico **arranca a la vez** que el Continuista, dentro del techo concurrente, con sus tokens contados. Ahorro esperado: una llamada de juez por intento (estimado 10–15 minutos por novela; **se mide en la corrida**).

**Por qué es seguro:** el Crítico **no usa** la salida del Continuista (`service.py:307-315`) y **no decide** nada (`RF-JUZ-06`): su resultado no entra en `aprobado`. La puerta G1a sigue esperando al Continuista, como hoy.

**Files:**
- Modify: `src/backend/app/features/escritura/service.py:437-484`
- Modify: `src/backend/app/features/escritura/tests/test_observabilidad_del_ciclo.py` (el orden de spans deja de ser estrictamente secuencial: se comprueba por **inicio**, no por fin)
- Test: `src/backend/app/features/escritura/tests/test_jueces_en_paralelo.py`

**Interfaces:**
- Consumes: `PresupuestoConcurrente.turno(tokens, *, espera_maxima)` (`commons/jobs/turnos.py:99-117`); `SOBRECARGA_POR_LLAMADA` (T5); `render_critico` y `ContadorDeTokens.contar`.

- [ ] **Paso 1: test rojo, el solape.** Dobles de Continuista y Crítico que registran `inicio` y `fin` con un `asyncio.Event`; el Continuista no termina hasta que el Crítico ha empezado. Con el código de hoy el test **se cuelga**: se le pone `asyncio.wait_for(..., 2)` y el rojo es `TimeoutError`.
- [ ] **Paso 2: test rojo, sin interbloqueo (Review Focus 4).** Presupuesto con techo tan pequeño que el paquete ya en vuelo más el Crítico no caben: **el Crítico corre después del Continuista, en serie, sin esperar turno** (se pide con `espera_maxima=0`, y `TiempoAgotado` significa «en serie»). El test comprueba que termina y que el orden es secuencial.
- [ ] **Paso 3: implementación.**

```python
tokens_critico = contador.contar(render_critico(...)) + SOBRECARGA_POR_LLAMADA
tarea_critico = None
try:
    turno = presupuesto.turno(tokens_critico, espera_maxima=0, paso="critico en paralelo")
    await turno.__aenter__()
    tarea_critico = asyncio.create_task(_juzgar(critico, str(version.id), texto, observacion))
except TiempoAgotado:
    turno = None  # no cabe ahora: se juzga despues, como hasta hoy

# ... continuista y puerta G1a, sin cambios ...

juicio = await tarea_critico if tarea_critico else await _juzgar(critico, str(version.id), texto, observacion)
if turno is not None:
    await turno.__aexit__(None, None, None)
```

  *(En el código real, con `contextlib.AsyncExitStack` en vez de `__aenter__` a mano; aquí se ve la forma.)* **`escribir_capitulo` recibe `presupuesto` como parámetro nuevo** desde `ciclo._escribir`, que ya lo tiene.
- [ ] **Paso 4: verde** de los dos tests; ajustar `test_observabilidad_del_ciclo.py` para que compare el orden de **inicio** de los spans, y decir en el test por qué cambió.
- [ ] **Paso 5: una excepción del Crítico en paralelo no puede tumbar el intento** (hoy tampoco lo tumba porque no decide): test rojo con un Crítico que lanza `SalidaMalFormada`; el capítulo se aprueba igual y el span lo registra. Verde.
- [ ] **Paso 6: commit.**

---

## Tarea 7 · Langfuse: que las trazas sirvan para el *tuning*

**Qué entrega:** P-22.1–3 cerrados. El 22.4 queda fuera por D-5.

**Files:**
- Modify: `src/backend/app/commons/observabilidad/langfuse.py` (`puntuar` con criterio; `cerrar()` que hace `flush`)
- Modify: `src/backend/app/commons/observabilidad/trazas.py` (`Span.prompt(id, version, hash)`)
- Modify: `src/backend/app/commons/observabilidad/dobles.py`, `blindaje.py` (el método nuevo)
- Modify: `src/backend/app/commons/observabilidad/__init__.py` (`obtener_observador` cacheado: **un** cliente por proceso)
- Modify: `src/backend/app/main.py` (`lifespan`: cierra el observador al apagar)
- Modify: `features/escena/agents.py`, `outline/agents.py`, `canon/agents.py` (`PROMPT_ID`, `PROMPT_VERSION`, `HASH_DE_PLANTILLA` que hoy no tienen)
- Modify: el cableado de cada rol en `escritura/service.py`, `escritura/ciclo.py`, `outline/service.py` (llaman a `span.prompt(...)`)
- Test: `commons/observabilidad/tests/test_langfuse.py`, `test_blindaje.py`, `escritura/tests/test_observabilidad_del_ciclo.py`

- [ ] **Paso 1: criterio, test rojo.** Con un `Langfuse` falso inyectado, `puntuar(Puntuacion(nombre="juez_con_rubrica", valor=4, criterio="voz"))` llama a `score(name="juez_con_rubrica.voz", ...)`. Rojo; implementar `name = f"{p.nombre}.{p.criterio}" if p.criterio else p.nombre`; verde.
- [ ] **Paso 2: `flush`, test rojo.** El `lifespan` de `crear_app` al salir llama a `cerrar()` del observador, y `cerrar()` llama a `flush()` del cliente si se abrió. **Review Focus 5:** si `flush` lanza, el apagado termina igual (va por el blindaje, y el contador de fallos sube). Rojo; implementar `obtener_observador` con `@lru_cache(maxsize=1)` —hoy crea un cliente por petición—, `cerrar()` en `ObservadorLangfuse` y en el blindado; verde. Los tests que sobrescriben `obtener_observador` (el `conftest` ya lo hace) siguen igual.
- [ ] **Paso 3: prompt versionado, test rojo.** En `test_observabilidad_del_ciclo.py`, cada span de rol con modelo (`planificador`, `escritor`, `continuista`, `critico`, `extractor`) lleva `prompt == (id, version, hash)` con el hash de **la plantilla que de verdad se envió**. Y el de `arquitecto` en `test_observabilidad_del_outline.py`. Rojo.
- [ ] **Paso 4: implementar** `Span.prompt(...)` (protocolo, doble en memoria, blindado, y en Langfuse `update(metadata={"prompt_id":…, "prompt_version":…, "prompt_hash":…})`), las constantes que faltan en Planificador, Arquitecto y Extractor (`hash_de_plantilla(PLANTILLA)` como el Continuista), y la llamada en cada sitio del cableado. Verde.
- [ ] **Paso 5: quitar la pieza y ver caer** (RELEVO, «los tests con el nombre correcto que no pueden fallar»): comentar la llamada a `span.prompt` en el Escritor y confirmar que el test de T7 se pone rojo; restaurar.
- [ ] **Paso 6: commits** (criterio; flush + cliente único; prompt versionado).

---

## Lo que esta fase deja cerrado

| Problema | Cómo se cierra |
| --- | --- |
| P-19 | T1 lo mide; T2–T3 lo resuelven si la cuenta anonimiza |
| P-20 | T4 |
| P-21 | T5 mide, T6 paraleliza |
| P-22.1–3 | T7 |
| P-26 (`PLANTILLA_V1` que carga v2) | T2 paso 9 |

## Lo que esta fase NO hace, y no es un olvido

- **La corrida real no es una tarea.** Es operación, con la cuenta nueva, en cuanto T4, T6 y T7 estén en verde (y T2–T3 si T1 dice que hacen falta). Su resultado alimenta el plan 6 (evals) y el registro de iteraciones.
- **P-18 (tarifa de la caché):** sigue siendo una decisión de tarifa de `maujimenez4`.
- **P-22.4 (Entrevistador en Langfuse):** D-5.
- **`python-dotenv`** para que el backend lea el `.env` solo: dependencia nueva, pregunta aparte (`CLAUDE.md` §3.7).
- **Excepciones de los jueces dentro del bucle** (`SalidaMalFormada` del Continuista hoy tumba el trabajo sin estado final): se anota en `problemas-abiertos.md` si T4 lo confirma; no se arregla aquí salvo el caso del Crítico en paralelo (T6 paso 5).

## Desviaciones

| Tarea | Qué se desvió | Por qué |
| --- | --- | --- |
| **T1** | La sonda se hizo **dos veces**: con el nombre real y con un nombre inventado («Oriana», pasado como argumento) | La primera confirmó el anonimizado; faltaba saber si el marcador lo esquivaría. La segunda dio **0 apariciones y 13 marcas**: la cuenta de trabajo anonimiza cualquier nombre de persona |
| **T2, T3** | **No se ejecutan** | D-1 decía «solo si la cuenta anonimiza». Anonimiza, pero **también anonimiza el marcador**, así que T2–T3 no resolverían P-19. La causa son las instrucciones de la organización de la cuenta; la solución es generar con una cuenta sin ellas. Quedan escritas por si una cuenta futura anonimizara solo nombres reales. Ver P-19 |
