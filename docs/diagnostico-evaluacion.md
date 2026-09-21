# Diagnóstico para evaluación y mejora

Panorama de lo que hoy se puede medir en StoryMaker, qué falta para meter evaluators de
Langfuse y qué loop de mejora tiene sentido montar primero.

Levantado por lectura estática del repo y de las tres novelas existentes
(`dead-floor`, `neon-smoke`, `within-tolerance`). **No se ejecutó el bucle ni se llamó a
ningún subagente.** Lo que no pude verificar va marcado como `[SIN VERIFICAR]`.

---

## 0. Advertencia sobre los datos existentes

Antes de usar nada de `novels/` como corpus, tres avisos que condicionan todo lo demás.

**`within-tolerance` está contaminada.** El commit
[`c283a1b`](../novels/within-tolerance) lo dice en su asunto: «corrida contaminada por
colisión de dos orquestadores». Se ve en el historial —`ch01` y `ch02` tienen dos commits
cada uno con títulos distintos («La tercera comprobación» / «El desvío que sale a mano»)—
y en la telemetría: 12 llamadas por capítulo donde el diagrama pide 6 o 7, con marcas de
tiempo solapadas. Sus 44 líneas de `agent-calls.jsonl` son **dos corridas entrelazadas**,
no una. Sirven para medir el coste de un agente aislado; no sirven para medir la forma del
bucle ni para comparar capítulos.

**El rastro está repartido entre dos ficheros y ninguna novela tiene los dos.**

| Novela | `agent-calls.jsonl` | `run-log.jsonl` | `notes/*-issues.json` |
|---|---|---|---|
| `dead-floor` | 2 líneas | — | 3 |
| `neon-smoke` | — | 22 líneas | 3 |
| `within-tolerance` | 44 líneas (contaminadas) | — | 3 |

`agent-calls.jsonl` lo escribe el hook y trae agente, modelo, tokens desglosados, duración
y uso de herramientas ([trace-langfuse.mjs:277-281](../.claude/hooks/trace-langfuse.mjs)).
`run-log.jsonl` lo escribe el orquestador a mano y trae la secuencia de nodos correcta,
pero su `usage` es solo `{subagentTokens}`. **No hay ninguna novela con telemetría de hook
y secuencia de nodos fiable a la vez.**

**El corpus de incidencias es diminuto:** 6 incidencias en 9 ficheros. 5 `warning` y 1
`note`. **Cero `blocker`.** Eso importa mucho y se desarrolla en §5.

---

## 1. Por agente: contexto, producto y verificabilidad

El contexto de los nodos del bucle de capítulo lo ensambla
[`tools/assemble-context.mjs`](../tools/assemble-context.mjs) en un solo fichero por nodo
(`RECIPES`, [línea 97](../tools/assemble-context.mjs)). Los nodos de setup no pasan por él.

