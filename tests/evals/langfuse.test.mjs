// Fase A4.1 · el envío de scores, sin salir de la máquina.
//
// Todo lo que toca la red va contra un servidor HTTP local que cuenta lo que recibe. No
// hace falta ejecutar nada en subproceso, así que el bucle de eventos queda libre y el
// servidor puede contestar: la lección de los tests de A1.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { mkdtempSync, existsSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import {
  evalRunIdOf, traceIdOfRun, scoresOf, rootSpanOf,
  enviarRaiz, enviarScores, yaEnviado, MEDIDAS, desgloseDe, SCORES_SCHEMA,
} from '../../tools/evals/langfuse.mjs';
import { rootSpanIdOf } from '../../.claude/hooks/otlp.mjs';

const AUTH = 'Basic de-mentira';

// Por defecto, un evaluator **sin medida asociada**: así un resultado produce un solo
// score y los casos que cuentan envíos siguen contando una cosa cada uno. Los que
// necesitan la medida aparte la piden explícitamente.
const resultado = (extra = {}) => ({
  evaluator: 'sin-terminos-prohibidos', target: 'scene-writer', novela: 'la-prueba', capitulo: 1,
  pass: true, value: 0, detalle: 'sin términos prohibidos', ...extra,
});

async function servidorFalso({ estado = 200 } = {}) {
  const recibido = { trazas: [], scores: [] };
  const server = createServer((req, res) => {
    let cuerpo = '';
    req.on('data', (c) => { cuerpo += c; });
    req.on('end', () => {
      let json = null;
      try { json = JSON.parse(cuerpo); } catch { /* lo guardamos como null */ }
      if (req.url.includes('/otel/')) recibido.trazas.push({ json, headers: req.headers });
      else recibido.scores.push({ json, headers: req.headers });
      res.writeHead(estado, { 'Content-Type': 'application/json', Connection: 'close' });
      res.end(estado >= 400 ? '{"error":"de mentira"}' : '{}');
      res.on('finish', () => req.socket.end());
    });
  });
  server.keepAliveTimeout = 1;
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  server.unref();
  return { url: `http://127.0.0.1:${server.address().port}`, recibido, cerrar: () => new Promise((r) => server.close(r)) };
}

const repoFalso = () => mkdtempSync(join(tmpdir(), 'storymaker-a4-'));

// ── Identidad de la tanda ────────────────────────────────────────────────────────

test('el evalRunId identifica la medición, no el momento ni el commit', () => {
  const a = evalRunIdOf({ evaluatorsSha: 'v1', results: [resultado()] });
  const b = evalRunIdOf({ evaluatorsSha: 'v1', results: [resultado()] });
  assert.equal(a, b, 'volver a correr sin que nada cambie tiene que caer en la misma traza');

  // Si el commit entrara en el hash, tocar un README reenviaría los 91 scores.
  assert.notEqual(a, evalRunIdOf({ evaluatorsSha: 'v2', results: [resultado()] }), 'otra versión de evaluators, otra traza');
  assert.notEqual(a, evalRunIdOf({ evaluatorsSha: 'v1', results: [resultado({ value: 0.9 })] }), 'otro resultado, otra traza');
  assert.match(traceIdOfRun(a), /^[0-9a-f]{32}$/);
});

test('cambiar el esquema de scores da traza nueva', () => {
  const results = [resultado()];
  const conV2 = evalRunIdOf({ evaluatorsSha: 'v1', results, schema: 'scores@2' });
  const conV1 = evalRunIdOf({ evaluatorsSha: 'v1', results, schema: 'scores@1' });
  // Los mismos números contados de otra forma no pueden convivir en una traza.
  assert.notEqual(conV2, conV1);
  assert.equal(conV2, evalRunIdOf({ evaluatorsSha: 'v1', results }), 'scores@2 es el valor por defecto');
  assert.equal(SCORES_SCHEMA, 'scores@2');
});

test('el desglose cuenta por nombre y tipo, y delata una mezcla', () => {
  const { filas, total, mezclados } = desgloseDe([
    { name: 'a', dataType: 'BOOLEAN' }, { name: 'a', dataType: 'BOOLEAN' }, { name: 'b', dataType: 'NUMERIC' },
  ]);
  assert.deepEqual(filas, [
    { name: 'a', dataType: 'BOOLEAN', n: 2 },
    { name: 'b', dataType: 'NUMERIC', n: 1 },
  ]);
  assert.equal(total, 3);
  assert.deepEqual(mezclados, []);

  const sucio = desgloseDe([{ name: 'a', dataType: 'BOOLEAN' }, { name: 'a', dataType: 'NUMERIC' }]);
  assert.deepEqual(sucio.mezclados, [{ name: 'a', tipos: ['BOOLEAN', 'NUMERIC'] }]);
});

