// El recorrido del diagrama. Cada nodo numerado es una llamada aislada.
//
// Este módulo es mecánico a propósito: encadena llamadas, cuenta ciclos, escribe
// ficheros y hace commits. Todo lo que es juicio vive en agents/*.md y skills/*.md.

import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

import { callAgent } from './call.js';
import { composePrompt, canWrite } from './agents.js';
import * as git from './git.js';
import {
  novelDir, writeState, appendLog, writeArtifact, readIfExists, countWords,
} from './state.js';
import { gateNeeded, present, askDecision } from './gate.js';

const nn = (n) => String(n).padStart(2, '0');

// ── Esquemas de salida estructurada ───────────────────────────────────────────
// Se los pasamos al SDK para que la respuesta valide sola. Evita el reintento por
// JSON malformado, que es gasto puro: se paga dos veces por la misma respuesta.
const ISSUES_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['issues'],
  properties: {
    issues: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['severity', 'kind', 'where', 'claim', 'fix'],
        properties: {
          severity: { type: 'string', enum: ['blocker', 'warning', 'note'] },
          kind: { type: 'string' },
          where: { type: 'string' },
          claim: { type: 'string' },
          canon: { type: ['string', 'null'] },
          fix: { type: 'string' },
        },
      },
    },
  },
};

const BEATS_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['title', 'goal', 'conflict', 'turn', 'hook', 'researchQuestions'],
  properties: {
    title: { type: 'string' },
    goal: { type: 'string' },
    conflict: { type: 'string' },
    turn: { type: 'string' },
    hook: { type: 'string' },
    researchQuestions: { type: 'array', items: { type: 'string' } },
  },
};

// ── Llamada con contabilidad ──────────────────────────────────────────────────
async function invoke(ctx, { agentId, mode, node, chapter, userPrompt, output, limits }) {
  const agent = ctx.agents.get(agentId);
  if (!agent) throw new Error(`No existe el agente "${agentId}" en agents/`);

  const systemPrompt = composePrompt({
    agent, mode, skills: ctx.skills, genrePack: ctx.genrePack.text,
  });

  const envelope = {
    envelope: 'storymaker/handoff@1',
    call: { agent: agentId, mode: mode ?? 'default', node, issuedAt: new Date().toISOString() },
    run: {
      novel: ctx.cfg.run.novel, profile: ctx.cfg.profileName, genre: ctx.cfg.run.genre,
      chapter: chapter ?? null, act: chapter ? actOf(ctx.cfg, chapter) : null,
      attempt: ctx.attempt ?? 1, dryRun: ctx.cfg.execution.dryRun,
    },
    skills: agent.skills,
    limits: { ...(limits ?? {}), maxSearches: agent.tools.includes('WebSearch')
      ? (limits?.maxSearches ?? 0) : 0 },
    output: output ?? { format: 'text' },
    userPrompt,
  };

  const response = await callAgent({
    agent, mode, systemPrompt, envelope,
    cfg: ctx.cfg, budget: ctx.budget, root: ctx.root,
  });

  ctx.budget.record(response.usage);

  // Una denegación significa que el agente intentó usar algo que no tiene. Es señal
  // de que su prompt y sus permisos no coinciden, y merece verse.
  if (response.denials.length) {
    console.warn(`  ⚠  ${agentId} intentó usar herramientas denegadas: ` +
      response.denials.map((d) => d.tool_name ?? '?').join(', '));
  }

  appendLog(ctx.root, ctx.cfg.run.novel, {
    at: new Date().toISOString(),
    node, agent: agentId, mode: mode ?? 'default',
    chapter: chapter ?? null, attempt: ctx.attempt ?? 1,
    tools: agent.tools,
    usage: response.usage,
    dryRun: response.dryRun,
  });

  let json = null;
  if (output?.format === 'json') {
    try {
      json = JSON.parse(response.text);
    } catch {
      throw new Error(`${agentId}: se esperaba JSON y no lo es:\n${response.text.slice(0, 300)}`);
    }
  }

  return { ...response, json, agent };
}

function actOf(cfg, chapter) {
  const perAct = Math.ceil(cfg.scope.chapters / cfg.scope.acts);
  return Math.min(cfg.scope.acts, Math.ceil(chapter / perAct));
}

