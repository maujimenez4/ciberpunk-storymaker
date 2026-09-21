// Fase A2 · el cuerpo OTLP que sale del hook, sin red y sin gasto.
//
// Todo pasa por `--selftest`, que imprime el sobre y sale antes de tocar la red, el
// espejo y las marcas de envío. Cada aserción de aquí es la regresión de un agujero
// concreto de docs/diagnostico-evaluacion.md; cuando una falle, el §3.2 dice por qué
// importaba.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, existsSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { rootSpanIdOf, spanIdOf } from '../../.claude/hooks/otlp.mjs';
import { usageOf } from '../../.claude/hooks/usage.mjs';

const HOOK = resolve('.claude/hooks/trace-langfuse.mjs');
const FIXTURES = resolve('tests/fixtures/hooks');

/** Un repo de mentira, para no rozar las novelas de verdad. */
function repoFalso(estado = {}) {
  const raiz = mkdtempSync(join(tmpdir(), 'storymaker-test-'));
  mkdirSync(join(raiz, 'novels', 'test-novel'), { recursive: true });
  writeFileSync(join(raiz, 'novels', 'test-novel', 'run-state.json'), JSON.stringify({
    novel: 'test-novel', profile: 'neo-noir', phase: 'chapter-loop', chapter: 7,
    node: 'WRITE', counters: {}, limits: {}, dryRun: false, ...estado,
  }));
  return raiz;
}

function correrSelftest(fixture, { raiz = repoFalso(), parche = {} } = {}) {
  const sobre = { ...JSON.parse(readFileSync(join(FIXTURES, fixture), 'utf8')), cwd: raiz, ...parche };
  const salida = execFileSync('node', [HOOK, '--selftest'], { input: JSON.stringify(sobre), encoding: 'utf8' });
  return { ...JSON.parse(salida), raiz };
}

const atributos = (cuerpo) => Object.fromEntries(
  cuerpo.resourceSpans[0].scopeSpans[0].spans[0].attributes.map((a) => [
    a.key, a.value.stringValue ?? a.value.intValue ?? a.value.boolValue ?? a.value.doubleValue,
  ]),
);
const elSpan = (cuerpo) => cuerpo.resourceSpans[0].scopeSpans[0].spans[0];

test('los ids tienen la longitud que exige OTel y el padre es derivable de la traza', () => {
  const { resolved, body } = correrSelftest('agent-una-iteracion.json');
  const s = elSpan(body);
  assert.match(s.traceId, /^[0-9a-f]{32}$/);
  assert.match(s.spanId, /^[0-9a-f]{16}$/);
  assert.match(s.parentSpanId, /^[0-9a-f]{16}$/);
  // La raíz se emite después que los hijos: tiene que salir de la traza, no de un estado.
  assert.equal(s.parentSpanId, rootSpanIdOf(s.traceId));
  assert.equal(resolved.label, 'ch07');
});

test('el spanId sale de tool_use_id, así que repetir el hook no duplica la observación', () => {
  const a = correrSelftest('agent-una-iteracion.json');
  const b = correrSelftest('agent-una-iteracion.json');
  assert.equal(a.resolved.spanId, b.resolved.spanId);
  assert.equal(a.resolved.spanId, spanIdOf('toolu_01HrM2eo4zn3uJyvm4FBt2ho'));
});

test('§3.2(d): dos corridas de la misma novela y capítulo ya no comparten traza', () => {
  const a = correrSelftest('agent-una-iteracion.json', { parche: { session_id: 'sesion-A' } });
  const b = correrSelftest('agent-una-iteracion.json', { parche: { session_id: 'sesion-B' } });
  assert.notEqual(a.resolved.runId, b.resolved.runId);
  assert.notEqual(a.resolved.traceId, b.resolved.traceId);
});

test('§3.2(e): la duración del span es la real, no cero', () => {
  const { body, resolved } = correrSelftest('agent-una-iteracion.json');
  const s = elSpan(body);
  const durNanos = BigInt(s.endTimeUnixNano) - BigInt(s.startTimeUnixNano);
  assert.equal(resolved.durationMs, 12643); // totalDurationMs, no duration_ms del harness
  assert.equal(durNanos, 12643n * 1000000n);
  assert.equal(atributos(body)['langfuse.observation.metadata.duration_source'], 'totalDurationMs');
});

