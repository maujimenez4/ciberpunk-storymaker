#!/usr/bin/env node
// Corre los evaluators deterministas sobre las novelas del repo y deja el resultado en
// evals/out/results.json, además de una tabla para leer por encima.
//
//   npm run evals
//   npm run evals -- --novela=dead-floor
//   npm run evals -- --evaluator=longitud-en-rango
//   npm run evals -- --excluir-contaminadas
//   npm run evals -- --strict            (sale con 1 si algo falla; para CI)
//
// No llama a ningún modelo, no sale a la red y no escribe dentro de novels/.

import { readFileSync, readdirSync, existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { EVALUATORS, evaluarNovela } from './evaluators.mjs';

const argv = process.argv.slice(2);
const opcion = (nombre) => {
  const hit = argv.find((a) => a.startsWith(`--${nombre}=`));
  return hit ? hit.slice(nombre.length + 3) : null;
};
const bandera = (nombre) => argv.includes(`--${nombre}`);

const REPO = process.cwd().replace(/\\/g, '/');

/**
 * Corridas que no sirven para medir secuencia de nodos.
 *
 * `within-tolerance` se corrió con dos orquestadores a la vez sobre la misma novela (§0 del
 * diagnóstico), así que el orden de sus nodos está mezclado. Sus capítulos y su biblia sí
 * valen —son ficheros terminados— y por eso entra por defecto: ninguno de los cinco
 * evaluators de aquí mira la secuencia. Queda marcada en el JSON para que un evaluator
 * futuro que sí la mire pueda descartarla, y `--excluir-contaminadas` la quita entera.
 */
const CONTAMINADAS = new Set((opcion('contaminadas') ?? 'within-tolerance').split(',').filter(Boolean));

function scopeDe(perfil) {
  const base = JSON.parse(readFileSync(`${REPO}/config/run.base.json`, 'utf8'));
  let scope = { ...(base.scope ?? {}) };
  const ruta = `${REPO}/config/profiles/${perfil}.json`;
  if (perfil && existsSync(ruta)) {
    try { scope = { ...scope, ...(JSON.parse(readFileSync(ruta, 'utf8')).scope ?? {}) }; } catch { /* nos quedamos con la base */ }
  }
  return scope;
}

function novelas() {
  const base = `${REPO}/novels`;
  if (!existsSync(base)) return [];
  return readdirSync(base, { withFileTypes: true })
    .filter((d) => d.isDirectory() && existsSync(`${base}/${d.name}/run-state.json`))
    .map((d) => {
      let estado = {};
      try { estado = JSON.parse(readFileSync(`${base}/${d.name}/run-state.json`, 'utf8')); } catch { /* perfil por defecto */ }
      return {
        slug: d.name,
        novelDir: `${base}/${d.name}`,
        repoRoot: REPO,
        perfil: estado.profile ?? null,
        scope: scopeDe(estado.profile),
        contaminated: CONTAMINADAS.has(d.name),
      };
    })
    .sort((a, b) => a.slug.localeCompare(b.slug));
}

// ── Presentación ─────────────────────────────────────────────────────────────────

const pad = (s, n) => String(s).padEnd(n);
const padI = (s, n) => String(s).padStart(n);

function tabla(resultados, orden) {
  const filas = [];
  for (const evaluator of orden) {
    const delEval = resultados.filter((r) => r.evaluator === evaluator);
    const porNovela = new Map();
    for (const r of delEval) {
      const acc = porNovela.get(r.novela) ?? { pass: 0, fail: 0, skip: 0 };
      if (r.pass === null) acc.skip += 1; else if (r.pass) acc.pass += 1; else acc.fail += 1;
      porNovela.set(r.novela, acc);
    }
    for (const [novela, a] of porNovela) {
      filas.push({ evaluator, novela, texto: `${a.pass}/${a.pass + a.fail}`, skip: a.skip, ok: a.fail === 0 });
    }
    const t = [...porNovela.values()].reduce((s, a) => ({ pass: s.pass + a.pass, fail: s.fail + a.fail, skip: s.skip + a.skip }), { pass: 0, fail: 0, skip: 0 });
    filas.push({ evaluator, novela: 'TOTAL', texto: `${t.pass}/${t.pass + t.fail}`, skip: t.skip, ok: t.fail === 0, total: true });
  }

  const anchoE = Math.max(9, ...filas.map((f) => f.evaluator.length));
  const anchoN = Math.max(6, ...filas.map((f) => f.novela.length));
  console.log(`\n${pad('evaluator', anchoE)}  ${pad('novela', anchoN)}  ${padI('pasan', 7)}  omitidos`);
  console.log('─'.repeat(anchoE + anchoN + 22));
  let anterior = null;
  for (const f of filas) {
    if (anterior && anterior !== f.evaluator) console.log('');
    anterior = f.evaluator;
    const marca = f.ok ? ' ' : '✗';
    console.log(`${pad(f.total ? '' : f.evaluator, anchoE)}  ${pad(f.novela, anchoN)}  ${padI(f.texto, 7)}  ${padI(f.skip || '', 8)} ${marca}`);
  }
}

function desglosePorOrigen(resultados) {
  const canon = resultados.filter((r) => r.evaluator === 'canon-resoluble');
  if (!canon.length) return;
  console.log('\ncanon-resoluble, por origen de la cita:');
  for (const origen of ['bible', 'issue']) {
    const del = canon.filter((r) => r.origen === origen);
    if (!del.length) continue;
    const pasan = del.filter((r) => r.pass).length;
    console.log(`  ${pad(origen === 'bible' ? 'citas de la biblia' : 'campo canon de incidencias', 30)} ${padI(`${pasan}/${del.length}`, 7)}`);
  }
}

/**
 * Los dos evaluators cuyo número importa tanto como su veredicto. Un 3/3 en longitud no
 * dice si la novela roza la tolerancia o la parte por la mitad, y esa diferencia es justo
 * lo que discrimina entre corridas.
 */
function numeros(resultados) {
  const largos = resultados.filter((r) => r.evaluator === 'longitud-en-rango' && r.value !== null);
  const voces = resultados.filter((r) => r.evaluator === 'voice-editor-no-anade' && r.value !== null);
  if (!largos.length && !voces.length) return;

  console.log('\nPor capítulo:');
  const novelas = [...new Set([...largos, ...voces].map((r) => r.novela))];
  for (const novela of novelas) {
    const partes = [];
    for (const r of largos.filter((x) => x.novela === novela)) {
      const palabras = /^(\d+) palabras/.exec(r.detalle)?.[1] ?? '?';
      const pct = /\(([+-][\d.]+) %/.exec(r.detalle)?.[1] ?? '?';
      partes.push(`ch${String(r.capitulo).padStart(2, '0')} ${palabras} (${pct} %)`);
    }
    console.log(`  ${pad(novela, 18)} longitud: ${partes.join('  ')}`);
    const deltas = voces.filter((x) => x.novela === novela)
      .map((r) => `ch${String(r.capitulo).padStart(2, '0')} ${r.value > 0 ? '+' : ''}${r.value}`);
    if (deltas.length) console.log(`  ${pad('', 18)} voice-editor: ${deltas.join('  ')}`);
  }
}

function fallos(resultados) {
  const malos = resultados.filter((r) => r.pass === false);
  const omitidos = resultados.filter((r) => r.pass === null);
  if (malos.length) {
    console.log(`\nFallos (${malos.length}):`);
    for (const r of malos) {
      const cap = r.capitulo ? ` ch${String(r.capitulo).padStart(2, '0')}` : '';
      console.log(`  ✗ ${r.evaluator} · ${r.novela}${cap} · target=${r.target}`);
      console.log(`      ${r.detalle}`);
    }
  } else {
    console.log('\nSin fallos.');
  }
  if (omitidos.length) {
    console.log(`\nOmitidos, no se pudo juzgar (${omitidos.length}):`);
    for (const r of omitidos) console.log(`  – ${r.evaluator} · ${r.novela} · ${r.detalle}`);
  }
}

// ── Punto de entrada ─────────────────────────────────────────────────────────────

const soloNovela = opcion('novela');
const soloEvaluator = opcion('evaluator');
const nombres = soloEvaluator ? soloEvaluator.split(',') : null;

if (nombres) {
  const desconocidos = nombres.filter((n) => !EVALUATORS.some((e) => e.nombre === n));
  if (desconocidos.length) {
    console.error(`Evaluator desconocido: ${desconocidos.join(', ')}.`);
    console.error(`Los que hay: ${EVALUATORS.map((e) => e.nombre).join(', ')}.`);
    process.exit(2);
  }
}

let objetivo = novelas();
if (soloNovela) objetivo = objetivo.filter((n) => n.slug === soloNovela);
if (bandera('excluir-contaminadas')) objetivo = objetivo.filter((n) => !n.contaminated);

if (!objetivo.length) {
  console.error('No hay ninguna novela que evaluar.');
  process.exit(2);
}

const resultados = [];
for (const contexto of objetivo) resultados.push(...await evaluarNovela(contexto, nombres));

const orden = (nombres ?? EVALUATORS.map((e) => e.nombre)).filter((n) => resultados.some((r) => r.evaluator === n));

console.log(`Novelas: ${objetivo.map((n) => n.slug + (n.contaminated ? ' (contaminada)' : '')).join(', ')}`);
tabla(resultados, orden);
desglosePorOrigen(resultados);
numeros(resultados);
fallos(resultados);

const resumen = orden.map((evaluator) => {
  const del = resultados.filter((r) => r.evaluator === evaluator);
  return {
    evaluator,
    pass: del.filter((r) => r.pass === true).length,
    fail: del.filter((r) => r.pass === false).length,
    skipped: del.filter((r) => r.pass === null).length,
  };
});

const destino = `${REPO}/evals/out`;
mkdirSync(destino, { recursive: true });
writeFileSync(`${destino}/results.json`, `${JSON.stringify({
  schema: 'storymaker/eval-results@1',
  generatedAt: new Date().toISOString(),
  novels: objetivo.map((n) => ({ slug: n.slug, perfil: n.perfil, wordsPerChapter: n.scope?.wordsPerChapter ?? null, contaminated: n.contaminated })),
  summary: resumen,
  results: resultados,
}, null, 2)}\n`);

console.log(`\nEscrito evals/out/results.json · ${resultados.length} resultados`);

// Por defecto sale con 0 aunque haya fallos: en este repo las líneas base **tienen**
// fallos reales —el anclaje roto de dead-floor es uno—, así que un código distinto de cero
// por defecto sería ruido constante y dejaría de significar nada. Con --strict sí corta,
// que es lo que quiere una tubería de CI.
const hayFallos = resultados.some((r) => r.pass === false);
process.exit(bandera('strict') && hayFallos ? 1 : 0);
