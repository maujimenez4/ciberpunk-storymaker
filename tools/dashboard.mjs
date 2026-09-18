#!/usr/bin/env node
// Panel local de StoryMaker: arranque, monitor del bucle y resumen por agente.
//
// Vive en local y no en una página publicada porque necesita dos cosas que una página
// remota no tiene: leer `run-state.json` y `agent-calls.jsonl` del disco, y lanzar una
// corrida. Sin servidor no hay ni monitor ni botón.
//
// Solo escucha en 127.0.0.1. Este proceso puede arrancar corridas, así que no se expone.
//
//   node tools/dashboard.mjs [--port 4173]

import { createServer } from 'node:http';
import { readFileSync, existsSync, writeFileSync, mkdirSync, readdirSync, openSync, appendFileSync, statSync, rmSync } from 'node:fs';
import { spawn } from 'node:child_process';
import { resolve, extname } from 'node:path';
import { hostname } from 'node:os';
import { randomUUID } from 'node:crypto';
import { loadConfig } from './config.js';

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const portFlag = process.argv.indexOf('--port');
const PORT = portFlag !== -1 ? Number(process.argv[portFlag + 1]) : 4173;

const readJson = (path, fallback = null) => {
  try { return JSON.parse(readFileSync(path, 'utf8')); } catch { return fallback; }
};

const readLines = (path) => {
  if (!existsSync(path)) return [];
  return readFileSync(path, 'utf8').split('\n').filter(Boolean)
    .map((line) => { try { return JSON.parse(line); } catch { return null; } })
    .filter(Boolean);
};

const listNovels = () => (existsSync(`${ROOT}/novels`)
  ? readdirSync(`${ROOT}/novels`, { withFileTypes: true }).filter((d) => d.isDirectory()).map((d) => d.name)
  : []);

const listProfiles = () => (existsSync(`${ROOT}/config/profiles`)
  ? readdirSync(`${ROOT}/config/profiles`).filter((f) => f.endsWith('.json')).map((f) => f.replace(/\.json$/, ''))
  : []);

/** Qué rol corre en cada nodo. VAL lanza dos en paralelo, y por eso son dos entradas. */
const NODE_AGENTS = {
  RES0: ['researcher'], ARCH: ['plot-architect'], PROF: ['character-profiler'],
  SEED: ['continuity-keeper'], BEAT: ['beat-planner'], RES1: ['researcher'],
  WRITE: ['scene-writer'], VOICE: ['voice-editor'],
  VAL: ['continuity-keeper', 'technical-verifier'], COMP: ['compiler'],
  COMMIT: ['continuity-keeper'],
};

