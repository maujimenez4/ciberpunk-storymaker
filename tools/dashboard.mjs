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
import { readFileSync, existsSync, writeFileSync, mkdirSync, readdirSync, openSync, appendFileSync, statSync } from 'node:fs';
import { spawn } from 'node:child_process';
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

function snapshot(slug) {
  const dir = `${ROOT}/novels/${slug}`;
  const state = readJson(`${dir}/run-state.json`);
  const brief = briefOf(dir);
  // Una corrida recién lanzada aún no ha escrito estado: eso no es "no hay corrida".
  const launched = existsSync(`${dir}/run-console.log`);
  if (!state) return { novel: slug, missing: true, brief, launched };

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

  // Compuerta pendiente: hay petición y ninguna decisión posterior que la responda.
  const gateRequest = readJson(`${dir}/gate-request.json`);
  const gateDecision = readJson(`${dir}/gate-decision.json`);
  const answered = gateRequest && gateDecision
    && gateDecision.chapter === gateRequest.chapter
    && Date.parse(gateDecision.decidedAt) >= Date.parse(gateRequest.createdAt);
  const gate = gateRequest && !answered
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
function spawnRun(profile, dir) {
  const out = openSync(`${dir}/run-console.log`, 'a');
  const isWindows = process.platform === 'win32';
  const args = ['-p', '--allowedTools', ...ALLOWED_TOOLS.split(/\s+/)];

  const child = isWindows
    ? spawn(process.env.COMSPEC || 'cmd.exe', ['/d', '/s', '/c', `claude ${args.join(' ')}`], {
        cwd: ROOT, stdio: ['pipe', out, out], windowsHide: true })
    : spawn('claude', args, { cwd: ROOT, stdio: ['pipe', out, out] });

  child.stdin.end(`/novela ${profile}\n`);
  // El código de salida va al mismo log: una corrida que muere al arrancar deja de ser
  // un fichero vacío y pasa a decir por qué.
  child.on('exit', (code, signal) => {
    appendFileSync(`${dir}/run-console.log`,
      `\n[panel] proceso terminado · código ${code}${signal ? ` · señal ${signal}` : ''}\n`);
  });
  child.on('error', (error) => {
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

  writeFileSync(`${dir}/gate-decision.json`, JSON.stringify({
    decision: 'storymaker/gate-decision@1',
    novel: cfg.run.novel, chapter: request.chapter,
    action, notes: notes ?? null, rollbackTo: rollbackTo ?? null,
    decidedAt: new Date().toISOString(),
  }, null, 2) + '\n');

  return { slug: cfg.run.novel, chapter: request.chapter, action, pid: spawnRun(profile, dir) };
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

  return { slug, pid: spawnRun(profile, dir), profile };
}

const send = (res, code, body, type = 'application/json') => {
  res.writeHead(code, { 'Content-Type': `${type}; charset=utf-8`, 'Cache-Control': 'no-store' });
  res.end(typeof body === 'string' ? body : JSON.stringify(body));
};

createServer((req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);

  if (url.pathname === '/' || url.pathname === '/index.html') {
    return send(res, 200, readFileSync(`${ROOT}/tools/dashboard/index.html`, 'utf8'), 'text/html');
  }

  if (url.pathname === '/api/meta') {
    const novels = listNovels();
    // La novela con el estado escrito más recientemente es la que está corriendo. El
    // panel la sigue sola: antes la lista se cargaba una vez al abrir la página, así que
    // una novela creada después no aparecía nunca y el monitor se quedaba mirando otra.
    const active = novels
      .map((n) => ({ n, at: existsSync(`${ROOT}/novels/${n}/run-state.json`)
        ? statSync(`${ROOT}/novels/${n}/run-state.json`).mtimeMs : 0 }))
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

  return send(res, 404, { error: 'no such route' });
}).listen(PORT, '127.0.0.1', () => {
  console.log(`Panel de StoryMaker en http://127.0.0.1:${PORT}`);
  console.log(`Novelas: ${listNovels().join(', ') || '(ninguna)'} · perfiles: ${listProfiles().join(', ')}`);
});
