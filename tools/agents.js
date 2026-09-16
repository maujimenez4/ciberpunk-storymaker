// Carga de comportamiento desde ficheros de texto y comprobación de invariantes.
//
// El comportamiento de los agentes NO vive aquí: vive en agents/*.md y skills/*.md.
// Este módulo solo los lee, compone el prompt y se niega a arrancar si el reparto de
// permisos que declaran contradice las invariantes 2 o 3.

import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';

// Única herramienta que algún agente puede declarar. Todo lo demás se rechaza en
// la comprobación de arranque: permisos al mínimo, y la lista está aquí, en código,
// para que editar un .md no pueda ampliarla.
const ALLOWED_TOOLS = ['WebSearch'];

// ── Frontmatter mínimo ────────────────────────────────────────────────────────
// Soporta escalares y listas en línea. No es YAML completo a propósito: mantener
// una dependencia menos vale más que soportar una sintaxis que aquí no se usa.
function parseFrontmatter(text, source) {
  if (!text.startsWith('---')) throw new Error(`${source}: falta el frontmatter`);
  const end = text.indexOf('\n---', 3);
  if (end === -1) throw new Error(`${source}: frontmatter sin cerrar`);

  const meta = {};
  for (const line of text.slice(3, end).split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const sep = trimmed.indexOf(':');
    if (sep === -1) throw new Error(`${source}: línea de frontmatter inválida: "${trimmed}"`);
    const key = trimmed.slice(0, sep).trim();
    const raw = trimmed.slice(sep + 1).trim();

    if (raw.startsWith('[')) {
      const inner = raw.slice(1, raw.lastIndexOf(']')).trim();
      meta[key] = inner === ''
        ? []
        : inner.split(',').map((v) => v.trim().replace(/^["']|["']$/g, ''));
    } else if (raw === 'true' || raw === 'false') {
      meta[key] = raw === 'true';
    } else {
      meta[key] = raw.replace(/^["']|["']$/g, '');
    }
  }
  return { meta, body: text.slice(end + 4).trim() };
}

// ── Modos ─────────────────────────────────────────────────────────────────────
// Un agente con varios modos los separa con "## MODO: <nombre>". Se envía el tronco
// común más el modo activo, nunca los demás: mandar modos que no se van a usar es
// gastar tokens de entrada en cada llamada.
function bodyForMode(body, mode, source) {
  const parts = body.split(/^## MODO: /m);
  const trunk = parts[0].trim();
  if (parts.length === 1) return trunk;

  const modes = new Map();
  for (const part of parts.slice(1)) {
    const nl = part.indexOf('\n');
    modes.set(part.slice(0, nl).trim(), part.slice(nl + 1).trim());
  }
  if (!mode || !modes.has(mode)) {
    throw new Error(`${source}: modo "${mode}" no definido (hay: ${[...modes.keys()].join(', ')})`);
  }
  return `${trunk}\n\n## Modo activo: ${mode}\n\n${modes.get(mode)}`;
}

// ── Rutas de escritura ────────────────────────────────────────────────────────
// Cada agente declara en su frontmatter qué rutas puede producir. El orquestador
// rechaza cualquier escritura fuera de esa declaración.
function patternToRegex(pattern) {
  // Los comodines se apartan ANTES de escapar, porque el escape convierte {NN} en
  // \{NN\} y entonces ya no hay nada que traducir.
  const NUM = '';
  const DEEP = '';
  const escaped = pattern
    .replace(/\{NN\}/g, NUM)
    .replace(/\*\*/g, DEEP)
    .replace(/[.+^${}()|[\]\\]/g, '\\$&')
    .replace(/\*/g, '[^/]*')
    .replaceAll(DEEP, '.*')
    .replaceAll(NUM, '\\d{2}');
  return new RegExp(`^${escaped}$`);
}

export function canWrite(agent, relativePath) {
  const normal = relativePath.replace(/\\/g, '/');
  return (agent.writes ?? []).some((p) => patternToRegex(p).test(normal));
}

// ── Carga ─────────────────────────────────────────────────────────────────────
export function loadSkills(root) {
  const dir = join(root, 'skills');
  const skills = new Map();
  if (!existsSync(dir)) return skills;
  for (const file of readdirSync(dir).filter((f) => f.endsWith('.md'))) {
    const source = `skills/${file}`;
    const { meta, body } = parseFrontmatter(readFileSync(join(dir, file), 'utf8'), source);
    if (!meta.id) throw new Error(`${source}: falta "id" en el frontmatter`);
    skills.set(meta.id, { ...meta, body, source });
  }
  return skills;
}

export function loadAgents(root) {
  const dir = join(root, 'agents');
  if (!existsSync(dir)) throw new Error('No existe el directorio agents/');
  const agents = new Map();
  for (const file of readdirSync(dir).filter((f) => f.endsWith('.md'))) {
    const source = `agents/${file}`;
    const { meta, body } = parseFrontmatter(readFileSync(join(dir, file), 'utf8'), source);
    if (!meta.id) throw new Error(`${source}: falta "id" en el frontmatter`);
    if (!Array.isArray(meta.tools)) throw new Error(`${source}: "tools" debe ser una lista`);
    agents.set(meta.id, {
      id: meta.id,
      tools: meta.tools,
      skills: meta.skills ?? [],
      writes: meta.writes ?? [],
      body,
      source,
    });
  }
  return agents;
}

// ── Invariantes 2 y 3 ─────────────────────────────────────────────────────────
// Esto es lo que convierte las invariantes en precondición de ejecución: si el
// reparto de permisos declarado en los .md no da exactamente uno y uno, no se corre.
export function checkInvariants(agents) {
  const withWeb = [];
  const withBible = [];

  for (const a of agents.values()) {
    if (a.tools.some((t) => t.startsWith('Web'))) withWeb.push(a);
    if (a.writes.some((p) => p.replace(/\\/g, '/').startsWith('bible/'))) withBible.push(a);
  }

  const failures = [];
  if (withWeb.length !== 1) {
    failures.push(
      `Invariante 3 (un solo rol con acceso web): hay ${withWeb.length} — ` +
      `${withWeb.map((a) => a.source).join(', ') || 'ninguno'}`,
    );
  } else if (withWeb[0].id !== 'researcher') {
    failures.push(`Invariante 3: el acceso web lo declara ${withWeb[0].source}, no researcher`);
  }

  if (withBible.length !== 1) {
    failures.push(
      `Invariante 2 (un solo escritor de la biblia): hay ${withBible.length} — ` +
      `${withBible.map((a) => a.source).join(', ') || 'ninguno'}`,
    );
  } else if (withBible[0].id !== 'continuity-keeper') {
    failures.push(`Invariante 2: la biblia la escribe ${withBible[0].source}, no continuity-keeper`);
  }

  for (const a of agents.values()) {
    const web = a.tools.some((t) => t.startsWith('Web'));
    const bible = a.writes.some((p) => p.startsWith('bible/'));
    if (web && bible) failures.push(`${a.source} acumula acceso web y escritura de biblia`);
    // Permisos al mínimo: ninguna herramienta de fichero ni de shell, para nadie.
    const forbidden = a.tools.filter((t) => !ALLOWED_TOOLS.includes(t));
    if (forbidden.length) {
      failures.push(`${a.source} declara herramientas no permitidas: ${forbidden.join(', ')}`);
    }
  }

  if (failures.length) {
    throw new Error(`Comprobación de invariantes fallida:\n  - ${failures.join('\n  - ')}`);
  }

  return { web: withWeb[0].id, bible: withBible[0].id, total: agents.size };
}

// ── Composición del prompt ────────────────────────────────────────────────────
// Orden deliberado: lo estable primero (agente, skills, pack de género), lo volátil
// después. El prefijo estable se repite idéntico entre llamadas del mismo rol, que es
// la condición para que la caché de prompt sirva de algo.
export function composePrompt({ agent, mode, skills, genrePack }) {
  const chunks = [bodyForMode(agent.body, mode, agent.source)];

  for (const id of agent.skills) {
    const skill = skills.get(id);
    if (!skill) throw new Error(`${agent.source} declara la skill "${id}", que no existe`);
    chunks.push(`# Skill: ${id}\n\n${skill.body}`);
  }

  if (genrePack && agent.skills.includes('genre-pack-loader')) {
    chunks.push(`# Pack de género\n\n${genrePack}`);
  }

  return chunks.join('\n\n---\n\n');
}

export function loadGenrePack(root, genre) {
  const dir = join(root, 'genres', genre);
  const packPath = join(dir, 'pack.md');
  const bannedPath = join(dir, 'banned-terms.txt');
  if (!existsSync(packPath)) throw new Error(`No existe el pack de género: genres/${genre}/pack.md`);

  let text = readFileSync(packPath, 'utf8').trim();
  let banned = [];
  if (existsSync(bannedPath)) {
    banned = readFileSync(bannedPath, 'utf8')
      .split('\n').map((l) => l.trim()).filter((l) => l && !l.startsWith('#'));
    text += `\n\n## Términos prohibidos\n\nNinguno de estos puede aparecer en la prosa ` +
      `(invariante 9). Usarlos es una incidencia \`blocker\` de tipo \`banned-term\`.\n\n` +
      banned.map((t) => `- ${t}`).join('\n');
  }
  return { text, banned };
}
