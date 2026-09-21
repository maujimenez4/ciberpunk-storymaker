# Estado de la migración de telemetría a Langfuse v4

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
| A1 | `node` y `attempt` desde el encargo | pendiente |
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
