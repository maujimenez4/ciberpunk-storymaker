// Un fixture que pasa y otro que falla por cada evaluator.
//
// Ninguno mira novels/: cada caso se monta su propio repo de mentira en un temporal, con
// su biblia, sus incidencias y hasta su lista de términos prohibidos. Si mañana cambia una
// novela del repo, estos tests siguen diciendo lo mismo — que es lo que se le pide a un
// test y justo lo que no puede dar la corrida real.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import {
  voiceEditorNoAnade, sinTerminosProhibidos, issuesSchemaValido,
  canonResoluble, longitudEnRango, rolDeIncidencia,
} from '../../tools/evals/evaluators.mjs';

const GUARD_PROSE = resolve('.claude/hooks/guard-prose.mjs');
const TERMINO_INVENTADO = 'zumbatrón';

/**
 * Un repo mínimo con una novela dentro. El género y su lista de prohibidos también son de
 * mentira: guard-prose deduce la raíz del repo de la ruta del fichero, así que leerá los
 * de aquí y no los del proyecto.
 */
function repo({ chapters = {}, bible = {}, issues = {}, scope } = {}) {
  const raiz = mkdtempSync(join(tmpdir(), 'storymaker-evals-'));
  const novelDir = join(raiz, 'novels', 'la-prueba');

  mkdirSync(join(raiz, 'config'), { recursive: true });
  writeFileSync(join(raiz, 'config', 'run.base.json'), JSON.stringify({ run: { genre: 'genero-de-prueba' } }));
  mkdirSync(join(raiz, 'genres', 'genero-de-prueba'), { recursive: true });
  writeFileSync(join(raiz, 'genres', 'genero-de-prueba', 'banned-terms.txt'),
    `# lista de mentira para el test\n${TERMINO_INVENTADO}\n`);

  for (const [dir, ficheros] of [['chapters', chapters], ['bible', bible], ['notes', issues]]) {
    mkdirSync(join(novelDir, dir), { recursive: true });
    for (const [nombre, contenido] of Object.entries(ficheros)) {
      const ruta = join(novelDir, dir, nombre);
      mkdirSync(join(ruta, '..'), { recursive: true });
      writeFileSync(ruta, typeof contenido === 'string' ? contenido : JSON.stringify(contenido, null, 2));
    }
  }

  return { slug: 'la-prueba', novelDir, repoRoot: raiz, scope, guardProse: GUARD_PROSE };
}

const palabras = (n) => Array.from({ length: n }, (_, i) => `palabra${i}`).join(' ');
const incidencia = (extra = {}) => ({
  id: 'ck-01', severity: 'note', kind: 'thread-dropped',
  where: 'ch01 ¶4', claim: 'algo', canon: null, fix: 'hacer esto', ...extra,
});
const informe = (issues) => ({ report: 'storymaker/issue-report@1', novel: 'la-prueba', chapter: 1, issues });

// ── 1 · voice-editor-no-anade ────────────────────────────────────────────────────

test('voice-editor-no-anade · pasa cuando el editado es más corto que el borrador', () => {
  const ctx = repo({ chapters: { 'ch01.draft.md': palabras(20), 'ch01.md': palabras(15) } });
  const [r] = voiceEditorNoAnade(ctx);
  assert.equal(r.pass, true);
  assert.equal(r.value, -5);
  assert.equal(r.target, 'voice-editor');
  assert.equal(r.capitulo, 1);
});

test('voice-editor-no-anade · falla cuando el editado añade palabras', () => {
  const ctx = repo({ chapters: { 'ch01.draft.md': palabras(15), 'ch01.md': palabras(20) } });
  const [r] = voiceEditorNoAnade(ctx);
  assert.equal(r.pass, false);
  assert.equal(r.value, 5);
  assert.match(r.detalle, /final 20 palabras, borrador 15/);
});

test('voice-editor-no-anade · sin borrador no juzga, y lo dice', () => {
  const ctx = repo({ chapters: { 'ch01.md': palabras(15) } });
  const [r] = voiceEditorNoAnade(ctx);
  assert.equal(r.pass, null);
  assert.match(r.detalle, /no hay borrador/);
});

// ── 2 · sin-terminos-prohibidos ──────────────────────────────────────────────────

test('sin-terminos-prohibidos · pasa con prosa limpia', async () => {
  const ctx = repo({ chapters: { 'ch01.md': 'El ascensor subió sin nadie dentro.' } });
  const [r] = await sinTerminosProhibidos(ctx);
  assert.equal(r.pass, true);
  assert.equal(r.value, 0);
  assert.equal(r.target, 'scene-writer');
});

