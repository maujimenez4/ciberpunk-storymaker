---
description: Escribe una novela capítulo a capítulo recorriendo el bucle de agentes
argument-hint: [perfil]  p.ej. smoke-3ch
---

Vas a recorrer el bucle de StoryMaker como orquestador. Perfil: **$1** (si está vacío,
usa `smoke-3ch`).

El flujo está en `docs/architecture/agent-loop.mmd` y **no se rediseña**. Tú lo recorres.

## Reglas que no puedes romper

1. **No metas prosa en tu contexto.** Los subagentes escriben en disco y te devuelven
   rutas y contadores. Tú pasas rutas. La única excepción es la compuerta, donde sí lees
   el capítulo para enseñárselo a la persona.
2. **No hagas el trabajo de un subagente.** Si toca `scene-writer`, lanzas
   `scene-writer`. Nunca escribes prosa tú.
3. **No escribas bajo `novels/*/bible/`.** Es de `continuity-keeper`. Hay un hook.
4. **Actualiza `run-state.json` en cada transición de nodo**, antes de seguir.
5. **No hay topes de gasto.** No cuentes dinero ni tokens, y no pares por consumo.

## 0 · Arranque

```
node tools/config.js $1
```

De ahí sacas `run.novel`, `scope`, `supervision`, `validation`, `research`, `limits`,
`output` y `execution`. Llama `<novel>` a `novels/<run.novel>/`.

Comprueba que existe `<novel>/brief.md`. Si no, para y dilo.

Lee `<novel>/run-state.json` si existe. Si no existe o está corrupto, reconstruye desde
git: `git log --grep "^ch[0-9][0-9]:" -1 --format="%h %s" -- novels/<slug>` te da el
último capítulo aprobado. **El historial manda sobre el fichero de estado.**

## 1 · BOOT

¿Existe `<novel>/bible/canon.md`?

- **No** → ve a **Setup**.
- **Sí** → ve al **bucle de capítulo**, empezando en `lastApprovedChapter + 1`. Todo lo
  aprobado **no se regenera nunca**.

## 2 · Setup (corre una vez)

1. **RES0** — si `research.enabled`, lanza `researcher` en modo dossier. Dile el tope de
   `research.maxSearchesSetup` búsquedas y que escriba en `<novel>/research/dossier.md`.
2. **ARCH** — lanza `plot-architect`. Dale la ruta del dossier y el brief,
   `scope.chapters` capítulos y `scope.acts` actos. Escribe en
   `<novel>/research/outline-proposal.md`.
3. **PROF** — lanza `character-profiler`. Dale brief y escaleta propuesta. Escribe en
   `<novel>/research/characters-proposal.md`.
4. **SEED** — lanza `continuity-keeper` en modo seed con las tres rutas. Escribe
   `<novel>/bible/`. Este paso no es una caja del diagrama: existe porque la invariante 2
   exige que la biblia la escriba `continuity-keeper` y no los dos proponentes.

Comprueba que `bible/canon.md` existe. Commit: `setup: bible seed`.

## 3 · Bucle de capítulo

Para cada capítulo `N` desde `lastApprovedChapter + 1` hasta `scope.chapters`:

### LOAD

Reúne las **rutas** —no el contenido— de: los ficheros de `<novel>/bible/`, los últimos
`scope.summaryWindow` resúmenes (`bible/summaries/`), y la entrada de `N` en
`bible/outline.md`. No leas capítulos anteriores.

### BEAT

Lanza `beat-planner` con esas rutas. Te devuelve la ruta de
`<novel>/notes/ch<NN>-beats.md`, el título y la lista de lagunas.

### GAP ⇄ RES1

Si hay lagunas y `research.enabled`, lanza `researcher` en modo notes con las preguntas y
el tope de `research.maxSearchesPerChapter`. Escribe en
`<novel>/research/ch<NN>-notes.md`.

Vuelve a mirar si quedan lagunas. **Máximo `limits.maxResearchRounds` rondas.** Al
agotarse, sigue a WRITE diciéndole al escritor que no afirme nada sobre lo que quedó sin
resolver, y anota un `warning` para la compuerta.

### WRITE

Lanza `scene-writer` con: rutas de beats, notas, biblia y resúmenes; objetivo
`scope.wordsPerChapter` palabras y máximo `wordsPerChapter × (1 + wordsTolerance)`.

Si esta es una reescritura, añade **solo los `blocker`** del reporte anterior. Si viene de
notas del editor humano, añade las notas.

### VOICE

Lanza `voice-editor` con la ruta del borrador. Escribe `<novel>/chapters/ch<NN>.md`.