/** Lo que hay de brief en disco, para que pegar el texto equivocado se vea al momento. */
function briefOf(dir) {
  const path = `${dir}/brief.md`;
  if (!existsSync(path)) return null;
  const text = readFileSync(path, 'utf8');
  return {
    words: (text.match(/\S+/g) ?? []).length,
    sections: (text.match(/^##\s+.*$/gm) ?? []).map((h) => h.replace(/^##\s+/, '')),
    excerpt: text.slice(0, 400),
  };
}

/**
 * La petición de compuerta si sigue sin respuesta, o null.
 *
 * Una decisión responde a una petición solo si es del mismo capítulo y posterior: el
 * `gate-decision.json` de la compuerta anterior se queda en disco, y compararlo solo por
 * existencia daría por contestada una compuerta que nadie ha mirado.
 */
function pendingGate(dir) {
  const request = readJson(`${dir}/gate-request.json`);
  if (!request) return null;
  const decision = readJson(`${dir}/gate-decision.json`);
  const answered = decision
    && decision.chapter === request.chapter
    && Date.parse(decision.decidedAt) >= Date.parse(request.createdAt);
  return answered ? null : request;
}

/** Dónde va el manuscrito según el perfil. La base lo fija en `out/manuscript.md`. */
function loadManuscriptPath(state) {
  try { return loadConfig(state.profile, ROOT).output.manuscriptPath; } catch { return 'out/manuscript.md'; }
}

function snapshot(slug) {
  const dir = `${ROOT}/novels/${slug}`;
  const state = readJson(`${dir}/run-state.json`);
  const brief = briefOf(dir);
  // Una corrida recién lanzada aún no ha escrito estado: eso no es "no hay corrida".
  const launched = existsSync(`${dir}/run-console.log`);
  if (!state) return { novel: slug, missing: true, brief, launched, lock: readLock(dir) };

  const calls = readLines(`${dir}/agent-calls.jsonl`);
  // run-log.jsonl lo escribe el orquestador a mano y a menudo no existe. agent-calls lo
  // escribe el hook, siempre, con nodo y capítulo: sirve de recorrido y es más fiable.
  const log = readLines(`${dir}/run-log.jsonl`);
  const trail = log.length ? log : calls.map((c) => ({
    ts: c.ts, node: c.node, chapter: c.chapter, phase: c.phase, counters: c.counters ?? null,
  }));

  // El resumen sale de agent-calls.jsonl, que escribe el hook fuera del modelo. Si aún
  // no existe —corrida anterior al hook—, se deduce del recorrido de nodos, y se dice.
  const derived = calls.length === 0;
  const perAgent = {};
  const bump = (agent, tokens, node) => {
    perAgent[agent] ??= { agent, calls: 0, tokens: 0, nodes: {} };
    perAgent[agent].calls += 1;
    perAgent[agent].tokens += tokens || 0;
    perAgent[agent].nodes[node] = (perAgent[agent].nodes[node] ?? 0) + 1;
  };
  if (derived) {
    for (const row of trail) for (const a of NODE_AGENTS[row.node] ?? []) bump(a, 0, row.node);
  } else {
    for (const c of calls) bump(c.agent, c.tokens, c.node);
  }

  let scope = null;
  try { scope = loadConfig(state.profile, ROOT).scope; } catch { /* perfil ausente */ }

  const gateRequest = pendingGate(dir);
  const gate = gateRequest
    ? {
        ...gateRequest,
        chapterText: existsSync(`${dir}/${gateRequest.chapterPath}`)
          ? readFileSync(`${dir}/${gateRequest.chapterPath}`, 'utf8')
          : null,
        issues: readJson(`${dir}/${gateRequest.issuesPath}`, { issues: [], counts: {} }),
        act: (gateRequest.actChapters ?? []).map((n) => {
          const p = `${dir}/chapters/ch${String(n).padStart(2, '0')}.md`;
          return { chapter: n, text: existsSync(p) ? readFileSync(p, 'utf8') : null };
        }),
      }
    : null;

  const consolePath = `${dir}/run-console.log`;
  const consoleTail = existsSync(consolePath)
    ? readFileSync(consolePath, 'utf8').split('\n').slice(-40).join('\n')
    : '';

  return {
    novel: slug, state, scope, derived, gate, brief, launched: true,
    lock: readLock(dir),
    // El bucle acaba en EXPORT y `DONE` es el artefacto. Lo que dice si de verdad
    // terminó no es el nodo: es que `out/manuscript.md` esté en disco.
    manuscript: existsSync(`${dir}/${loadManuscriptPath(state)}`),
    agents: Object.values(perAgent).sort((a, b) => b.calls - a.calls),
    totals: {
      calls: Object.values(perAgent).reduce((a, r) => a + r.calls, 0),
      tokens: Object.values(perAgent).reduce((a, r) => a + r.tokens, 0),
    },
    timeline: trail.slice(-60).map((r) => ({
      ts: r.ts, node: r.node, chapter: r.chapter, phase: r.phase, counters: r.counters,
    })),
    calls: calls.slice(-60),
    consoleTail,
    errors: existsSync(`${dir}/.langfuse-errors.log`)
      ? readFileSync(`${dir}/.langfuse-errors.log`, 'utf8').split('\n').filter(Boolean).slice(-5)
      : [],
  };
}

/* ------------------------------------------------------------------ *
 * Historial
 *
 * Todo lo que sigue es de solo lectura y va aparte del monitor a propósito. El monitor
 * se refresca cada segundo; recorrer los capítulos de todas las novelas a ese ritmo
 * sería absurdo, así que el historial se pide al abrir la pestaña y no antes.
 * ------------------------------------------------------------------ */

const pad = (n) => String(n).padStart(2, '0');
const wordsIn = (text) => (text.match(/\S+/g) ?? []).length;

/** Los capítulos escritos, por número. `chNN.draft.md` no cuenta: es el paso previo. */
function chapterNumbers(dir) {
  if (!existsSync(`${dir}/chapters`)) return [];
  return readdirSync(`${dir}/chapters`)
    .filter((f) => /^ch\d+\.md$/.test(f))
    .map((f) => Number(f.slice(2, -3)))
    .sort((a, b) => a - b);
}

/**
 * Título de la novela. El brief lo lleva en su primer `#` y existe siempre; el
 * manuscrito compilado es la segunda opción y el slug la última.
 */
function titleOf(dir, slug) {
  for (const rel of ['brief.md', 'out/manuscript.md']) {
    const path = `${dir}/${rel}`;
    if (!existsSync(path)) continue;
    const match = readFileSync(path, 'utf8').match(/^#\s+(.+)$/m);
    if (match) return match[1].trim();
  }
  return slug;
}

/**
 * Títulos de capítulo del manuscrito compilado, indexados por número.
 *
 * El nivel del encabezado no es estable entre corridas —`##` en dead-floor, `###` en
 * neon-smoke, porque lo decide `compiler` según haya actos o no—, así que se acepta
 * cualquiera de 2 a 4 y el capítulo se saca del número, nunca de la posición.
 */
function chapterTitles(dir) {
  const path = `${dir}/out/manuscript.md`;
  if (!existsSync(path)) return {};
  const titles = {};
  const pattern = /^#{2,4}\s*Cap[íi]tulo\s+(\d+)\s*(?:[—–-]\s*)?(.*)$/gm;
  for (const match of readFileSync(path, 'utf8').matchAll(pattern)) {
    const title = match[2].trim().replace(/^[«"']+|[»"']+$/g, '').trim();
    titles[Number(match[1])] = title || null;
  }
  return titles;
}

/**
 * Título de un capítulo, del manuscrito si existe y del plan de beats si no.
 *
 * El manuscrito solo aparece al compilar, así que una novela parada en compuerta tendría
 * todos los capítulos sin título justo cuando más apetece mirarlos. `beat-planner` ya
 * puso uno en su primera línea y sirve igual de bien.
 */
function chapterTitle(dir, n, fromManuscript) {
  if (fromManuscript[n]) return fromManuscript[n];
  const beats = `${dir}/notes/ch${pad(n)}-beats.md`;
  if (!existsSync(beats)) return null;
  const match = readFileSync(beats, 'utf8').match(/^#\s+(.+)$/m);
  return match ? match[1].trim() : null;
}

/** Agregado de `agent-calls.jsonl`. `measured: false` = corrida anterior al hook. */
function callStats(dir) {
  const calls = readLines(`${dir}/agent-calls.jsonl`);
  const empty = { calls: 0, tokens: 0, first: null, last: null, byChapter: {}, agents: [], measured: false };
  if (!calls.length) return empty;

  const byChapter = {};
  const byAgent = {};
  let tokens = 0;
  for (const call of calls) {
    tokens += call.tokens || 0;
    const key = call.phase === 'chapter-loop' ? call.chapter : 0;
    byChapter[key] = (byChapter[key] ?? 0) + (call.tokens || 0);
    byAgent[call.agent] ??= { agent: call.agent, calls: 0, tokens: 0 };
    byAgent[call.agent].calls += 1;
    byAgent[call.agent].tokens += call.tokens || 0;
  }
  const stamps = calls.map((c) => c.ts).filter(Boolean).sort();
  return {
    calls: calls.length, tokens, byChapter, measured: true,
    first: stamps[0] ?? null, last: stamps[stamps.length - 1] ?? null,
    agents: Object.values(byAgent).sort((a, b) => b.calls - a.calls),
  };
}

/** Última vez que la corrida tocó el disco, mire donde mire. */
function lastTouch(dir) {
  return ['run-state.json', 'run-console.log', 'agent-calls.jsonl']
    .map((f) => (existsSync(`${dir}/${f}`) ? statSync(`${dir}/${f}`).mtimeMs : 0))
    .reduce((a, b) => Math.max(a, b), 0);
}

/**
 * En qué punto quedó la corrida.
 *
 * `stale` no lo escribe nadie: es una corrida que ni terminó ni espera decisión y que
 * lleva una hora sin tocar el disco. Sin ese estado, una corrida muerta se enseñaría
 * como "en curso" para siempre, que es justo lo que un historial no debe hacer.
 */
const STALE_MS = 60 * 60 * 1000;
function statusOf(dir, state, gateOpen) {
  if (!state) return existsSync(`${dir}/run-console.log`) ? 'launched' : 'never-run';
  if (state.phase === 'done') return 'done';
  if (gateOpen) return 'gate';
  return Date.now() - lastTouch(dir) > STALE_MS ? 'stale' : 'running';
}

/** Las incidencias de un capítulo, tal como las dejó el reporte. */
function issuesOf(dir, n) {
  const report = readJson(`${dir}/notes/ch${pad(n)}-issues.json`);
  return {
    issues: report?.issues ?? [],
    counts: { blocker: 0, warning: 0, note: 0, ...(report?.counts ?? {}) },
  };
}

/** Ficha de una novela para la rejilla. Sin una línea de prosa: esto se pide en bloque. */
function historyCard(slug) {
  const dir = `${ROOT}/novels/${slug}`;
  const state = readJson(`${dir}/run-state.json`);
  const gate = pendingGate(dir);
  const stats = callStats(dir);

  let scope = null;
  try { if (state?.profile) scope = loadConfig(state.profile, ROOT).scope; } catch { /* perfil ausente */ }

  const numbers = chapterNumbers(dir);
  const counts = { blocker: 0, warning: 0, note: 0 };
  let words = 0;
  for (const n of numbers) {
    words += wordsIn(readFileSync(`${dir}/chapters/ch${pad(n)}.md`, 'utf8'));
    const chapter = issuesOf(dir, n).counts;
    counts.blocker += chapter.blocker;
    counts.warning += chapter.warning;
    counts.note += chapter.note;
  }

  const touched = lastTouch(dir);
  return {
    slug,
    title: titleOf(dir, slug),
    profile: state?.profile ?? null,
    status: statusOf(dir, state, Boolean(gate)),
    gateChapter: gate?.chapter ?? null,
    node: state?.node ?? null,
    // `progress` son los contadores y `chapters` es la lista, en los dos endpoints. Antes
    // el objeto de progreso también se llamaba `chapters` y el detalle lo pisaba con la
    // lista, así que en la ficha de una novela los contadores salían vacíos.
    progress: {
      written: numbers.length,
      approved: state?.lastApprovedChapter ?? 0,
      planned: scope?.chapters ?? null,
      numbers,
    },
    flagged: state?.flagged ?? [],
    words,
    issues: counts,
    calls: stats.calls,
    tokens: stats.tokens,
    measured: stats.measured,
    // Una barra por capítulo escrito, en orden. Alimenta el sparkline de la tarjeta.
    tokensByChapter: numbers.map((n) => stats.byChapter[n] ?? 0),
    startedAt: stats.first,
    updatedAt: state?.updatedAt ?? null,
    touchedAt: touched ? new Date(touched).toISOString() : null,
    manuscript: existsSync(`${dir}/out/manuscript.md`),
  };
}

const historyIndex = () => listNovels()
  .map(historyCard)
  .sort((a, b) => Date.parse(b.touchedAt ?? 0) - Date.parse(a.touchedAt ?? 0));

/** Detalle de una novela: capítulos con su resumen de la biblia y sus incidencias. */
function historyNovel(slug) {
  const dir = `${ROOT}/novels/${slug}`;
  if (!existsSync(dir)) return null;

  const titles = chapterTitles(dir);
  const stats = callStats(dir);
  const chapters = chapterNumbers(dir).map((n) => {
    const summaryPath = `${dir}/bible/summaries/ch${pad(n)}.md`;
    return {
      chapter: n,
      title: chapterTitle(dir, n, titles),
      words: wordsIn(readFileSync(`${dir}/chapters/ch${pad(n)}.md`, 'utf8')),
      hasDraft: existsSync(`${dir}/chapters/ch${pad(n)}.draft.md`),
      // El resumen de `continuity-keeper`, sin su encabezado: es lo único que los
      // capítulos siguientes llegaron a saber de este, así que es lo que hay que enseñar.
      summary: existsSync(summaryPath)
        ? readFileSync(summaryPath, 'utf8').replace(/^#\s+.*\n/, '').trim()
        : null,
      ...issuesOf(dir, n),
    };
  });

  return {
    ...historyCard(slug),
    brief: briefOf(dir),
    agents: stats.agents,
    chapters,
  };
}

/** El texto de un capítulo, o el manuscrito entero con `chapter=all`. Bajo demanda. */
function historyText(slug, chapter) {
  const dir = `${ROOT}/novels/${slug}`;
  if (!existsSync(dir)) return null;

  if (chapter === 'all') {
    const path = `${dir}/out/manuscript.md`;
    if (!existsSync(path)) return null;
    return { slug, chapter: 'all', title: titleOf(dir, slug), text: readFileSync(path, 'utf8') };
  }

  const n = Number(chapter);
  if (!Number.isInteger(n) || n < 1) return null;
  const path = `${dir}/chapters/ch${pad(n)}.md`;
  if (!existsSync(path)) return null;
  return {
    slug, chapter: n,
    title: chapterTitle(dir, n, chapterTitles(dir)),
    text: readFileSync(path, 'utf8'),
  };
}

// Herramientas que el bucle necesita. En modo headless nadie puede aprobar un permiso,
// así que sin esta lista el orquestador recibe "permiso denegado" en cuanto intenta
// `node tools/config.js` y la corrida muere en el arranque. Es una lista explícita y no
// un bypass general: la lista `deny` de .claude/settings.json —git push, rm -rf,
// git reset --hard— sigue por delante.
// WebSearch va aquí porque sin ella `researcher` no puede buscar, y entonces todos los
// huecos del dossier quedan declarados y sin rellenar: en la corrida de dead-floor eso
// produjo cinco incidencias, todas del mismo patrón, y una reescritura por capítulo.
// Que esté permitida no la abre a todos: guard-permissions sigue denegando el acceso web
// a cualquier rol que no sea researcher.
const ALLOWED_TOOLS = process.env.STORYMAKER_ALLOWED_TOOLS
  ?? 'Read Write Edit Bash Task Glob Grep WebSearch';

/* ------------------------------------------------------------------ *
 * Lock por novela
 *
 * Dos orquestadores sobre el mismo slug se destruyen en silencio: comparten biblia,
 * capítulos y un único `run-state.json`, así que cada uno lee el estado que el otro
 * acaba de escribir. Pasó de verdad en `within-tolerance` —dos `setup: bible seed`,
 * capítulos de dos genealogías mezclados— y no lo detectó ningún mecanismo: lo vio un
 * humano leyendo los commits.
 *
 * El lock es un fichero con el PID. No es un semáforo del sistema operativo y no
 * pretende serlo: cubre el caso que el panel puede provocar por sí mismo, que ahora es
 * el más probable porque responder una compuerta relanza la corrida.
 * ------------------------------------------------------------------ */

const lockPath = (dir) => `${dir}/run.lock`;

/** ¿Sigue vivo ese PID? `kill(pid, 0)` no envía señal: solo pregunta. */
function alivePid(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    // EPERM = existe pero es de otro usuario. Existe, que es lo que se pregunta.
    return error.code === 'EPERM';
  }
}

/**
 * Cuánto aguanta un lock sin señales de vida. Tiene que ser el mismo número que usa
 * `guard-run-lock.mjs`: si el panel caducara antes, reclamaría el lock de una corrida
 * que el hook todavía da por viva, y volveríamos a tener dos.
 */
const LOCK_STALE_MS = 10 * 60 * 1000;

/**
 * El lock vigente de una novela, o null.
 *
 * Dos clases de dueño y por eso dos formas de comprobar que sigue ahí:
 *
 * - **El panel**, que escribe su `pid` y se puede preguntar al sistema si vive.
 * - **Una sesión de Claude Code**, que no tiene PID que consultar desde aquí. Su prueba
 *   de vida es `touchedAt`: `guard-run-lock.mjs` lo refresca en cada escritura.
 *
 * Un lock que no pasa ninguna de las dos es basura de una corrida que murió sin soltarlo
 * —un Ctrl-C, un apagón, un panel cerrado a lo bruto—. Se puede reclamar, y se dice en la
 * respuesta para que no parezca que el lock no llegó a escribirse.
 */
function readLock(dir) {
  const lock = readJson(lockPath(dir));
  if (!lock) return null;
  const touched = Date.parse(lock.touchedAt ?? lock.startedAt ?? 0);
  const fresco = Number.isFinite(touched) && Date.now() - touched < LOCK_STALE_MS;
  const vivo = alivePid(lock.pid) || fresco;
  return { ...lock, alive: vivo, stale: !vivo };
}

/** Toma el lock o explica quién lo tiene. Lanza: el error sube al 400 del endpoint. */
function acquireLock(dir, slug, profile, runToken) {
  const held = readLock(dir);
  if (held?.alive) {
    // El dueño puede ser este panel —hay PID— o una sesión de Claude Code lanzada a mano,
    // que no lo tiene. Decir cuál es lo que convierte el error en algo accionable.
    const quien = held.childPid ?? held.pid
      ? `PID ${held.childPid ?? held.pid}`
      : `sesión ${String(held.sessionId ?? '?').slice(0, 8)}, lanzada fuera del panel`;
    throw new Error(
      `Ya hay una corrida de "${slug}" en marcha (${quien}, desde las `
      + `${new Date(held.startedAt).toTimeString().slice(0, 5)}). Dos corridas sobre la misma `
      + 'novela se pisan la biblia y los capítulos. Espera a que termine o para ese proceso.',
    );
  }
  // Sin `sessionId`: lo pone el orquestador hijo al adoptarlo en su primera escritura, y
  // a partir de ahí `guard-run-lock.mjs` lo defiende de cualquier otra sesión.
  const stamp = new Date().toISOString();
  writeFileSync(lockPath(dir), JSON.stringify({
    lock: 'storymaker/run-lock@1',
    novel: slug, profile, pid: process.pid,
    // El testigo que identifica a la corrida que este panel va a lanzar. Solo quien lo
    // trae en el entorno puede adoptar este lock, así que no hay carrera que ganar.
    runToken,
    startedAt: stamp, touchedAt: stamp,
    host: hostname(),
  }, null, 2) + '\n');
  return held?.stale ? (held.pid ?? held.sessionId) : null;
}

/** Suelta el lock solo si sigue siendo nuestro: nunca el de otro proceso. */
function releaseLock(dir) {
  const held = readJson(lockPath(dir));
  if (held?.pid === process.pid) {
    try { rmSync(lockPath(dir)); } catch { /* ya no está, da igual */ }
  }
}

/**
 * Lanza `/novela <perfil>` en segundo plano, con la salida a run-console.log.
 *
 * Tres cosas aquí son cicatrices de fallos reales, no preferencias:
 *
 * 1. **Sin `detached`.** Con `detached: true` en Windows el proceso pierde la consola y
 *    `claude` sale con código 1 sin escribir una línea. Medido: sin detach exit=0 y
 *    salida capturada; con detach exit=1 y fichero vacío. El precio es que la corrida
 *    vive mientras viva el panel, que para un panel es lo que se quiere.
 * 2. **El prompt por stdin.** `claude` es un .cmd y hay que pasar por cmd.exe, pero con
 *    `shell: true` Node concatena los argumentos sin escapar y cualquier token con
 *    espacio se parte. Por stdin no hay comillas que perder.
 * 3. **cmd.exe como ejecutable, no `shell: true`.** Así el binario no lleva espacios y
 *    se controla la línea de comando entera.
 */
function spawnRun(profile, slug, dir) {
  // El testigo que hace inequívoco quién es el dueño del lock: va dentro del fichero y
  // viaja al hijo en el entorno. Sin él, la corrida que el panel acaba de lanzar tenía
  // que deducir de la tabla de procesos si era ella misma, y una vez dedujo que no: se
  // negó a empezar creyéndose un intruso.
  const runToken = randomUUID();

  // Antes de nada: si ya hay una corrida viva sobre esta novela, esto no sale de aquí.
  const reclaimed = acquireLock(dir, slug, profile, runToken);
  if (reclaimed) {
    appendFileSync(`${dir}/run-console.log`,
      `\n[panel] lock huérfano del PID ${reclaimed} reclamado: ese proceso ya no existe.\n`);
  }

  const out = openSync(`${dir}/run-console.log`, 'a');
  const isWindows = process.platform === 'win32';
  const args = ['-p', '--allowedTools', ...ALLOWED_TOOLS.split(/\s+/)];

  // `guard-run-lock.mjs` lee el testigo del entorno: los hooks los lanza `claude`, así
  // que heredan esto sin que haya que pasárselo por ningún otro sitio.
  const env = { ...process.env, STORYMAKER_RUN_TOKEN: runToken };

  let child;
  try {
    child = isWindows
      ? spawn(process.env.COMSPEC || 'cmd.exe', ['/d', '/s', '/c', `claude ${args.join(' ')}`], {
          cwd: ROOT, stdio: ['pipe', out, out], windowsHide: true, env })
      : spawn('claude', args, { cwd: ROOT, stdio: ['pipe', out, out], env });
  } catch (error) {
    // Un lock retenido por una corrida que nunca llegó a existir bloquea la novela entera.
    releaseLock(dir);
    throw error;
  }

  // El PID del hijo se anota para que el mensaje de "ya hay una corrida" diga qué parar.
  // El dueño del lock sigue siendo el panel: el hijo no sobrevive a este proceso.
  const held = readJson(lockPath(dir));
  if (held) writeFileSync(lockPath(dir), JSON.stringify({ ...held, childPid: child.pid }, null, 2) + '\n');

  child.stdin.end(`/novela ${profile}\n`);
  // El código de salida va al mismo log: una corrida que muere al arrancar deja de ser
  // un fichero vacío y pasa a decir por qué.
  child.on('exit', (code, signal) => {
    releaseLock(dir);
    appendFileSync(`${dir}/run-console.log`,
      `\n[panel] proceso terminado · código ${code}${signal ? ` · señal ${signal}` : ''}\n`);
  });
  child.on('error', (error) => {
    releaseLock(dir);
    appendFileSync(`${dir}/run-console.log`, `\n[panel] no se pudo lanzar: ${error.message}\n`);
  });
  return child.pid;
}

/**
 * Responde una compuerta y relanza. La corrida anterior terminó al llegar a GATE: el
 * estado está en disco y el bucle sabe reanudar, así que continuar es arrancar de nuevo.
 * Sale más barato y más robusto que dejar un proceso bloqueado esperando un fichero.
 */
function decideGate({ profile, action, notes, rollbackTo }) {
  if (!['approve', 'revise', 'rollback'].includes(action)) {
    throw new Error(`Decisión desconocida: "${action}".`);
  }
  const cfg = loadConfig(profile, ROOT);
  const dir = `${ROOT}/novels/${cfg.run.novel}`;
  const request = readJson(`${dir}/gate-request.json`);
  if (!request) throw new Error('No hay ninguna compuerta abierta para esta novela.');
  if (action === 'revise' && !(notes ?? '').trim()) {
    throw new Error('Una revisión sin notas no le dice nada al escritor. Escribe qué falla.');
  }
  if (action === 'rollback' && !(rollbackTo >= 1 && rollbackTo < request.chapter)) {
    throw new Error(`El rollback tiene que apuntar a un capítulo entre 1 y ${request.chapter - 1}.`);
  }

  // El lock se comprueba **antes** de escribir la decisión, y no dentro de `spawnRun`.
  // Al revés, una compuerta rechazada por el lock dejaba el `gate-decision.json` escrito
  // con fecha fresca: `pendingGate()` la daba por contestada, el panel escondía la
  // compuerta y nadie había relanzado nada. La decisión se perdía en silencio.
  const held = readLock(dir);
  if (held?.alive) {
    throw new Error(
      `Ya hay una corrida de "${cfg.run.novel}" en marcha (PID ${held.childPid ?? held.pid}). `
      + 'No se ha registrado la decisión: responder la compuerta relanza la corrida, y dos '
      + 'sobre la misma novela se pisan la biblia y los capítulos.',
    );
  }

  writeFileSync(`${dir}/gate-decision.json`, JSON.stringify({
    decision: 'storymaker/gate-decision@1',
    novel: cfg.run.novel, chapter: request.chapter,
    action, notes: notes ?? null, rollbackTo: rollbackTo ?? null,
    decidedAt: new Date().toISOString(),
  }, null, 2) + '\n');

  return {
    slug: cfg.run.novel, chapter: request.chapter, action,
    pid: spawnRun(profile, cfg.run.novel, dir),
  };
}

function startRun({ profile, brief }) {
  // La novela la fija el perfil y nada más. Aceptar aquí un slug suelto escribiría el
  // brief en un sitio mientras `/novela <perfil>` corre sobre otro: un perfil por novela.
  const cfg = loadConfig(profile, ROOT);
  const slug = cfg.run.novel;
  const dir = `${ROOT}/novels/${slug}`;
  mkdirSync(dir, { recursive: true });

  // El brief es la entrada de la novela: si el formulario trae texto, se escribe. Si no,
  // se conserva el que ya hubiera. Nunca se borra uno existente con un campo vacío.
  if (brief && brief.trim()) writeFileSync(`${dir}/brief.md`, brief.trim() + '\n');
  if (!existsSync(`${dir}/brief.md`)) {
    throw new Error(`No hay brief para "${slug}". Escribe uno en el formulario: sin brief el bucle para en el arranque.`);
  }

  return { slug, pid: spawnRun(profile, slug, dir), profile };
}

const send = (res, code, body, type = 'application/json') => {
  res.writeHead(code, { 'Content-Type': `${type}; charset=utf-8`, 'Cache-Control': 'no-store' });
  res.end(typeof body === 'string' ? body : JSON.stringify(body));
};

const DIST = `${ROOT}/tools/dashboard/dist`;
const norm = (p) => p.replace(/\\/g, '/');

const MIME = {
  '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
  '.json': 'application/json', '.map': 'application/json', '.svg': 'image/svg+xml',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp',
  '.ico': 'image/x-icon', '.woff': 'font/woff', '.woff2': 'font/woff2',
};

/**
 * El panel sin construir no puede devolver un 404 mudo: quien abre el puerto quiere ver
 * el panel y lo que necesita es el comando exacto, no un fallo del navegador.
 */
const BUILD_ME = `<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>StoryMaker — falta construir el panel</title>
<style>body{font:16px/1.6 system-ui,sans-serif;max-width:46rem;margin:12vh auto;padding:0 1.5rem;color:#233441}
code{background:#F4F7F8;border:1px solid #E3E9ED;border-radius:6px;padding:.15em .45em;font-size:.9em}
h1{font-size:1.5rem;letter-spacing:-.02em}</style></head><body>
<h1>El panel no está construido</h1>
<p>El servidor funciona, pero <code>tools/dashboard/dist/</code> no existe todavía. El panel
se compila con Vite y el build no se versiona.</p>
<p>Para construirlo y servirlo de una vez:</p>
<p><code>npm install &amp;&amp; npm run panel</code></p>
<p>Para desarrollar con recarga en caliente, deja este proceso vivo y arranca
<code>npm run panel:dev</code> en otra terminal.</p>
</body></html>`;

/**
 * Sirve el build del panel.
 *
 * La ruta se resuelve y se comprueba que cae dentro de `dist/` antes de abrir nada. Este
 * proceso puede lanzar corridas, así que un `..` que se escapara no sería un fallo
 * cosmético; que solo escuche en localhost no es razón para saltarse la comprobación.
 */
function serveStatic(pathname, res) {
  if (!existsSync(DIST)) return send(res, 503, BUILD_ME, 'text/html');

  const distRoot = norm(resolve(DIST));
  const target = norm(resolve(DIST, `.${pathname === '/' ? '/index.html' : pathname}`));
  if (target !== distRoot && !target.startsWith(`${distRoot}/`)) {
    return send(res, 403, { error: 'ruta fuera del build' });
  }

  // El router es de hash, así que cualquier ruta desconocida es la propia app.
  const path = existsSync(target) && statSync(target).isFile() ? target : `${distRoot}/index.html`;
  if (!existsSync(path)) return send(res, 503, BUILD_ME, 'text/html');

  const type = MIME[extname(path).toLowerCase()] ?? 'application/octet-stream';
  res.writeHead(200, { 'Content-Type': `${type}; charset=utf-8`, 'Cache-Control': 'no-store' });
  return res.end(readFileSync(path));
}

createServer((req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);

  if (url.pathname === '/api/history') {
    return send(res, 200, { novels: historyIndex() });
  }

  if (url.pathname === '/api/history/novel') {
    const detail = historyNovel(url.searchParams.get('slug') ?? '');
    return detail
      ? send(res, 200, detail)
      : send(res, 404, { error: 'no hay ninguna novela con ese slug' });
  }

  if (url.pathname === '/api/history/text') {
    const text = historyText(url.searchParams.get('slug') ?? '', url.searchParams.get('chapter') ?? '');
    return text
      ? send(res, 200, text)
      : send(res, 404, { error: 'no hay texto para esa novela y ese capítulo' });
  }

  if (url.pathname === '/api/meta') {
    const novels = listNovels();
    // La novela tocada más recientemente es la que está corriendo, y el panel la sigue
    // sola: antes la lista se cargaba una vez al abrir la página, así que una novela
    // creada después no aparecía nunca y el monitor se quedaba mirando otra.
    //
    // Cuenta también `run-console.log`, no solo `run-state.json`. Una corrida recién
    // lanzada tarda en escribir estado, y si en ese hueco se mira solo el estado, la
    // novela que acabas de lanzar no es "la activa" y el panel se va solo a otra. Pasó
    // con `night-haul`: la corrida no llegó a escribir estado nunca y el monitor se
    // quedó enseñando una novela distinta, que parecía que no se actualizaba.
    const touched = (n) => ['run-state.json', 'run-console.log']
      .map((f) => (existsSync(`${ROOT}/novels/${n}/${f}`) ? statSync(`${ROOT}/novels/${n}/${f}`).mtimeMs : 0))
      .reduce((a, b) => Math.max(a, b), 0);
    const active = novels
      .map((n) => ({ n, at: touched(n) }))
      .filter((r) => r.at > 0)
      .sort((a, b) => b.at - a.at)[0]?.n ?? null;
    return send(res, 200, { novels, profiles: listProfiles(), active });
  }

  if (url.pathname === '/api/state') {
    const slug = url.searchParams.get('novel') || listNovels()[0];
    if (!slug) return send(res, 200, { empty: true });
    return send(res, 200, snapshot(slug));
  }

  if ((url.pathname === '/api/run' || url.pathname === '/api/gate') && req.method === 'POST') {
    const act = url.pathname === '/api/run' ? startRun : decideGate;
    let body = '';
    req.on('data', (c) => { body += c; });
    req.on('end', () => {
      try {
        return send(res, 200, { ok: true, ...act(JSON.parse(body || '{}')) });
      } catch (error) {
        return send(res, 400, { ok: false, error: error.message });
      }
    });
    return undefined;
  }

  if (url.pathname.startsWith('/api/')) return send(res, 404, { error: 'no such route' });

  return serveStatic(url.pathname, res);
}).listen(PORT, '127.0.0.1', () => {
  console.log(`Panel de StoryMaker en http://127.0.0.1:${PORT}`);
  console.log(`Novelas: ${listNovels().join(', ') || '(ninguna)'} · perfiles: ${listProfiles().join(', ')}`);
});