| Agente | Contexto que recibe | Produce | ¿Verificable por código? |
|---|---|---|---|
| `researcher` (RES0) | brief, pack de género | `research/dossier.md` | **Parcial.** El formato de nota es estricto y parseable ([sourced-notes-format](../.claude/skills/sourced-notes-format/SKILL.md)): afirmación como `###`, `Fuente`, `Consultado` (fecha ISO), `Confianza`, y `HUECO:` para lo no respaldado. Se puede validar forma, fechas y ratio de huecos. La veracidad, no. |
| `researcher` (RES1) | lagunas de `beat-planner`, dossier | `research/ch<NN>-notes.md` | Igual que arriba, más: **¿responde a las lagunas declaradas?** Cotejable por texto. |
| `plot-architect` | brief, dossier, `scope.chapters`, `scope.acts` | `proposals.outline` → `bible/outline.md` | **Sí, estructuralmente.** Nº de capítulos y actos contra `scope`; una entrada por capítulo. |
| `character-profiler` | brief, dossier, outline | `proposals.characters` → `bible/characters.md` | **Sí, parcialmente.** Cobertura: todo personaje citado en la escaleta tiene ficha. |
| `continuity-keeper` (seed) | propuestas + dossier | `bible/*` | **Sí.** Existencia de los 6 documentos; `canon.md` decide `BOOT` ([spec §9](spec.md)). |
| `beat-planner` | `ctx-beat`: canon, mundo, personajes, entrada de escaleta, cronología, hilos, resúmenes (ventana), **índice** del dossier ([recetas:100-111](../tools/assemble-context.mjs)) | `notes/ch<NN>-beats.md` + `requests[research]` | **Parcial.** Tiene `# Título` en primera línea (lo explota [dashboard.mjs:222](../tools/dashboard.mjs)). Las lagunas declaradas son cotejables contra las notas que produce RES1. |
| `scene-writer` | `ctx-write`: lo de beat **menos** cronología, **más** beats, notas del capítulo y **dossier entero con fuentes** ([recetas:112-123](../tools/assemble-context.mjs)) | `chapters/ch<NN>.draft.md` | **Sí, en superficie.** Longitud contra `scope.wordsPerChapter`; términos prohibidos; que no afirme nada marcado como `HUECO`. |
| `voice-editor` | solo el borrador | `chapters/ch<NN>.md` | **Sí, y es el caso más limpio del sistema.** Invariante 4 = recuento de palabras. Ver §2. |
| `continuity-keeper` (validate) | `ctx-val-ck`: canon, mundo, personajes, entrada de escaleta, cronología, hilos, resúmenes ([recetas:124-133](../tools/assemble-context.mjs)) + el capítulo aparte | `notes/ch<NN>-val-ck.json` | **La forma sí, el juicio no.** Schema, severidades del enum, `where` con formato `ch<NN> ¶<n>`, y `canon` resoluble contra la biblia. |
| `technical-verifier` | `ctx-val-tv`: **solo** dossier y notas del capítulo ([recetas:134-138](../tools/assemble-context.mjs)) + el capítulo | `notes/ch<NN>-val-tv.json` | **Igual, y mejor:** su `canon` debe apuntar a `research/`, no a `bible/`. Cotejable. |
| `continuity-keeper` (commit) | `ctx-commit`: cronología, hilos, reporte de incidencias, resúmenes. **Sin canon, mundo ni personajes**, deliberadamente ([novela.md:232](../.claude/commands/novela.md)) | biblia actualizada + `bible/summaries/ch<NN>.md` | **Sí, parcialmente.** Que exista resumen por capítulo aprobado; que los hilos citados resuelvan; que un hilo marcado como cerrado no reaparezca abierto. |
| `compiler` | capítulos aprobados, escaleta | `out/manuscript.md` | **Sí, del todo.** Nº de capítulos, orden, títulos, y que el texto sea idéntico al de `chapters/`. |

**Lectura de conjunto.** Los tres agentes cuya salida es JSON con schema
(`continuity-keeper` validate, `technical-verifier`, y el `REPORT` que funde ambos) son los
únicos con salida **verificable de forma barata y objetiva**. Los tres que producen prosa
o canon (`scene-writer`, `voice-editor`, `continuity-keeper` commit) solo admiten
verificación de superficie. `compiler` es mecánico y debería tener un evaluator
determinista al 100 %.

---

## 2. Chequeos deterministas que ya existen

### 2.1 Hooks (corren fuera del modelo, en `PreToolUse`)

Declarados en [`.claude/settings.json:13-55`](../.claude/settings.json).

| Hook | Matcher | Qué impone | ¿Reutilizable como evaluator? |
|---|---|---|---|
| [`guard-permissions.mjs`](../.claude/hooks/guard-permissions.mjs) | `Write\|Edit\|NotebookEdit\|WebSearch\|WebFetch` | Invariantes 2 y 3: nadie salvo `continuity-keeper` escribe en `bible/`; nadie salvo `researcher` busca; cada rol solo escribe sus rutas de [`ownership.json`](../.claude/hooks/ownership.json) | **Sí, como evaluator binario de corrida.** Cuenta de denegaciones = 0. |
| [`guard-prose.mjs`](../.claude/hooks/guard-prose.mjs) | `Write\|Edit` | Invariante 4 (el editado no crece, [:80-92](../.claude/hooks/guard-prose.mjs)) e invariante 9 (36 términos prohibidos de `genres/cyberpunk-thriller/banned-terms.txt`, [:62-72](../.claude/hooks/guard-prose.mjs)) | **Sí, los dos.** Son las dos mejores semillas de evaluator del repo. |
| [`guard-cycles.mjs`](../.claude/hooks/guard-cycles.mjs) | `Agent\|Task` | Invariante 6: topes de `rewrites` y `researchRounds` | **Sí,** como métrica de proceso (intentos por capítulo). |
| [`guard-run-lock.mjs`](../.claude/hooks/guard-run-lock.mjs) | `Write\|Edit\|NotebookEdit` | Una sola corrida por novela | **Sí, y urgente:** es lo que habría evitado la contaminación de §0. |

