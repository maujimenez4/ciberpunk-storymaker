#!/usr/bin/env node
// Lint de la estructura nativa. No corre el bucle: comprueba que el reparto de
// permisos declarado en .claude/ no contradice las invariantes 2 y 3, antes de que
// nadie lance una corrida.
//
// Los hooks imponen las invariantes en tiempo de ejecución. Esto las comprueba en
// tiempo de revisión, que es más barato: un permiso mal puesto se ve aquí en un
// segundo, y en una corrida se ve a mitad del capítulo cuatro.

import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const AGENTS_DIR = join(ROOT, '.claude', 'agents');
const SKILLS_DIR = join(ROOT, '.claude', 'skills');
const OWNERSHIP = join(ROOT, '.claude', 'hooks', 'ownership.json');

// Ninguna de estas debería estar en manos de un subagente narrativo.
const FORBIDDEN_TOOLS = ['Bash', 'Task', 'WebFetch'];
const WEB_TOOLS = ['WebSearch', 'WebFetch'];

const failures = [];
const notes = [];

function frontmatter(text, source) {
  if (!text.startsWith('---')) throw new Error(`${source}: falta el frontmatter`);
  const end = text.indexOf('\n---', 3);
  if (end === -1) throw new Error(`${source}: frontmatter sin cerrar`);
  const meta = {};
  for (const line of text.slice(3, end).split('\n')) {
    const t = line.trim();
    if (!t || t.startsWith('#')) continue;
    const sep = t.indexOf(':');
    if (sep === -1) continue;
    const key = t.slice(0, sep).trim();
    const raw = t.slice(sep + 1).trim();
    meta[key] = raw.startsWith('[')
      ? raw.slice(1, raw.lastIndexOf(']')).split(',').map((v) => v.trim()).filter(Boolean)
      : raw;
  }
  return meta;
}

if (!existsSync(AGENTS_DIR)) {
  console.error('✗ No existe .claude/agents/');
  process.exit(1);
}

const agents = new Map();
for (const file of readdirSync(AGENTS_DIR).filter((f) => f.endsWith('.md'))) {
  const source = `.claude/agents/${file}`;
  const meta = frontmatter(readFileSync(join(AGENTS_DIR, file), 'utf8'), source);
  if (!meta.name) { failures.push(`${source}: falta "name"`); continue; }
  if (!meta.description) failures.push(`${source}: falta "description" — sin ella el orquestador no sabe cuándo delegarle`);
  if (meta.name !== file.replace(/\.md$/, '')) {
    failures.push(`${source}: el "name" (${meta.name}) no coincide con el nombre del fichero`);
  }
  agents.set(meta.name, { ...meta, source, tools: meta.tools ?? [] });
}

// ── Invariante 3 ──────────────────────────────────────────────────────────────
const withWeb = [...agents.values()].filter((a) => a.tools.some((t) => WEB_TOOLS.includes(t)));
if (withWeb.length !== 1) {
  failures.push(`Invariante 3: ${withWeb.length} agentes con acceso web (${withWeb.map((a) => a.name).join(', ') || 'ninguno'}); debe ser exactamente uno`);
} else if (withWeb[0].name !== 'researcher') {
  failures.push(`Invariante 3: el acceso web lo tiene ${withWeb[0].name}, no researcher`);
}

// ── Herramientas de más ───────────────────────────────────────────────────────
for (const a of agents.values()) {
  const bad = a.tools.filter((t) => FORBIDDEN_TOOLS.includes(t));
  if (bad.length) failures.push(`${a.source}: herramientas que un subagente narrativo no debe tener: ${bad.join(', ')}`);
}

// ── Invariante 2, vía ownership.json ──────────────────────────────────────────
if (!existsSync(OWNERSHIP)) {
  failures.push('Falta .claude/hooks/ownership.json: sin él el hook no puede acotar escrituras');
} else {
  const owned = JSON.parse(readFileSync(OWNERSHIP, 'utf8'));
  const withBible = Object.entries(owned)
    .filter(([k]) => !k.startsWith('_'))
    .filter(([, paths]) => paths.some((p) => p.startsWith('bible/')));

  if (withBible.length !== 1) {
    failures.push(`Invariante 2: ${withBible.length} roles pueden escribir en bible/ (${withBible.map(([k]) => k).join(', ') || 'ninguno'}); debe ser exactamente uno`);
  } else if (withBible[0][0] !== 'continuity-keeper') {
    failures.push(`Invariante 2: la biblia la escribe ${withBible[0][0]}, no continuity-keeper`);
  }

  for (const name of agents.keys()) {
    if (!owned[name]) notes.push(`${name} no tiene rutas en ownership.json: no podrá escribir dentro de novels/`);
  }
  for (const key of Object.keys(owned)) {
    if (key.startsWith('_') || key === '__main__') continue;
    if (!agents.has(key)) failures.push(`ownership.json declara rutas para "${key}", que no es un agente de .claude/agents/`);
  }
}

// ── Skills ────────────────────────────────────────────────────────────────────
const skills = existsSync(SKILLS_DIR)
  ? new Set(readdirSync(SKILLS_DIR, { withFileTypes: true }).filter((d) => d.isDirectory()).map((d) => d.name))
  : new Set();
for (const a of agents.values()) {
  for (const s of a.skills ?? []) {
    if (!skills.has(s)) failures.push(`${a.source} declara la skill "${s}", que no existe en .claude/skills/`);
  }
}

// ── Informe ───────────────────────────────────────────────────────────────────
if (failures.length) {
  console.error('✗ Comprobación de invariantes fallida:');
  for (const f of failures) console.error(`  - ${f}`);
  process.exit(1);
}

console.log(`✓ Invariantes de permisos: ${agents.size} subagentes · ${skills.size} skills · acceso web solo researcher · escribe la biblia solo continuity-keeper`);
for (const n of notes) console.log(`  · ${n}`);