// ── Ensamblado de contexto (nodo LOAD) ────────────────────────────────────────
// Invariante 5: se ensambla, no se acumula. Y es aquí donde se decide que el coste
// no crezca con el número de capítulos escritos: solo entran los últimos
// scope.summaryWindow resúmenes, nunca el manuscrito.
function assembleContext(ctx, chapter) {
  const dir = novelDir(ctx.root, ctx.cfg.run.novel);
  const bible = {};
  for (const name of ['canon', 'world', 'characters', 'outline', 'timeline', 'threads']) {
    const text = readIfExists(join(dir, 'bible', `${name}.md`));
    if (text) bible[name] = text.trim();
  }

  const window = ctx.cfg.scope.summaryWindow ?? 3;
  const summaries = [];
  for (let n = Math.max(1, chapter - window); n < chapter; n += 1) {
    const text = readIfExists(join(dir, 'bible', 'summaries', `ch${nn(n)}.md`));
    if (text) summaries.push(`### Capítulo ${n}\n${text.trim()}`);
  }

  const parts = [];
  for (const [name, text] of Object.entries(bible)) {
    parts.push(`## Biblia · ${name}.md\n\n${text}`);
  }
  if (summaries.length) {
    parts.push(`## Resúmenes previos (últimos ${summaries.length})\n\n${summaries.join('\n\n')}`);
  }
  return parts.join('\n\n');
}

// ── Formato multi-fichero de continuity-keeper ────────────────────────────────
// Marcadores en vez de JSON: escapar markdown dentro de JSON cuesta tokens en cada
// llamada y no compra nada aquí.
function splitFiles(text) {
  const files = [];
  const re = /<<<FILE:\s*(.+?)\s*>>>/g;
  const marks = [...text.matchAll(re)];
  for (let i = 0; i < marks.length; i += 1) {
    const start = marks[i].index + marks[i][0].length;
    const end = i + 1 < marks.length ? marks[i + 1].index : text.length;
    files.push({ path: marks[i][1].trim(), content: text.slice(start, end).trim() });
  }
  return files;
}

function writeBibleFiles(ctx, agent, files) {
  const written = [];
  for (const f of files) {
    const rel = f.path.startsWith('bible/') ? f.path : `bible/${f.path}`;
    writeArtifact({
      root: ctx.root, novel: ctx.cfg.run.novel, relativePath: rel,
      content: f.content, agent, canWrite,
    });
    written.push(rel);
  }
  return written;
}

// ── Presupuesto ───────────────────────────────────────────────────────────────
function checkBudget(ctx) {
  if (!ctx.budget.exceeded()) return null;
  const s = ctx.budget.summary();
  console.warn(`\n⚠  Presupuesto superado: ~${s.estimatedUsd} USD de ${s.maxUsd} · ` +
    `${s.inputTokens + s.outputTokens} tokens. Política: ${ctx.budget.onExceed}`);
  return ctx.budget.onExceed;
}

