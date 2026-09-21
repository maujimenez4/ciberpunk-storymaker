// Fase A1 · el nodo sale del encargo, y el cierre de traza se dispara solo.
//
// Los tres últimos casos necesitan la ruta real de envío —marcas en .trace/sent/, raíz,
// barrido—, así que levantan un servidor local y apuntan LANGFUSE_HOST ahí. No sale nada
// de la máquina y no se gasta nada.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { createServer } from 'node:http';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, utimesSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { rootSpanIdOf, traceIdOf } from '../../.claude/hooks/otlp.mjs';
import { parseTraceHeader } from '../../.claude/hooks/handoff.mjs';

const HOOK = resolve('.claude/hooks/trace-langfuse.mjs');
const FIXTURE = resolve('tests/fixtures/hooks/agent-una-iteracion.json');

function repoFalso(estado = {}) {
  const raiz = mkdtempSync(join(tmpdir(), 'storymaker-a1-'));
  mkdirSync(join(raiz, 'novels', 'test-novel'), { recursive: true });
  mkdirSync(join(raiz, 'home'), { recursive: true });
  writeFileSync(join(raiz, 'novels', 'test-novel', 'run-state.json'), JSON.stringify({
    novel: 'test-novel', profile: 'neo-noir', phase: 'chapter-loop', chapter: 7,
    node: 'WRITE', attempt: 1, counters: {}, limits: {}, dryRun: false, ...estado,
  }));
  return raiz;
}

/** Recoge lo que el hook manda, para poder contar raíces. */
async function servidorFalso() {
  const recibido = [];
  const server = createServer((req, res) => {
    let cuerpo = '';
    req.on('data', (c) => { cuerpo += c; });
    req.on('end', () => {
      try { recibido.push(JSON.parse(cuerpo)); } catch { recibido.push(null); }
      // `Connection: close` no es cosmético: el hook no llama a process.exit a propósito
      // —hacerlo con el socket abierto aborta libuv en Windows—, así que con keep-alive el
      // proceso no terminaría nunca y el test se colgaría en vez de fallar.
      res.writeHead(200, { 'Content-Type': 'application/json', Connection: 'close' });
      res.end('{}');
      res.on('finish', () => req.socket.end());
    });
  });
  server.keepAliveTimeout = 1;
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  // Que un servidor olvidado no impida salir al proceso: sin esto, un assert que falle
  // antes del cierre deja el runner colgado en vez de dar un fallo.
  server.unref();
  const url = `http://127.0.0.1:${server.address().port}`;
  const spans = () => recibido.flatMap((e) => e?.resourceSpans?.[0]?.scopeSpans?.[0]?.spans ?? []);
  return { url, envios: () => recibido.length, spans, cerrar: () => new Promise((r) => server.close(r)) };
}

const sobre = (raiz, { prompt, node, estado } = {}) => {
  const base = JSON.parse(readFileSync(FIXTURE, 'utf8'));
  base.cwd = raiz;
  base.session_id = 'corrida-a1';
  if (prompt !== undefined) base.tool_input.prompt = prompt;
  if (node) base.tool_use_id = `toolu_${node}_${Math.random().toString(36).slice(2, 8)}`;
  if (estado) Object.assign(base.tool_response, estado);
  return base;
};

const entorno = (raiz, url) => ({
  ...process.env, HOME: join(raiz, 'home'), LANGFUSE_HOST: url,
  LANGFUSE_PUBLIC_KEY: 'pk-de-mentira', LANGFUSE_SECRET_KEY: 'sk-de-mentira',
});

// Asíncrono, y no `execFileSync`, porque el servidor de prueba vive en ESTE proceso: una
// llamada síncrona bloquea el bucle de eventos y el servidor no llega a contestar, así que
// el hook agota su timeout contra un servidor sordo y el test miente.
const ejecutar = promisify(execFile);

function correr(raiz, payload, args = [], env = process.env) {
  const promesa = ejecutar('node', [HOOK, ...args], { encoding: 'utf8', env, cwd: raiz, timeout: 20000 });
  promesa.child.stdin.end(payload ? JSON.stringify(payload) : '');
  return promesa;
}