// ── Cuerpos ──────────────────────────────────────────────────────────────────────

test('cada score lleva coordenadas en el comment, no solo en la metadata', () => {
  const { scores } = scoresOf({ evalRunId: 'r1', results: [resultado({ pass: false, capitulo: 7 })] });
  const [s] = scores;
  // `metadata` no está en el contrato documentado del endpoint, así que la coordenada
  // tiene que sobrevivir aunque el servidor la tire.
  assert.match(s.comment, /la-prueba ch07/);
  assert.match(s.comment, /target=scene-writer/);
  assert.match(s.comment, /^✗/);
  assert.equal(s.metadata.novela, 'la-prueba');
  assert.equal(s.metadata.capitulo, 7);
  assert.equal(s.metadata.pass, false);
});

test('el nombre del evaluator es siempre BOOLEAN y 1 siempre es pasa', () => {
  const { scores } = scoresOf({
    evalRunId: 'r1',
    results: [
      resultado({ evaluator: 'canon-resoluble', value: 0, pass: false, origen: 'bible', cita: 'threads.md#x' }),
      resultado({ evaluator: 'sin-terminos-prohibidos', value: 1, pass: false }),
      resultado({ evaluator: 'voice-editor-no-anade', value: -8, pass: true }),
    ],
  });
  const veredictos = scores.filter((s) => !Object.values(MEDIDAS).includes(s.name));
  assert.deepEqual(veredictos.map((s) => s.dataType), ['BOOLEAN', 'BOOLEAN', 'BOOLEAN']);
  // En la versión vieja `sin-terminos-prohibidos` mandaba 1 para "hay un término prohibido"
  // y `canon-resoluble` 1 para "la cita resuelve": el mismo número, sentidos opuestos.
  assert.deepEqual(veredictos.map((s) => s.value), [0, 0, 1]);
});

test('la medida va aparte, con su propio nombre, y solo donde informa', () => {
  const { scores } = scoresOf({
    evalRunId: 'r1',
    results: [
      resultado({ evaluator: 'voice-editor-no-anade', value: -8 }),
      resultado({ evaluator: 'longitud-en-rango', value: 0.206 }),
      resultado({ evaluator: 'issues-schema-valido', value: 3, issueId: 'ck-01' }),
      resultado({ evaluator: 'canon-resoluble', value: 1, origen: 'bible', cita: 'threads.md#x' }),
      resultado({ evaluator: 'sin-terminos-prohibidos', value: 0 }),
    ],
  });
  const medidas = scores.filter((s) => s.dataType === 'NUMERIC');
  assert.deepEqual(medidas.map((s) => s.name),
    ['voice-editor-delta-palabras', 'longitud-desviacion', 'issues-violaciones']);
  assert.deepEqual(medidas.map((s) => s.value), [-8, 0.206, 3]);
  // Los dos binarios no producen medida: sería el booleano otra vez con otro nombre.
  assert.equal(scores.length, 5 + 3);
});

test('ningún nombre de score sale con dos tipos distintos', () => {
  const results = Object.keys(MEDIDAS).concat(['canon-resoluble', 'sin-terminos-prohibidos'])
    .flatMap((evaluator) => [
      resultado({ evaluator, value: 1, pass: true, capitulo: 1 }),
      resultado({ evaluator, value: 0, pass: false, capitulo: 2 }),
    ]);
  const { scores } = scoresOf({ evalRunId: 'r1', results });
  const tipos = new Map();
  for (const s of scores) {
    const previo = tipos.get(s.name);
    assert.ok(previo === undefined || previo === s.dataType,
      `el nombre "${s.name}" sale como ${previo} y como ${s.dataType}: una serie no cambia de tipo`);
    tipos.set(s.name, s.dataType);
  }
});

test('los resultados sin veredicto no se mandan, y se devuelven aparte', () => {
  const { scores, omitidos } = scoresOf({
    evalRunId: 'r1',
    results: [resultado(), resultado({ pass: null, value: null, detalle: 'no hay borrador' })],
  });
  assert.equal(scores.length, 1);
  assert.equal(omitidos.length, 1);
  assert.match(omitidos[0].detalle, /no hay borrador/);
});

