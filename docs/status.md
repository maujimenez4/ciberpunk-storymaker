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


---

# A4 · Scores de los evaluators en Langfuse

Fase 1 cerrada el 21-09-2026: módulo de envío, `--selftest` y tests contra un servidor
local. **No se ha enviado nada.** Cero marcas en `.trace/sent/`, ningún
`.langfuse-errors.log`.

```
npm run evals:send -- --selftest    imprime los cuerpos, no toca la red
npm run evals:send -- --uno         una traza y UN score
npm run evals:send -- --todo        la traza y los 67 scores
npm run evals:send -- --sin-metadata   quita metadata del cuerpo del score
```

Sin `--selftest`, `--uno` ni `--todo` el comando no hace nada y sale con 2: mandar datos
fuera no puede ser el comportamiento por defecto de una orden tecleada a medias.

La traza va por OTLP con los constructores de [`otlp.mjs`](../.claude/hooks/otlp.mjs), los
mismos del hook. Los scores van por `POST /api/public/scores`, que es otro endpoint con otra
forma. La lógica está en [`tools/evals/langfuse.mjs`](../tools/evals/langfuse.mjs) y el CLI
en [`send.mjs`](../tools/evals/send.mjs), separados para que los tests carguen la primera sin
disparar el segundo.

## Tres decisiones que tomé, con su motivo

**El `evalRunId` sale de la huella de los resultados y de la versión de los evaluators.**
Ni de un reloj ni del commit. Con un reloj, cada ejecución duplicaría 67 scores idénticos.
Con el commit —que fue el primer intento— tocar un README daría traza nueva y reenviaría los
mismos 67, que es la duplicación que la idempotencia existe para evitar. Lo que interesa
comparar es cuándo cambia una medida, no cuándo cambia el repo. El commit viaja igual, como
metadata de la raíz.

**Las coordenadas van en el `comment` además de en `metadata`.** La guía de migración lista
`traceId`, `observationId`, `name`, `value`, `dataType` y `comment`; **no lista `metadata`**.
Se manda igualmente, porque un 4xx respondería la duda en una llamada, pero novela, capítulo
y target no dependen de que cuaje: el `comment` empieza por `✓/✗ <novela> ch<NN> ·
target=<rol>`. Si la metadata se cae, se pierde poder filtrar, no el dato.

**Un nombre, un tipo.** *Corregido el 21-09-2026, después del envío de prueba.* La primera
versión mandaba la medida bajo el nombre del evaluator, así que `voice-editor-no-anade` salía
NUMERIC y `canon-resoluble` BOOLEAN: el mismo campo con dos tipos según la fila. Un nombre de
score es una serie y una serie no cambia de tipo. Ahora:

- **el nombre del evaluator es siempre BOOLEAN**, con 1 = pasa, para los 67 resultados;
- **la medida va en un score NUMERIC aparte**, solo donde dice algo que el veredicto no:
  `voice-editor-delta-palabras`, `longitud-desviacion` e `issues-violaciones`.

`sin-terminos-prohibidos` y `canon-resoluble` no tienen medida: su valor era 0/1, o sea el
booleano otra vez con otro nombre. `issues-violaciones` no estaba en el encargo y lo añadí
porque distingue una incidencia con un campo mal de otra con los cuatro; se quita borrando
una línea de `MEDIDAS`.

Esto arregla de paso la advertencia de dirección que este documento traía antes: ya no hay
evaluators donde 1 sea malo. Son **91 scores**: 67 veredictos y 24 medidas.

**El id determinista** lleva evaluator, target, novela, capítulo, nombre del score y
`dataType`, más el discriminador de origen y cita y un ordinal — sin eso, las varias citas de
canon de un mismo capítulo colisionarían en un solo id.

## Lo que sigue sin saberse, y lo sabrá la fase 2

- **Si el endpoint acepta `metadata`.** Un 400 lo diría; un 200 no prueba que la guarde, eso
  hay que verlo en la UI.
- **Si acepta el `id` determinista** para hacer upsert. Igual: un 400 lo diría. Las marcas
  locales en `.trace/sent/` no dependen de esto y son la garantía real.

## Una decisión que sigue siendo tuya

`resolveAuth()` tampoco está exportada —vive en `trace-langfuse.mjs`, que al importarse se
queda escuchando stdin—, así que está **duplicada** en `langfuse.mjs`. Es el segundo caso,
después de `bannedTerms()`. El arreglo de fondo es sacar los ayudantes compartidos a un
módulo propio, como ya se hizo con `usage.mjs`, `otlp.mjs` y `handoff.mjs`, y eso es tocar
hooks. Con dos duplicados ya no es una excepción, es una deuda: dilo y lo hago en un cambio
aparte.

## El envío de prueba del 21-09-2026

Una raíz y un score, los dos con HTTP 200:

```
traceId   9b16a40b06f15746d9afde0b8f426edc
raíz      8abb44f36cf39a9d
score     ce39076c43a3ac3b35902c77ed54a6db   voice-editor-no-anade · -8 · NUMERIC
```

Salió con el esquema viejo, el de un nombre con dos tipos. Ese score queda en Langfuse como
residuo de la prueba y **no se va a reescribir**: con el esquema nuevo, `voice-editor-no-anade`
es BOOLEAN y tiene otro id. Conviene borrarlo a mano en la UI, o dejarlo sabiendo que es el
único punto NUMERIC bajo ese nombre.

