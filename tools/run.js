#!/usr/bin/env node
// Punto de entrada. Un solo comando:
//
//   npm start                       corre el perfil smoke-3ch tal y como está
//   npm start -- --profile X        otro perfil
//   npm start -- --dry-run          fuerza modo en seco
//   npm run invariantes             solo comprueba permisos y sale
//
// El código de aquí abajo es mecánico: leer flags, cargar, comprobar, arrancar.

import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { existsSync, mkdirSync } from 'node:fs';

import { loadConfig, applyFlags } from './config.js';
import { loadAgents, loadSkills, loadGenrePack, checkInvariants } from './agents.js';
import { Budget } from './call.js';
import { readState, emptyState, writeState, novelDir } from './state.js';
import { run } from './loop.js';
import * as git from './git.js';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');

function parseFlags(argv) {
  const flags = { profile: 'smoke-3ch', checkOnly: false };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--profile' || arg === '-p') flags.profile = argv[++i];
    else if (arg === '--novel' || arg === '-n') flags.novel = argv[++i];
    else if (arg === '--dry-run') flags.dryRun = true;
    else if (arg === '--live') flags.dryRun = false;
    else if (arg === '--check-only') flags.checkOnly = true;
    else if (arg === '--yes') flags.scripted = (flags.scripted ?? []).concat('a');
    else if (arg === '--decide') flags.scripted = (flags.scripted ?? []).concat(argv[++i]);
    else if (arg === '--help' || arg === '-h') flags.help = true;
    else throw new Error(`Flag desconocido: ${arg}`);
  }
  return flags;
}

const HELP = `
StoryMaker — escribe una novela capítulo a capítulo.

  npm start                        perfil smoke-3ch (viene en seco)
  npm start -- --profile <id>      otro perfil de config/profiles/
  npm start -- --novel <slug>      otra novela de novels/
  npm start -- --dry-run | --live  fuerza o desactiva el modo en seco
  npm start -- --decide a          respuesta guionizada para la compuerta
  npm run invariantes              comprueba permisos de los agentes y sale
`;

async function main() {
  const flags = parseFlags(process.argv.slice(2));
  if (flags.help) { console.log(HELP); return; }

  if (!git.isRepo(ROOT)) throw new Error('Esto no es un repositorio git, y el commit por capítulo es parte del diseño.');

  // 1. Comportamiento desde ficheros de texto
  const agents = loadAgents(ROOT);
  const skills = loadSkills(ROOT);

  // 2. Invariantes 2 y 3 como precondición de ejecución, antes de nada
  const check = checkInvariants(agents);
  console.log(`✓ Invariantes de permisos: ${check.total} agentes · ` +
    `acceso web solo ${check.web} · escribe la biblia solo ${check.bible}`);
  if (flags.checkOnly) return;

  // 3. Configuración
  const cfg = applyFlags(loadConfig(flags.profile, ROOT), flags);
  const genrePack = loadGenrePack(ROOT, cfg.run.genre);

  const dir = novelDir(ROOT, cfg.run.novel);
  if (!existsSync(join(dir, 'brief.md'))) {
    throw new Error(`Falta novels/${cfg.run.novel}/brief.md`);
  }
  mkdirSync(dir, { recursive: true });

  // 4. Estado: el índice se lee, pero la verdad es el historial de git
  let state = readState(ROOT, cfg.run.novel);
  if (!state) {
    const last = git.lastChapterCommit(ROOT, cfg.run.novel);
    state = emptyState(cfg);
    if (last?.chapter) {
      state.lastApprovedChapter = last.chapter;
      state.lastApprovedCommit = last.hash;
      console.log(`  Estado reconstruido desde git: último capítulo aprobado ${last.chapter} (${last.hash}).`);
    }
    writeState(ROOT, cfg.run.novel, state);
  }

  const budget = new Budget(cfg);

  console.log(`\nStoryMaker · novela "${cfg.run.novel}" · perfil "${cfg.profileName}"`);
  console.log(`  ${cfg.scope.chapters} capítulos · ${cfg.scope.acts} acto(s) · ` +
    `${cfg.scope.wordsPerChapter} palabras/capítulo`);
  console.log(`  supervisión: ${cfg.supervision.approvalMode} · ` +
    `reescrituras: ${cfg.limits.maxRewrites} · web: ${cfg.research.enabled ? 'sí' : 'no'}`);
  console.log(cfg.execution.dryRun
    ? '  MODO EN SECO: no se llama a ningún modelo, no se gasta nada.'
    : `  MODO REAL: tope de gasto ${cfg.budget.maxUsd} USD (${cfg.budget.onExceed}).`);

  const ctx = {
    root: ROOT, cfg, agents, skills, genrePack, budget, state,
    scriptedDecisions: flags.scripted ?? null,
    attempt: 1, pendingHumanNotes: '',
  };

  const outcome = await run(ctx);

  const s = budget.summary();
  console.log(`\n${'─'.repeat(72)}`);
  console.log(`Fin · ${outcome.stopped ? `detenido por ${outcome.stopped}` : 'completado'} ` +
    `en el capítulo ${outcome.lastChapter}`);
  console.log(`Gasto: ${s.calls} llamadas · ${s.inputTokens} tokens de entrada · ` +
    `${s.outputTokens} de salida · ${s.cacheReadTokens} leídos de caché · ` +
    `${s.searches} búsquedas · ~${s.estimatedUsd} USD de ${s.maxUsd}`);
  console.log(`Registro por llamada: novels/${cfg.run.novel}/run-log.jsonl`);
}

main().catch((e) => {
  console.error(`\n✗ ${e.message}`);
  process.exitCode = 1;
});
