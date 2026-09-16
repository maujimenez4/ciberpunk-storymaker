// Carga de configuración: base + overlay de perfil, merge superficial por sección.
// Mecánico. No decide nada de comportamiento; solo lee ficheros y los funde.

import { readFileSync, existsSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';

const META_KEYS = new Set(['config', 'profile', 'extends']);

// Secciones cuyo contenido se funde clave a clave. Los arrays se reemplazan enteros.
const SECTIONS = [
  'run', 'scope', 'supervision', 'validation',
  'research', 'limits', 'budget', 'output', 'execution',
];

function readJson(path) {
  if (!existsSync(path)) throw new Error(`No existe el fichero de configuración: ${path}`);
  try {
    return JSON.parse(readFileSync(path, 'utf8'));
  } catch (e) {
    throw new Error(`JSON inválido en ${path}: ${e.message}`);
  }
}

// Merge superficial por sección, tal y como lo fija la spec §12.1.
// execution.models es la única excepción: se declara como mapa fusionable.
function mergeConfig(base, overlay) {
  const out = structuredClone(base);
  for (const [key, value] of Object.entries(overlay)) {
    if (META_KEYS.has(key)) { out[key] = value; continue; }
    if (!SECTIONS.includes(key)) {
      throw new Error(`Sección desconocida en el overlay: "${key}"`);
    }
    out[key] = { ...(out[key] ?? {}), ...value };
    if (key === 'execution' && value.models) {
      out.execution.models = { ...(base.execution?.models ?? {}), ...value.models };
    }
  }
  return out;
}

const REQUIRED_KEYS = [
  'run.genre', 'scope.chapters', 'scope.acts', 'scope.wordsPerChapter',
  'supervision.approvalMode', 'research.enabled', 'limits.maxRewrites',
  'limits.maxResearchRounds', 'limits.maxHumanRevisions',
  'budget.maxUsd', 'budget.onExceed', 'output.outputFormats', 'execution.models',
];

const APPROVAL_MODES = ['every-chapter', 'act-end-or-flagged', 'never'];
const ON_EXCEED = ['pause-at-gate', 'stop-after-chapter', 'warn'];
const FORMATS = ['markdown', 'pdf', 'epub'];

function readPath(obj, path) {
  return path.split('.').reduce((o, k) => (o == null ? undefined : o[k]), obj);
}

function validate(cfg) {
  for (const path of REQUIRED_KEYS) {
    if (readPath(cfg, path) === undefined) {
      throw new Error(`Falta la clave obligatoria de configuración: ${path}`);
    }
  }
  if (!APPROVAL_MODES.includes(cfg.supervision.approvalMode)) {
    throw new Error(`supervision.approvalMode inválido: ${cfg.supervision.approvalMode}`);
  }
  if (!ON_EXCEED.includes(cfg.budget.onExceed)) {
    throw new Error(`budget.onExceed inválido: ${cfg.budget.onExceed}`);
  }
  for (const f of cfg.output.outputFormats) {
    if (!FORMATS.includes(f)) throw new Error(`Formato de salida desconocido: ${f}`);
  }
  if (cfg.scope.acts > cfg.scope.chapters) {
    throw new Error('scope.acts no puede superar a scope.chapters');
  }
  // Invariante 3: desactivar la exigencia de fuente y fecha no está soportado.
  if (cfg.research.enabled && cfg.research.requireSourceAndDate === false) {
    throw new Error('research.requireSourceAndDate: false contradice la invariante 3');
  }
  // La invariante 8 hace de markdown el formato canónico: no es opcional.
  if (!cfg.output.outputFormats.includes('markdown')) {
    throw new Error('output.outputFormats debe incluir "markdown" (invariante 8)');
  }
  return cfg;
}

/**
 * Carga el perfil indicado y lo funde sobre su base.
 * @param {string} profile  nombre del fichero en config/profiles, sin extensión
 * @param {string} root     raíz del repositorio
 */
export function loadConfig(profile, root) {
  const profilePath = join(root, 'config', 'profiles', `${profile}.json`);
  const overlay = readJson(profilePath);
  const basePath = overlay.extends
    ? resolve(dirname(profilePath), overlay.extends)
    : join(root, 'config', 'run.base.json');
  const cfg = validate(mergeConfig(readJson(basePath), overlay));
  cfg.profileName = profile;
  return cfg;
}

/** Aplica los overrides de la línea de comandos sobre la configuración ya fundida. */
export function applyFlags(cfg, flags) {
  if (flags.novel) cfg.run.novel = flags.novel;
  if (flags.dryRun !== undefined) cfg.execution.dryRun = flags.dryRun;
  if (!cfg.run.novel) {
    throw new Error('run.novel no está fijado en el perfil: pásalo con --novel <slug>');
  }
  return cfg;
}