### 2.2 Lint estático

[`tools/check-invariants.mjs`](../tools/check-invariants.mjs) valida, sin correr nada:
frontmatter de los 9 agentes, que exactamente uno tenga web y sea `researcher`
([:64-70](../tools/check-invariants.mjs)), que ninguno tenga `Bash`/`Task`/`WebFetch`
([:73-76](../tools/check-invariants.mjs)), que exactamente un rol escriba en `bible/`
([:84-90](../tools/check-invariants.mjs)) y que las skills declaradas existan
([:104-108](../tools/check-invariants.mjs)). Es un test de configuración, no de salida.

### 2.3 Conteos que ya se calculan en el panel

[`tools/dashboard.mjs`](../tools/dashboard.mjs) ya deriva: palabras por capítulo
([:302](../tools/dashboard.mjs)), incidencias por severidad ([:277-284](../tools/dashboard.mjs)),
tokens por capítulo y por agente ([:230-253](../tools/dashboard.mjs)), y estado `stale`
([:265-272](../tools/dashboard.mjs)).

### 2.4 Los nueve evaluators que yo sacaría de aquí

Ordenados por facilidad de implementación. Los cinco primeros no necesitan ningún modelo.

1. **`voice-editor-no-anade`** — `words(ch<NN>.md) <= words(ch<NN>.draft.md)`. Ya lo
   comprobé sobre los 9 capítulos del repo: **9/9 pasan**, con deltas de −5 a −30 palabras.
   Determinista, sin falsos positivos, y ya tiene línea base.
2. **`sin-terminos-prohibidos`** — reutiliza literalmente `bannedTerms()` de
   [guard-prose.mjs:34-40](../.claude/hooks/guard-prose.mjs) sobre el texto final.
3. **`issues-schema-valido`** — `severity ∈ {blocker,warning,note}`, `where` casa
   `/^ch\d+ ¶\d+/`, `fix` no vacío, `id` con prefijo `ck-`/`tv-`
   ([novela.md:170](../.claude/commands/novela.md)). En el corpus actual: **6/6 pasan**.
4. **`canon-resoluble`** — que el campo `canon` de una incidencia y las citas
   `fichero.md#ancla` de la biblia apunten a un encabezado real. **Ya hay implementación
   en el repo**: [`tools/dashboard/src/anchors.js`](../tools/dashboard/src/anchors.js),
   `resolveAnchor()`. Sobre las tres biblias resuelve 31 de 32; la que falla es real
   (`bible/outline.md` de `dead-floor` cita `threads.md#expediente-abierto`, hilo que nunca
   llegó a `threads.md`). Es un evaluator con un fallo verdadero ya detectado.
5. **`longitud-en-rango`** — `|words − scope.wordsPerChapter| / objetivo`. Línea base real
   con objetivo 350: `within-tolerance` 350/339/359 (≤3 %), `neon-smoke` 327/355/317
   (≤10 %), `dead-floor` 373/386/422 (hasta **+21 %**). Discrimina entre corridas, que es
   justo lo que se le pide a un evaluator.
6. **`resumen-por-capitulo`** — todo capítulo aprobado tiene `bible/summaries/ch<NN>.md`.
7. **`cobertura-de-lagunas`** — toda laguna declarada por `beat-planner` aparece respondida
   o explícitamente como `HUECO` en las notas.
8. **`notas-con-fuente-bien-formadas`** — parseo del formato de
   [sourced-notes-format](../.claude/skills/sourced-notes-format/SKILL.md): fecha ISO
   presente, `Confianza` en el enum, una afirmación por nota.