// ── SETUP ─────────────────────────────────────────────────────────────────────
async function runSetup(ctx) {
  const { cfg } = ctx;
  const dir = novelDir(ctx.root, cfg.run.novel);
  const brief = readIfExists(join(dir, 'brief.md'));
  if (!brief) throw new Error(`Falta novels/${cfg.run.novel}/brief.md (input del usuario)`);

  console.log('\n▸ SETUP · corre una vez');

  // RES0 — dossier temático
  let dossier = '';
  if (cfg.research.enabled) {
    console.log('  1 · researcher (dossier)');
    const res = await invoke(ctx, {
      agentId: 'researcher', mode: 'dossier', node: 'RES0',
      limits: { maxSearches: cfg.research.maxSearchesSetup },
      userPrompt: `Brief de la novela:\n\n${brief}\n\n` +
        `Produce el dossier temático. Tope duro: ${cfg.research.maxSearchesSetup} búsquedas.`,
    });
    dossier = res.text;
    writeArtifact({
      root: ctx.root, novel: cfg.run.novel, relativePath: 'research/dossier.md',
      content: dossier, agent: res.agent, canWrite,
    });
  } else {
    console.log('  1 · researcher (dossier) — omitido: research.enabled = false');
  }

  // ARCH — actos y escaleta (propuesta; no escribe en disco)
  console.log('  2 · plot-architect');
  const arch = await invoke(ctx, {
    agentId: 'plot-architect', node: 'ARCH',
    userPrompt: `Brief:\n\n${brief}\n\n## Dossier\n\n${dossier || '(sin dossier)'}\n\n` +
      `Divide la novela en ${cfg.scope.acts} acto(s) y ${cfg.scope.chapters} capítulos, ` +
      `de unas ${cfg.scope.wordsPerChapter} palabras cada uno.`,
  });

  // PROF — fichas de personaje (propuesta; no escribe en disco)
  console.log('  3 · character-profiler');
  const prof = await invoke(ctx, {
    agentId: 'character-profiler', node: 'PROF',
    userPrompt: `Brief:\n\n${brief}\n\n## Escaleta propuesta\n\n${arch.text}\n\n` +
      `Produce las fichas de los personajes que la escaleta necesita.`,
  });

  // Seed — la invariante 2 exige que la escritura inicial la haga continuity-keeper
  console.log('  · continuity-keeper (seed) — escritura inicial de la biblia');
  const seed = await invoke(ctx, {
    agentId: 'continuity-keeper', mode: 'seed', node: 'SEED',
    output: {
      format: 'files',
      files: ['canon.md', 'world.md', 'characters.md', 'outline.md', 'timeline.md', 'threads.md'],
    },
    userPrompt: `## Brief\n\n${brief}\n\n## Escaleta propuesta\n\n${arch.text}\n\n` +
      `## Fichas propuestas\n\n${prof.text}\n\n## Dossier\n\n${dossier || '(sin dossier)'}`,
  });
  const written = writeBibleFiles(ctx, seed.agent, splitFiles(seed.text));
  if (!written.some((p) => p.endsWith('canon.md'))) {
    throw new Error('El seed no produjo bible/canon.md, que es lo que decide BOOT');
  }

  git.stageAndCommit({
    root: ctx.root,
    paths: [`novels/${cfg.run.novel}`],
    subject: 'setup: bible seed',
    body: `Dossier, escaleta y fichas fundidos en la biblia por continuity-keeper.\n` +
      `Ficheros: ${written.join(', ')}.`,
  });
  console.log(`  ✓ biblia sembrada: ${written.join(', ')}`);
}

