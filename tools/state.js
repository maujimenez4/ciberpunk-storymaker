// run-state.json y el registro de llamadas.
//
// run-state.json es un índice, no la verdad (spec §10.1). La verdad es el historial de
// git: un commit por capítulo aprobado. Si discrepan, gana el historial.

import { readFileSync, writeFileSync, existsSync, mkdirSync, appendFileSync } from 'node:fs';
import { join, dirname } from 'node:path';

export function novelDir(root, novel) {
  return join(root, 'novels', novel);
}

export function statePath(root, novel) {
  return join(novelDir(root, novel), 'run-state.json');
}

export function logPath(root, novel) {
  return join(novelDir(root, novel), 'run-log.jsonl');
}

export function emptyState(cfg) {
  return {
    state: 'storymaker/run-state@1',
    novel: cfg.run.novel,
    profile: cfg.profileName,
    phase: 'setup',
    node: 'START',
    chapter: 1,
    act: 1,
    counters: { researchRounds: 0, rewrites: 0, humanRevisions: 0 },
    lastApprovedChapter: 0,
    lastApprovedCommit: null,
    flagged: [],
    usage: { calls: 0, inputTokens: 0, outputTokens: 0, searches: 0, estimatedUsd: 0 },
    updatedAt: new Date().toISOString(),
  };
}

export function readState(root, novel) {
  const path = statePath(root, novel);
  if (!existsSync(path)) return null;
  try {
    return JSON.parse(readFileSync(path, 'utf8'));
  } catch {
    // Estado corrupto: no es fatal. Se reconstruye desde el historial (spec §10.2).
    return null;
  }
}

export function writeState(root, novel, state) {
  state.updatedAt = new Date().toISOString();
  const path = statePath(root, novel);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, `${JSON.stringify(state, null, 2)}\n`, 'utf8');
  return state;
}

/**
 * Una línea por llamada: el sobre de handoff reducido a lo auditable.
 * No guarda prosa — solo rutas, contadores y uso. Es lo que hace comprobable el
 * criterio de aceptación 1: en seco, inputTokens es 0 en todas las líneas.
 */
export function appendLog(root, novel, entry) {
  const path = logPath(root, novel);
  mkdirSync(dirname(path), { recursive: true });
  appendFileSync(path, `${JSON.stringify(entry)}\n`, 'utf8');
}

/** Escritura de artefacto con control de propiedad de ruta (invariante 2). */
export function writeArtifact({ root, novel, relativePath, content, agent, canWrite }) {
  if (!canWrite(agent, relativePath)) {
    throw new Error(
      `${agent.id} intentó escribir en "${relativePath}", que no está en sus rutas declaradas ` +
      `(${agent.writes.join(', ') || 'ninguna'}). Escritura rechazada.`,
    );
  }
  const full = join(novelDir(root, novel), relativePath);
  mkdirSync(dirname(full), { recursive: true });
  writeFileSync(full, content.endsWith('\n') ? content : `${content}\n`, 'utf8');
  return full;
}

export function readIfExists(path) {
  return existsSync(path) ? readFileSync(path, 'utf8') : null;
}

export function countWords(text) {
  return (text.match(/\S+/g) ?? []).length;
}
