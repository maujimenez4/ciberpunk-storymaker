# Estado: telemetría y evaluación

## Migración de telemetría a Langfuse v4

Langfuse Cloud apaga `/api/public/ingestion` el **16 de noviembre de 2026**: desde esa
fecha solo acepta eventos `score-create` y rechaza el resto. El hook
[`trace-langfuse.mjs`](../.claude/hooks/trace-langfuse.mjs) escribía por ahí, así que la
migración no es opcional ni aplazable.

El trabajo va por fases del plan de instrumentación (§6.A de
[diagnostico-evaluacion.md](diagnostico-evaluacion.md)). Cada una se cierra por separado y
ninguna toca el diagrama del bucle ni `novels/*/bible/`.

| fase | qué cubre | estado |
|---|---|---|
| A0 | reconocimiento del sobre de hook | **cerrada** (20-09-2026, §3.3) |
| A2 | transporte OTLP + `runId` estable | **código cerrado** (20-09-2026); falta mirar el canario en la UI |
| A1 | `node` y `attempt` desde el encargo | **código cerrado** (20-09-2026); falta la sonda real |
| A3 | entrada y salida por observación | pendiente |
| A4 | scores de los validadores | pendiente |
| A5 | registro de lecturas por subagente | pendiente |

## Lo que ya está en marcha

**Transporte.** `POST /api/public/otel/v1/traces` en OTLP HTTP/JSON, con
`x-langfuse-ingestion-version: 4`. Sin dependencias: el hook sigue corriendo con `node`
pelado, un `fetch` y un `try/catch`. El envío legacy se eliminó en el mismo cambio, así que
no hay ningún id viajando por las dos vías a la vez.

**Identidad.** El `runId` sale de `run.lock` —`sessionId` + `startedAt`, nunca `touchedAt`,
que se mueve— y se cachea en `novels/<slug>/.trace/run-id`. Dos corridas de la misma novela y perfil ya
no escriben en la misma traza, que era §3.2(d). El `spanId` es
`sha256(tool_use_id)` truncado, así que es determinista y no depende de que el hook corra
una sola vez.

**Idempotencia.** v4 no deduplica de forma fiable, así que tras un 2xx se deja una marca en
`novels/<slug>/.trace/sent/<spanId>` y ese span no se vuelve a mandar. Un timeout **no** se reintenta
solo: se anota en `.langfuse-errors.log` y se deja para el barrido.

**Raíz.** Langfuse exige span raíz y el hook corre en un proceso que muere tras cada
subagente, así que la raíz se emite al cerrar la fase (`--close-trace`) con duración real
calculada sobre los hijos, que ya apuntaban a su `parentSpanId` determinista. Las raíces que
falten por una corrida interrumpida las recoge `--sweep` al principio de la siguiente.

Ambas órdenes están enganchadas en [`novela.md`](../.claude/commands/novela.md): el barrido
al arrancar, el cierre en `SEED` y en `COMMIT`. La raíz se construye con lo que registraron
sus hijos —cada fila de `.trace/spans/<traceId>.jsonl` lleva su `runId`, novela, perfil y
fase— y no con el estado del momento, porque quien cierra una traza puede ser el barrido de
la corrida siguiente, cuando el estado ya habla de otra cosa.

## Lo que no cambia

El espejo local `agent-calls.jsonl` se sigue escribiendo **antes** de la red y ahora lleva
también `runId` y `agent_id`. Es la fuente del panel y no puede depender de que Langfuse
conteste. Y la regla de siempre: ningún fallo de telemetría rompe una corrida. Sin
credencial, con la red caída o con un 500 al otro lado, el hook anota y sale con `{}`.

## Cómo se prueba sin gastar

```
npm test                                    # fixtures y aserciones, cero red
node .claude/hooks/trace-langfuse.mjs --selftest < fixture.json   # imprime el cuerpo OTLP
node .claude/hooks/trace-langfuse.mjs --canary                    # única vía que gasta
```