### VAL1 ∥ VAL2 — en paralelo

Si `validation.runInParallel`, **lanza los dos en el mismo mensaje** para que corran a la
vez. Es la única paralelización del diseño, y es legítima porque ninguno de los dos
escribe en la biblia.

- `continuity-keeper` en modo validate → `<novel>/notes/ch<NN>-val-ck.json`
- `technical-verifier` → `<novel>/notes/ch<NN>-val-tv.json`

Salta el que esté desactivado en `validation`.

### REPORT

Lee los dos JSON —son pequeños, no son prosa— y fúndelos **sin reordenar ni
reinterpretar** en `<novel>/notes/ch<NN>-issues.json`:

```json
{ "report": "storymaker/issue-report@1", "novel": "...", "chapter": N, "attempt": A,
  "issues": [ ... ], "counts": { "blocker": 0, "warning": 0, "note": 0 } }
```

Prefija los `id`: `ck-01`, `tv-01`. El hook de términos prohibidos puede añadir los suyos.

### BLOCK

**Solo `blocker` reescribe** (invariante 7). `warning` y `note` se acumulan y se imprimen
en la compuerta.

- ¿Hay `blocker` y quedan reescrituras (`attempt ≤ limits.maxRewrites`)? → vuelve a
  **WRITE**, incrementando `attempt`.
- ¿Hay `blocker` y se agotaron? → **FLAG**: marca el capítulo como no resuelto. Fuerza
  compuerta sea cual sea `approvalMode`.
- ¿No hay? → **GATE**.

### GATE

¿Hace falta parar? Según `supervision.approvalMode`:

- `never` → no paras, salvo que el capítulo esté marcado y `onFlagged` sea `force-gate`.
- `every-chapter` → siempre.
- `act-end-or-flagged` → al cerrar acto (`N` múltiplo de `ceil(chapters/acts)`, o el
  último) o si está marcado.

Si paras, **enseña a la persona**: el texto del capítulo, las incidencias abiertas con su
severidad, y si está marcado. Luego pregunta y **espera**:

- **aprobar** → COMMIT.
- **revisar con notas** → vuelve a WRITE con las notas. El contador de reescrituras
  **vuelve a cero**: es otro ciclo, con otra causa. Máximo `limits.maxHumanRevisions`.
- **rollback al capítulo K** → ve a ROLLBACK.

### COMMIT

Lanza `continuity-keeper` en modo commit con la ruta del capítulo aprobado. Actualiza la
biblia y escribe `bible/summaries/ch<NN>.md`.

Luego haz tú el commit de git —esto es mecánico y es tuyo, no suyo—:

```
ch<NN>: <título del capítulo>

Biblia actualizada: <ficheros>.
Incidencias abiertas: <n> warning, <n> note.
```

Actualiza `run-state.json`: `lastApprovedChapter`, `lastApprovedCommit`, contadores a
cero.

## 4 · ROLLBACK

Los capítulos `K+1..N` **se archivan, no se borran**:

```
git mv novels/<slug>/chapters/ch<NN>.md novels/<slug>/attic/<timestamp>/
git checkout <commit de K> -- novels/<slug>/bible
```

Commit: `rollback: to ch<K>, archived ch<K+1>..ch<N>`. Vuelve a LOAD con `K+1`.

## 5 · COMP y EXPORT

Cuando no queden capítulos, lanza `compiler` con las rutas de los capítulos aprobados y
`bible/outline.md`. Escribe `<novel>/out/manuscript.md`.

`EXPORT` es mecánico y no tiene agente. Si `output.outputFormats` pide `pdf` o `epub`,
avisa de que requieren herramienta externa y de que el Markdown canónico sí está.

Commit: `compile: manuscript.md (<n> capítulos)`.

## Modo en seco

Si `execution.dryRun` es `true`, **no lances ningún subagente**. Recorre el bucle tú,
escribiendo en cada ruta un fichero marcador con la forma correcta y contenido
`[DRY-RUN] <agente> ch<NN>`. Sirve para comprobar rutas, contadores, compuerta y commits.

A diferencia del harness de `main`, esto **no** es gratis: tú eres un modelo y recorrer el
bucle cuesta. Lo que ahorra es las llamadas a los nueve subagentes.

Si `execution.dryRunInjectBlockerAt` trae un número de capítulo, inyecta ahí un `blocker`
sintético para que el camino `BLOCK → WRITE → FLAG` también se recorra. Sin eso, el seco
solo pasa por el camino feliz, que es el único que nunca se rompe.