const selftest = async (raiz, payload) => JSON.parse((await correr(raiz, payload, ['--selftest'])).stdout);

const atributo = (span, clave) => {
  const a = span.attributes.find((x) => x.key === clave);
  return a ? (a.value.stringValue ?? a.value.intValue ?? a.value.boolValue) : undefined;
};

// ── 1 y 2 · procedencia del nodo ─────────────────────────────────────────────────

test('la cabecera gana a un state.node equivocado', async () => {
  const raiz = repoFalso({ node: 'WRITE', attempt: 1, chapter: 7 });
  const r = (await selftest(raiz, sobre(raiz, {
    prompt: '<!-- storymaker-trace node=VAL2 attempt=3 chapter=9 -->\nValida el capítulo.',
  }))).resolved;
  assert.equal(r.node, 'VAL2');          // el estado decía WRITE
  assert.equal(r.attempt, 3);            // el estado decía 1
  assert.equal(r.chapter, 9);            // el estado decía 7
  assert.equal(r.node_source, 'header');
  assert.equal(r.chapter_source, 'header');
  assert.equal(r.label, 'ch09');
});

test('sin cabecera se usa el estado y queda marcado como tal', async () => {
  const raiz = repoFalso({ node: 'WRITE', attempt: 2 });
  const r = (await selftest(raiz, sobre(raiz, { prompt: 'Escribe el capítulo. Sin encabezado.' }))).resolved;
  assert.equal(r.node, 'WRITE');
  assert.equal(r.attempt, 2);
  assert.equal(r.node_source, 'state');
  assert.equal(r.chapter_source, 'state');
});

test('una cabecera inválida no se cuela: cae al estado', async () => {
  assert.equal(parseTraceHeader('<!-- storymaker-trace node=scene-writer -->'), null);
  const raiz = repoFalso({ node: 'WRITE' });
  const r = (await selftest(raiz, sobre(raiz, { prompt: '<!-- storymaker-trace attempt=2 -->\nHaz algo.' }))).resolved;
  assert.equal(r.node_source, 'state');
});

// ── 3 · cuándo se cierra la traza ────────────────────────────────────────────────

test('el cierre se dispara en SEED y en COMMIT, y solo con nodo de cabecera', async () => {
  for (const [caso, opciones, esperado] of [
    ['COMMIT por cabecera', { prompt: '<!-- storymaker-trace node=COMMIT attempt=1 chapter=7 -->\nx' }, true],
    ['SEED por cabecera', { prompt: '<!-- storymaker-trace node=SEED attempt=1 chapter=0 -->\nx' }, true],
    ['WRITE por cabecera', { prompt: '<!-- storymaker-trace node=WRITE attempt=1 chapter=7 -->\nx' }, false],
    ['COMMIT sin cabecera', { prompt: 'sin encabezado' }, false],
    ['COMMIT con subagente fallido', {
      prompt: '<!-- storymaker-trace node=COMMIT attempt=1 chapter=7 -->\nx',
      estado: { status: 'error' },
    }, false],
  ]) {
    const raiz = repoFalso({ node: 'COMMIT' }); // el estado dice COMMIT siempre: no debe bastar
    const r = await selftest(raiz, sobre(raiz, opciones));
    assert.equal(r.resolved.would_close, esperado, `${caso}: se esperaba would_close=${esperado}`);
  }
});

test('en COMMIT el hook manda la observación y además la raíz', async () => {
  const srv = await servidorFalso();
  let spans;
  try {
    const raiz = repoFalso({ node: 'WRITE' });
    await correr(raiz, sobre(raiz, {
      prompt: '<!-- storymaker-trace node=COMMIT attempt=1 chapter=7 -->\nx',
    }), [], entorno(raiz, srv.url));
    spans = srv.spans();
  } finally { await srv.cerrar(); }

  assert.equal(spans.length, 2, 'observación y raíz');
  const traceId = spans[0].traceId;
  const raices = spans.filter((s) => s.spanId === rootSpanIdOf(traceId));
  assert.equal(raices.length, 1);
  assert.equal(atributo(raices[0], 'langfuse.observation.metadata.closed_by'), 'close-trace');
  assert.equal(atributo(raices[0], 'langfuse.observation.metadata.children'), '1');
});

