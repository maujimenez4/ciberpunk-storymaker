#!/usr/bin/env node
// PostToolUse sobre Task · telemetría a Langfuse por OTLP (v4).
//
// No es una guarda: no deniega nada y no puede romper una corrida. Es el sustituto
// fiable de `run-log.jsonl`, que el orquestador escribe a mano y por eso se desalinea
// —en la corrida de neon-smoke perdió el 10,5 % de los tokens—. Este hook corre fuera
// del modelo, después de cada subagente, así que no depende de que nadie se acuerde.
//
// Agrupa en una traza por fase: una para el setup y una por capítulo. Cada llamada a
// subagente es un span dentro de su traza, así que el dashboard enseña el coste por
// capítulo y por rol sin tener que sumar nada.
//
// ── Por qué OTLP y no el endpoint de siempre ──────────────────────────────────────
// Langfuse Cloud apaga `/api/public/ingestion` el 16-11-2026: desde esa fecha solo
// acepta `score-create`. El envío antiguo se quitó entero en el mismo cambio, no se
// dejó detrás de un flag: mandar los mismos ids por las dos vías al mismo proyecto es
// justo lo que la guía de migración prohíbe.
//
// ── La raíz ───────────────────────────────────────────────────────────────────────
// Langfuse exige un span raíz y este hook vive en un proceso que muere tras cada
// subagente: no puede sostener abierto un span de fase. Así que los hijos se emiten al
// vuelo apuntando a un `parentSpanId` **derivable de la traza**, y la raíz se emite
// después, al cerrar la fase (`--close-trace`), con la duración real que dan los hijos
// ya registrados. Si una corrida se interrumpe y deja la raíz sin emitir, la recoge
// `--sweep` al principio de la siguiente.
//
// ── Idempotencia ──────────────────────────────────────────────────────────────────
// El `spanId` sale de `sha256(tool_use_id)`, así que es el mismo si el hook se repite.
// Pero v4 no deduplica de forma fiable, de modo que además se deja una marca en
// `.trace/sent/<spanId>` tras un 2xx y ese span no se vuelve a mandar. Un timeout **no**
// se reintenta solo: no se sabe si el otro lado lo ingirió, y un duplicado silencioso
// estropea el coste por capítulo más que un hueco declarado.
//
// Credenciales, por orden: LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY, o la cabecera
// Authorization que ya tiene configurada el servidor MCP de Langfuse en ~/.claude.json.
// El hook nunca imprime la credencial, ni siquiera en el log de errores.
//
// Comprobación en seco, sin enviar nada:
//   node .claude/hooks/trace-langfuse.mjs --selftest < tests/fixtures/hooks/<x>.json

import { readFileSync, writeFileSync, existsSync, readdirSync, appendFileSync, statSync, mkdirSync } from 'node:fs';
import { createHash, randomUUID } from 'node:crypto';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { traceIdOf, spanIdOf, rootSpanIdOf, span, envelope, postSpans } from './otlp.mjs';
import { usageOf } from './usage.mjs';
import { parseTraceHeader } from './handoff.mjs';

const argv = process.argv.slice(2);
const has = (flag) => argv.includes(flag);
const arg = (name) => {
  const hit = argv.find((a) => a.startsWith(`${name}=`));
  if (hit) return hit.slice(name.length + 1);
  const at = argv.indexOf(name);
  return at >= 0 ? argv[at + 1] : null;
};

const SELFTEST = has('--selftest');
const CANARY = has('--canary');
const CLOSE = has('--close-trace');
const SWEEP = has('--sweep');
const TIMEOUT_MS = 5000;

/** Un hook de telemetría que rompe la corrida es peor que no tener telemetría. */
const done = () => { process.stdout.write('{}'); process.exit(0); };

const readJson = (path) => {
  try { return JSON.parse(readFileSync(path, 'utf8')); } catch { return null; }
};

const traceDir = (novelDir) => `${novelDir}/.trace`;
const ensure = (dir) => { try { mkdirSync(dir, { recursive: true }); } catch { /* da igual */ } };