`--selftest` no toca la red, no escribe el espejo y no deja marcas de envío; `npm test` lo
usa contra los fixtures de `tests/fixtures/hooks/`, que traen sobres reales capturados en
A0. Once aserciones, y cada una es la regresión de un agujero concreto del §3.2.

**Nodo del encargo.** Cada prompt a un subagente empieza por
`<!-- storymaker-trace node=<NODO> attempt=<n> chapter=<n> -->`. Lo emite
[`novela.md`](../.claude/commands/novela.md) y lo ignoran los roles, que tienen la
instrucción en [`handoff-envelope`](../.claude/skills/handoff-envelope/SKILL.md). El hook lo
parsea; si falta o no valida —el nodo tiene que ser mayúsculas del diagrama— cae a
`run-state.json` y marca `node_source: "state"` en vez de `"header"`, para que un dato
dudoso no pase por bueno. Esto cierra §3.2(b) y §3.2(c).

**Cierre automático.** Con `node=SEED` o `node=COMMIT` en el encabezado y el subagente
completado, el hook cierra la traza él mismo. Se exige que el nodo venga del encabezado: con
el del estado dispararía en el nodo equivocado, que es justo el fallo que A1 arregla. Los
bloques de `novela.md` siguen como respaldo y no duplican nada, porque la raíz lleva marca
de envío.

## El canario del 20-09-2026

`--canary` sustituye al viejo `--ping`. Se lanzó una vez, con tag
`canary-20260921050920-aad5c815` y `traceId 8ce11a3ffd767b29424d6c8b910a7704`: primero el
`generation` y su hijo, tres segundos de espera, y después la raíz. Los dos envíos salieron
con **HTTP 200** y la respuesta confirmó `ingestionVersion: 4` y clave válida.

Que el transporte funciona ya está demostrado. Lo que **falta mirar en la UI**, y condiciona
seguir con A1:

1. **La jerarquía se reconstruyó** con el padre llegando tarde. Es el punto que decide si la
   opción (d) sirve o hay que pasar al plan B —raíz en la primera llamada, con la duración
   marcada como desconocida—.
2. Los tiempos: raíz ~4 s, `generation` ~2,5 s, hijo ~1 s.
3. Entrada y salida visibles en la raíz y en el `generation`.
4. La metadata filtrable en los tres spans (`tag`, `purpose`).
5. Si el coste del `generation` contempla las claves de caché, que la documentación no
   aclara y aquí cambia la aritmética por cinco.

## Canario A2 (verificado en la UI)
Jerarquía raíz > generation > hijo correcta con la raíz tardía, tiempos y
entrada/salida correctos, sin duplicados. Pendiente: canario de caché
(¿el costo cambia con cache_read_input_tokens?).


---

# Evaluators deterministas

`npm run evals` ([tools/evals/run.mjs](../tools/evals/run.mjs)) corre los cinco primeros
evaluators de §2.4 sobre las novelas de `novels/`. Ninguno llama a un modelo ni sale a la
red. La lógica está en [`tools/evals/evaluators.mjs`](../tools/evals/evaluators.mjs), aparte
del CLI, para que los tests la carguen sin montar una corrida.

Cada resultado sale con la forma `{ evaluator, target, novela, capitulo, pass, value,
detalle }`, más `dataType` y algún campo de origen. `target` es **el agente cuya salida se
juzga**, no quien detecta el fallo: una longitud fuera de rango es de `scene-writer` aunque
la mida esto, y un anclaje roto es de `continuity-keeper` porque la biblia es suya. El JSON
va a `evals/out/results.json`, que está en `.gitignore`.

`pass` puede ser `null` —un capítulo sin borrador, un perfil sin objetivo de longitud—, y
esos casos no cuentan ni a favor ni en contra pero **se emiten igualmente**: un evaluator
que descarta casos en silencio miente sobre su propia cobertura.

## Contra las líneas base del diagnóstico