9. **`sin-afirmar-sobre-huecos`** (LLM-as-judge) — el único que necesita modelo: ¿el
   capítulo afirma algo que el dossier declara como `HUECO`? Es exactamente el patrón de 5
   de las 6 incidencias reales del corpus (`unsourced-*`, `unsupported-claim`), así que hay
   ejemplos etiquetados para calibrarlo.

---

## 3. Qué envía hoy `trace-langfuse.mjs` y qué falta

### 3.1 Lo que envía

Por cada llamada a subagente (`PostToolUse` sobre `Agent|Task`), un batch de dos eventos a
`/api/public/ingestion` ([:234-268](../.claude/hooks/trace-langfuse.mjs)):

- **`trace-create`** — id derivado de `sha256(runId:fase|capítulo)`
  ([:110-113](../.claude/hooks/trace-langfuse.mjs)), `sessionId = runId`, tags
  `[storymaker, perfil, fase]`, metadata `{novel, profile, phase, chapter}`.
- **`generation-create`** — `name` = tipo de subagente, `model`, y uso desglosado:
  `input`, `output`, `cache_read_input_tokens`, `cache_creation_input_tokens`, `total`
  ([:211-217](../.claude/hooks/trace-langfuse.mjs)). Metadata: `node`, `chapter`,
  `attempt`, `counters`, `rawTokenFields`, `durationMs`, `toolUses`.

El desglose de caché es un acierto y no es cosmético: en `within-tolerance` el **78,9 %**
de los 899.088 tokens fue lectura de caché. Sin ese campo, cualquier cuenta de coste se
va casi por cinco.

También escribe siempre el espejo local `agent-calls.jsonl` **antes** de la red
([:275-284](../.claude/hooks/trace-langfuse.mjs)), y jamás rompe la corrida: sin credencial
o con fallo de red anota en `.langfuse-errors.log` y sale con `{}`.

### 3.2 Lo que falta, por orden de gravedad

**a) No se manda ni entrada ni salida. Es el bloqueo principal.** El cuerpo de la
`generation` no lleva `input` ni `output` ([:249-268](../.claude/hooks/trace-langfuse.mjs)).
Un evaluator de Langfuse —LLM-as-judge o el que sea— puntúa sobre el par entrada/salida de
una observación. Hoy en Langfuse hay un contador de tokens con nombre: **no hay nada que
evaluar**. Mínimo viable: mandar las **rutas** de `inputs` y `artifacts` del sobre, y para
los agentes con salida JSON pequeña (`val-ck`, `val-tv`, `issues`), el JSON entero. Nunca
prosa inline: la invariante 5 rige también aquí.

**b) `attempt` está siempre vacío.** El hook lo lee de `state.attempt`
([:262](../.claude/hooks/trace-langfuse.mjs)) pero ese campo **no existe** en el
`run-state.json` de `dead-floor` ni de `within-tolerance`; solo en el de `neon-smoke`.
Medido: **0 de 44** llamadas de `within-tolerance` llevan `attempt`. Evaluar por intento es
imposible hoy, y evaluar por intento es justo lo que mide si una reescritura mejora algo.

**c) El `node` registrado no es de fiar.** El hook toma `state.node` en `PostToolUse`
([:260](../.claude/hooks/trace-langfuse.mjs)), es decir después de que el orquestador haya
podido mover el estado. En los datos sale `scene-writer` en los nodos `BEAT`, `VAL` y
`VOICE`, y `continuity-keeper` en `WRITE`. Agrupar por nodo en Langfuse da basura. El nodo
correcto debería venir del encargo, no del estado. (En `within-tolerance` esto se agrava
por la contaminación de §0, pero el mecanismo falla igual en una corrida limpia.)

**d) `runId` colisiona entre corridas.** `state.runId ?? \`${novel}:${profile}\``
([:224](../.claude/hooks/trace-langfuse.mjs)) y **ningún `run-state.json` del repo tiene
`runId`**. Como el `traceId` sale de hashear ese valor con fase y capítulo, dos corridas de
la misma novela y perfil **escriben en la misma traza**. No se pueden comparar dos corridas,
que es el gesto básico de una mejora iterativa.

