// La compuerta: el único punto donde el bucle cede el control (nodo GATE del diagrama).

import { createInterface } from 'node:readline/promises';
import { stdin, stdout } from 'node:process';

const SEVERITY_LABEL = { blocker: 'BLOQUEA', warning: 'aviso', note: 'nota' };

/** ¿Hace falta parar? Lee la configuración, como dice el diagrama. */
export function gateNeeded({ cfg, chapter, flagged, budgetPaused }) {
  const { approvalMode, onFlagged } = cfg.supervision;

  // Un capítulo marcado como no resuelto fuerza compuerta, sea cual sea el modo.
  if (flagged && (onFlagged ?? 'force-gate') === 'force-gate') return 'flagged';
  if (budgetPaused) return 'budget';
  if (approvalMode === 'never') return null;
  if (approvalMode === 'every-chapter') return 'every-chapter';

  // act-end-or-flagged: parar al cerrar acto.
  const perAct = Math.ceil(cfg.scope.chapters / cfg.scope.acts);
  const isActEnd = chapter % perAct === 0 || chapter === cfg.scope.chapters;
  return isActEnd ? 'act-end' : null;
}

function renderIssues(issues) {
  if (!issues.length) return '  (ninguna)';
  return issues
    .map((i) => `  [${SEVERITY_LABEL[i.severity] ?? i.severity}] ${i.id} · ${i.kind} · ${i.where}\n` +
      `        ${i.claim}\n        → ${i.fix}`)
    .join('\n');
}

export function present({ cfg, chapter, reason, chapters, issues, budget, flagged }) {
  const line = '─'.repeat(72);
  console.log(`\n${line}`);
  console.log(`COMPUERTA · capítulo ${chapter} · motivo: ${reason}`);
  console.log(line);

  for (const c of chapters) {
    console.log(`\n### Capítulo ${c.number}${c.title ? ` — ${c.title}` : ''} (${c.words} palabras)\n`);
    console.log(c.text);
  }

  console.log(`\n${line}`);
  // Invariante 7: warning y note no reescriben, se imprimen aquí para que el humano juzgue.
  console.log('Incidencias abiertas:');
  console.log(renderIssues(issues));
  if (flagged) {
    console.log('\n⚠  Capítulo marcado como NO RESUELTO: se agotaron las reescrituras.');
  }
  console.log(`\nGasto: ${budget.calls} llamadas · ${budget.inputTokens} tokens de entrada · ` +
    `${budget.outputTokens} de salida · ~${budget.estimatedUsd} USD de ${budget.maxUsd}`);
  console.log(line);
}

/**
 * Pide la decisión. Las tres salidas son las del diagrama: approve, revise, rollback.
 * @param {object} scripted  respuestas pre-escritas, para la corrida en seco desatendida
 */
export async function askDecision({ chapter, allowRevise, scripted }) {
  if (scripted && scripted.length) {
    const answer = scripted.shift();
    console.log(`Decisión (guionizada): ${answer}`);
    return parseDecision(answer, chapter, allowRevise);
  }

  const rl = createInterface({ input: stdin, output: stdout });
  try {
    const opciones = allowRevise
      ? 'a = aprobar · r = revisar con notas · k <N> = rollback al capítulo N'
      : 'a = aprobar · k <N> = rollback al capítulo N  (revisiones agotadas)';
    for (;;) {
      const raw = (await rl.question(`\n${opciones}\n> `)).trim();
      const decision = parseDecision(raw, chapter, allowRevise);
      if (decision) {
        if (decision.type === 'revise' && !decision.notes) {
          decision.notes = (await rl.question('Notas para la reescritura: ')).trim();
        }
        return decision;
      }
      console.log('No te he entendido.');
    }
  } finally {
    rl.close();
  }
}

function parseDecision(raw, chapter, allowRevise) {
  const text = raw.toLowerCase();
  if (text === 'a' || text === 'approve' || text === 'aprobar') return { type: 'approve' };
  if (allowRevise && (text === 'r' || text.startsWith('revise') || text.startsWith('revisar'))) {
    const notes = raw.slice(raw.indexOf(' ') + 1).trim();
    return { type: 'revise', notes: notes === raw ? '' : notes };
  }
  const rollback = text.match(/^k\s*(\d+)$/) ?? text.match(/^rollback\s+(\d+)$/);
  if (rollback) {
    const target = Number(rollback[1]);
    if (target >= 1 && target < chapter) return { type: 'rollback', target };
    console.log(`El capítulo de rollback debe estar entre 1 y ${chapter - 1}.`);
    return null;
  }
  return null;
}