test('dos resultados del mismo capítulo no colisionan de id', () => {
  const { scores } = scoresOf({
    evalRunId: 'r1',
    results: [
      resultado({ evaluator: 'canon-resoluble', value: 1, origen: 'bible', cita: 'threads.md#a' }),
      resultado({ evaluator: 'canon-resoluble', value: 0, origen: 'bible', cita: 'threads.md#b' }),
      resultado({ evaluator: 'canon-resoluble', value: 0, origen: 'bible', cita: 'threads.md#b' }),
    ],
  });
  assert.equal(new Set(scores.map((s) => s.id)).size, 3);
});

test('el id cambia si cambia cualquiera de sus componentes, y solo entonces', () => {
  const uno = (extra) => scoresOf({ evalRunId: 'r1', results: [resultado(extra)] }).scores;
  const base = uno({});
  assert.equal(base[0].id, uno({})[0].id, 'mismos datos, mismo id');

  // evaluator, target, novela, capítulo — y, como de un resultado salen dos scores,
  // también el nombre y el tipo, que es lo que los separa entre sí.
  for (const cambio of [
    { evaluator: 'canon-resoluble' }, { target: 'voice-editor' },
    { novela: 'otra' }, { capitulo: 2 },
  ]) {
    assert.notEqual(base[0].id, uno(cambio)[0].id, `el id debería cambiar con ${JSON.stringify(cambio)}`);
  }
  const [veredicto, medida] = uno({ evaluator: 'voice-editor-no-anade', value: -8 });
  assert.notEqual(veredicto.id, medida.id, 'veredicto y medida del mismo resultado, ids distintos');
  assert.equal(veredicto.dataType, 'BOOLEAN');
  assert.equal(medida.dataType, 'NUMERIC');
});

test('la raíz declara las contaminadas y la versión de los evaluators', () => {
  const evalRunId = 'r1';
  const root = rootSpanOf({
    evalRunId,
    novels: [{ slug: 'dead-floor', contaminated: false }, { slug: 'within-tolerance', contaminated: true }],
    summary: [{ evaluator: 'longitud-en-rango', pass: 3, fail: 0, skipped: 0 }],
    evaluatorsSha: 'abc123', commit: 'deadbeef', startMs: 1000, endMs: 2000,
  });
  const at = Object.fromEntries(root.attributes.map((a) => [a.key, a.value.stringValue ?? a.value.boolValue ?? a.value.intValue]));
  assert.equal(root.traceId, traceIdOfRun(evalRunId));
  assert.equal(root.spanId, rootSpanIdOf(root.traceId));
  assert.equal(at['langfuse.trace.name'], 'storymaker evals');
  assert.deepEqual(JSON.parse(at['langfuse.trace.tags']), ['storymaker', 'evals']);
  assert.deepEqual(JSON.parse(at['langfuse.trace.metadata.contaminadas']), ['within-tolerance']);
  assert.equal(at['langfuse.trace.metadata.hay_contaminadas'], true);
  assert.equal(at['langfuse.trace.metadata.evaluators_sha'], 'abc123');
});

// ── Contra el servidor ───────────────────────────────────────────────────────────

test('la raíz va por OTLP y los scores por el endpoint de scores', async () => {
  const srv = await servidorFalso();
  const repoRoot = repoFalso();
  try {
    const evalRunId = 'r1';
    const root = rootSpanOf({ evalRunId, novels: [], summary: [], startMs: 1000, endMs: 2000 });
    const { scores } = scoresOf({ evalRunId, results: [resultado(), resultado({ capitulo: 2 })] });

    const raiz = await enviarRaiz({ repoRoot, host: srv.url, authHeader: AUTH, root });
    // Sin espaciado: aquí se mira el encaminamiento, no el ritmo, que tiene sus propios casos.
    const out = await enviarScores({ repoRoot, host: srv.url, authHeader: AUTH, scores, intervaloMs: 0 });

    assert.equal(raiz.ok, true);
    assert.equal(srv.recibido.trazas.length, 1);
    assert.equal(srv.recibido.trazas[0].headers['x-langfuse-ingestion-version'], '4');
    assert.equal(out.enviados, 2);
    assert.equal(srv.recibido.scores.length, 2);
    assert.equal(srv.recibido.scores[0].json.traceId, traceIdOfRun(evalRunId));
    assert.equal(srv.recibido.scores[0].headers.authorization, AUTH);
  } finally { await srv.cerrar(); }
});