**e) La latencia es siempre cero.** `startTime: now, endTime: now`
([:256-257](../.claude/hooks/trace-langfuse.mjs)). El dato real existe —`durationMs`, que
en `within-tolerance` va de 19 s a 113 s por llamada— pero va enterrado en metadata en vez
de en los campos que Langfuse usa para su gráfica de latencia. Arreglo trivial:
`startTime = now − durationMs`.

**f) No se manda ni un `score`.** No hay ningún evento `score-create`. Los resultados de
`val-ck`/`val-tv` —que ya son juicios estructurados, producidos en la corrida y gratis— no
llegan a Langfuse. Es la fruta más baja de todo este documento.

**g) No hay nivel de error.** Ni `level` ni `statusMessage`; un subagente que falla es
indistinguible de uno que va bien.

**h) `[SIN VERIFICAR]`** si la instancia acepta `usageDetails` o exige `usage`, y si la
credencial sirve para la API de ingesta. El hook trae `--ping` para resolverlo
([:122-165](../.claude/hooks/trace-langfuse.mjs)) pero **no lo ejecuté**: manda una traza
real y eso es gasto. Hoy, además, no hay credencial configurada por ninguna de las dos vías.

---

### 3.3 Lo que midió A0

Sondeo del 20-09-2026, antes de tocar el transporte. Un subagente mínimo en Haiku disparó
los dos hooks ya registrados —`trace-langfuse.mjs` en `PostToolUse` y `guard-permissions.mjs`
en `PreToolUse`— con un andamio temporal que volcaba la **forma** del sobre, no su contenido.
Coste: 28.169 tokens, de los que 27.902 fueron lectura de caché.

Resolvió las tres incógnitas que bloqueaban el resto:

- **La duración real existe en el sobre.** `duration_ms` en el nivel 1 y
  `tool_response.totalDurationMs` un poco por debajo: la diferencia es sobrecoste del
  harness, no del subagente. §3.2(e) no necesita fichero lateral.
- **La atribución de lecturas va por `agent_id`, no por `agent_type`.** El `PreToolUse`
  anidado trae `agent_id`, y el `PostToolUse` de la llamada devuelve el mismo id en
  `tool_response.agentId`: join exacto. `session_id` **no** sirve —es idéntico en el hilo
  principal y en el subagente— y `agent_type` colisiona cuando el mismo rol se llama dos
  veces en el capítulo, que es justo el caso de `scene-writer` en una reescritura.
- **El encargo llega al hook.** `tool_input.prompt` viaja entero, así que el encabezado
  `storymaker-trace` de A1 es parseable desde ahí.

Campos del sobre que el §3.2 no contemplaba y que sí se mandan a partir de A2:

| campo | para qué |
|---|---|
| `output_tokens_details.thinking_tokens` | se factura como salida y no se estaba contando |
| `cache_creation.ephemeral_5m/1h_input_tokens` | la caché de 1 h no cuesta lo mismo que la de 5 min |
| `usage.iterations[]` | número de llamadas al modelo dentro de un subagente |
| `tool_response.status` | resuelve §3.2(g): distinto de `completed` → `level: ERROR` |
| `toolStats.readCount` | control cruzado de la atribución de lecturas |
| `tool_use_id` | id estable por llamada; de él sale el `spanId` determinista |

Y dejó dos cosas por arreglar:

**`collectTokenFields` ([:66-77](../.claude/hooks/trace-langfuse.mjs)) acumula en un mapa
plano.** Recorre también `usage.iterations[]`, así que las claves repetidas se pisan: con
varias iteraciones, `input_tokens` acaba siendo el de la última y no la suma. Y la ruta de
respaldo suma campos solapados —`thinking_tokens` está dentro de `output_tokens`,
`ephemeral_*` dentro de `cache_creation_input_tokens`—. Hoy no muerde porque `totalTokens`
gana la precedencia y la aritmética cuadra, pero es una mina en cuanto cambie el sobre.

**En v4 los hijos se emiten antes que su raíz.** Con la opción (d) —raíz al cerrar la
traza— cada span de subagente se exporta apuntando a un `parentSpanId` determinista que
todavía no existe. OTLP lo admite; que Langfuse reconstruya la jerarquía es el primer punto
que verifica el canario.