// ── 4 · idempotencia ─────────────────────────────────────────────────────────────

test('cerrar la misma traza dos veces manda la raíz una sola vez', async () => {
  const srv = await servidorFalso();
  let spans;
  try {
    const raiz = repoFalso({ node: 'WRITE' });
    const env = entorno(raiz, srv.url);
    const cabecera = '<!-- storymaker-trace node=COMMIT attempt=1 chapter=7 -->\nx';

    await correr(raiz, sobre(raiz, { prompt: cabecera, node: 'uno' }), [], env);
    await correr(raiz, sobre(raiz, { prompt: cabecera, node: 'dos' }), [], env);
    // Y por si fuera poco, el bloque de respaldo de novela.md.
    await correr(raiz, sobre(raiz, { prompt: cabecera, node: 'tres' }),
      ['--close-trace', '--novel=test-novel', '--label=ch07'], env);
    spans = srv.spans();
  } finally { await srv.cerrar(); }

  const traceId = spans[0].traceId;
  const raices = spans.filter((s) => s.spanId === rootSpanIdOf(traceId));
  assert.equal(raices.length, 1, 'v4 no deduplica: la raíz tiene que salir una sola vez');
  assert.equal(spans.filter((s) => s.spanId !== rootSpanIdOf(traceId)).length, 2, 'dos observaciones');
});

// ── 5 · el barrido no cruza identidades ──────────────────────────────────────────

test('el barrido cierra dos trazas distintas sin mezclarlas', async () => {
  const srv = await servidorFalso();
  const raiz = repoFalso();
  const dir = join(raiz, 'novels', 'test-novel', '.trace', 'spans');
  mkdirSync(dir, { recursive: true });

  const trazas = [
    { runId: 'corrida-vieja-aaa', label: 'ch01', profile: 'neo-noir', spanId: 'aaaaaaaaaaaaaaa1' },
    { runId: 'corrida-nueva-bbb', label: 'ch02', profile: 'otro-perfil', spanId: 'bbbbbbbbbbbbbbb2' },
  ].map((t) => ({ ...t, traceId: traceIdOf(t.runId, t.label) }));

  const viejo = Date.now() - 60 * 60 * 1000;
  for (const t of trazas) {
    const f = join(dir, `${t.traceId}.jsonl`);
    writeFileSync(f, JSON.stringify({
      spanId: t.spanId, startMs: viejo, endMs: viejo + 5000, name: 'scene-writer',
      label: t.label, runId: t.runId, novel: 'test-novel', profile: t.profile,
      phase: 'chapter-loop', chapter: Number(t.label.slice(2)),
    }) + '\n');
    utimesSync(f, new Date(viejo), new Date(viejo)); // sin actividad reciente
  }

  let spans;
  try {
    await correr(raiz, null, ['--sweep'], entorno(raiz, srv.url));
    spans = srv.spans();
  } finally { await srv.cerrar(); }

  assert.equal(spans.length, 2, 'una raíz por traza');
  for (const t of trazas) {
    const raiz_ = spans.find((s) => s.traceId === t.traceId);
    assert.ok(raiz_, `falta la raíz de ${t.label}`);
    assert.equal(raiz_.spanId, rootSpanIdOf(t.traceId));
    // Lo que importa: cada raíz lleva la identidad de SUS hijos, no la de la otra traza.
    assert.equal(atributo(raiz_, 'langfuse.session.id'), t.runId);
    assert.equal(atributo(raiz_, 'langfuse.trace.metadata.profile'), t.profile);
    assert.equal(atributo(raiz_, 'langfuse.trace.name'), `test-novel ${t.label}`);
  }
});
