#!/usr/bin/env node
// PreToolUse · invariantes 2 y 3.
//
// Cuando el orquestador es un modelo, el prompt deja de ser garantía: es una petición
// que se puede ignorar, olvidar o reinterpretar. Este hook corre FUERA del modelo, así
// que no se le puede persuadir. Es el equivalente de tools/agents.js en la rama main.
//
// Deniega:
//   - Escritura bajo novels/*/bible/** a cualquiera que no sea continuity-keeper.
//   - Escritura en una ruta que el rol no tenga declarada en ownership.json.
//   - Búsqueda web a cualquiera que no sea researcher, incluido el hilo principal.

import { readFileSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HOOKS_DIR = dirname(fileURLToPath(import.meta.url));
const OWNERSHIP = JSON.parse(readFileSync(join(HOOKS_DIR, 'ownership.json'), 'utf8'));

const WRITE_TOOLS = new Set(['Write', 'Edit', 'NotebookEdit']);
const WEB_TOOLS = new Set(['WebSearch', 'WebFetch']);

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

function allow() {
  process.stdout.write('{}');
  process.exit(0);
}

// {NN} casa dos dígitos, ** cualquier profundidad, * cualquier cosa menos "/".
function patternToRegex(pattern) {
  const NUM = '';
  const DEEP = '';
  const body = pattern
    .replace(/\{NN\}/g, NUM)
    .replace(/\*\*/g, DEEP)
    .replace(/[.+^${}()|[\]\\]/g, '\\$&')
    .replace(/\*/g, '[^/]*')
    .replaceAll(DEEP, '.*')
    .replaceAll(NUM, '\\d{2}');
  return new RegExp(`^${body}$`);
}

/** Devuelve la ruta relativa a novels/<slug>/, o null si la escritura cae fuera. */
function novelRelative(filePath) {
  const normal = String(filePath).replace(/\\/g, '/');
  const match = normal.match(/novels\/[^/]+\/(.+)$/);
  return match ? match[1] : null;
}

function dryRunActive(filePath) {
  const normal = String(filePath).replace(/\\/g, '/');
  const match = normal.match(/^(.*novels\/[^/]+)\//);
  if (!match) return false;
  const statePath = `${match[1]}/run-state.json`; // Node acepta barras normales en Windows
  if (!existsSync(statePath)) return false;
  try {
    return JSON.parse(readFileSync(statePath, 'utf8')).dryRun === true;
  } catch {
    return false;
  }
}

let input = '';
process.stdin.on('data', (c) => { input += c; });
process.stdin.on('end', () => {
  let hook;
  try {
    hook = JSON.parse(input);
  } catch {
    allow(); // Un hook que no entiende su entrada no debe bloquear la sesión entera.
  }

  const tool = hook.tool_name;
  // agent_type solo viene cuando la llamada nace dentro de un subagente. Su ausencia
  // significa hilo principal, es decir el orquestador.
  const role = hook.agent_type ?? '__main__';

  // ── Invariante 3 ──────────────────────────────────────────────────────────
  if (WEB_TOOLS.has(tool)) {
    if (role !== 'researcher') {
      deny(
        `Invariante 3: solo "researcher" tiene acceso web, y esta llamada viene de ` +
        `"${role}". Los hechos llegan a la prosa únicamente por notas con fuente. ` +
        `Si hace falta un dato, lánzale el encargo a researcher.`,
      );
    }
    allow();
  }

  if (!WRITE_TOOLS.has(tool)) allow();

  const filePath = hook.tool_input?.file_path ?? hook.tool_input?.notebook_path;
  if (!filePath) allow();

  const relative = novelRelative(filePath);
  if (!relative) allow(); // Fuera de novels/: es código o documentación, no estado narrativo.

  // ── Invariante 2 ──────────────────────────────────────────────────────────
  if (relative.startsWith('bible/') && role !== 'continuity-keeper') {
    deny(
      `Invariante 2: la biblia narrativa tiene un solo escritor, "continuity-keeper", ` +
      `y esta escritura viene de "${role}". Si el canon tiene que cambiar, lánzale el ` +
      `encargo a continuity-keeper en modo commit; no lo edites por tu cuenta.`,
    );
  }

  // ── Rutas declaradas ──────────────────────────────────────────────────────
  // En seco el orquestador escribe todos los ficheros marcador, así que se le deja.
  if (role === '__main__' && dryRunActive(filePath)) allow();

  const owned = OWNERSHIP[role];
  if (!owned) {
    deny(`"${role}" no tiene rutas declaradas en .claude/hooks/ownership.json, así que no puede escribir dentro de novels/.`);
  }
  if (!owned.some((p) => patternToRegex(p).test(relative))) {
    deny(
      `"${role}" no puede escribir en "${relative}". Sus rutas declaradas son: ` +
      `${owned.join(', ')}. Escribe donde te toca, o pide el cambio en ` +
      `.claude/hooks/ownership.json.`,
    );
  }

  allow();
});