/**
 * A qué novela pertenece esta llamada.
 *
 * La versión anterior devolvía null en cuanto había más de una novela con estado, y un
 * null aquí apaga el hook **en silencio**: en la segunda corrida no se trazó nada y no
 * hubo ni un error que lo dijera. Con dos novelas en el repo eso pasa de caso raro a
 * caso normal.
 *
 * El orden va de la señal más fiable a la más débil:
 *   1. El encargo al subagente lleva las rutas de su novela. Es indiscutible.
 *   2. Una sola novela con estado: es esa.
 *   3. Varias y ningún indicio: la de estado escrito más recientemente es la que corre.
 */
function findNovelDir(cwd, hint) {
  const base = `${String(cwd ?? '').replace(/\\/g, '/')}/novels`;
  if (!existsSync(base)) return null;
  const slugs = readdirSync(base, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name)
    .filter((n) => existsSync(`${base}/${n}/run-state.json`));
  if (!slugs.length) return null;

  const named = String(hint ?? '').match(/novels[/\\]([^/\\]+)[/\\]/);
  if (named && slugs.includes(named[1])) return `${base}/${named[1]}`;
  if (slugs.length === 1) return `${base}/${slugs[0]}`;

  return `${base}/${slugs
    .map((n) => ({ n, at: statSync(`${base}/${n}/run-state.json`).mtimeMs }))
    .sort((a, b) => b.at - a.at)[0].n}`;
}

/** Modelo declarado en el frontmatter del subagente, para que Langfuse pueda imputar coste. */
function modelOf(repoRoot, agentType) {
  const path = `${repoRoot}/.claude/agents/${agentType}.md`;
  if (!agentType || !existsSync(path)) return null;
  const match = readFileSync(path, 'utf8').match(/^model:\s*(\S+)/m);
  return match ? match[1] : null;
}

/** Credenciales. Devuelve la cabecera ya montada, nunca sus partes. */
function resolveAuth() {
  const { LANGFUSE_PUBLIC_KEY: pk, LANGFUSE_SECRET_KEY: sk } = process.env;
  if (pk && sk) {
    return { header: `Basic ${Buffer.from(`${pk}:${sk}`).toString('base64')}`, from: 'env' };
  }
  try {
    const cfg = JSON.parse(readFileSync(join(homedir(), '.claude.json'), 'utf8'));
    for (const project of Object.values(cfg.projects ?? {})) {
      for (const [name, server] of Object.entries(project.mcpServers ?? {})) {
        const header = server?.headers?.Authorization;
        if (/langfuse/i.test(name) && header) return { header, from: 'mcp' };
      }
    }
  } catch { /* sin configuración legible no hay credencial */ }
  return null;
}

function host() {
  return (process.env.LANGFUSE_HOST ?? 'https://us.cloud.langfuse.com').replace(/\/$/, '');
}

/**
 * Identidad de la corrida.
 *
 * Ningún `run-state.json` del repo tiene `runId`, así que el hook hasheaba
 * `novela:perfil` y **dos corridas de la misma novela escribían en la misma traza**: no se
 * podían comparar, que es el gesto básico de una mejora iterativa.
 *
 * Ahora sale de algo que ya existe y que no escribe el modelo: la sesión. `session_id`
 * viene en todos los sobres de hook y dura lo que dura la corrida; `run.lock` lo confirma
 * con `sessionId` + `startedAt` (nunca `touchedAt`, que se mueve con cada latido). Se
 * cachea en `.trace/run-id` para que `--close-trace` y `--sweep`, que corren desde la
 * línea de órdenes y no tienen sobre, lleguen al mismo valor.
 */