---

## 4. Por dónde se contamina un validador

### 4.1 Lo que está bien resuelto

El reparto de contexto es deliberado y correcto. `val-tv` recibe **solo** dossier y notas,
442 palabras en `dead-floor`, y no ve la biblia: no puede confundir canon con hecho
verificado ([recetas:134-138](../tools/assemble-context.mjs)). `val-ck` recibe la biblia
pero no el dossier. Y el capítulo se pasa como ruta aparte y no dentro del contexto,
explícitamente «es el artefacto que juzgan, no contexto de fondo»
([novela.md:155](../.claude/commands/novela.md)).

### 4.2 Los cinco agujeros

**a) La lectura no está vigilada por ningún hook. Es el agujero grande.** Los matchers de
[settings.json:13-44](../.claude/settings.json) cubren `Write`, `Edit`, `NotebookEdit`,
`WebSearch` y `WebFetch`. **`Read` no aparece en ninguno**, y los nueve agentes declaran
`tools: [Read, Write]`. La única cosa que impide a un validador abrir la biblia entera, los
capítulos anteriores, el JSON del otro validador o los beats es una frase en la cabecera del
contexto ensamblado: «no abras los ficheros originales»
([assemble-context.mjs:161](../tools/assemble-context.mjs)). Eso es exactamente lo que
[CLAUDE.md](../CLAUDE.md) llama una petición y no una garantía. Todo el argumento del
proyecto —los hooks existen porque el prompt no basta— se sostiene en la escritura y se cae
en la lectura. **No pude verificar si algún agente lo ha hecho de verdad**: haría falta el
registro de llamadas a `Read` por subagente, que hoy no se guarda. `agent-calls.jsonl` trae
`toolUses` como número total (2 a 10 por llamada) pero no qué herramienta ni sobre qué
fichero.

**b) `val-ck` recibe la entrada de escaleta del capítulo**
([recetas:127](../tools/assemble-context.mjs)), o sea **el plan**. Un validador de
continuidad que ve lo que el capítulo *pretendía* ser puede marcar como conflicto de canon
lo que solo es una desviación del plan. Son dos juicios distintos y el contexto los mezcla.

**c) `continuity-keeper` se valida a sí mismo.** El mismo rol escribe los resúmenes en
`COMMIT` ([spec §9](spec.md)) y luego, en modo validate, recibe esos resúmenes como base
para juzgar ([recetas:131](../tools/assemble-context.mjs)). Si el resumen del capítulo 2
omitió algo, el validador del capítulo 3 hereda la omisión y no puede detectarla. Es un
bucle cerrado sobre su propia salida.

**d) Los contextos ensamblados se quedan en disco para siempre.** `notes/` acumula los
`ch<NN>-ctx-*.md` de todos los capítulos (15 ficheros en `dead-floor`) y nada los borra ni
los protege de lectura. El contexto del capítulo 1 sigue ahí cuando corre el 3.

**e) Los dos validadores corren en paralelo y ninguno escribe**
([novela.md:144-152](../.claude/commands/novela.md)), lo cual es seguro hoy. La propia spec
avisa de que nada en el árbol de ficheros lo impone ([§15.6](spec.md)): si un validador
futuro escribiera, la paralelización dejaría de ser correcta en silencio.

---

## 5. Datos reales aprovechables como dataset

### 5.1 Lo que hay

| Material | Volumen | Calidad |
|---|---|---|
| Capítulos con borrador y final | **9 pares** | Buena. Es el dataset limpio del repo. |
| Biblias completas | 3 × 6 documentos | Buena. 32 anclajes de canon, 31 resuelven. |
| Reportes de incidencias | 9 ficheros, **6 incidencias** | **Escaso.** Ver abajo. |
| Salidas crudas de validador | 18 ficheros `val-ck`/`val-tv` | Buena para validar schema. |
| Telemetría por llamada | 44 líneas (contaminadas) + 2 | Pobre y sesgada. |
| Secuencia de nodos | 22 líneas, solo `neon-smoke` | Buena pero única. |
| Rollback | 1 en `novels/dead-floor/attic/20260918T012102Z/` | Un solo caso. |
| Corridas en seco | 3 commits `[DRY-RUN]` | Útiles como caso negativo. |

