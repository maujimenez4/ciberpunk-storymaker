# StoryMaker — Especificación

Documento ejecutable. Quien lea solo esto debe poder implementar el sistema.

Todo lo que sigue está derivado del diagrama de
[`docs/architecture/agent-loop.mmd`](architecture/agent-loop.mmd), que es la fuente
única del flujo. Donde esta spec se aparta del diagrama o de una invariante, lo dice en
el [§16](#16-desviaciones-respecto-al-diagrama-y-a-las-invariantes); no hay desviaciones
fuera de esa sección.

**Convenciones.** Prosa y documentación en español. Identificadores, claves de
configuración, nombres de fichero y el diagrama en inglés. Identificadores en kebab-case
(`scene-writer`, nunca `sceneWriter`). Las rutas que empiezan por `novels/<slug>/` se
abrevian como `<novel>/`.

---

## 0. Las nueve invariantes

El diseño entero se apoya en ellas. Cada sección señala cuál hace cumplir.

1. **Una sola fuente de verdad.** La biblia narrativa contiene el canon. Si no está ahí,
   no es canon.
2. **Un solo escritor del estado.** Solo `continuity-keeper` escribe en la biblia, y solo
   después de aprobación.
3. **Un solo rol con acceso web.** Solo `researcher`. Los hechos llegan a la prosa
   únicamente por notas con fuente y fecha.
4. **`voice-editor` no añade.** Solo quita y afila.
5. **El contexto se ensambla, no se acumula.** Ningún rol recibe el manuscrito completo.
6. **Todo ciclo tiene tope.** Al agotarse, escala al humano.
7. **Solo `blocker` dispara reescritura.** `warning` y `note` se imprimen en la compuerta.
8. **Markdown es el formato canónico.** PDF y EPUB son derivados regenerables.
9. **Worldbuilding original.** El pack de género codifica convenciones, nunca nombres
   propios ni elementos de obras existentes.

---

## 1. Modelo de ejecución

Una **corrida** toma una novela (`<novel>/brief.md`) y una configuración
(`config/profiles/<perfil>.json`) y avanza el estado en disco hasta producir el
manuscrito. El orquestador recorre el diagrama; cada nodo numerado es una llamada a un
subagente con el sobre de handoff del [§5](#5-contrato-de-handoff).

### 1.1 Arranque — `START` → `BOOT`

`BOOT` comprueba si existe `<novel>/bible/canon.md`.

- **No existe** → fase `setup` ([§1.2](#12-setup--corre-una-vez)).
- **Existe** → fase `chapter-loop`, entrando por `LOAD`. Es también el camino de la
  reanudación ([§10](#10-estado-y-reanudación)).

### 1.2 Setup — corre una vez

| Paso | Nodo | Agente | Produce |
|---|---|---|---|
| 1 | `RES0` | `researcher` (modo `dossier`) | `<novel>/research/dossier.md` |
| 2 | `ARCH` | `plot-architect` | propuesta de actos y escaleta |
| 3 | `PROF` | `character-profiler` | propuesta de fichas de personaje |
| 4 | — | `continuity-keeper` (modo `seed`) | `<novel>/bible/**` inicial |

El paso 4 no es una caja del diagrama. Es la escritura inicial de la biblia, y la
invariante 2 exige que la haga `continuity-keeper`. Ver
[§16.1](#161-el-paso-seed-no-está-en-el-diagrama).

Al terminar el setup, el orquestador hace un commit `setup: bible seed` y entra en
`LOAD`.

### 1.3 Bucle de capítulo

`LOAD` ensambla el contexto del turno —biblia, resúmenes de capítulos previos, hilos
abiertos, la entrada de escaleta del capítulo actual— y **nunca** el manuscrito completo
(invariante 5). Los artefactos grandes viajan por ruta, no inline.

```
LOAD → BEAT → GAP ⇄ RES1 → WRITE → VOICE → {VAL1 ∥ VAL2} → REPORT → BLOCK → GATE → COMMIT → MORE
```

- `BEAT` (`beat-planner`) produce meta, conflicto, giro y gancho, y declara sus lagunas
  de investigación.
- `GAP` mira los `requests[kind="research"]` de la respuesta de `BEAT`. Si hay y la
  investigación está activa, llama a `RES1` (`researcher`, modo `notes`) y vuelve a
  `GAP`. Ciclo acotado por `limits.maxResearchRounds` ([§7](#7-ciclos-acotados)).
- `WRITE` (`scene-writer`) escribe prosa y nada más. No busca (invariante 3).
- `VOICE` (`voice-editor`) recorta y afila. No añade (invariante 4).
- `VAL1` (`continuity-keeper`, modo `validate`) y `VAL2` (`technical-verifier`) corren
  **en paralelo**. Es la única paralelización del diseño, y es legítima porque ninguno de
  los dos escribe.
- `REPORT` funde los dos informes en un reporte único ([§6](#6-reporte-de-incidencias)).
- `BLOCK` mira si hay incidencias `blocker`. Solo `blocker` reentra en `WRITE`
  (invariante 7).
- `GATE` lee `supervision.approvalMode` y decide si cede el control al humano.
- `COMMIT` (`continuity-keeper`, modo `commit`) escribe biblia y resumen; el orquestador
  hace el commit de git.
- `MORE` avanza al siguiente capítulo o sale a `COMP`.

### 1.4 Cierre

`COMP` (`compiler`) ensambla `<novel>/out/manuscript.md`. `EXPORT` es mecánico: lee
`output.outputFormats` y deriva PDF y EPUB del Markdown. No hay agente en `EXPORT` porque
no hay decisión que tomar (invariante 8).

---

## 2. Inventario de agentes

Diez roles. El orquestador no aparece como caja en el diagrama porque *es* el bucle, pero
cuenta como el décimo y es el principal.

| # | id | Nodo(s) | Escribe biblia | Acceso web |
|---|---|---|---|---|
| — | `orchestrator` | el bucle entero | no | no |
| 1 | `researcher` | `RES0`, `RES1` | no | **yes** |
| 2 | `plot-architect` | `ARCH` | no | no |
| 3 | `character-profiler` | `PROF` | no | no |
| 4 | `beat-planner` | `BEAT` | no | no |
| 5 | `scene-writer` | `WRITE` | no | no |
| 6 | `voice-editor` | `VOICE` | no | no |
| 7 | `continuity-keeper` | `VAL1`, `COMMIT`, seed | **yes** | no |
| 8 | `technical-verifier` | `VAL2` | no | no |
| 9 | `compiler` | `COMP` | no | no |

Un solo `yes` por columna. Las invariantes 2 y 3 son esta tabla.

### 2.1 Detalle por rol

Cada bloque lista: responsabilidad · lee · escribe · prohibido.

**`orchestrator`**
- Recorre el diagrama, ensambla el contexto de cada turno, cuenta los ciclos, aplica la
  configuración, presenta la compuerta en la CLI y hace los commits de git.
- Lee: `config/**`, `<novel>/**`, historial de git.
- Escribe: `<novel>/run-state.json`, `<novel>/notes/ch<NN>-issues.json` (el reporte
  fundido), commits de git.
- Prohibido: generar prosa, decidir canon, tocar `<novel>/bible/**`.

**`researcher`** — *único rol con acceso web (invariante 3)*
- Modo `dossier`: investigación temática amplia a partir del brief. Modo `notes`: notas
  puntuales que responden a las lagunas declaradas por `beat-planner`.
- Lee: `<novel>/brief.md`, el pack de género, las preguntas del sobre.
- Escribe: `<novel>/research/dossier.md`, `<novel>/research/ch<NN>-notes.md`.
- Prohibido: escribir prosa de la novela, proponer trama, emitir un hecho sin fuente y
  fecha.

**`plot-architect`**
- Divide la novela en actos y produce la escaleta capítulo a capítulo, con la promesa
  narrativa de cada uno.
- Lee: `<novel>/brief.md`, `<novel>/research/dossier.md`, el pack de género,
  `scope.chapters` y `scope.acts`.
- Escribe: nada en disco. Devuelve la escaleta como propuesta en el sobre.
- Prohibido: escribir en `bible/`, escribir prosa, inventar personajes con ficha (eso es
  del `character-profiler`).

**`character-profiler`**
- Fichas de personaje: deseo, herida, voz, límites morales, arco previsto.
- Lee: brief, dossier, escaleta del paso anterior.
- Escribe: nada en disco. Devuelve las fichas como propuesta en el sobre.
- Prohibido: escribir en `bible/`, alterar la escaleta, escribir prosa.

**`beat-planner`**
- Para el capítulo `N`: meta, conflicto, giro y gancho. Declara qué hechos necesita
  verificados antes de escribir.
- Lee: contexto ensamblado por `LOAD` (biblia, resúmenes previos, hilos abiertos, entrada
  de escaleta del capítulo `N`).
- Escribe: `<novel>/notes/ch<NN>-beats.md`.
- Prohibido: escribir prosa, buscar en la web (declara la laguna; no la resuelve).

**`scene-writer`**
- Convierte el plan de beats en prosa. Es el único que escribe texto nuevo de la novela.
- Lee: contexto ensamblado, `<novel>/notes/ch<NN>-beats.md`,
  `<novel>/research/ch<NN>-notes.md`, pack de género, notas del humano si la reescritura
  viene de `DEC`.
- Escribe: `<novel>/chapters/ch<NN>.draft.md`.
- Prohibido: buscar en la web, afirmar hechos técnicos que no estén en las notas con
  fuente, tocar `bible/`, usar términos de la lista prohibida del pack de género.

**`voice-editor`**
- Ritmo, registro y cortes. **Solo quita y afila** (invariante 4).
- Lee: `<novel>/chapters/ch<NN>.draft.md`, skill de registro, pack de género.
- Escribe: `<novel>/chapters/ch<NN>.md`.
- Prohibido: **añadir** contenido —hechos, diálogo, detalle sensorial nuevo, nombres—. Si
  pudiera añadir, metería hechos después de que los validadores ya corrieron. El
  orquestador comprueba que el recuento de palabras no sube.

**`continuity-keeper`** — *único escritor de la biblia (invariante 2)*
- Modo `seed`: escritura inicial de la biblia desde las propuestas de `ARCH` y `PROF`.
  Modo `validate`: contrasta el capítulo contra el canon. Modo `commit`: actualiza la
  biblia y escribe el resumen del capítulo aprobado.
- Lee: `<novel>/bible/**`, el capítulo, el plan de beats.
- Escribe: `<novel>/bible/**` —y nadie más lo hace—.
- Prohibido: escribir prosa de la novela, buscar en la web, escribir en `bible/` antes de
  la aprobación (en modo `validate` su salida es solo un informe).

**`technical-verifier`**
- Contrasta las afirmaciones técnicas de la prosa contra las notas con fuente. Esta
  verificación significa algo precisamente porque `scene-writer` no busca: cualquier
  hecho que no esté en las notas es un hecho inventado.
- Lee: `<novel>/chapters/ch<NN>.md`, `<novel>/research/ch<NN>-notes.md`,
  `<novel>/research/dossier.md`, lista de términos prohibidos.
- Escribe: nada en disco. Devuelve su informe en el sobre.
- Prohibido: buscar en la web (si le falta una fuente, emite `warning`, no la busca),
  corregir el texto, juzgar continuidad narrativa.

**`compiler`**
- Ensambla `manuscript.md` en orden, con portada, cortes de acto y títulos de capítulo.
- Lee: `<novel>/chapters/ch*.md` (solo los aprobados), `<novel>/bible/outline.md`.
- Escribe: `<novel>/out/manuscript.md`.
- Prohibido: reescribir prosa, corregir continuidad, incluir capítulos no aprobados o
  archivados.

---

## 3. Modos de agente

Dos agentes tienen más de un modo. Son **el mismo agente y el mismo prompt**, con una
sección de modo distinta; no son roles separados. Sin esto, el inventario aparentaría
tener doce roles y las invariantes 2 y 3 dejarían de ser comprobables por conteo.

| Agente | Modo | Nodo | Diferencia |
|---|---|---|---|
| `researcher` | `dossier` | `RES0` | Amplio, una vez, a partir del brief |
| `researcher` | `notes` | `RES1` | Puntual, por capítulo, responde preguntas concretas |
| `continuity-keeper` | `seed` | — | Escritura inicial de la biblia |
| `continuity-keeper` | `validate` | `VAL1` | Solo lee y emite informe |
| `continuity-keeper` | `commit` | `COMMIT` | Escribe biblia y resumen, tras aprobación |

El modo viaja en `call.mode` del sobre.

---

## 4. Inventario de skills

**Regla de admisión: una skill necesita dos o más consumidores.** Si algo lo usa un solo
agente, va en su prompt. La distinción es entre *quién es* un agente (su prompt) y un
*procedimiento compartido* (una skill). Es fácil de dejar podrida —todo acaba duplicado
en diez prompts— y por eso la regla es numérica.

| Skill | Qué define | La cargan |
|---|---|---|
| `handoff-envelope` | Formato del sobre de petición y respuesta ([§5](#5-contrato-de-handoff)) | los diez |
| `bible-schema` | Ficheros de la biblia, secciones y cómo se cita una entrada de canon | `continuity-keeper`, `plot-architect`, `character-profiler`, `beat-planner`, `scene-writer`, `compiler` |
| `sourced-notes-format` | Forma de una nota con fuente: afirmación, fuente, fecha de consulta, confianza | `researcher` (escribe), `scene-writer` (lee), `technical-verifier` (verifica) |
| `issue-report` | Formato y semántica de severidad ([§6](#6-reporte-de-incidencias)) | `continuity-keeper`, `technical-verifier`, `orchestrator` |
| `neo-noir-register` | Registro: qué frase pertenece a la novela y cuál no | `scene-writer`, `voice-editor` |
| `genre-pack-loader` | Cómo se lee un pack de `genres/<id>/` y cómo se comprueba su lista de términos prohibidos (invariante 9) | `scene-writer`, `voice-editor`, `continuity-keeper`, `technical-verifier` |

### 4.1 Qué deliberadamente *no* es skill

| Conocimiento | Único consumidor |
|---|---|
| Estructura meta · conflicto · giro · gancho | `beat-planner` |
| Estructura de actos y curva de tensión | `plot-architect` |
| Protocolo de búsqueda web y criterio de fuente | `researcher` |
| Plantilla de ficha de personaje | `character-profiler` |
| Ensamblado del manuscrito y portada | `compiler` |
| Ensamblado de contexto y conteo de ciclos | `orchestrator` |

Ubicación: `agents/<id>.md` y `skills/<id>.md`. El contenido de esos ficheros es
comportamiento y llega en el commit 3.

---

## 5. Contrato de handoff

Un único sobre para las diez llamadas. Sin esto, diez prompts inventan diez formatos y el
desastre aparece al integrar.

### 5.1 Petición

```json
{
  "envelope": "storymaker/handoff@1",
  "call": {
    "id": "ch03-a2-scene-writer",
    "agent": "scene-writer",
    "mode": "default",
    "issuedAt": "2026-09-16T10:12:03Z"
  },
  "run": {
    "novel": "neon-smoke",
    "profile": "smoke-3ch",
    "genre": "cyberpunk-thriller",
    "chapter": 3,
    "act": 1,
    "attempt": 2,
    "dryRun": false
  },
  "skills": ["handoff-envelope", "bible-schema", "sourced-notes-format", "neo-noir-register", "genre-pack-loader"],
  "inputs": {
    "paths": {
      "beats": "novels/neon-smoke/notes/ch03-beats.md",
      "notes": "novels/neon-smoke/research/ch03-notes.md",
      "bible": "novels/neon-smoke/bible/",
      "summaries": [
        "novels/neon-smoke/bible/summaries/ch01.md",
        "novels/neon-smoke/bible/summaries/ch02.md"
      ]
    },
    "values": {
      "openThreads": ["el trato del muelle sigue sin cerrar"],
      "humanNotes": null,
      "blockers": ["ck-003"]
    }
  },
  "limits": { "maxWords": 455, "maxSearches": 0 },
  "output": { "path": "novels/neon-smoke/chapters/ch03.draft.md" }
}
```

**Reglas del sobre.**

- `inputs.paths` lleva rutas; `inputs.values` lleva escalares y listas cortas. **La prosa
  nunca viaja inline en el sobre**: el manuscrito no cabe y no debe caber (invariante 5).
- Como ningún agente tiene herramienta de lectura de ficheros ([§17](#17-el-harness)), es
  **el orquestador quien resuelve esas rutas** e inserta su contenido en el mensaje que
  envía. La invariante 5 se mantiene porque solo se resuelven las rutas listadas en el
  sobre, nunca el manuscrito: el sobre es el límite de lo que un turno puede ver.
- `limits.maxSearches` es `0` para los nueve agentes que no son `researcher`, y la
  implementación además no les da la herramienta
  ([§14](#14-criterios-de-aceptación), criterio 3).
- `skills` es la lista literal que el agente carga. Si una skill no está en la lista, el
  agente no la tiene.

### 5.2 Respuesta

```json
{
  "envelope": "storymaker/handoff@1",
  "call": {
    "id": "ch03-a2-scene-writer",
    "agent": "scene-writer",
    "completedAt": "2026-09-16T10:13:41Z"
  },
  "status": "ok",
  "artifacts": [
    { "role": "prose", "path": "novels/neon-smoke/chapters/ch03.draft.md", "words": 412 }
  ],
  "issues": [],
  "requests": [],
  "proposals": null,
  "usage": { "inputTokens": 8140, "outputTokens": 1290, "searches": 0, "estimatedUsd": 0.11 }
}
```

`status` toma uno de: `ok`, `needs-research`, `blocked`, `failed`.

| Campo | Lo usa |
|---|---|
| `artifacts` | El orquestador, para encadenar rutas al siguiente sobre |
| `issues` | `VAL1` y `VAL2`; el orquestador los funde en `REPORT` |
| `requests` | `BEAT`, para declarar lagunas; lo lee `GAP` |
| `proposals` | `ARCH` y `PROF`; lo consume `continuity-keeper` en modo `seed` |
| `usage` | El orquestador, para los topes de `budget` |

### 5.3 Qué recibe y devuelve cada agente

| Agente | `inputs` principales | Devuelve |
|---|---|---|
| `researcher` (`dossier`) | brief, pack de género | `artifacts[dossier]` |
| `researcher` (`notes`) | preguntas de `requests`, dossier | `artifacts[notes]` |
| `plot-architect` | brief, dossier, `scope.chapters`, `scope.acts` | `proposals.outline` |
| `character-profiler` | brief, dossier, `proposals.outline` | `proposals.characters` |
| `continuity-keeper` (`seed`) | `proposals.outline`, `proposals.characters`, dossier | `artifacts[bible]` |
| `beat-planner` | contexto ensamblado, entrada de escaleta | `artifacts[beats]`, `requests[research]` |
| `scene-writer` | beats, notas, biblia, resúmenes, `humanNotes`, `blockers` | `artifacts[prose]` |
| `voice-editor` | borrador | `artifacts[prose]` |
| `continuity-keeper` (`validate`) | capítulo, biblia, beats | `issues` |
| `technical-verifier` | capítulo, notas, dossier, términos prohibidos | `issues` |
| `continuity-keeper` (`commit`) | capítulo aprobado, biblia, beats | `artifacts[bible, summary]` |
| `compiler` | capítulos aprobados, escaleta | `artifacts[manuscript]` |

---

## 6. Reporte de incidencias

`REPORT` funde los `issues` de `VAL1` y `VAL2` en `<novel>/notes/ch<NN>-issues.json`, sin
reordenar ni reinterpretar.

```json
{
  "report": "storymaker/issue-report@1",
  "novel": "neon-smoke",
  "chapter": 3,
  "attempt": 2,
  "issues": [
    {
      "id": "ck-003",
      "source": "continuity-keeper",
      "severity": "blocker",
      "kind": "canon-conflict",
      "where": "ch03 ¶4",
      "claim": "El personaje entra en el edificio con su propia credencial.",
      "canon": "bible/characters.md#credenciales-revocadas",
      "fix": "Necesita una credencial prestada o forzar la entrada."
    },
    {
      "id": "tv-001",
      "source": "technical-verifier",
      "severity": "warning",
      "kind": "unsourced-claim",
      "where": "ch03 ¶7",
      "claim": "La latencia del enlace es de cuatro milisegundos.",
      "canon": null,
      "fix": "Ninguna nota con fuente lo respalda. O se quita la cifra, o se pide nota."
    }
  ],
  "counts": { "blocker": 1, "warning": 1, "note": 0 }
}
```

### 6.1 Semántica de severidad (invariante 7)

| Severidad | Qué significa | Qué provoca |
|---|---|---|
| `blocker` | El capítulo contradice el canon, afirma de forma sustantiva un hecho técnico sin nota que lo respalde, o usa un término prohibido. | Reentra en `WRITE` mientras queden reescrituras. |
| `warning` | Debilita el texto, pero no lo hace falso ni incoherente. | Se acumula y se imprime en `GATE`. |
| `note` | Observación de oficio. | Se acumula y se imprime en `GATE`. |

Solo `blocker` dispara reescritura. Si toda observación forzara reintento, se gastarían
los tres intentos en comas.

### 6.2 Tipos por emisor

| `source` | `kind` posibles |
|---|---|
| `continuity-keeper` | `canon-conflict`, `timeline-conflict`, `character-drift`, `thread-dropped` |
| `technical-verifier` | `unsourced-claim`, `contradicts-note`, `stale-source`, `banned-term` |

`banned-term` es siempre `blocker` (invariante 9). `character-drift` es `blocker` cuando
contradice una ficha, y `warning` cuando solo la tensiona.

---

## 7. Ciclos acotados

El diagrama tiene tres ciclos. Solo uno lleva número dibujado; los tres van acotados
(invariante 6). Al agotarse, **ninguno sigue intentando: escala al humano.**

| Ciclo | Nodos | Clave | Al agotarse |
|---|---|---|---|
| Investigación | `GAP` ⇄ `RES1` | `limits.maxResearchRounds` | Las lagunas sin resolver pasan a `WRITE` como restricción explícita («no afirmes nada sobre X») y se emite un `warning` que se verá en `GATE`. |
| Reescritura | `BLOCK` → `WRITE` | `limits.maxRewrites` | `FLAG`: el capítulo queda marcado como no resuelto y **fuerza compuerta humana**, sea cual sea `approvalMode`. |
| Revisión humana | `DEC` → `WRITE` | `limits.maxHumanRevisions` | Se presenta al humano sin la opción `revise`: quedan `approve` y `rollback`. |

El contador de reescrituras **se reinicia** cuando la reentrada en `WRITE` viene de `DEC`
(notas del humano) y no de `BLOCK`. Son dos ciclos distintos con dos causas distintas; si
compartieran contador, tres notas del humano podrían chocar contra un presupuesto ya
gastado por los validadores. Ver
[§16.2](#162-el-contador-de-reescrituras-se-reinicia-tras-notas-del-humano).

---

## 8. Inputs

El usuario no conversa con el sistema: lo configura y lo lanza. Escribe a mano **dos
ficheros y solo dos**.

### 8.1 `novels/<slug>/brief.md`

Markdown con estas secciones, en este orden. Las seis primeras son obligatorias.

```markdown
# <título provisional>

## Premisa
Dos o tres frases. El motor de la historia, no su resumen.

## Protagonista
Quién es, qué quiere, qué le impide conseguirlo.

## Antagonismo
La fuerza opuesta. Puede ser una persona, una institución o una condición.

## Mundo
Reglas del entorno que la novela no puede contradecir.

## Tono y registro
Referencias de registro, no de obra. Invariante 9.

## Restricciones
Lo que la novela no debe hacer. Una línea por restricción.

## Fuera de alcance
Opcional. Temas que el researcher no debe investigar.
```

El brief alimenta a `RES0` y, a través del dossier, a `ARCH` y `PROF`. Se escribe una vez
por novela y no se vuelve a tocar: a partir del seed, el canon vive en la biblia
(invariante 1).

### 8.2 El perfil de corrida

`config/profiles/<perfil>.json`. Ver [§12](#12-configuración).

---

## 9. Outputs

Cada fichero, con su ruta, quién lo escribe y en qué nodo del diagrama aparece.

| Ruta | Escribe | Aparece en |
|---|---|---|
| `<novel>/research/dossier.md` | `researcher` | `RES0`, una vez |
| `<novel>/bible/canon.md` | `continuity-keeper` | seed; su existencia es lo que decide `BOOT` |
| `<novel>/bible/world.md` | `continuity-keeper` | seed, actualizado en `COMMIT` |
| `<novel>/bible/characters.md` | `continuity-keeper` | seed, actualizado en `COMMIT` |
| `<novel>/bible/outline.md` | `continuity-keeper` | seed; se reescribe solo tras `ROLL` |
| `<novel>/bible/timeline.md` | `continuity-keeper` | `COMMIT` |
| `<novel>/bible/threads.md` | `continuity-keeper` | `COMMIT` |
| `<novel>/bible/summaries/ch<NN>.md` | `continuity-keeper` | `COMMIT` |
| `<novel>/notes/ch<NN>-beats.md` | `beat-planner` | `BEAT` |
| `<novel>/notes/ch<NN>-issues.json` | `orchestrator` | `REPORT` |
| `<novel>/research/ch<NN>-notes.md` | `researcher` | `RES1`, si hay lagunas |
| `<novel>/chapters/ch<NN>.draft.md` | `scene-writer` | `WRITE` |
| `<novel>/chapters/ch<NN>.md` | `voice-editor` | `VOICE` |
| `<novel>/run-state.json` | `orchestrator` | cada transición de nodo |
| `<novel>/run-log.jsonl` | `orchestrator` | una línea por llamada; sin prosa, solo rutas y uso |
| `<novel>/out/manuscript.md` | `compiler` | `COMP`, al terminar los capítulos |
| `<novel>/out/manuscript.pdf` | export mecánico | `EXPORT`, si está en `outputFormats` |
| `<novel>/out/manuscript.epub` | export mecánico | `EXPORT`, si está en `outputFormats` |
| `<novel>/attic/<timestamp>/` | `orchestrator` | `ROLL` ([§11](#11-rollback)) |

**Todo lo que cuelga de `<novel>/bible/` lo escribe `continuity-keeper` y nadie más.** La
invariante 2 se comprueba mirando un directorio, no leyendo diez prompts.

### 9.1 Commits de git

Un commit por capítulo aprobado, hecho por el orquestador en `COMMIT`:

```
ch03: <título del capítulo>

Biblia actualizada: threads.md, timeline.md.
Incidencias abiertas: 1 warning (tv-001).
```

El commit incluye el capítulo, su resumen, la biblia y el reporte de incidencias: el
estado completo de la novela tras ese capítulo. Eso es lo que hace viable `ROLL`:
revertir es un revert, no una reconstrucción.

---

## 10. Estado y reanudación

### 10.1 `run-state.json`

```json
{
  "state": "storymaker/run-state@1",
  "novel": "neon-smoke",
  "profile": "smoke-3ch",
  "phase": "chapter-loop",
  "node": "VOICE",
  "chapter": 3,
  "act": 1,
  "counters": { "researchRounds": 1, "rewrites": 0, "humanRevisions": 0 },
  "lastApprovedChapter": 2,
  "lastApprovedCommit": "9f41c2a",
  "flagged": [],
  "usage": { "inputTokens": 61200, "outputTokens": 9840, "searches": 3, "estimatedUsd": 0.94 },
  "updatedAt": "2026-09-16T10:13:41Z"
}
```

**`run-state.json` es un índice, no la verdad.** La verdad es el historial de git: un
commit por capítulo aprobado. Si el estado y el historial discrepan, gana el historial, y
el orquestador reconstruye el estado desde `lastApprovedCommit`.

### 10.2 Cómo se retoma una corrida interrumpida

1. Leer `run-state.json`; si no existe o está corrupto, reconstruirlo desde el último
   commit `ch<NN>:` del historial.
2. `lastApprovedChapter = K`. Todo lo aprobado hasta `K` **no se regenera nunca**.
3. Descartar el trabajo en vuelo del capítulo `K+1`: borrador, capítulo editado, beats y
   reporte de incidencias. Nada no aprobado es canon (invariante 1), así que nada no
   aprobado merece conservarse.
4. Reentrar por `LOAD` con `chapter = K+1` y los contadores a cero.

La reanudación no tiene camino propio en el diagrama porque no lo necesita: es exactamente
la rama `BOOT -->|yes| LOAD`. Retomar una corrida interrumpida y continuar una novela son
la misma operación.

---

## 11. Rollback

`DEC -->|rollback to chapter K| ROLL` revierte la biblia al estado del commit de `K` e
invalida los capítulos `K+1..N`.

**Decisión: los capítulos invalidados se archivan, no se borran.** Se mueven con `git mv`
a `<novel>/attic/<timestamp>/`, en un commit propio
(`rollback: to ch<K>, archived ch<K+1>..ch<N>`).

Razones:

- El historial de git ya los conserva, pero quien hace rollback normalmente quiere reusar
  un párrafo. Obligarle a un `git show` para eso no aporta nada.
- Sacarlos de `chapters/` garantiza que ni el ensamblado de contexto de `LOAD` ni el
  `compiler` puedan volver a leer texto invalidado. La invariante 1 se mantiene por
  construcción: lo archivado no es canon porque no está donde se lee el canon.
- Archivar es un movimiento y un commit. Es reversible, y es barato.

`attic/` se versiona. No entra nunca en ningún sobre de handoff.

---

## 12. Configuración

Cambiar el comportamiento de una corrida no debe tocar la spec ni los prompts.

### 12.1 Base más overlays

```
config/run.base.json             todas las claves, valores de novela completa
config/profiles/full-novel.json  overlay casi vacío: novela completa ES el caso base
config/profiles/smoke-3ch.json   solo las claves que cambian para la prueba
```

**Merge superficial por sección.** Se recorren las secciones de primer nivel; dentro de
cada una, una clave presente en el overlay reemplaza a la de la base. Los arrays se
reemplazan enteros, no se concatenan. No hay merge recursivo más allá de ese nivel, salvo
en `execution.models`, que se declara explícitamente como mapa fusionable. Las claves
`config`, `profile` y `extends` son metadatos del fichero y no participan en el merge.

Elijo overlays en vez de dos ficheros completos porque el delta entre «prueba pequeña» y
«novela completa» queda visible en el propio fichero, que es justo lo que hay que poder
auditar. El coste es una regla de merge que el harness tiene que implementar, y queda
escrita arriba.

### 12.2 Secciones

| Sección | Qué gobierna |
|---|---|
| `run` | Qué novela, qué género, qué idioma |
| `scope` | Capítulos, actos, extensión |
| `supervision` | `approvalMode` — el nodo `GATE` |
| `validation` | Qué validaciones corren |
| `research` | Si hay web y con qué tope |
| `limits` | Los tres ciclos acotados del [§7](#7-ciclos-acotados) |
| `budget` | Topes de coste y tokens, y qué hacer al superarlos |
| `output` | `outputFormats` — el nodo `EXPORT` |
| `execution` | Modo en seco, modelos, política de rollback |

El salto de prueba a novela completa toca `scope` y `budget`, y poco más. Esa es la razón
del agrupamiento.

### 12.3 Claves

| Clave | Valores | Efecto |
|---|---|---|
| `run.novel` | slug o `null` | Si es `null`, la corrida exige `--novel` y falla sin él. |
| `run.genre` | id de `genres/` | Qué pack cargan las skills de género. |
| `run.language` | código ISO | Idioma de la prosa. |
| `scope.chapters` | entero ≥ 1 | Condición de `MORE`. |
| `scope.acts` | entero ≥ 1 | Dónde cae el corte de acto que consulta `GATE`. |
| `scope.wordsPerChapter` | entero | Objetivo; viaja como `limits.maxWords` en el sobre. |
| `scope.wordsTolerance` | 0–1 | Margen sobre el objetivo. |
| `scope.summaryWindow` | entero ≥ 0 | Cuántos resúmenes previos entran en el contexto. Es lo que impide que el coste por capítulo crezca con el número de capítulos escritos. |
| `supervision.approvalMode` | `every-chapter`, `act-end-or-flagged`, `never` | La decisión de `GATE`. |
| `supervision.presentUnit` | `chapter`, `act` | Qué se imprime en `HUMAN`. |
| `supervision.onFlagged` | `force-gate`, `continue` | `force-gate` hace que `FLAG` interrumpa aunque `approvalMode` sea `never`. |
| `validation.continuity` | bool | Activa `VAL1`. |
| `validation.technical` | bool | Activa `VAL2`. |
| `validation.bannedTerms` | bool | Comprobación de la invariante 9. |
| `validation.runInParallel` | bool | `false` los serializa; el resultado no cambia. |
| `research.enabled` | bool | Si es `false`, `GAP` siempre sale por `no`. |
| `research.maxSearchesSetup` | entero | Tope de búsquedas de `RES0`. |
| `research.maxSearchesPerChapter` | entero | Tope de búsquedas de `RES1` por capítulo. |
| `research.requireSourceAndDate` | bool | Invariante 3. Ponerlo a `false` no está soportado. |
| `limits.maxResearchRounds` | entero | Ciclo `GAP` ⇄ `RES1`. |
| `limits.maxRewrites` | entero | Ciclo `BLOCK` → `WRITE`. El diagrama dibuja 3. |
| `limits.maxHumanRevisions` | entero | Ciclo `DEC` → `WRITE`. |
| `budget.maxUsd` | número | Tope de coste estimado de la corrida. |
| `budget.maxTokens` | entero | Tope de tokens de la corrida. |
| `budget.maxUsdPerCall` | número o ausente | Tope duro por llamada. Acota el daño de un turno que se desmande, que es lo que `budget.maxUsd` no puede hacer ([§15](#15-limitaciones-conocidas), limitación 3). |
| `budget.onExceed` | `pause-at-gate`, `stop-after-chapter`, `warn` | Qué hacer al superarlo. |
| `output.outputFormats` | lista de `markdown`, `pdf`, `epub` | El nodo `EXPORT`. |
| `output.manuscriptPath` | ruta relativa a `<novel>/` | Salida de `COMP`. |
| `execution.dryRun` | bool | Modo en seco ([§12.4](#124-modo-en-seco)). |
| `execution.dryRunInjectBlockerAt` | entero o `null` | Capítulo donde el seco inyecta un `blocker` sintético. |
| `execution.models` | mapa `agente → modelo` | `default` más overrides por agente. |
| `execution.commitPerChapter` | bool | Ponerlo a `false` rompe `ROLL`; existe solo para depurar. |
| `execution.rollbackPolicy` | `archive`, `delete` | Por defecto `archive` ([§11](#11-rollback)). |

`budget.onExceed` en detalle: `pause-at-gate` termina el capítulo en curso y fuerza
compuerta humana; `stop-after-chapter` termina el capítulo, hace su commit y sale; `warn`
solo imprime. Ninguno aborta a mitad de capítulo, porque abortar a mitad deja trabajo
pagado y sin commitear.

### 12.4 Modo en seco

Con `execution.dryRun: true`, el orquestador recorre el bucle completo **sin llamar a
ningún modelo**. Cada nodo de agente escribe un fichero marcador con la forma correcta —el
sobre de respuesta válido, el fichero en su ruta, el front matter esperado— y contenido de
relleno identificable (`[DRY-RUN] scene-writer ch03`).

Lo que el modo en seco sí ejercita: el recorrido de nodos, las rutas de fichero, el merge
de configuración, los contadores de ciclo, la compuerta, los commits de git, el ensamblado
del manuscrito y el export. Lo que no puede ejercitar: la calidad de la prosa y el
contenido de las incidencias.

Para que las ramas de `BLOCK` y `GATE` no queden sin recorrer, el seco acepta
`execution.dryRunInjectBlockerAt`: el capítulo en el que inyecta una incidencia `blocker`
sintética. Sin eso, una corrida en seco siempre sale por el camino feliz, que es el único
que nunca se rompe.

**Si el bucle falla vacío, falla gratis.** El modo en seco se verifica antes de gastar en
llamadas reales.

---

## 13. Perfil de prueba — 3 capítulos

La prueba objetivo es **3 capítulos de 3 o 4 párrafos cada uno**, configurada en
`config/profiles/smoke-3ch.json` y lista para correr sobre `novels/neon-smoke/`.

Apagar de más deja caminos del bucle sin probar, que es justo donde se rompen las cosas.
Cada decisión del perfil, con su razón:

| Decisión | Valor | Por qué |
|---|---|---|
| Web **encendida**, con tope duro | `enabled: true`, 2 búsquedas en setup, 1 por capítulo | Apagarla dejaría sin probar `RES1`, el ciclo `GAP` y al `technical-verifier` entero, que es donde vive la invariante 3. Es el apagado más tentador y el peor. |
| Los dos validadores **encendidos** | `continuity: true`, `technical: true` | Son la única paralelización del diseño. Apagar uno no prueba la convergencia en `REPORT`. |
| `approvalMode: act-end-or-flagged`, 1 acto | — | Auto-aprueba los capítulos 1 y 2 y para en el 3: las dos ramas de `GATE` en una sola corrida, con una sola interrupción humana. |
| `maxRewrites: 1` en vez de 3 | — | Con 1 se prueban las dos salidas de `BLOCK` igual que con 3 —reentrada en `WRITE` y agotamiento hacia `FLAG`—, y la segunda pasa de teórica a alcanzable. |
| PDF y EPUB **apagados** | `outputFormats: ["markdown"]` | No cuestan tokens, así que no se apagan por dinero: se apagan porque meten una dependencia externa de conversión que haría fallar la prueba por algo que no es el bucle. Encenderlos es una palabra. |
| `dryRun: true` de entrada | — | La primera pasada se verifica vacía. Ponerlo a `false` es el segundo paso, no el primero. |
| `dryRunInjectBlockerAt: 2` | — | Fuerza el camino `BLOCK → WRITE → FLAG` en la corrida en seco. Sin esto, el seco solo recorre el camino feliz. |
| `budget.maxUsd: 5`, `onExceed: stop-after-chapter` | — | Una prueba que se desmadra en coste es un fallo de la prueba. Cortar por capítulo deja siempre estado commiteado. |
| `models.scene-writer` sigue en el modelo grande | — | Lo que la prueba juzga cualitativamente es la prosa. Degradar justo ese rol ahorraría céntimos y haría la prueba menos informativa. |

Nada queda apagado en `validation`, `research` ni `limits` más allá de sus topes. Los
únicos caminos del diagrama que esta corrida no recorre son `DEC → rollback` y
`DEC → revise`, que dependen de lo que el humano elija en la única compuerta.

---

## 14. Criterios de aceptación

Comprobables, en este orden.

1. **Modo en seco.** Con `smoke-3ch` y `dryRun: true`, la corrida produce 3 capítulos
   marcador, 3 commits `ch0N:` y un `manuscript.md`, **sin una sola llamada a un modelo**.
   Verificable porque `usage.inputTokens` es 0 en todos los sobres.
2. **Un solo escritor de la biblia.** `git log --name-only -- 'novels/*/bible/**'` no
   muestra ninguna escritura que no venga del nodo `COMMIT` o del seed. Ningún prompt
   distinto de `continuity-keeper` declara una ruta de salida bajo `bible/`.
3. **Un solo rol con web.** Los nueve agentes que no son `researcher` reciben
   `limits.maxSearches: 0` **y** no tienen la herramienta de búsqueda declarada. La
   invariante 3 es cierta en la implementación, no solo en el prompt: un agente sin
   herramienta no puede buscar aunque quiera.
4. **`voice-editor` no añade.** Para los 3 capítulos, el recuento de palabras de
   `ch<NN>.md` es menor o igual que el de `ch<NN>.draft.md`.
5. **Solo `blocker` reescribe.** Un capítulo con `warning` y sin `blocker` avanza a `GATE`
   sin reentrar en `WRITE`, y su `warning` aparece impreso en la compuerta.
6. **Topes.** Con un `blocker` que no se resuelve, la corrida hace exactamente
   `maxRewrites` reintentos y luego marca `FLAG`; no un intento más.
7. **Compuerta.** Con `act-end-or-flagged` y 1 acto, el sistema se detiene una vez, en el
   capítulo 3.
8. **Commit por capítulo.** Tras la corrida hay un commit por capítulo aprobado, y cada
   uno contiene capítulo, resumen y biblia de ese momento.
9. **Rollback.** Un rollback a `K` deja `<novel>/bible/` byte a byte idéntico al del
   commit de `K`, y `chapters/` sin ningún fichero posterior a `K`.
10. **Reanudación.** Matar la corrida a mitad del capítulo 2 y relanzarla produce el mismo
    resultado que no haberla matado, sin regenerar el capítulo 1.
11. **Contexto ensamblado.** Ningún sobre contiene el texto de más de un capítulo. El
    tamaño del sobre no crece con el número de capítulos escritos.
12. **Términos prohibidos.** Un término de la lista del pack de género en la prosa produce
    un `blocker` de tipo `banned-term`.

---

## 15. Limitaciones conocidas

1. **La coherencia global no se verifica capítulo a capítulo.** `continuity-keeper`
   contrasta el capítulo `N` contra la biblia, no contra el arco completo. Un arco que se
   desinfla despacio a lo largo de veinte capítulos pasa todas las validaciones locales.
   La compuerta de fin de acto es el único punto donde eso puede detectarse, y lo detecta
   un humano, no el sistema.
2. **Los validadores comparten familia de modelo con el escritor.** Un error de
   razonamiento que el escritor comete, el validador puede no verlo por la misma razón. La
   verificación técnica está protegida de esto porque compara contra notas externas; la de
   continuidad no lo está.
3. **El coste solo se conoce a posteriori del turno.** `budget.maxUsd` se comprueba
   después de cada llamada, no antes. `budget.maxUsdPerCall` acota el daño —se pasa como
   tope duro al SDK, que corta la llamada al alcanzarlo— pero sigue siendo un límite por
   turno, no una previsión: nadie sabe lo que va a costar un turno hasta que termina.
4. **La prueba de 3 capítulos no ejercita el problema real.** El sistema existe porque un
   modelo olvida en el capítulo 30 lo que estableció en el 3. Con 3 capítulos, la biblia
   cabe holgadamente en el contexto y la gestión de estado no está bajo presión. La prueba
   valida el bucle, no la tesis.
5. **`voice-editor` se controla por conteo, no por comprensión.** La comprobación de la
   invariante 4 es que el texto no crece. Un editor que sustituyera una frase por otra del
   mismo largo pasaría el control. La invariante está escrita en su prompt; el conteo solo
   atrapa el caso burdo.
6. **La paralelización de los validadores no la garantiza la estructura de datos.** Es
   segura porque ninguno escribe, pero nada en el árbol de ficheros lo impide. Si un
   futuro validador escribiera, la paralelización dejaría de ser correcta en silencio.
7. **El export a PDF y EPUB depende de herramienta externa.** Está fuera del bucle y no se
   prueba en la corrida de humo.

---

## 16. Desviaciones respecto al diagrama y a las invariantes

### 16.1 El paso `seed` no está en el diagrama

`plot-architect` y `character-profiler` producen escaleta y fichas, que **son** contenido
de la biblia. La invariante 2 dice que solo `continuity-keeper` escribe la biblia. El
diagrama va `PROF --> LOAD` sin pasar por él.

Resolución: `ARCH` y `PROF` no escriben en disco. Devuelven `proposals` en su sobre, y el
orquestador llama a `continuity-keeper` en modo `seed` antes de `LOAD`. Es un modo de un
agente que ya existe, no una caja nueva, y deja `BOOT` coherente: la biblia existe porque
alguien autorizado la escribió.

Coste: un paso implícito que el diagrama no dibuja. La alternativa era declarar el setup
como excepción a la invariante 2, que es más fiel al diagrama y más débil con la
invariante.

### 16.2 El contador de reescrituras se reinicia tras notas del humano

El diagrama dibuja `BLOCK -->|yes · retries < 3| WRITE` y
`DEC -->|revise with notes| WRITE` como dos entradas al mismo nodo, sin decir si comparten
contador.

Resolución: no lo comparten. `limits.maxRewrites` cuenta los reintentos por `blocker`;
`limits.maxHumanRevisions` cuenta las revisiones pedidas por una persona. Al entrar por
`DEC`, el contador de reescrituras vuelve a cero. Son dos ciclos con dos causas distintas,
y si compartieran presupuesto una persona podría quedarse sin margen por culpa de un
validador.

### 16.3 El commit de git lo hace el orquestador, no `continuity-keeper`

El nodo `COMMIT` dice «7 · Continuity Keeper — write bible + summary · git commit per
chapter». `continuity-keeper` escribe biblia y resumen; el `git commit` lo ejecuta el
orquestador.

Razón: el commit es mecánico, y el comportamiento de los agentes vive en texto, no en
código. Dar a un agente la capacidad de ejecutar git para cumplir una caja del diagrama al
pie de la letra sería ampliarle los permisos por una cuestión de dibujo.

---

## 17. El harness

Orquestador determinista en Node más el **Claude Agent SDK** para cada llamada. Una
`query()` aislada por nodo del diagrama, sin conversación acumulada entre nodos.

Se lanza con un solo comando: `npm start`.

### 17.1 Por qué así

Lo determinista —contadores, topes, ramas, rutas, commits— vive en código. Lo que es
juicio vive en `agents/*.md` y `skills/*.md`, que son ficheros de texto editables.

Se descartaron dos alternativas. **Subagentes conducidos por un slash command**: el
orquestador sería un modelo, y entonces el modo en seco es imposible —no se puede
recorrer el bucle «sin llamar a ningún modelo» si el bucle *es* un modelo— y los
contadores dejan de ser deterministas. **Messages API con clave propia**: exige una
clave de API aparte, cuando el entorno fija que los modelos llegan por el acceso a
Claude de la cuenta.

### 17.2 Cómo se hacen ciertas las invariantes 2 y 3

**Ningún agente recibe herramienta de fichero ni de shell.** Cada llamada fija
`tools` desde el frontmatter del agente: `[]` en nueve de los diez, `['WebSearch']` solo
en `researcher`. En el SDK, `tools` es lo que restringe qué herramientas existen;
`allowedTools` solo auto-aprueba las que ya existen, que no es lo mismo. Se añade
`settingSources: []` para que ningún `CLAUDE.md` ni `settings.json` amplíe permisos por
la puerta de atrás, y `permissionMode: 'dontAsk'` para que lo no pre-aprobado se deniegue
en vez de preguntarse.

Eso convierte a los diez roles en generadores de texto puro: **el orquestador lee y
escribe todos los ficheros**. Su función de escritura comprueba la ruta contra las que el
agente declara en su frontmatter y rechaza cualquier otra.

**Comprobación de arranque.** Antes del primer nodo se verifica que exactamente un agente
declara herramienta web, que exactamente uno declara escritura bajo `bible/`, que no son
el mismo, y que nadie declara una herramienta fuera de la lista permitida. Si la cuenta
no sale, la corrida no empieza. `npm run invariantes` la ejecuta sola.

### 17.3 Control de gasto

El coste de este diseño crece con facilidad, así que se acota en seis sitios:

| Palanca | Qué evita |
|---|---|
| `scope.summaryWindow` | Que el contexto —y por tanto el precio de cada capítulo— crezca con el número de capítulos ya escritos. |
| `maxTurns: 1` | Turnos extra. Sin herramientas no hay bucle agéntico que justificarlos. |
| `budget.maxUsdPerCall` | Que un turno desmandado se lleve el presupuesto de la corrida. |
| `budget.maxUsd` + `onExceed` | Que la corrida siga gastando pasado el tope. Ninguna política aborta a mitad de capítulo: eso dejaría trabajo pagado y sin commitear. |
| Salida estructurada (`outputFormat`) | Reintentos por JSON malformado, que se pagan dos veces por la misma respuesta. |
| Solo el modo activo en el prompt | Enviar en cada llamada las instrucciones de modos que no se van a usar. |

El prompt se compone con lo estable delante —agente, skills, pack de género— y lo volátil
detrás, que es la condición para que la caché de prompt sirva de algo. Cada llamada deja
una línea en `run-log.jsonl` con sus tokens, su coste y las herramientas que tenía.

### 17.4 Ficheros

| Módulo | Qué hace |
|---|---|
| `tools/run.js` | CLI y arranque. El único comando. |
| `tools/config.js` | Base + overlay, merge por sección, validación. |
| `tools/agents.js` | Carga de `agents/` y `skills/`, composición del prompt, invariantes. |
| `tools/call.js` | La llamada al SDK, el modo en seco y la contabilidad de gasto. |
| `tools/loop.js` | El recorrido del diagrama. |
| `tools/gate.js` | Presentación en CLI y decisión humana. |
| `tools/git.js` | Commits, archivado del rollback, lectura del historial. |
| `tools/state.js` | `run-state.json`, registro y escritura con control de ruta. |