function runIdFor(novelDir, sessionId, state) {
  const dir = traceDir(novelDir);
  const cachePath = `${dir}/run-id`;
  const lock = readJson(`${novelDir}/run.lock`);
  const identity = sessionId
    ?? (lock?.sessionId && lock?.startedAt ? `${lock.sessionId}:${lock.startedAt}` : null)
    ?? state?.runId
    ?? null;

  const cached = readJson(cachePath);
  if (!identity) return cached?.runId ?? createHash('sha256')
    .update(`${state?.novel}:${state?.profile}`).digest('hex').slice(0, 16);
  if (cached?.identity === identity && cached.runId) return cached.runId;

  const runId = createHash('sha256').update(`${state?.novel}:${identity}`).digest('hex').slice(0, 16);
  if (!SELFTEST) {
    ensure(dir);
    try { writeFileSync(cachePath, JSON.stringify({ identity, runId, at: new Date().toISOString() })); } catch { /* seguimos */ }
  }
  return runId;
}

const labelOf = (phase, chapter) =>
  (phase === 'chapter-loop' ? `ch${String(chapter).padStart(2, '0')}` : (phase ?? 'setup'));

// ── Marcas de envío ──────────────────────────────────────────────────────────────
const sentPath = (novelDir, spanId) => `${traceDir(novelDir)}/sent/${spanId}`;
const isSent = (novelDir, spanId) => existsSync(sentPath(novelDir, spanId));
function markSent(novelDir, spanId) {
  try {
    ensure(`${traceDir(novelDir)}/sent`);
    writeFileSync(sentPath(novelDir, spanId), new Date().toISOString());
  } catch { /* si no se puede marcar, lo peor es un duplicado; no se rompe nada */ }
}

/**
 * Los hijos dejan rastro para que la raíz pueda calcular su duración real al cerrarse.
 *
 * Cada fila lleva la identidad entera —runId, novela, perfil, fase— y no solo los tiempos,
 * porque quien cierra la traza puede ser un `--sweep` de la corrida siguiente: para
 * entonces el estado en disco y la caché del runId ya hablan de otra cosa. La raíz se
 * construye con lo que registraron sus hijos, nunca con el presente.
 */
function recordChild(novelDir, traceId, row) {
  try {
    ensure(`${traceDir(novelDir)}/spans`);
    appendFileSync(`${traceDir(novelDir)}/spans/${traceId}.jsonl`, JSON.stringify(row) + '\n');
  } catch { /* la traza sigue siendo válida sin raíz; la recoge --sweep */ }
}

function logError(novelDir, line) {
  try { appendFileSync(`${novelDir}/.langfuse-errors.log`, `${new Date().toISOString()} ${line}\n`); } catch { /* nada */ }
}

/**
 * Envía los spans que no estén ya marcados y marca los que lleguen. Nunca lanza: el peor
 * desenlace posible de esta función es una línea en `.langfuse-errors.log`.
 */
async function deliver(novelDir, spans, tag = '') {
  const pending = spans.filter((s) => !isSent(novelDir, s.spanId));
  if (!pending.length) return { ok: true, skipped: true };

  const auth = resolveAuth();
  if (!auth) {
    logError(novelDir, 'sin credencial: define LANGFUSE_PUBLIC_KEY y LANGFUSE_SECRET_KEY, o configura el MCP de Langfuse');
    return { ok: false, status: 0, body: 'sin credencial' };
  }

  const result = await postSpans({ host: host(), authHeader: auth.header, spans: pending, timeoutMs: TIMEOUT_MS });
  if (result.ok) {
    for (const s of pending) markSent(novelDir, s.spanId);
  } else {
    // Sin reintento automático: tras un timeout no se sabe si el otro lado ingirió, y v4
    // no deduplica de forma fiable. Queda anotado y lo recoge una pasada manual.
    logError(novelDir, `${tag} HTTP ${result.status}: ${result.body}`);
  }
  return result;
}