test('usage_details solo lleva partes disjuntas y su total es la suma de ellas', () => {
  const { details } = usageOf(JSON.parse(readFileSync(join(FIXTURES, 'agent-una-iteracion.json'), 'utf8')).tool_response);
  assert.deepEqual(Object.keys(details).sort(),
    ['cache_creation_input_tokens', 'cache_read_input_tokens', 'input', 'output', 'total']);
  assert.equal(details.total, details.input + details.output
    + details.cache_read_input_tokens + details.cache_creation_input_tokens);
  assert.equal(details.total, 28169); // cuadra con totalTokens del harness
});

test('con varias iteraciones no se cuenta dos veces ni se pisa con la última', () => {
  const sobre = JSON.parse(readFileSync(join(FIXTURES, 'agent-varias-iteraciones.json'), 'utf8')).tool_response;
  const { details, extras } = usageOf(sobre);

  // El fallo viejo: el mapa plano se quedaba con la última iteración (100) en vez del total.
  assert.equal(details.input, 300);
  assert.equal(details.output, 630);
  assert.equal(details.total, 300 + 630 + 2100 + 300);
  assert.equal(details.total, sobre.totalTokens, 'la suma disjunta tiene que dar el total del harness');

  // Y lo que se solapa se queda fuera de la suma, en metadata.
  assert.equal(extras.thinking_tokens, 180);        // dentro de output
  assert.equal(extras.ephemeral_5m_input_tokens, 200); // dentro de cache_creation
  assert.equal(extras.ephemeral_1h_input_tokens, 100);
  assert.equal(extras.iterations, 3);
  const suma = details.input + details.output + details.cache_read_input_tokens + details.cache_creation_input_tokens;
  assert.equal(suma, details.total, 'ningún campo solapado se coló en la aritmética');
});

test('§3.2(g): un subagente que falla se distingue de uno que va bien', () => {
  const { body } = correrSelftest('agent-fallido.json');
  const s = elSpan(body);
  const at = atributos(body);
  assert.equal(s.status.code, 2);
  assert.equal(at['langfuse.observation.level'], 'ERROR');
  assert.match(String(at['langfuse.observation.status_message']), /error/);
});

test('el encargo en crudo no viaja, y entrada/salida se dejan para A3', () => {
  const { body } = correrSelftest('agent-una-iteracion.json');
  const serializado = JSON.stringify(body);
  assert.ok(!serializado.includes('SECRETO_QUE_NO_DEBE_VIAJAR'),
    'el prompt del encargo no puede acabar en el cuerpo OTLP');
  const at = atributos(body);
  assert.equal(at['langfuse.observation.input'], undefined);
  assert.equal(at['langfuse.observation.output'], undefined);
});

test('la metadata filtrable lleva lo que A0 encontró', () => {
  const at = atributos(correrSelftest('agent-una-iteracion.json').body);
  assert.equal(at['langfuse.observation.type'], 'generation');
  assert.equal(at['langfuse.observation.model.name'], 'claude-haiku-4-5-20251001');
  assert.equal(at['langfuse.observation.metadata.agent_id'], 'a0957f044a53e4dd4');
  assert.equal(at['langfuse.observation.metadata.thinking_tokens'], '203');
  assert.equal(at['langfuse.observation.metadata.read_count'], '0');
  assert.equal(at['langfuse.observation.metadata.node_source'], 'state'); // hasta A1
  assert.equal(JSON.parse(at['langfuse.trace.tags']).includes('storymaker'), true);
});

test('--selftest no escribe nada: ni espejo, ni marcas, ni cache de runId', () => {
  const raiz = repoFalso();
  correrSelftest('agent-una-iteracion.json', { raiz });
  const novela = join(raiz, 'novels', 'test-novel');
  assert.ok(!existsSync(join(novela, 'agent-calls.jsonl')));
  assert.ok(!existsSync(join(novela, '.trace')));
  assert.ok(!existsSync(join(novela, '.langfuse-errors.log')));
  rmSync(raiz, { recursive: true, force: true });
});

test('en seco no se traza: no hay gasto que contar', () => {
  const raiz = repoFalso({ dryRun: true });
  const sobre = { ...JSON.parse(readFileSync(join(FIXTURES, 'agent-una-iteracion.json'), 'utf8')), cwd: raiz };
  const salida = execFileSync('node', [HOOK, '--selftest'], { input: JSON.stringify(sobre), encoding: 'utf8' });
  assert.equal(salida.trim(), '{}');
  rmSync(raiz, { recursive: true, force: true });
});
