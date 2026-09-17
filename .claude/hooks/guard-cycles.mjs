#!/usr/bin/env node
// PreToolUse sobre Task · invariante 6: todo ciclo tiene tope.
//
// Este hook NO controla gasto. No cuenta dinero ni tokens, y no existe ningún tope de
// consumo en esta rama. Lo que hace es impedir que un ciclo del diagrama gire para
// siempre: al agotarse, el diseño manda escalar al humano, no seguir intentando.
//
// Sin esto, los contadores viven en la cabeza del modelo, y un blocker que no se
// resuelve reescribe sin fin: FLAG no llegaría a dispararse nunca y la compuerta
// nunca vería el capítulo.

import { readFileSync, existsSync, readdirSync } from 'node:fs';

function deny(reason) {
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'deny',
      permissionDecisionReason: reason,
    },
  }));
  process.exit(0);
}

const allow = () => { process.stdout.write('{}'); process.exit(0); };

// Qué contador vigila cada subagente.
const CYCLE_OF = {
  'scene-writer': { counter: 'rewrites', limit: 'maxRewrites' },
  researcher: { counter: 'researchRounds', limit: 'maxResearchRounds' },
};

function findNovelDir(cwd) {
  const dir = `${cwd}/novels`;
  if (!existsSync(dir)) return null;
  const slugs = readdirSync(dir, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => `${dir}/${d.name}`)
    .filter((p) => existsSync(`${p}/run-state.json`));
  return slugs.length === 1 ? slugs[0] : null;
}

let input = '';
process.stdin.on('data', (c) => { input += c; });
process.stdin.on('end', () => {
  let hook;
  try {
    hook = JSON.parse(input);
  } catch {
    allow();
  }

  if (hook.tool_name !== 'Task') allow();

  const target = hook.tool_input?.subagent_type;
  const cycle = CYCLE_OF[target];
  if (!cycle) allow();

  const novelDir = findNovelDir(String(hook.cwd ?? '').replace(/\\/g, '/'));
  if (!novelDir) allow(); // Sin estado que consultar no se puede afirmar que haya exceso.

  let state;
  try {
    state = JSON.parse(readFileSync(`${novelDir}/run-state.json`, 'utf8'));
  } catch {
    allow();
  }

  const used = state.counters?.[cycle.counter] ?? 0;
  const max = state.limits?.[cycle.limit];
  if (typeof max !== 'number') allow(); // El tope tiene que estar en el estado para regir.

  // El primer intento no es una repetición del ciclo: el tope cuenta reintentos.
  if (used > max) {
    deny(
      `Invariante 6: el ciclo "${cycle.counter}" ya está en ${used} y su tope es ${max}. ` +
      `Al agotarse un ciclo, el diseño manda escalar al humano, no seguir intentando. ` +
      `Marca el capítulo como no resuelto (FLAG) y llévalo a la compuerta. ` +
      `Si la reentrada viene de notas del editor humano, pon counters.${cycle.counter} ` +
      `a cero en run-state.json antes de volver a lanzarlo: es otro ciclo, con otra causa.`,
    );
  }

  allow();
});