// ── Atributos comunes ────────────────────────────────────────────────────────────
// Solo lo prefijado como metadata es filtrable en Langfuse; el resto cae en un cajón.
function traceAttrs({ novel, profile, phase, chapter, runId, label }) {
  return {
    'langfuse.trace.name': `${novel} ${label}`,
    'langfuse.session.id': runId,
    'langfuse.trace.tags': JSON.stringify(['storymaker', profile, phase].filter(Boolean)),
    'langfuse.trace.metadata.novel': novel,
    'langfuse.trace.metadata.profile': profile,
    'langfuse.trace.metadata.phase': phase,
    'langfuse.trace.metadata.chapter': chapter,
    'langfuse.trace.metadata.run_id': runId,
  };
}

// ── --close-trace y --sweep ──────────────────────────────────────────────────────

/** Dónde vive el registro de hijos de una traza. */
const spansPath = (novelDir, traceId) => `${traceDir(novelDir)}/spans/${traceId}.jsonl`;

function readChildren(novelDir, traceId) {
  const path = spansPath(novelDir, traceId);
  if (!existsSync(path)) return [];
  return readFileSync(path, 'utf8').trim().split('\n')
    .map((l) => { try { return JSON.parse(l); } catch { return null; } })
    .filter(Boolean);
}

/**
 * Emite la raíz de una traza con la duración real que dan sus hijos ya registrados.
 *
 * El `traceId` se pasa explícito y no se deduce: la primera versión lo derivaba de la
 * caché del runId, así que un `--sweep` podía leer el fichero de una traza y cerrar otra.
 * Todo lo que describe la raíz sale de las filas de sus hijos.
 */
async function closeTrace(novelDir, traceId, { quiet = false } = {}) {
  const rootId = rootSpanIdOf(traceId);
  const children = readChildren(novelDir, traceId);
  if (!children.length) {
    if (!quiet) console.log(`No hay hijos registrados en ${traceId}; nada que cerrar.`);
    return { skipped: true, traceId };
  }
  if (isSent(novelDir, rootId)) {
    if (!quiet) console.log(`La raíz de ${traceId} ya se envió (${rootId}).`);
    return { skipped: true, traceId };
  }

  const primero = children[0];
  const label = primero.label ?? 'setup';
  const startMs = Math.min(...children.map((c) => c.startMs));
  const endMs = Math.max(...children.map((c) => c.endMs));

  const root = span({
    traceId,
    spanId: rootId,
    name: `${primero.novel ?? 'storymaker'} ${label}`,
    startMs,
    endMs,
    attrs: {
      ...traceAttrs({
        novel: primero.novel, profile: primero.profile, phase: primero.phase,
        chapter: primero.chapter, runId: primero.runId, label,
      }),
      'langfuse.observation.type': 'span',
      'langfuse.observation.metadata.children': children.length,
      'langfuse.observation.metadata.closed_by': 'close-trace',
    },
  });

  const result = await deliver(novelDir, [root], `raíz ${label}`);
  if (!quiet) {
    console.log(`Raíz de ${label}: traceId ${traceId}, spanId ${rootId}, ${children.length} hijos, ` +
      `${((endMs - startMs) / 1000).toFixed(1)} s · ${result.ok ? 'enviada' : `FALLO (${result.status})`}`);
  }
  return { traceId, rootId, result };
}

/** Las trazas con hijos registrados en una novela, con su etiqueta y su última actividad. */
function tracesOf(novelDir) {
  const dir = `${traceDir(novelDir)}/spans`;
  if (!existsSync(dir)) return [];
  return readdirSync(dir).filter((f) => f.endsWith('.jsonl')).map((f) => {
    const traceId = f.replace(/\.jsonl$/, '');
    const rows = readChildren(novelDir, traceId);
    return { traceId, label: rows[0]?.label ?? null, runId: rows[0]?.runId ?? null, touchedMs: statSync(`${dir}/${f}`).mtimeMs };
  }).filter((t) => t.label);
}

/**
 * Raíces que quedaron sin emitir. Se salta las trazas con actividad reciente, porque una
 * corrida en marcha todavía está escribiendo hijos y cerrarla ahora la partiría en dos.
 */