test('sin-terminos-prohibidos · falla y nombra el término, preguntándole al guard de verdad', async () => {
  const ctx = repo({ chapters: { 'ch01.md': `Cruzó el ${TERMINO_INVENTADO} sin mirar atrás.` } });
  const [r] = await sinTerminosProhibidos(ctx);
  assert.equal(r.pass, false);
  assert.equal(r.value, 1);
  assert.equal(r.termino, TERMINO_INVENTADO);
  // Si guard-prose cambia el texto de su denegación, este test cae: es su cometido.
  assert.match(r.detalle, new RegExp(TERMINO_INVENTADO));
});

// ── 3 · issues-schema-valido ─────────────────────────────────────────────────────

test('issues-schema-valido · pasa una incidencia bien formada', () => {
  const ctx = repo({ issues: { 'ch01-issues.json': informe([incidencia()]) } });
  const [r] = issuesSchemaValido(ctx);
  assert.equal(r.pass, true);
  assert.equal(r.value, 0);
  assert.equal(r.target, 'continuity-keeper');
});

test('issues-schema-valido · falla y enumera los cuatro incumplimientos', () => {
  const ctx = repo({
    issues: { 'ch01-issues.json': informe([incidencia({ id: 'x-09', severity: 'grave', where: 'por ahí', fix: '   ' })]) },
  });
  const [r] = issuesSchemaValido(ctx);
  assert.equal(r.pass, false);
  assert.equal(r.value, 4);
  assert.match(r.detalle, /severity "grave"/);
  assert.match(r.detalle, /where "por ahí"/);
  assert.match(r.detalle, /fix vacío/);
  assert.match(r.detalle, /sin prefijo ck-\/tv-/);
  assert.equal(r.target, 'desconocido');
});

test('issues-schema-valido · el target sale del prefijo del id', () => {
  assert.equal(rolDeIncidencia('ck-01'), 'continuity-keeper');
  assert.equal(rolDeIncidencia('tv-12'), 'technical-verifier');
  assert.equal(rolDeIncidencia('vaya-01'), 'desconocido');
});

// ── 4 · canon-resoluble ──────────────────────────────────────────────────────────

const HILOS = '# Hilos\n\n### Reloj de la ciudad — mecanismo de invalidación\n\nTexto.\n';

test('canon-resoluble · pasa cuando la cita apunta a un encabezado real', () => {
  const ctx = repo({
    bible: { 'threads.md': HILOS, 'outline.md': 'Ver `threads.md#reloj-de-la-ciudad`.\n' },
  });
  const r = canonResoluble(ctx).find((x) => x.origen === 'bible');
  assert.equal(r.pass, true);
  assert.equal(r.target, 'continuity-keeper');
  assert.match(r.detalle, /threads\.md#reloj-de-la-ciudad/);
});

test('canon-resoluble · falla cuando el anclaje no existe', () => {
  const ctx = repo({
    bible: { 'threads.md': HILOS, 'outline.md': 'Ver `threads.md#expediente-abierto`.\n' },
  });
  const r = canonResoluble(ctx).find((x) => x.origen === 'bible');
  assert.equal(r.pass, false);
  assert.match(r.detalle, /no apunta a ningún encabezado/);
});

test('canon-resoluble · también juzga el campo canon de una incidencia, y es de quien la firmó', () => {
  const ctx = repo({
    bible: { 'threads.md': HILOS },
    issues: { 'ch01-issues.json': informe([incidencia({ id: 'tv-03', canon: 'bible/threads.md#no-existe' })]) },
  });
  const r = canonResoluble(ctx).find((x) => x.origen === 'issue');
  assert.equal(r.pass, false);
  assert.equal(r.target, 'technical-verifier');
});

// ── 5 · longitud-en-rango ────────────────────────────────────────────────────────

test('longitud-en-rango · pasa dentro de la tolerancia', () => {
  const ctx = repo({ chapters: { 'ch01.md': palabras(105) }, scope: { wordsPerChapter: 100, wordsTolerance: 0.1 } });
  const [r] = longitudEnRango(ctx);
  assert.equal(r.pass, true);
  assert.equal(r.value, 0.05);
  assert.equal(r.target, 'scene-writer');
});

test('longitud-en-rango · falla al pasarse de la tolerancia', () => {
  const ctx = repo({ chapters: { 'ch01.md': palabras(130) }, scope: { wordsPerChapter: 100, wordsTolerance: 0.1 } });
  const [r] = longitudEnRango(ctx);
  assert.equal(r.pass, false);
  assert.equal(r.value, 0.3);
  assert.match(r.detalle, /\+30\.0 %/);
});

test('longitud-en-rango · sin objetivo no inventa uno', () => {
  const ctx = repo({ chapters: { 'ch01.md': palabras(130) }, scope: {} });
  const [r] = longitudEnRango(ctx);
  assert.equal(r.pass, null);
  assert.match(r.detalle, /sin scope\.wordsPerChapter/);
});