| evaluator | línea base | medido | |
|---|---|---|---|
| `voice-editor-no-anade` | 9/9, deltas −5 a −30 | 9/9, deltas −5 a −30 | ✓ |
| `sin-terminos-prohibidos` | informar | 9/9 limpio, ningún término | ✓ |
| `issues-schema-valido` | 6/6 | **5/6** | ✗ |
| `canon-resoluble` (biblia) | 31/32, fallo real en `dead-floor` | 31/32, el mismo fallo | ✓ |
| `longitud-en-rango` | 350/339/359 · 327/355/317 · 373/386/422 | idénticas | ✓ |

`dead-floor` llega a **+20,6 %** en `ch03`, como decía el diagnóstico. Las tres corridas se
separan igual que allí: `within-tolerance` ≤3 %, `neon-smoke` ≤10 %, `dead-floor` hasta 21 %.

Sobre `within-tolerance`: entra por defecto. Está marcada como contaminada en el JSON y hay
`--excluir-contaminadas`, pero **ninguno de estos cinco evaluators mira la secuencia de
nodos**, que es lo que su contaminación estropea. Sus capítulos y su biblia son ficheros
terminados y sirven para medir.

## Dos decisiones que necesito de ti

**1. Cómo reutilizar `bannedTerms()`.** No está exportada y vive en un script que escucha
stdin, así que no se puede importar sin editar `guard-prose.mjs`, y me dijiste que no tocara
hooks. Lo he resuelto **invocando el propio hook como subproceso** con un sobre sintético:
reutiliza no solo la lista sino el emparejado real —el `\b` y la bandera unicode viven en el
cuerpo del hook, no en la función—, así que no puede desincronizarse. Se le pasa la ruta del
borrador con el texto final dentro, que es la forma de pedirle solo la invariante 9 sin
arrastrar la 4. Funciona y hay un test que lo prueba con una lista de términos inventada.

La alternativa más limpia es extraer `bannedTerms()` a un módulo compartido, como ya se hizo
con `usage.mjs`, `otlp.mjs` y `handoff.mjs`. Son dos líneas en `guard-prose.mjs` y las tengo
prohibidas: dilo y lo cambio.

**2. `where` con localizador de capítulo entero.** El corpus da 5/6 y no 6/6. La que falla es
`within-tolerance` `ck-01`, con `where: "ch03 (capítulo completo)"`, que no casa
`/^ch\d+ ¶\d+/`. La regla la fijaste tú y la skill [issue-report](../.claude/skills/issue-report/SKILL.md)
solo documenta la forma `ch03 ¶4`, así que el evaluator está haciendo lo que se le pidió y la
línea base de 6/6 del diagnóstico es la que no se sostiene. Caben dos arreglos y son
distintos: **ampliar el esquema** para admitir un localizador de capítulo entero —un hilo
abandonado no tiene párrafo—, o **corregir a `continuity-keeper`** para que siempre dé
párrafo. No he tocado ninguno de los dos.

## Lo que no pude verificar

- **Que el JSON sirva tal cual como score de Langfuse.** Está construido para eso —`value`
  numérico, `pass` booleano, `dataType`, y `target`/`novela`/`capitulo` como metadata— pero
  no se ha enviado ninguno: eso es A4, y esta tanda era sin red.
- **Si `research/dossier.md#eje-1` debería contar.** El evaluator la marca rota y lo está: el
  dossier numera sus secciones `## 1. Sincronización…`, no `## Eje 1`, así que no hay ningún
  encabezado al que apuntar. Es un segundo positivo verdadero, del mismo tipo que el de
  `dead-floor`, pero **no estaba en la línea base de 31/32**, que solo contaba las citas
  internas de la biblia. Por eso la salida las separa por origen.
- **La cobertura del evaluator de términos prohibidos.** El hook deniega en el primer término
  que encuentra, así que si un capítulo tuviera dos, solo se vería uno. Con 9/9 limpios no
  hay forma de comprobarlo sobre el corpus real.