### 5.2 El problema serio del corpus de incidencias

De 6 incidencias: **5 `warning`, 1 `note`, cero `blocker`**. Por prefijo, **5 de
`technical-verifier` y 1 de `continuity-keeper`**.

Tres consecuencias:

- **La decisión cara no tiene ni un ejemplo.** `blocker` es lo único que dispara reescritura
  (invariante 7, [issue-report](../.claude/skills/issue-report/SKILL.md)) y no hay un solo
  caso etiquetado. Un evaluator de severidad no se puede calibrar contra cero positivos.
- **`continuity-keeper` casi no encuentra nada.** 1 hallazgo en 9 capítulos. O la
  continuidad es fácil con 3 capítulos —lo que la spec admite en
  [§15.4](spec.md)— o el validador no está mordiendo. **No pude distinguir cuál** sin
  correr casos con errores inyectados.
- **El `kind` es casi monotema:** `unsourced-technical-detail`, `unsourced-claim`,
  `unsupported-claim` ×2, `unsourced-stretch` — cinco variantes del mismo patrón «afirma
  algo que el dossier no respalda»— más un `thread-dropped`. Buena noticia para el evaluator
  nº 9 de §2.4; mala para cubrir el espacio de fallos.

También: el `kind` `banned-term` que exige el criterio 12 de
[spec §14](spec.md) **no puede aparecer nunca**, porque `guard-prose` **deniega la
escritura** en vez de emitir una incidencia ([:62-72](../.claude/hooks/guard-prose.mjs)). El
criterio de aceptación y la implementación no dicen lo mismo. Prevenir es mejor que
reportar, pero entonces el criterio hay que reescribirlo.

### 5.3 Qué haría con esto

El corpus vale para **fijar líneas base de evaluators deterministas**, no para entrenar ni
calibrar juicio. Para lo segundo hace falta generar casos: coger los 9 capítulos buenos e
inyectar errores conocidos —una contradicción de canon, un término prohibido, un dato sobre
un `HUECO` declarado, un hilo abandonado— y comprobar que los validadores los pillan. Eso sí
es un dataset de evaluación, y se construye sin correr el bucle entero.

---

## 6. Candidatos a loop de mejora

Cinco candidatos con su `Trigger / Goal / Verify / Stop / Memory`, rankeados.

### A. Instrumentar antes de evaluar — **impacto alto, medición trivial**

- **Trigger:** manual, una vez.
- **Goal:** que cada `generation` en Langfuse lleve entrada, salida, `attempt` real,
  `runId` único, latencia real y nodo del encargo. Es §3.2 (a)-(g).
- **Verify:** una corrida en seco con `--selftest` enseña el batch sin gastar; después,
  `attempt` no nulo en el 100 % de las llamadas y dos corridas de la misma novela producen
  dos `traceId` distintos.
- **Stop:** cuando los seis campos estén; no es iterativo.
- **Memory:** ninguna; es un cambio de código.

**No es un loop, y va primero igualmente.** Sin esto los otros cuatro no se pueden medir.

### B. Calibración de severidad de los validadores — **impacto alto, medición media**

- **Trigger:** cada `REPORT`.
- **Goal:** que `blocker` se reserve para lo que contradice canon o afirma sin respaldo de
  forma sustantiva, y que `continuity-keeper` deje de devolver vacío por defecto.
- **Verify:** contra el dataset de errores inyectados de §5.3: recall de errores plantados y
  tasa de falsos `blocker` sobre los 9 capítulos buenos, que no tienen ninguno.
- **Stop:** recall ≥ 0,8 con cero falsos `blocker`, o 5 iteraciones sin mejorar.
- **Memory:** los casos fallados, como ejemplos en la skill
  [issue-report](../.claude/skills/issue-report/SKILL.md).

Es donde está el dinero —cada `blocker` cuesta una reescritura entera— pero **necesita el
dataset construido primero**, y hoy no existe.

### C. Higiene de anclajes de canon — **impacto medio, medición trivial**

