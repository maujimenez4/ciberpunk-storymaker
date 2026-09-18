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

Escríbelo con esta forma exacta. Los campos `limits` y `dryRun` **no son decorativos**:
los leen los hooks, y sin ellos las guardas no pueden hacer su trabajo.

```json
{
  "state": "storymaker/run-state@1",
  "novel": "<slug>", "profile": "<perfil>",
  "phase": "setup | chapter-loop | done", "node": "<nodo actual>",
  "chapter": 1, "act": 1,
  "counters": { "researchRounds": 0, "rewrites": 0, "humanRevisions": 0 },
  "limits": { "maxResearchRounds": 3, "maxRewrites": 1, "maxHumanRevisions": 3 },
  "dryRun": false,
  "lastApprovedChapter": 0, "lastApprovedCommit": null,
  "flagged": [], "updatedAt": "<ISO-8601>"
}
```

`limits` se copia tal cual de la configuración. `counters.rewrites` cuenta reintentos por
`blocker`, y **vuelve a cero** cuando la reentrada en WRITE viene de notas del editor
humano: es otro ciclo con otra causa.

## 1 · BOOT

¿El estado dice `node: "GATE"` y hay un `<novel>/gate-decision.json` que responde a la
petición en disco? Entonces esta corrida es la continuación de una compuerta: aplica la
decisión y sigue desde ahí, sin rehacer nada. Es el camino normal cuando el panel te
relanza, no una excepción.

Si no, ¿existe `<novel>/bible/canon.md`?

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

**Ensambla el contexto, no repartas rutas.** Un fichero por nodo:

```
node tools/assemble-context.mjs <slug> beat   N
node tools/assemble-context.mjs <slug> write  N
node tools/assemble-context.mjs <slug> val-ck N
node tools/assemble-context.mjs <slug> val-tv N
node tools/assemble-context.mjs <slug> commit N
```

Cada uno escribe `<novel>/notes/ch<NN>-ctx-<nodo>.md` con el canon, los resúmenes de la
ventana y la entrada de `N` en la escaleta, **recortado a lo que ese nodo necesita**.

Esto es la invariante 5 en serio: el contexto **se ensambla aquí, una vez**, en lugar de
que cada rol lo monte abriendo ocho ficheros. Repartir rutas costaba 34 lecturas por
capítulo y reenviaba el contexto acumulado en cada una; así son 5.

Tú sigues sin leer nada de eso. El ensamblador lo escribe, tú pasas la ruta.

Los de `write` y `val-*` se ensamblan **después** de GAP ⇄ RES1, para que recojan
`research/ch<NN>-notes.md` si existe. El de `commit`, después de REPORT.

### BEAT

Lanza `beat-planner` con `<novel>/notes/ch<NN>-ctx-beat.md` — **esa ruta y ninguna más**.
Dile que ahí está todo su contexto y que no abra los ficheros originales. Te devuelve la
ruta de `<novel>/notes/ch<NN>-beats.md`, el título y la lista de lagunas.

### GAP ⇄ RES1

Si hay lagunas y `research.enabled`, lanza `researcher` en modo notes con las preguntas y
el tope de `research.maxSearchesPerChapter`. Escribe en
`<novel>/research/ch<NN>-notes.md`.

Vuelve a mirar si quedan lagunas. **Máximo `limits.maxResearchRounds` rondas.** Al
agotarse, sigue a WRITE diciéndole al escritor que no afirme nada sobre lo que quedó sin
resolver, y anota un `warning` para la compuerta.

### WRITE

Reensambla el contexto —ahora ya existen las notas de RES1— y lanza `scene-writer` con
`<novel>/notes/ch<NN>-ctx-write.md`, **esa ruta y ninguna más**. Lleva dentro los beats,
las notas con fuente, el canon y los resúmenes. Objetivo `scope.wordsPerChapter` palabras,
máximo `wordsPerChapter × (1 + wordsTolerance)`.

Si esta es una reescritura, añade **solo los `blocker`** del reporte anterior. Si viene de
notas del editor humano, añade las notas.

### VOICE

Lanza `voice-editor` con la ruta del borrador. Escribe `<novel>/chapters/ch<NN>.md`.

### VAL1 ∥ VAL2 — en paralelo

Si `validation.runInParallel`, **lanza los dos en el mismo mensaje** para que corran a la
vez. Es la única paralelización del diseño, y es legítima porque ninguno de los dos
escribe en la biblia.

- `continuity-keeper` en modo validate, con `notes/ch<NN>-ctx-val-ck.md` → escribe
  `<novel>/notes/ch<NN>-val-ck.json`
- `technical-verifier`, con `notes/ch<NN>-ctx-val-tv.md` → escribe
  `<novel>/notes/ch<NN>-val-tv.json`

A cada uno, **dos rutas**: su contexto y el capítulo (`chapters/ch<NN>.md`). El capítulo va
aparte a propósito: es el artefacto que juzgan, no contexto de fondo.

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

Si paras, la decisión llega por uno de dos canales, según `supervision.gateChannel`
(por defecto `cli`):

**`cli` — hay una persona al otro lado.** Enseña el texto del capítulo, las incidencias
abiertas con su severidad y si está marcado. Luego pregunta y **espera**.

**`file` — corres sin terminal, lanzado desde el panel.** No puedes preguntar y no debes
adivinar. Escribe `<novel>/gate-request.json` y **termina la corrida ahí**, limpiamente:

```json
{ "request": "storymaker/gate-request@1", "novel": "<slug>", "chapter": N, "attempt": A,
  "reason": "act-end | flagged | every-chapter", "flagged": false,
  "chapterPath": "chapters/ch<NN>.md", "issuesPath": "notes/ch<NN>-issues.json",
  "presentUnit": "<supervision.presentUnit>", "actChapters": [1, 2, 3],
  "counters": { ... }, "limits": { ... }, "createdAt": "<ISO-8601>" }
```

Parar **no es abandonar**: el estado está en disco y todo lo aprobado tiene su commit. El
panel enseña la petición, la persona decide y vuelve a lanzarte. Bloquearte esperando un
fichero sería peor: gastarías contexto en no hacer nada y una caída se llevaría el turno.

Antes de escribir la petición, **mira si ya hay respuesta**. Honra
`<novel>/gate-decision.json` solo si su `chapter` es el capítulo actual y su `decidedAt` es
posterior al `createdAt` de la petición que hay en disco. Así una decisión vieja no puede
reabrir una compuerta ya resuelta, y nadie tiene que borrar ficheros.

Las tres decisiones, venga del canal que venga:

- **aprobar** → COMMIT.
- **revisar con notas** → vuelve a WRITE con las notas. El contador de reescrituras
  **vuelve a cero**: es otro ciclo, con otra causa. Máximo `limits.maxHumanRevisions`.
- **rollback al capítulo K** → ve a ROLLBACK.

### COMMIT

Reensambla `commit` —ahora ya existe el reporte de incidencias— y lanza
`continuity-keeper` en modo commit con **dos rutas**: `notes/ch<NN>-ctx-commit.md` y el
capítulo aprobado. Actualiza la biblia y escribe `bible/summaries/ch<NN>.md`.

Ese contexto **no lleva `canon.md`, `world.md` ni `characters.md`**, y es deliberado: un
capítulo mueve cronología e hilos, no las reglas del mundo. Si el reporte señala un
personaje o una regla, entonces sí, añádele esa ruta suelta.

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