El 200 demuestra que el endpoint no rechaza `metadata` ni el `id` determinista. No demuestra
que los guarde: eso hay que verlo en la UI.

Las dos marcas de ese envío se borraron de `.trace/sent/`.

**Prueba de idempotencia del servidor.** El mismo score BOOLEAN, dos POST seguidos con el
mismo id, saltándose la marca local a propósito. Los dos con HTTP 200 y los dos devolviendo
**el id que se envió**, no uno generado por el servidor: el endpoint acepta id de cliente.
Que además deduplique es compatible con esa respuesta pero no está demostrado desde aquí;
se ve en la UI, contando cuántos `voice-editor-no-anade` hay en la traza.

## `scores@2`: la traza cambia cuando cambia la codificación

El `evalRunId` no lleva el commit, así que commitear no daba traza nueva y el envío completo
habría reenviado la raíz de la prueba. Lo que sí cambió es **cómo** se codifican los mismos
resultados en scores —de 67 a 91, con otros nombres y otros tipos—, y eso sí entra ahora en
el hash como `SCORES_SCHEMA`. Los mismos números contados de otra forma no pueden convivir en
una traza: una serie con dos codificaciones no se puede leer.

Con `scores@2` la identidad es otra, y la raíz de la prueba no se toca:

```
evalRunId  f7a20fdbf477c615
traceId    c68a0843f27ea339886059ca8d0fa442
raíz       cd5dd61d1aeed1d1
```

Hay además una guarda que aborta si la raíz volviera a ser `8abb44f36cf39a9d`, para que sea
una garantía y no una deducción.

## Tres guardas antes de cualquier envío

1. **La raíz de la prueba no se reenvía**, por id.
2. **Ningún nombre de score puede mezclar tipos.** Se comprueba sobre los 91 reales, no
   sobre el razonamiento — que es de donde salió el fallo de `scores@1`.
3. **El árbol de git tiene que estar limpio.** La raíz lleva el commit como metadata; con
   cambios sin commitear ese commit describe un código que no produjo estos números, y una
   traza que miente sobre su origen es peor que no tenerla. Si `git` no se puede consultar,
   tampoco se envía.

Ninguna aplica a `--selftest`, que no sale a la red.

## El desglose de los 91

| nombre | tipo | n |
|---|---|---|
| `canon-resoluble` | BOOLEAN | 34 |
| `issues-schema-valido` | BOOLEAN | 6 |
| `issues-violaciones` | NUMERIC | 6 |
| `longitud-desviacion` | NUMERIC | 9 |
| `longitud-en-rango` | BOOLEAN | 9 |
| `sin-terminos-prohibidos` | BOOLEAN | 9 |
| `voice-editor-delta-palabras` | NUMERIC | 9 |
| `voice-editor-no-anade` | BOOLEAN | 9 |

67 veredictos, uno por resultado, y 24 medidas. Con `scores@1` eran 67 a secas: un score por
resultado, con el nombre del evaluator y el tipo cambiando según el evaluator.


## El envío completo del 21-09-2026, y el límite de ritmo

La raíz entró con HTTP 200 y **29 de los 91 scores**; los otros 62 rebotaron con **429**:

```
{"code":"rate_limited","details":{"retryAfterSeconds":56,"limit":30,"remaining":0}}
```

Treinta por minuto en el endpoint de scores. El enviador los mandaba seguidos, sin pausa, así
que el servidor cortó en el trigésimo. Las marcas se comportaron como debían: 30 escritas,
exactamente las de los 2xx, y 62 líneas de 429 en `.langfuse-errors.log`.

```
traceId   c68a0843f27ea339886059ca8d0fa442
raíz      cd5dd61d1aeed1d1        enviada, con marca
commit    35f8df33de10ca775f3712cc890cbe68354ebbc6
```

**La raíz refleja el commit `35f8df3`, y el control de ritmo se añadió después.** No cambia
ningún resultado: los 91 scores salen de `evals/out/results.json`, que no se ha vuelto a
generar, y el `evalRunId` no depende del commit sino de la huella de los resultados más
`scores@2`. Por eso los 62 que faltan van a la misma traza que los 29 que ya entraron, que es
lo que se quiere. Lo único que cambió es el ritmo al que salen.

### Cómo se respeta el límite

Dos frenos, y el segundo es el que lo garantiza:

- **espaciado fijo** de 2,5 s entre envíos, o sea 24 por minuto, que evita el 429 en el caso
  normal;
- **ventana deslizante** que no deja pasar más de 29 en 60 s, que lo sostiene aunque el
  espaciado se quede corto.

Ante un 429 se espera lo que pida el servidor más un segundo y se reintenta **ese** score,
porque no llegó a entrar. Cualquier otro error no se reintenta: un 400 volvería a ser 400.
Tras tres esperas seguidas sin pasar, se detiene y lo dice, en vez de insistir.

El reloj y la espera se inyectan, así que los cuatro casos —el reintento tras 429, el límite
por ventana, que un 429 no deje marca y que un 400 no se reintente— se prueban con reloj
simulado y sin que pase el tiempo.