// ── Un capítulo ───────────────────────────────────────────────────────────────
async function runChapter(ctx, chapter) {
  const { cfg } = ctx;
  const act = actOf(cfg, chapter);
  console.log(`\n▸ Capítulo ${chapter} (acto ${act})`);

  const context = assembleContext(ctx, chapter);
  const maxWords = Math.round(cfg.scope.wordsPerChapter * (1 + (cfg.scope.wordsTolerance ?? 0.2)));

  // BEAT
  console.log('  4 · beat-planner');
  const beat = await invoke(ctx, {
    agentId: 'beat-planner', node: 'BEAT', chapter,
    output: {
      format: 'json',
      schema: BEATS_SCHEMA,
      // En seco, el marcador trae la forma del esquema, no un objeto cualquiera:
      // así el resto del bucle se ejercita con datos de la misma pinta que los reales.
      dryRunValue: {
        title: `[DRY-RUN] Capítulo ${chapter}`,
        goal: 'Meta marcador.', conflict: 'Conflicto marcador.',
        turn: 'Giro marcador.', hook: 'Gancho marcador.',
        // Una pregunta en el capítulo 1 para que el ciclo GAP ⇄ RES1 también se recorra.
        researchQuestions: chapter === 1 ? ['[DRY-RUN] pregunta marcador'] : [],
      },
    },
    userPrompt: `${context}\n\n## Tarea\n\nPlanifica el capítulo ${chapter} de ` +
      `${cfg.scope.chapters} (acto ${act}). Declara en researchQuestions solo los hechos ` +
      `que necesites verificados antes de escribir; si no necesitas ninguno, deja la lista vacía.`,
  });
  const beats = beat.json ?? { title: `Capítulo ${chapter}`, goal: '', conflict: '', turn: '', hook: '', researchQuestions: [] };
  writeArtifact({
    root: ctx.root, novel: cfg.run.novel, relativePath: `notes/ch${nn(chapter)}-beats.md`,
    agent: beat.agent, canWrite,
    content: `# ${beats.title}\n\n- **Meta:** ${beats.goal}\n- **Conflicto:** ${beats.conflict}\n` +
      `- **Giro:** ${beats.turn}\n- **Gancho:** ${beats.hook}\n\n` +
      `## Lagunas de investigación\n\n${(beats.researchQuestions ?? []).map((q) => `- ${q}`).join('\n') || '- (ninguna)'}\n`,
  });

  // GAP ⇄ RES1 — ciclo acotado
  let notes = '';
  let rounds = 0;
  let questions = cfg.research.enabled ? (beats.researchQuestions ?? []) : [];
  while (questions.length && rounds < cfg.limits.maxResearchRounds) {
    rounds += 1;
    console.log(`  1 · researcher (notes) · ronda ${rounds}`);
    const res = await invoke(ctx, {
      agentId: 'researcher', mode: 'notes', node: 'RES1', chapter,
      limits: { maxSearches: cfg.research.maxSearchesPerChapter },
      userPrompt: `Preguntas del capítulo ${chapter}:\n\n` +
        questions.map((q, i) => `${i + 1}. ${q}`).join('\n') +
        `\n\nTope duro: ${cfg.research.maxSearchesPerChapter} búsquedas. ` +
        `Toda afirmación lleva fuente y fecha de consulta.`,
    });
    notes += `${res.text}\n`;
    questions = []; // una ronda por pregunta declarada; el tope está en el bucle
  }
  if (notes) {
    writeArtifact({
      root: ctx.root, novel: cfg.run.novel, relativePath: `research/ch${nn(chapter)}-notes.md`,
      content: notes, agent: ctx.agents.get('researcher'), canWrite,
    });
  }
  const unresolved = cfg.research.enabled && rounds >= cfg.limits.maxResearchRounds && questions.length;

  // WRITE → VOICE → validadores → REPORT → BLOCK, con tope de reescrituras
  let attempt = 0;
  let flagged = false;
  let chapterText = '';
  let issues = [];
  let humanNotes = ctx.pendingHumanNotes ?? '';
  ctx.pendingHumanNotes = '';

  for (;;) {
    attempt += 1;
    ctx.attempt = attempt;
    const blockers = issues.filter((i) => i.severity === 'blocker');

    console.log(`  5 · scene-writer · intento ${attempt}`);
    const draft = await invoke(ctx, {
      agentId: 'scene-writer', node: 'WRITE', chapter,
      limits: { maxWords },
      userPrompt: `${context}\n\n## Plan del capítulo\n\n` +
        `Meta: ${beats.goal}\nConflicto: ${beats.conflict}\nGiro: ${beats.turn}\nGancho: ${beats.hook}\n\n` +
        `## Notas con fuente\n\n${notes || '(ninguna: no afirmes hechos técnicos concretos)'}\n\n` +
        (unresolved ? `## Restricción\n\nQuedaron lagunas sin resolver. No afirmes nada sobre ellas.\n\n` : '') +
        (blockers.length ? `## Incidencias que DEBES corregir\n\n${blockers.map((b) => `- ${b.where}: ${b.claim} → ${b.fix}`).join('\n')}\n\n` : '') +
        (humanNotes ? `## Notas del editor humano\n\n${humanNotes}\n\n` : '') +
        `## Tarea\n\nEscribe el capítulo ${chapter}. Objetivo: ${cfg.scope.wordsPerChapter} ` +
        `palabras, máximo ${maxWords}. Solo prosa.`,
    });
    const draftPath = writeArtifact({
      root: ctx.root, novel: cfg.run.novel, relativePath: `chapters/ch${nn(chapter)}.draft.md`,
      content: draft.text, agent: draft.agent, canWrite,
    });

    console.log('  6 · voice-editor');
    const voiced = await invoke(ctx, {
      agentId: 'voice-editor', node: 'VOICE', chapter,
      userPrompt: `Borrador del capítulo ${chapter}:\n\n${draft.text}\n\n## Tarea\n\n` +
        `Afila y recorta. No añadas nada: ni hechos, ni diálogo, ni nombres, ni detalle nuevo.`,
    });

    // Invariante 4 comprobada por conteo: el texto no puede crecer.
    const draftWords = countWords(draft.text);
    const voicedWords = countWords(voiced.text);
    if (voicedWords > draftWords) {
      console.warn(`  ⚠  voice-editor añadió texto (${draftWords} → ${voicedWords} palabras). ` +
        `Se conserva el borrador: la invariante 4 manda sobre su salida.`);
      chapterText = draft.text;
    } else {
      chapterText = voiced.text;
    }
    writeArtifact({
      root: ctx.root, novel: cfg.run.novel, relativePath: `chapters/ch${nn(chapter)}.md`,
      content: chapterText, agent: voiced.agent, canWrite,
    });

    // VAL1 ∥ VAL2 — la única paralelización del diseño, legítima porque ninguno escribe
    const validations = [];
    if (cfg.validation.continuity) {
      validations.push(invoke(ctx, {
        agentId: 'continuity-keeper', mode: 'validate', node: 'VAL1', chapter,
        output: { format: 'json', schema: ISSUES_SCHEMA },
        userPrompt: `${context}\n\n## Capítulo ${chapter}\n\n${chapterText}\n\n` +
          `## Tarea\n\nContrasta el capítulo contra el canon. Solo informas; no escribes nada.`,
      }).then((r) => ({ source: 'continuity-keeper', issues: r.json?.issues ?? [] })));
    }
    if (cfg.validation.technical) {
      validations.push(invoke(ctx, {
        agentId: 'technical-verifier', node: 'VAL2', chapter,
        output: { format: 'json', schema: ISSUES_SCHEMA },
        userPrompt: `## Capítulo ${chapter}\n\n${chapterText}\n\n## Notas con fuente\n\n` +
          `${notes || '(ninguna)'}\n\n## Tarea\n\nToda afirmación técnica de la prosa que no ` +
          `esté respaldada por las notas es un hecho inventado. Informa; no corrijas.`,
      }).then((r) => ({ source: 'technical-verifier', issues: r.json?.issues ?? [] })));
    }

    if (cfg.validation.continuity && cfg.validation.technical && cfg.validation.runInParallel) {
      console.log('  7 ∥ 8 · continuity-keeper (validate) y technical-verifier');
    }
    const reports = await Promise.all(validations);

    // REPORT — fundir sin reordenar ni reinterpretar
    issues = [];
    for (const r of reports) {
      const prefix = r.source === 'continuity-keeper' ? 'ck' : 'tv';
      r.issues.forEach((i, idx) => {
        issues.push({ id: `${prefix}-${nn(idx + 1)}`, source: r.source, canon: null, ...i });
      });
    }

    // Términos prohibidos: comprobación mecánica, no opinión (invariante 9).
    if (cfg.validation.bannedTerms) {
      for (const term of ctx.genrePack.banned) {
        const re = new RegExp(`\\b${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'iu');
        if (re.test(chapterText)) {
          issues.push({
            id: `bt-${issues.length + 1}`, source: 'orchestrator', severity: 'blocker',
            kind: 'banned-term', where: `ch${nn(chapter)}`, canon: `genres/${cfg.run.genre}/banned-terms.txt`,
            claim: `Aparece el término prohibido "${term}".`, fix: 'Sustitúyelo por lenguaje original.',
          });
        }
      }
    }

    // Blocker sintético del modo en seco: sin esto el seco solo recorre el camino feliz.
    if (cfg.execution.dryRun && cfg.execution.dryRunInjectBlockerAt === chapter) {
      issues.push({
        id: 'dry-01', source: 'orchestrator', severity: 'blocker', kind: 'canon-conflict',
        where: `ch${nn(chapter)} ¶1`, canon: null,
        claim: '[DRY-RUN] Incidencia sintética para recorrer BLOCK → WRITE → FLAG.',
        fix: 'Ninguna: existe para probar el camino, no para resolverse.',
      });
    }

    writeArtifact({
      root: ctx.root, novel: cfg.run.novel, relativePath: `notes/ch${nn(chapter)}-issues.json`,
      agent: ctx.agents.get('orchestrator'), canWrite,
      content: JSON.stringify({
        report: 'storymaker/issue-report@1', novel: cfg.run.novel, chapter, attempt, issues,
        counts: {
          blocker: issues.filter((i) => i.severity === 'blocker').length,
          warning: issues.filter((i) => i.severity === 'warning').length,
          note: issues.filter((i) => i.severity === 'note').length,
        },
      }, null, 2),
    });

    // BLOCK — invariante 7: solo blocker reescribe
    const nowBlockers = issues.filter((i) => i.severity === 'blocker');
    console.log(`  · REPORT: ${nowBlockers.length} blocker · ` +
      `${issues.filter((i) => i.severity === 'warning').length} warning · ` +
      `${issues.filter((i) => i.severity === 'note').length} note`);

    if (!nowBlockers.length) break;
    if (attempt > cfg.limits.maxRewrites) {
      flagged = true;
      console.warn(`  ⚠  FLAG: ${nowBlockers.length} blocker sin resolver tras ` +
        `${cfg.limits.maxRewrites} reescritura(s). Escala al humano.`);
      break;
    }
    humanNotes = '';
    console.log(`  ↻ BLOCK → WRITE (reescritura ${attempt} de ${cfg.limits.maxRewrites})`);
  }

  return { chapterText, issues, flagged, beats, act };
}

// ── COMMIT ────────────────────────────────────────────────────────────────────
async function commitChapter(ctx, chapter, { chapterText, issues, beats, flagged }) {
  const { cfg } = ctx;
  console.log('  7 · continuity-keeper (commit) — biblia + resumen');

  const commit = await invoke(ctx, {
    agentId: 'continuity-keeper', mode: 'commit', node: 'COMMIT', chapter,
    output: {
      format: 'files',
      files: [`summaries/ch${nn(chapter)}.md`, 'threads.md', 'timeline.md'],
    },
    userPrompt: `${assembleContext(ctx, chapter)}\n\n## Capítulo ${chapter} aprobado\n\n` +
      `${chapterText}\n\n## Tarea\n\nActualiza la biblia y escribe el resumen del capítulo. ` +
      `El resumen es corto: 120 palabras como mucho.`,
  });
  const written = writeBibleFiles(ctx, commit.agent, splitFiles(commit.text));

  const counts = {
    blocker: issues.filter((i) => i.severity === 'blocker').length,
    warning: issues.filter((i) => i.severity === 'warning').length,
    note: issues.filter((i) => i.severity === 'note').length,
  };
  const hash = git.stageAndCommit({
    root: ctx.root,
    paths: [`novels/${cfg.run.novel}`],
    subject: `ch${nn(chapter)}: ${beats.title ?? `Capítulo ${chapter}`}`,
    body: `Biblia actualizada: ${written.join(', ') || '(sin cambios)'}.\n` +
      `Incidencias abiertas: ${counts.warning} warning, ${counts.note} note` +
      (flagged ? `, ${counts.blocker} blocker SIN RESOLVER (capítulo marcado).` : '.'),
  });

  console.log(`  ✓ commit ${hash ?? '(sin cambios)'}`);
  return hash;
}

// ── Corrida completa ──────────────────────────────────────────────────────────
export async function run(ctx) {
  const { cfg } = ctx;
  const dir = novelDir(ctx.root, cfg.run.novel);

  // BOOT
  const bibleExists = existsSync(join(dir, 'bible', 'canon.md'));
  if (!bibleExists) {
    ctx.state.phase = 'setup';
    writeState(ctx.root, cfg.run.novel, ctx.state);
    await runSetup(ctx);
  } else {
    console.log('\n▸ BOOT · la biblia existe: se entra por LOAD (reanudación o continuación)');
  }

  ctx.state.phase = 'chapter-loop';
  const start = ctx.state.lastApprovedChapter + 1;
  if (start > 1) console.log(`  Reanudando: capítulos 1..${start - 1} ya aprobados, no se regeneran.`);

  let chapter = start;
  while (chapter <= cfg.scope.chapters) {
    ctx.state.chapter = chapter;
    ctx.state.node = 'LOAD';
    writeState(ctx.root, cfg.run.novel, ctx.state);

    const result = await runChapter(ctx, chapter);

    // GATE
    const budgetPolicy = checkBudget(ctx);
    const reason = gateNeeded({
      cfg, chapter, flagged: result.flagged,
      budgetPaused: budgetPolicy === 'pause-at-gate',
    });

    let decision = { type: 'approve' };
    if (reason) {
      present({
        cfg, chapter, reason,
        chapters: [{
          number: chapter, title: result.beats.title,
          words: countWords(result.chapterText), text: result.chapterText,
        }],
        issues: result.issues, flagged: result.flagged,
        budget: ctx.budget.summary(),
      });
      decision = await askDecision({
        chapter,
        allowRevise: ctx.state.counters.humanRevisions < cfg.limits.maxHumanRevisions,
        scripted: ctx.scriptedDecisions,
      });
    }

    if (decision.type === 'revise') {
      ctx.state.counters.humanRevisions += 1;
      ctx.pendingHumanNotes = decision.notes;
      console.log(`  ↻ DEC → WRITE con notas (revisión ${ctx.state.counters.humanRevisions} ` +
        `de ${cfg.limits.maxHumanRevisions}). El contador de reescrituras vuelve a cero.`);
      continue; // mismo capítulo, contador de reescrituras reiniciado (spec §16.2)
    }

    if (decision.type === 'rollback') {
      const target = decision.target;
      const stamp = new Date().toISOString().replace(/[:.]/g, '-');
      const { atticDir, moved } = git.archiveChapters({
        root: ctx.root, novel: cfg.run.novel,
        fromChapter: target + 1, toChapter: chapter, stamp,
      });
      const targetCommit = git.lastChapterCommit(ctx.root, cfg.run.novel);
      if (targetCommit) git.restoreBible({ root: ctx.root, novel: cfg.run.novel, commitHash: targetCommit.hash });
      git.stageAndCommit({
        root: ctx.root, paths: [`novels/${cfg.run.novel}`],
        subject: `rollback: to ch${nn(target)}, archived ch${nn(target + 1)}..ch${nn(chapter)}`,
        body: `Archivados en ${atticDir}: ${moved.join(', ') || '(nada)'}.\n` +
          `La biblia vuelve al estado del capítulo ${target}.`,
      });
      ctx.state.lastApprovedChapter = target;
      ctx.state.counters = { researchRounds: 0, rewrites: 0, humanRevisions: 0 };
      writeState(ctx.root, cfg.run.novel, ctx.state);
      console.log(`  ↺ ROLL → LOAD · vuelta al capítulo ${target + 1}`);
      chapter = target + 1;
      continue;
    }

    // COMMIT
    const hash = await commitChapter(ctx, chapter, result);
    ctx.state.lastApprovedChapter = chapter;
    ctx.state.lastApprovedCommit = hash;
    ctx.state.counters = { researchRounds: 0, rewrites: 0, humanRevisions: 0 };
    if (result.flagged) ctx.state.flagged.push({ chapter, issues: result.issues.length });
    ctx.state.usage = ctx.budget.summary();
    writeState(ctx.root, cfg.run.novel, ctx.state);

    if (budgetPolicy === 'stop-after-chapter') {
      console.warn('\n⚠  Presupuesto superado. Se corta tras el commit, con el estado a salvo.');
      return { stopped: 'budget', lastChapter: chapter };
    }

    chapter += 1;
  }

  // COMP
  console.log('\n▸ 9 · compiler — ensamblado del manuscrito');
  const chapters = [];
  for (let n = 1; n <= cfg.scope.chapters; n += 1) {
    const text = readIfExists(join(dir, 'chapters', `ch${nn(n)}.md`));
    if (text) chapters.push(`## Capítulo ${n}\n\n${text.trim()}`);
  }
  const compiled = await invoke(ctx, {
    agentId: 'compiler', node: 'COMP',
    userPrompt: `Escaleta:\n\n${readIfExists(join(dir, 'bible', 'outline.md')) ?? '(sin escaleta)'}\n\n` +
      `## Capítulos aprobados\n\n${chapters.join('\n\n')}\n\n## Tarea\n\nEnsambla el manuscrito: ` +
      `portada, cortes de acto y títulos. No reescribas la prosa.`,
  });
  writeArtifact({
    root: ctx.root, novel: cfg.run.novel,
    relativePath: cfg.output.manuscriptPath ?? 'out/manuscript.md',
    content: compiled.text, agent: compiled.agent, canWrite,
  });

  // EXPORT — mecánico, sin agente: no hay decisión que tomar
  for (const format of cfg.output.outputFormats) {
    if (format === 'markdown') continue;
    console.warn(`  ⚠  EXPORT ${format}: requiere herramienta externa de conversión, ` +
      `que no está en el harness. El Markdown canónico sí está (invariante 8).`);
  }

  git.stageAndCommit({
    root: ctx.root, paths: [`novels/${cfg.run.novel}`],
    subject: `compile: manuscript.md (${cfg.scope.chapters} capítulos)`,
    body: `Ensamblado por compiler. Formatos: ${cfg.output.outputFormats.join(', ')}.`,
  });

  ctx.state.phase = 'done';
  ctx.state.usage = ctx.budget.summary();
  writeState(ctx.root, cfg.run.novel, ctx.state);
  return { stopped: null, lastChapter: cfg.scope.chapters };
}