async function sweep() {
  const base = `${process.cwd().replace(/\\/g, '/')}/novels`;
  if (!existsSync(base)) return;
  const FRESCO_MS = 30 * 60 * 1000;
  for (const entry of readdirSync(base, { withFileTypes: true }).filter((d) => d.isDirectory())) {
    const novelDir = `${base}/${entry.name}`;
    for (const t of tracesOf(novelDir)) {
      if (isSent(novelDir, rootSpanIdOf(t.traceId))) continue;
      if (Date.now() - t.touchedMs < FRESCO_MS) {
        console.log(`${entry.name}/${t.label}: actividad reciente, se deja para más tarde.`);
        continue;
      }
      const out = await closeTrace(novelDir, t.traceId, { quiet: true });
      if (!out.skipped) {
        console.log(`${entry.name}: raíz de ${t.label} emitida (${t.traceId}) · ` +
          `${out.result?.ok ? 'ok' : `FALLO (${out.result?.status})`}`);
      }
    }
  }
}

// ── Canario ──────────────────────────────────────────────────────────────────────
/**
 * Sustituye al viejo `--ping`. Manda una traza con raíz, un `generation` y un hijo, con un
 * tag único para encontrarla en la UI. El orden importa y es lo primero que comprueba:
 * **primero el hijo, después la raíz**, que es como los va a emitir el hook de verdad. Si
 * Langfuse no reconstruye la jerarquía con el padre llegando tarde, hay que pasar al plan
 * B —raíz en la primera llamada, con la duración marcada como desconocida— y esto lo dice
 * antes de que se haya migrado nada.
 */
async function canary() {
  const auth = resolveAuth();
  if (!auth) {
    console.error('Sin credencial. Define LANGFUSE_PUBLIC_KEY y LANGFUSE_SECRET_KEY, o configura el MCP de Langfuse.');
    process.exit(1);
  }
  const tag = `canary-${new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)}-${randomUUID().slice(0, 8)}`;
  const runId = createHash('sha256').update(tag).digest('hex').slice(0, 16);
  const traceId = traceIdOf(runId, 'canary');
  const rootId = rootSpanIdOf(traceId);
  const genId = spanIdOf(`${tag}:generation`);
  const childId = spanIdOf(`${tag}:child`);

  const end = Date.now();
  const start = end - 4000;
  const base = {
    'langfuse.trace.name': `storymaker canario ${tag}`,
    'langfuse.session.id': runId,
    'langfuse.trace.tags': JSON.stringify(['storymaker', 'canary', tag]),
    'langfuse.trace.metadata.tag': tag,
    'langfuse.trace.metadata.purpose': 'verificacion de migracion v4',
  };

  const generation = span({
    traceId, spanId: genId, parentSpanId: rootId, name: 'canario:generation',
    startMs: start + 500, endMs: start + 3000,
    attrs: {
      ...base,
      'langfuse.observation.type': 'generation',
      'langfuse.observation.model.name': 'claude-haiku-4-5-20251001',
      'langfuse.observation.input': JSON.stringify({ nota: 'entrada sintetica del canario' }),
      'langfuse.observation.output': JSON.stringify({ nota: 'salida sintetica del canario' }),
      'langfuse.observation.usage_details': JSON.stringify({
        input: 10, output: 20, cache_read_input_tokens: 30, cache_creation_input_tokens: 40, total: 100,
      }),
      'langfuse.observation.metadata.rol': 'canario',
    },
  });
  const child = span({
    traceId, spanId: childId, parentSpanId: genId, name: 'canario:hijo',
    startMs: start + 1000, endMs: start + 2000,
    attrs: { ...base, 'langfuse.observation.type': 'span', 'langfuse.observation.metadata.nivel': 'hijo' },
  });
  const root = span({
    traceId, spanId: rootId, name: `canario ${tag}`,
    startMs: start, endMs: end,
    attrs: {
      ...base,
      'langfuse.observation.type': 'span',
      'langfuse.observation.input': JSON.stringify({ tag, orden: 'hijos primero, raiz despues' }),
      'langfuse.observation.output': JSON.stringify({ esperado: 'jerarquia raiz > generation > hijo' }),
    },
  });

  console.log(`Destino:    ${host()}/api/public/otel/v1/traces`);
  console.log(`Credencial: presente (origen: ${auth.from}), esquema ${auth.header.split(' ')[0]}`);
  console.log(`Tag:        ${tag}`);
  console.log(`traceId:    ${traceId}`);
  console.log(`  raíz       ${rootId}`);
  console.log(`  generation ${genId}  (padre: raíz)`);
  console.log(`  hijo       ${childId}  (padre: generation)`);
  console.log('');

  const paso1 = await postSpans({ host: host(), authHeader: auth.header, spans: [generation, child], timeoutMs: TIMEOUT_MS });
  console.log(`1) hijos primero  → HTTP ${paso1.status} ${paso1.ok ? 'ok' : 'FALLO'} ${paso1.body ? `· ${paso1.body}` : ''}`);
  if (!paso1.ok) process.exit(1);

  await new Promise((r) => setTimeout(r, 3000));

  const paso2 = await postSpans({ host: host(), authHeader: auth.header, spans: [root], timeoutMs: TIMEOUT_MS });
  console.log(`2) raíz después   → HTTP ${paso2.status} ${paso2.ok ? 'ok' : 'FALLO'} ${paso2.body ? `· ${paso2.body}` : ''}`);
  if (!paso2.ok) process.exit(1);

  console.log(`
Comprueba en la UI, buscando por el tag ${tag}:
  1. La jerarquía se reconstruyó: raíz > generation > hijo, con el padre llegando tarde.
     Si NO se reconstruye, hay que pasar al plan B (raíz en la primera llamada, duración
     marcada como desconocida) antes de seguir con A1.
  2. Los tiempos: raíz ~4 s, generation ~2,5 s, hijo ~1 s.
  3. Entrada y salida visibles en la raíz y en el generation.
  4. La metadata es filtrable en los tres spans (tag, purpose).
  5. El generation enseña uso y **coste**, y si el coste contempla las claves de caché.`);
  process.exit(0);
}