test('idempotencia: repetir el envío no manda nada dos veces', async () => {
  const srv = await servidorFalso();
  const repoRoot = repoFalso();
  try {
    const evalRunId = 'r1';
    const root = rootSpanOf({ evalRunId, novels: [], summary: [], startMs: 1000, endMs: 2000 });
    const { scores } = scoresOf({ evalRunId, results: [resultado()] });

    await enviarRaiz({ repoRoot, host: srv.url, authHeader: AUTH, root });
    const primera = await enviarScores({ repoRoot, host: srv.url, authHeader: AUTH, scores, intervaloMs: 0 });

    const raizOtraVez = await enviarRaiz({ repoRoot, host: srv.url, authHeader: AUTH, root });
    const segunda = await enviarScores({ repoRoot, host: srv.url, authHeader: AUTH, scores, intervaloMs: 0 });

    assert.equal(primera.enviados, 1);
    assert.equal(segunda.enviados, 0);
    assert.equal(segunda.saltados, 1);
    assert.equal(raizOtraVez.saltado, true);
    assert.equal(srv.recibido.trazas.length, 1, 'la raíz una sola vez');
    assert.equal(srv.recibido.scores.length, 1, 'el score una sola vez');
    assert.ok(yaEnviado(repoRoot, scores[0].id));
  } finally { await srv.cerrar(); }
});

test('un fallo del servidor no lanza, no marca y queda anotado', async () => {
  const srv = await servidorFalso({ estado: 400 });
  const repoRoot = repoFalso();
  try {
    const { scores } = scoresOf({ evalRunId: 'r1', results: [resultado()] });
    const out = await enviarScores({ repoRoot, host: srv.url, authHeader: AUTH, scores, intervaloMs: 0 });

    assert.equal(out.fallidos, 1);
    assert.equal(out.enviados, 0);
    assert.equal(yaEnviado(repoRoot, scores[0].id), false, 'sin 2xx no se marca: si no, se perdería para siempre');
    const log = readFileSync(join(repoRoot, '.langfuse-errors.log'), 'utf8');
    assert.match(log, /HTTP 400/);
  } finally { await srv.cerrar(); }
});

test('si no hay a quién llamar, tampoco se rompe', async () => {
  const repoRoot = repoFalso();
  const { scores } = scoresOf({ evalRunId: 'r1', results: [resultado()] });
  // Puerto cerrado a propósito.
  const out = await enviarScores({ repoRoot, host: 'http://127.0.0.1:1', authHeader: AUTH, scores, timeoutMs: 1500, intervaloMs: 0 });
  assert.equal(out.fallidos, 1);
  assert.equal(yaEnviado(repoRoot, scores[0].id), false);
  assert.ok(existsSync(join(repoRoot, '.langfuse-errors.log')));
});

// ── Control de ritmo ─────────────────────────────────────────────────────────────
// El endpoint de scores corta a 30 por minuto. Todo esto corre con un reloj simulado:
// `esperar` no duerme, adelanta el reloj, así que los tests miden minutos en milisegundos
// reales y son deterministas.

function relojFalso() {
  let t = 0;
  return {
    ahora: () => t,
    esperar: async (ms) => { t += Math.max(0, ms); },
    valor: () => t,
  };
}

/** Un servidor que decide por petición, y apunta a qué hora simulada le llegó cada una. */
async function servidorConRitmo({ reloj, responder }) {
  const llegadas = [];
  let n = 0;
  const server = createServer((req, res) => {
    req.on('data', () => {});
    req.on('end', () => {
      n += 1;
      llegadas.push(reloj.ahora());
      const { estado, retryAfterSeconds } = responder(n);
      const cuerpo = estado === 429
        ? JSON.stringify({ message: 'Rate limit exceeded', code: 'rate_limited', details: { retryAfterSeconds, limit: 30, remaining: 0 } })
        : '{}';
      res.writeHead(estado, { 'Content-Type': 'application/json', Connection: 'close' });
      res.end(cuerpo);
      res.on('finish', () => req.socket.end());
    });
  });
  server.keepAliveTimeout = 1;
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  server.unref();
  return { url: `http://127.0.0.1:${server.address().port}`, llegadas, cerrar: () => new Promise((r) => server.close(r)) };
}

const nScores = (n) => scoresOf({
  evalRunId: 'ritmo',
  results: Array.from({ length: n }, (_, i) => resultado({ capitulo: i + 1 })),
}).scores;

