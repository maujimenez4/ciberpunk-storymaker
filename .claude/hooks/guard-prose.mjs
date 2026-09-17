#!/usr/bin/env node
// PreToolUse sobre escrituras de capítulo · invariantes 4 y 9.
//
// Deniega ANTES de escribir, no avisa después. Prevenir es más barato que detectar:
// un capítulo con un término prohibido ya escrito cuesta una reescritura entera.
//
//   - Invariante 4: voice-editor no puede añadir. Si su salida tiene más palabras que
//     el borrador, se rechaza.
//   - Invariante 9: worldbuilding original. Un término de la lista de prohibidos del
//     pack de género no llega a disco.

import { readFileSync, existsSync } from 'node:fs';

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

const countWords = (text) => (String(text).match(/\S+/g) ?? []).length;

function bannedTerms(repoRoot, genre) {
  const path = `${repoRoot}/genres/${genre}/banned-terms.txt`;
  if (!existsSync(path)) return [];
  return readFileSync(path, 'utf8')
    .split('\n').map((l) => l.trim()).filter((l) => l && !l.startsWith('#'));
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

  if (!['Write', 'Edit'].includes(hook.tool_name)) allow();

  const filePath = String(hook.tool_input?.file_path ?? '').replace(/\\/g, '/');
  const chapter = filePath.match(/novels\/[^/]+\/chapters\/ch(\d{2})(\.draft)?\.md$/);
  if (!chapter) allow();

  const content = hook.tool_input?.content ?? hook.tool_input?.new_string ?? '';
  const isDraft = Boolean(chapter[2]);
  const repoRoot = filePath.replace(/\/novels\/.*$/, '');

  // ── Invariante 9 ──────────────────────────────────────────────────────────
  // Se comprueba en los dos —borrador y editado—: la lista no negocia.
  let genre = 'cyberpunk-thriller';
  const cfgPath = `${repoRoot}/config/run.base.json`;
  if (existsSync(cfgPath)) {
    try { genre = JSON.parse(readFileSync(cfgPath, 'utf8')).run?.genre ?? genre; } catch { /* valor por defecto */ }
  }

  for (const term of bannedTerms(repoRoot, genre)) {
    const re = new RegExp(`\\b${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'iu');
    if (re.test(content)) {
      deny(
        `Invariante 9 (worldbuilding original): el texto contiene "${term}", que está en ` +
        `genres/${genre}/banned-terms.txt. Es un término acuñado por una obra existente. ` +
        `Sustitúyelo por lenguaje original y vuelve a escribir.`,
      );
    }
  }

  // ── Invariante 4 ──────────────────────────────────────────────────────────
  if (!isDraft) {
    const draftPath = filePath.replace(/\.md$/, '.draft.md');
    if (existsSync(draftPath)) {
      const draftWords = countWords(readFileSync(draftPath, 'utf8'));
      const newWords = countWords(content);
      if (newWords > draftWords) {
        deny(
          `Invariante 4 (voice-editor no añade): la versión editada tiene ${newWords} ` +
          `palabras y el borrador ${draftWords}. El editor de voz solo quita y afila; ` +
          `si pudiera añadir, metería hechos después de que los validadores ya corrieron. ` +
          `Corta en vez de añadir.`,
        );
      }
    }
  }

  allow();
});