// ── Puntos de entrada de línea de órdenes ────────────────────────────────────────
if (CANARY) { await canary(); }
if (SWEEP) { await sweep(); process.exit(0); }
if (CLOSE) {
  const slug = arg('--novel');
  const root = process.cwd().replace(/\\/g, '/');
  const novelDir = slug ? `${root}/novels/${slug}` : findNovelDir(root, null);
  if (!novelDir || !existsSync(novelDir)) {
    console.error('No encuentro la novela. Pásala con --novel=<slug>.');
    process.exit(1);
  }
  const state = readJson(`${novelDir}/run-state.json`) ?? {};
  const label = arg('--label') ?? labelOf(state.phase, state.chapter);

  // Se prefiere la traza de la corrida en curso; si no hay, se busca por etiqueta entre
  // las que sí tienen hijos registrados, que es lo que de verdad hay que cerrar.
  let traceId = arg('--trace-id');
  if (!traceId) {
    const candidatas = tracesOf(novelDir).filter((t) => t.label === label);
    const runId = runIdFor(novelDir, null, state);
    traceId = (candidatas.find((t) => t.runId === runId) ?? candidatas[0])?.traceId ?? null;
    if (candidatas.length > 1) {
      console.log(`Aviso: hay ${candidatas.length} trazas con etiqueta ${label} en esta novela. ` +
        `Cierro ${traceId}; las demás las recoge --sweep.`);
    }
  }
  if (!traceId) {
    console.error(`No hay ninguna traza con hijos registrados para "${label}" en ${novelDir}.`);
    process.exit(1);
  }
  const out = await closeTrace(novelDir, traceId);
  process.exit(out.result && !out.result.ok ? 1 : 0);
}