test('un 429 hace esperar retryAfterSeconds + 1 y reintenta ese mismo score', async () => {
  const reloj = relojFalso();
  // La primera petición rebota; la segunda —el reintento del mismo score— pasa.
  const srv = await servidorConRitmo({ reloj, responder: (n) => (n === 1 ? { estado: 429, retryAfterSeconds: 56 } : { estado: 200 }) });
  const repoRoot = repoFalso();
  try {
    const scores = nScores(1);
    const out = await enviarScores({
      repoRoot, host: srv.url, authHeader: AUTH, scores,
      ahora: reloj.ahora, esperar: reloj.esperar,
    });

    assert.equal(out.enviados, 1);
    assert.equal(out.fallidos, 0);
    assert.equal(out.detenido, false);
    assert.equal(srv.llegadas.length, 2, 'el score se reintenta, no se descarta');
    // 56 + 1 segundos entre el rebote y el reintento.
    assert.equal(srv.llegadas[1] - srv.llegadas[0], 57_000);
    assert.ok(yaEnviado(repoRoot, scores[0].id));
  } finally { await srv.cerrar(); }
});

test('nunca se superan 30 envíos en una ventana de un minuto', async () => {
  const reloj = relojFalso();
  const srv = await servidorConRitmo({ reloj, responder: () => ({ estado: 200 }) });
  const repoRoot = repoFalso();
  try {
    // Sin espaciado fijo: así el que tiene que sostener el límite es la ventana deslizante.
    await enviarScores({
      repoRoot, host: srv.url, authHeader: AUTH, scores: nScores(80),
      intervaloMs: 0, maxPorVentana: 30,
      ahora: reloj.ahora, esperar: reloj.esperar,
    });

    assert.equal(srv.llegadas.length, 80);
    for (const inicio of srv.llegadas) {
      const enVentana = srv.llegadas.filter((t) => t >= inicio && t < inicio + 60_000).length;
      assert.ok(enVentana <= 30, `hubo ${enVentana} envíos en el minuto que empieza en ${inicio}`);
    }
  } finally { await srv.cerrar(); }
});

test('con el espaciado por defecto tampoco se llega al límite', async () => {
  const reloj = relojFalso();
  const srv = await servidorConRitmo({ reloj, responder: () => ({ estado: 200 }) });
  const repoRoot = repoFalso();
  try {
    await enviarScores({
      repoRoot, host: srv.url, authHeader: AUTH, scores: nScores(40),
      ahora: reloj.ahora, esperar: reloj.esperar,
    });
    for (const inicio of srv.llegadas) {
      const enVentana = srv.llegadas.filter((t) => t >= inicio && t < inicio + 60_000).length;
      assert.ok(enVentana <= 30, `${enVentana} envíos en un minuto con el espaciado de 2,5 s`);
    }
    // 2,5 s entre envíos: 40 scores no caben en un minuto ni de lejos.
    assert.ok(reloj.valor() >= 39 * 2500, 'el espaciado tiene que haber consumido tiempo');
  } finally { await srv.cerrar(); }
});

test('un 429 no deja marca, y tras tres esperas sin progreso se detiene', async () => {
  const reloj = relojFalso();
  const srv = await servidorConRitmo({ reloj, responder: () => ({ estado: 429, retryAfterSeconds: 10 }) });
  const repoRoot = repoFalso();
  try {
    const scores = nScores(5);
    const out = await enviarScores({
      repoRoot, host: srv.url, authHeader: AUTH, scores,
      ahora: reloj.ahora, esperar: reloj.esperar,
    });

    assert.equal(out.detenido, true);
    assert.equal(out.enviados, 0);
    assert.match(out.motivo, /esperas seguidas/);
    // Tres esperas de 11 s y un cuarto intento que ya no espera: cuatro peticiones.
    assert.equal(srv.llegadas.length, 4);
    for (const s of scores) {
      assert.equal(yaEnviado(repoRoot, s.id), false, 'un 429 no puede dejar marca: el score no llegó');
    }
    assert.match(readFileSync(join(repoRoot, '.langfuse-errors.log'), 'utf8'), /detenido por ritmo/);
  } finally { await srv.cerrar(); }
});

test('un 400 no se reintenta y no bloquea a los siguientes', async () => {
  const reloj = relojFalso();
  const srv = await servidorConRitmo({ reloj, responder: (n) => ({ estado: n === 1 ? 400 : 200 }) });
  const repoRoot = repoFalso();
  try {
    const scores = nScores(3);
    const out = await enviarScores({
      repoRoot, host: srv.url, authHeader: AUTH, scores,
      ahora: reloj.ahora, esperar: reloj.esperar,
    });
    assert.equal(out.fallidos, 1);
    assert.equal(out.enviados, 2);
    assert.equal(srv.llegadas.length, 3, 'el 400 no se reintenta: un 400 vuelve a ser 400');
    assert.equal(yaEnviado(repoRoot, scores[0].id), false);
  } finally { await srv.cerrar(); }
});
