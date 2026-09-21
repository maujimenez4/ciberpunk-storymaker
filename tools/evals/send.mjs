#!/usr/bin/env node
// Manda a Langfuse lo que dejó `npm run evals` en evals/out/results.json.
//
//   npm run evals:send -- --selftest    imprime los cuerpos y no toca la red
//   npm run evals:send -- --uno         una traza y UN score
//   npm run evals:send -- --todo        la traza y todos los scores
//   --sin-metadata                      quita el campo metadata del cuerpo del score,
//                                       que no está en el contrato documentado
//   --idempotencia                      manda UN score BOOLEAN dos veces con el mismo id
//                                       y nada más, para ver si el servidor deduplica
//
// Sin ninguna de las tres no hace nada: mandar datos a un servicio externo no puede ser
// el comportamiento por defecto de un comando que alguien teclea a medias.

import { readFileSync, existsSync, appendFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import {
  EVALS_VERSION, SCORES_SCHEMA, resolveAuth, hostOf, evalRunIdOf, scoresOf, rootSpanOf,
  enviarRaiz, enviarScores, envelopeDe, yaEnviado, postScore, desgloseDe,
} from './langfuse.mjs';

/**
 * La raíz del envío de prueba del 21-09-2026. Ya está en Langfuse y no se vuelve a mandar:
 * con `scores@2` el evalRunId cambia y sale otra, pero esto lo garantiza en vez de
 * deducirlo. Si alguna vez vuelve a salir este spanId, algo se ha revertido.
 */
const RAIZ_DE_PRUEBA = '8abb44f36cf39a9d';

const argv = process.argv.slice(2);
const bandera = (n) => argv.includes(`--${n}`);
const REPO = process.cwd().replace(/\\/g, '/');
const RESULTADOS = `${REPO}/evals/out/results.json`;

const SELFTEST = bandera('selftest');
const UNO = bandera('uno');
const TODO = bandera('todo');
const SIN_METADATA = bandera('sin-metadata');
const IDEMPOTENCIA = bandera('idempotencia');

if (!SELFTEST && !UNO && !TODO && !IDEMPOTENCIA) {
  console.error('Elige qué hacer: --selftest (sin red), --uno, --todo o --idempotencia.');
  process.exit(2);
}
if (!existsSync(RESULTADOS)) {
  console.error(`No existe ${RESULTADOS}. Corre antes: npm run evals`);
  process.exit(2);
}

const informe = JSON.parse(readFileSync(RESULTADOS, 'utf8'));
const results = informe.results ?? [];
if (!results.length) {
  console.error('El informe no trae resultados.');
  process.exit(2);
}

const commit = (() => {
  try { return execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8', cwd: REPO }).trim(); } catch { return null; }
})();

const evaluatorsSha = (() => {
  try {
    return createHash('sha256').update(readFileSync(`${REPO}/tools/evals/evaluators.mjs`)).digest('hex').slice(0, 12);
  } catch { return null; }
})();

const evalRunId = evalRunIdOf({ evaluatorsSha, results });  // lleva SCORES_SCHEMA dentro
const { traceId, scores: todosLosScores, omitidos } = scoresOf({ evalRunId, results });
// La guía del endpoint no lista `metadata`. Se manda por defecto —un 4xx sería la
// respuesta a esa duda— pero se puede quitar para aislarla, porque las coordenadas van
// también en el `comment` y no se pierden.
const scores = SIN_METADATA
  ? todosLosScores.map(({ metadata, ...resto }) => resto)
  : todosLosScores;

// La duración de la raíz es la de la tanda de evals, no la de este envío.
const endMs = Date.parse(informe.generatedAt) || Date.now();
const root = rootSpanOf({
  evalRunId,
  novels: informe.novels ?? [],
  summary: informe.summary ?? [],
  evaluatorsSha,
  commit,
  startMs: endMs - 1000,
  endMs,
});

const contaminadas = (informe.novels ?? []).filter((n) => n.contaminated).map((n) => n.slug);

const anotarFallo = (score, r) => {
  try {
    appendFileSync(`${REPO}/.langfuse-errors.log`,
      `${new Date().toISOString()} evals idempotencia ${score.name} ${score.id} HTTP ${r.status}: ${r.body}\n`);
  } catch { /* nada */ }
};

console.log(`Versión:     ${EVALS_VERSION} · ${SCORES_SCHEMA} · evaluators sha ${evaluatorsSha ?? '(desconocido)'}`);
console.log(`Commit:      ${commit ?? '(sin git)'}`);
console.log(`evalRunId:   ${evalRunId}`);
console.log(`traceId:     ${traceId}`);
console.log(`Raíz:        ${root.spanId}`);
console.log(`Novelas:     ${(informe.novels ?? []).map((n) => n.slug).join(', ')}${contaminadas.length ? ` · contaminadas: ${contaminadas.join(', ')}` : ''}`);
console.log(`Scores:      ${scores.length}${omitidos.length ? ` · ${omitidos.length} omitidos por pass=null` : ''}`);
console.log(`metadata:    ${SIN_METADATA ? 'NO se manda (--sin-metadata)' : 'se manda (no está en el contrato documentado)'}`);

const { filas, mezclados, total } = desgloseDe(scores);

function imprimirDesglose() {
  console.log('\n── Desglose por nombre y tipo ───────────────────────────────────');
  const ancho = Math.max(...filas.map((f) => f.name.length), 12);
  for (const f of filas) {
    console.log(`  ${f.name.padEnd(ancho)}  ${f.dataType.padEnd(8)}  ${String(f.n).padStart(3)}`);
  }
  console.log(`  ${''.padEnd(ancho)}  ${''.padEnd(8)}  ${String(total).padStart(3)}  total`);

  if (mezclados.length) {
    console.log('\n  ✗ NOMBRES CON MÁS DE UN TIPO:');
    for (const m of mezclados) console.log(`      ${m.name}: ${m.tipos.join(', ')}`);
  } else {
    console.log('\n  ✓ Ningún nombre mezcla tipos.');
  }
}

if (SELFTEST) {
  imprimirDesglose();
  console.log(`\n  ${results.length} resultados → ${total} scores: un veredicto BOOLEAN por resultado`);
  console.log(`  más una medida NUMERIC en los ${total - results.length + omitidos.length} casos donde el número dice algo que el veredicto no.`);
  console.log('  Con scores@1 eran 67, uno por resultado, con el nombre del evaluator y tipo variable.');

  const muestra = scores.slice(0, 3);
  console.log('\n── Cuerpo OTLP de la raíz ───────────────────────────────────────');
  console.log(JSON.stringify(envelopeDe(root), null, 2));
  console.log(`\n── Cuerpos de score (${muestra.length} de ${scores.length}) ────────────────────────────`);
  for (const s of muestra) console.log(JSON.stringify(s, null, 2));
  if (omitidos.length) {
    console.log(`\n── Omitidos (${omitidos.length}) ─────────────────────────────────────────`);
    for (const r of omitidos) console.log(`  ${r.evaluator} · ${r.novela} · ${r.detalle}`);
  }
  const yaVan = scores.filter((s) => yaEnviado(REPO, s.id)).length;
  console.log(`\nMarcas de envío ya presentes: ${yaVan} de ${scores.length}. Credencial: ${resolveAuth() ? 'presente' : 'NO ENCONTRADA'}.`);
  console.log('No se ha tocado la red, ni escrito ninguna marca.');
  process.exit(0);
}

// ── Guardas, solo para lo que sale a la red ──────────────────────────────────────

if (root.spanId === RAIZ_DE_PRUEBA) {
  console.error(`\nLa raíz volvería a ser ${RAIZ_DE_PRUEBA}, la del envío de prueba, que ya está en Langfuse.`);
  console.error('No la reenvío. Si esto salta, es que el esquema de scores volvió a scores@1.');
  process.exit(2);
}

if (mezclados.length) {
  console.error('\nHay nombres de score con más de un tipo; no mando nada:');
  for (const m of mezclados) console.error(`  ${m.name}: ${m.tipos.join(', ')}`);
  process.exit(2);
}

/**
 * Árbol sucio, no se envía.
 *
 * La raíz lleva el commit como metadata. Si hay cambios sin commitear, ese commit describe
 * un código que no es el que produjo estos números, y una traza que miente sobre su origen
 * es peor que no tenerla.
 */
const sucio = (() => {
  try { return execFileSync('git', ['status', '--porcelain'], { encoding: 'utf8', cwd: REPO }).trim(); } catch { return null; }
})();
if (sucio === null) {
  console.error('\nNo puedo consultar git, así que no puedo garantizar que el commit de la metadata sea el real. No envío.');
  process.exit(2);
}
if (sucio) {
  console.error(`\nEl árbol de git no está limpio (${sucio.split('\n').length} ficheros). No envío:`);
  console.error(sucio.split('\n').slice(0, 12).map((l) => `  ${l}`).join('\n'));
  console.error(`\nCommitea primero: la raíz va a decir que se midió en ${commit?.slice(0, 8)}, y eso tiene que ser verdad.`);
  process.exit(2);
}

const auth = resolveAuth();
if (!auth) {
  console.error('\nSin credencial. Define LANGFUSE_PUBLIC_KEY y LANGFUSE_SECRET_KEY.');
  process.exit(1);
}

const host = hostOf();
console.log(`\nDestino:     ${host}`);

/**
 * Prueba de idempotencia **del servidor**.
 *
 * Las marcas de `.trace/sent/` demuestran que este lado no repite envíos, pero no dicen
 * nada de qué hace Langfuse si le llega dos veces el mismo id. Aquí se le manda a
 * propósito: mismo cuerpo, mismo id, dos POST seguidos, saltándose la marca local. Si el
 * servidor deduplica, en la UI habrá un score; si no, habrá dos y la marca local pasa de
 * ser un refuerzo a ser la única defensa.
 *
 * No manda la raíz: la traza ya existe del envío anterior.
 */
if (IDEMPOTENCIA) {
  const score = scores.find((s) => s.dataType === 'BOOLEAN');
  if (!score) {
    console.error('No hay ningún score BOOLEAN que mandar.');
    process.exit(2);
  }
  console.log(`\nMismo score, dos veces. Marca local saltada a propósito.`);
  console.log(`  name     ${score.name}`);
  console.log(`  value    ${score.value} (${score.dataType})`);
  console.log(`  id       ${score.id}`);
  console.log(`  traceId  ${score.traceId}`);
  console.log('');

  for (const intento of [1, 2]) {
    const r = await postScore({ host, authHeader: auth.header, score });
    console.log(`  POST ${intento} → HTTP ${r.status} ${r.ok ? 'ok' : 'FALLO'}${r.body ? ` · ${r.body}` : ''}`);
    if (!r.ok) anotarFallo(score, r);
  }
  console.log(`\nEn la UI, la traza ${score.traceId} tiene que enseñar UN score "${score.name}" si el servidor deduplica, y dos si no.`);
  process.exit(0);
}

const raiz = await enviarRaiz({ repoRoot: REPO, host, authHeader: auth.header, root });
console.log(`1) raíz  → ${raiz.saltado ? 'ya estaba enviada' : `HTTP ${raiz.status} ${raiz.ok ? 'ok' : 'FALLO'}`}${raiz.body && !raiz.ok ? ` · ${raiz.body}` : ''}`);
if (!raiz.ok) {
  console.error('\nLa raíz no entró. No mando scores: quedarían colgando de una traza que no existe.');
  process.exit(1);
}

const limite = UNO ? 1 : Infinity;
const out = await enviarScores({ repoRoot: REPO, host, authHeader: auth.header, scores, limite });
console.log(`2) scores → ${out.enviados} enviados, ${out.saltados} ya estaban, ${out.fallidos} fallidos`);
for (const d of out.detalles) {
  console.log(`   ${d.ok ? '✓' : '✗'} ${d.name} ${d.id.slice(0, 12)} HTTP ${d.status}${d.ok ? '' : ` · ${d.body}`}`);
}

console.log(`\ntraceId: ${traceId}`);
if (UNO) console.log('Mandado solo uno. Míralo en la UI antes de lanzar --todo.');
process.exit(out.fallidos ? 1 : 0);
