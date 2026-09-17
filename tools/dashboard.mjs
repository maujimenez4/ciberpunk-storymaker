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
import { readFileSync, existsSync, writeFileSync, mkdirSync, readdirSync, openSync } from 'node:fs';
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

function snapshot(slug) {
  const dir = `${ROOT}/novels/${slug}`;
  const state = readJson(`${dir}/run-state.json`);
  if (!state) return { novel: slug, missing: true };

  const calls = readLines(`${dir}/agent-calls.jsonl`);
  const log = readLines(`${dir}/run-log.jsonl`);

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
    for (const row of log) for (const a of NODE_AGENTS[row.node] ?? []) bump(a, 0, row.node);
  } else {
    for (const c of calls) bump(c.agent, c.tokens, c.node);
  }

  let scope = null;
  try { scope = loadConfig(state.profile, ROOT).scope; } catch { /* perfil ausente */ }

  const consolePath = `${dir}/run-console.log`;
  const consoleTail = existsSync(consolePath)
    ? readFileSync(consolePath, 'utf8').split('\n').slice(-40).join('\n')
    : '';

  return {
    novel: slug, state, scope, derived,
    agents: Object.values(perAgent).sort((a, b) => b.calls - a.calls),
    totals: {
      calls: Object.values(perAgent).reduce((a, r) => a + r.calls, 0),
      tokens: Object.values(perAgent).reduce((a, r) => a + r.tokens, 0),
    },
    timeline: log.slice(-60).map((r) => ({
      ts: r.ts, node: r.node, chapter: r.chapter, phase: r.phase, counters: r.counters,
    })),
    calls: calls.slice(-60),
    consoleTail,
    errors: existsSync(`${dir}/.langfuse-errors.log`)
      ? readFileSync(`${dir}/.langfuse-errors.log`, 'utf8').split('\n').filter(Boolean).slice(-5)
      : [],
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

  const out = openSync(`${dir}/run-console.log`, 'a');
  const child = spawn('claude', ['-p', `/novela ${profile}`], {
    cwd: ROOT, stdio: ['ignore', out, out], detached: true, shell: process.platform === 'win32',
  });
  child.unref();
  return { slug, pid: child.pid, profile };
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
    return send(res, 200, { novels: listNovels(), profiles: listProfiles() });
  }

  if (url.pathname === '/api/state') {
    const slug = url.searchParams.get('novel') || listNovels()[0];
    if (!slug) return send(res, 200, { empty: true });
    return send(res, 200, snapshot(slug));
  }

  if (url.pathname === '/api/run' && req.method === 'POST') {
    let body = '';
    req.on('data', (c) => { body += c; });
    req.on('end', () => {
      try {
        return send(res, 200, { ok: true, ...startRun(JSON.parse(body || '{}')) });
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