// ── Hook ─────────────────────────────────────────────────────────────────────────
let input = '';
process.stdin.on('data', (chunk) => { input += chunk; });
process.stdin.on('end', async () => {
  let hook;
  try {
    hook = JSON.parse(input);
  } catch {
    done();
  }

  // El harness llama a esta herramienta **Agent**, no `Task`. Filtrar por `Task` a secas
  // hacía que el hook se invocara y saliera aquí mismo, sin trazar nada y sin decir nada:
  // una corrida entera con el dashboard de Langfuse vacío. Se aceptan los dos nombres.
  if (!['Agent', 'Task'].includes(hook.tool_name)) done();

  const repoRoot = String(hook.cwd ?? process.cwd()).replace(/\\/g, '/');
  const novelDir = findNovelDir(repoRoot, hook.tool_input?.prompt);
  if (!novelDir) done(); // Sin corrida identificable no hay nada que atribuir.

  const state = readJson(`${novelDir}/run-state.json`);
  if (!state) done();

  // En seco no se llama a ningún modelo, así que no hay gasto que trazar.
  if (state.dryRun === true) done();

  const agentType = hook.tool_input?.subagent_type ?? 'unknown';
  const response = hook.tool_response ?? {};
  const { details: usage, extras } = usageOf(response);

  // El modelo que de verdad resolvió la llamada, no el que declara el frontmatter.
  const model = response.resolvedModel ?? modelOf(repoRoot, agentType);

  // A0 confirmó que la duración viene en el sobre por dos vías. `totalDurationMs` es el
  // trabajo del subagente; `duration_ms` incluye además el sobrecoste del harness.
  const durationMs = response.totalDurationMs ?? hook.duration_ms ?? null;
  const endMs = Date.now();
  const startMs = durationMs === null ? endMs : endMs - durationMs;

  // El nodo sale del encargo, que no cambia, y no del estado, que el orquestador ya ha
  // podido mover para cuando corre este hook. Si el encabezado falta o no valida, se cae
  // al estado y se deja dicho de dónde vino: un dato dudoso disfrazado de bueno es peor
  // que un hueco declarado.
  const header = parseTraceHeader(hook.tool_input?.prompt);
  const node = header?.node ?? state.node ?? null;
  const attempt = header?.attempt ?? state.attempt ?? null;
  const nodeSource = header ? 'header' : 'state';

  const runId = runIdFor(novelDir, hook.session_id, state);
  const phase = state.phase ?? 'setup';
  const chapter = header?.chapter ?? state.chapter ?? 0;
  const chapterSource = header?.chapter !== null && header?.chapter !== undefined ? 'header' : 'state';
  const label = labelOf(phase, chapter);
  const traceId = traceIdOf(runId, label);
  // Determinista: si el hook se repite sobre la misma llamada, es el mismo span.
  const spanId = spanIdOf(hook.tool_use_id ?? `${traceId}:${agentType}:${endMs}`);

  // §3.2(g): un subagente que falla tiene que distinguirse de uno que va bien.
  const failed = response.status !== undefined && response.status !== 'completed';

  const observation = span({
    traceId,
    spanId,
    parentSpanId: rootSpanIdOf(traceId), // la raíz se emite después; ver cabecera
    name: agentType,
    startMs,
    endMs,
    error: failed ? `estado del subagente: ${response.status}` : null,
    attrs: {
      ...traceAttrs({ novel: state.novel, profile: state.profile, phase, chapter, runId, label }),
      'langfuse.observation.type': 'generation',
      'langfuse.observation.model.name': model,
      'langfuse.observation.usage_details': JSON.stringify(usage),
      'langfuse.observation.level': failed ? 'ERROR' : 'DEFAULT',
      'langfuse.observation.status_message': failed ? `estado del subagente: ${response.status}` : null,
      // Entrada y salida NO van aquí: el prompt en crudo no se manda nunca, y la salida se
      // lee del artefacto en disco. Es el trabajo de A3.
      'langfuse.observation.metadata.agent_type': agentType,
      'langfuse.observation.metadata.agent_id': response.agentId ?? null,
      'langfuse.observation.metadata.tool_use_id': hook.tool_use_id ?? null,
      'langfuse.observation.metadata.node': node,
      'langfuse.observation.metadata.attempt': attempt,
      'langfuse.observation.metadata.node_source': nodeSource,
      'langfuse.observation.metadata.chapter_source': chapterSource,
      'langfuse.observation.metadata.duration_source': durationMs === null ? 'desconocida' : 'totalDurationMs',
      'langfuse.observation.metadata.harness_duration_ms': hook.duration_ms ?? null,
      'langfuse.observation.metadata.tool_uses': response.totalToolUseCount ?? null,
      'langfuse.observation.metadata.read_count': response.toolStats?.readCount ?? null,
      'langfuse.observation.metadata.thinking_tokens': extras.thinking_tokens,
      'langfuse.observation.metadata.ephemeral_5m_input_tokens': extras.ephemeral_5m_input_tokens,
      'langfuse.observation.metadata.ephemeral_1h_input_tokens': extras.ephemeral_1h_input_tokens,
      'langfuse.observation.metadata.iterations': extras.iterations,
      'langfuse.observation.metadata.service_tier': extras.service_tier,
      'langfuse.observation.metadata.speed': extras.speed,
      'langfuse.observation.metadata.reported_total': extras.reported_total,
    },
  });

  if (SELFTEST) {
    process.stdout.write(JSON.stringify({
      resolved: {
        runId, traceId, spanId, parentSpanId: rootSpanIdOf(traceId), label,
        node, node_source: nodeSource, attempt, chapter, chapter_source: chapterSource,
        header,
        would_close: nodeSource === 'header' && ['SEED', 'COMMIT'].includes(node)
          && response.status === 'completed',
        durationMs, startMs, endMs, model, failed, usage, extras,
      },
      would_post_to: `${host()}/api/public/otel/v1/traces`,
      credential: resolveAuth() ? 'presente' : 'NO ENCONTRADA',
      body: envelope([observation]),
    }, null, 2) + '\n');
    process.exit(0);
  }

  // Registro local, siempre y antes de la red: es la fuente del panel y no puede depender
  // de que Langfuse conteste. Una línea por llamada de subagente, que es justo lo que
  // `run-log.jsonl` no consigue por escribirlo el orquestador a mano.
  try {
    appendFileSync(`${novelDir}/agent-calls.jsonl`, JSON.stringify({
      ts: new Date(endMs).toISOString(), runId, agent: agentType, agentId: response.agentId ?? null,
      model, node, nodeSource, phase, chapter, attempt,
      tokens: usage.total, usage, extras, durationMs,
      toolUses: response.totalToolUseCount ?? null, traceId, spanId,
    }) + '\n');
  } catch { /* si no se puede escribir, la corrida sigue igual */ }

  recordChild(novelDir, traceId, {
    spanId, startMs, endMs, name: agentType, label,
    runId, novel: state.novel, profile: state.profile, phase, chapter,
  });

  await deliver(novelDir, [observation], `${agentType} ${label}`);

  // Cierre automático de la traza.
  //
  // SEED y COMMIT son los dos nodos donde una fase termina, así que son el único momento
  // en que se puede emitir la raíz con duración real. Se exige que el nodo venga del
  // **encabezado**: con el del estado esto dispararía en el nodo equivocado, que es
  // justamente el fallo que A1 viene a arreglar. Los bloques de `novela.md` siguen ahí de
  // respaldo, y no duplican nada porque la raíz lleva marca de envío.
  if (nodeSource === 'header' && ['SEED', 'COMMIT'].includes(node) && response.status === 'completed') {
    await closeTrace(novelDir, traceId, { quiet: true });
  }

  // Aquí NO se llama a `done()`: un process.exit() con el handle del fetch todavía
  // cerrándose hace que libuv aborte en Windows con "Assertion failed: !(handle->flags
  // & UV_HANDLE_CLOSING)". Se contesta al harness y se deja que el proceso termine solo
  // cuando el socket se cierre. El hook ya no tiene nada que hacer.
  process.stdout.write('{}');
});