- **Trigger:** cada `COMMIT`.
- **Goal:** cero citas `fichero.md#ancla` sin destino en la biblia.
- **Verify:** `resolveAnchor()` de [anchors.js](../tools/dashboard/src/anchors.js), que ya
  existe. Línea base hoy: **31/32**.
- **Stop:** 32/32 y se queda como guarda de regresión.
- **Memory:** ninguna; es binario.

**El más barato del lote.** El evaluator está escrito, el fallo está localizado y la métrica
no admite discusión.

### D. Longitud de capítulo — **impacto bajo-medio, medición trivial**

- **Trigger:** cada `WRITE`.
- **Goal:** desviación ≤ 10 % sobre `scope.wordsPerChapter`.
- **Verify:** conteo. Línea base: `within-tolerance` ≤3 %, `neon-smoke` ≤10 %,
  `dead-floor` hasta +21 %.
- **Stop:** tres capítulos seguidos dentro del 10 %.
- **Memory:** la desviación del capítulo anterior, pasada a `scene-writer` como corrección.

Fácil y con señal real, pero es lo que menos daño hace si falla.

### E. Coste por capítulo — **impacto medio, medición hoy imposible**

- **Trigger:** cada `COMMIT`.
- **Goal:** bajar tokens por capítulo aprobado sin perder calidad.
- **Verify:** tokens por capítulo de `agent-calls.jsonl`, cruzado con los evaluators de §2.4.
- **Stop:** cuando cualquier evaluator de calidad baje.
- **Memory:** histórico por capítulo.

**Bloqueado.** Los únicos datos densos son los contaminados de §0, y sin `runId` único no se
comparan dos corridas.

### Recomendación

**Haz A, luego C, luego B. Aparca D y E.**

**A primero** porque es la precondición de todo lo demás y no es discutible: hoy Langfuse
recibe contadores de tokens sin entrada ni salida, así que no hay superficie donde enganchar
un evaluator. Es trabajo de código acotado, sin juicio de por medio.

**C después** porque es la única mejora que puedes cerrar entera en una tarde: el evaluator
ya está escrito, ya encontró un fallo real, y la métrica es un entero sobre un entero.
Sirve para rodar la maquinaria del loop —Trigger, Verify, Stop— en un caso donde nada es
ambiguo, antes de meterla en uno donde todo lo es.

**B es lo que de verdad importa** y por eso no va primera. Sin los ejemplos etiquetados de
§5.3, «mejorar la calibración de severidad» es una opinión con métrica inventada: cero
`blocker` en el corpus significa cero positivos contra los que medir. Construir el dataset
de errores inyectados es el paso previo, y es un trabajo en sí mismo.

Y hay un arreglo que no es un loop pero conviene meter en A: **el agujero de lectura de
§4.2(a)**. Mientras `Read` no pase por ningún hook, cualquier medición de «qué contexto
recibió este agente» es una suposición, porque el agente pudo haber leído cualquier otra
cosa. Eso contamina los evaluators antes de que existan.

---

## Apéndice: lo que no pude verificar

- ~~Si la credencial de Langfuse sirve para la API de ingesta.~~ **Resuelto el 20-09-2026:**
  el `--ping` salió con HTTP 207 y los dos eventos aceptados, con credencial de entorno. En
  la misma respuesta llegó el aviso de que `/api/public/ingestion` se apaga el 16-11-2026,
  que es lo que abre la migración a v4.
- Si algún subagente ha leído de verdad ficheros fuera de su contexto ensamblado. Sigue sin
  medirse, pero A0 encontró con qué: `agent_id` en el `PreToolUse` anidado da la atribución
  exacta, y `toolStats.readCount` sirve de control cruzado. Es el trabajo de A5.
- Si `continuity-keeper` encuentra poco porque hay poco que encontrar con 3 capítulos o
  porque no está mordiendo. Requiere casos con errores inyectados.
- El comportamiento real de los topes de ciclo: con cero `blocker` en el corpus, el camino
  `BLOCK → WRITE` y el `FLAG` por agotamiento **no se han ejercitado nunca** en estas tres
  novelas. Los `flagged` están vacíos en las tres.
