#!/usr/bin/env node
// PostToolUse sobre Task · telemetría a Langfuse.
//
// No es una guarda: no deniega nada y no puede romper una corrida. Es el sustituto
// fiable de `run-log.jsonl`, que el orquestador escribe a mano y por eso se desalinea
// —en la corrida de neon-smoke perdió el 10,5 % de los tokens—. Este hook corre fuera
// del modelo, después de cada subagente, así que no depende de que nadie se acuerde.
//
// Agrupa en una traza por fase: una para el setup y una por capítulo. Cada llamada a
// subagente es una generación dentro de su traza, así que el dashboard enseña el coste
// por capítulo y por rol sin tener que sumar nada.
//
// Credenciales, por orden: LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY, o la cabecera
// Authorization que ya tiene configurada el servidor MCP de Langfuse en ~/.claude.json.
// El hook nunca imprime la credencial, ni siquiera en el log de errores.
//
// Comprobación en seco, sin enviar nada:
//   echo '{"tool_name":"Task","tool_input":{"subagent_type":"scene-writer"},
//          "tool_response":{"usage":{"subagent_tokens":25562}},"cwd":"<repo>"}' \
//     | node .claude/hooks/trace-langfuse.mjs --selftest

import { readFileSync, existsSync, readdirSync, appendFileSync } from 'node:fs';
import { createHash, randomUUID } from 'node:crypto';
import { homedir } from 'node:os';
import { join } from 'node:path';

const SELFTEST = process.argv.includes('--selftest');
const TIMEOUT_MS = 5000;

/** Un hook de telemetría que rompe la corrida es peor que no tener telemetría. */
const done = () => { process.stdout.write('{}'); process.exit(0); };

function findNovelDir(cwd) {
  const dir = `${String(cwd ?? '').replace(/\\/g, '/')}/novels`;
  if (!existsSync(dir)) return null;
  const slugs = readdirSync(dir, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => `${dir}/${d.name}`)
    .filter((p) => existsSync(`${p}/run-state.json`));
  return slugs.length === 1 ? slugs[0] : null;
}

/**
 * El sobre de Task no tiene una forma documentada estable, así que en vez de asumir una
 * ruta concreta se recogen todos los números cuya clave hable de tokens. Si el formato
 * cambia, el hook sigue registrando algo en lugar de callarse.
 */
function collectTokenFields(value, depth = 0, out = {}) {
  if (!value || typeof value !== 'object' || depth > 6) return out;
  for (const [key, inner] of Object.entries(value)) {
    if (typeof inner === 'number' && /token/i.test(key)) out[key] = inner;
    else if (inner && typeof inner === 'object') collectTokenFields(inner, depth + 1, out);
  }
  return out;
}

/** Modelo declarado en el frontmatter del subagente, para que Langfuse pueda imputar coste. */
function modelOf(repoRoot, agentType) {
  const path = `${repoRoot}/.claude/agents/${agentType}.md`;
  if (!agentType || !existsSync(path)) return null;
  const match = readFileSync(path, 'utf8').match(/^model:\s*(\S+)/m);
  return match ? match[1] : null;
}

/** Credenciales. Devuelve la cabecera ya montada, nunca sus partes. */
function resolveAuth() {
  const { LANGFUSE_PUBLIC_KEY: pk, LANGFUSE_SECRET_KEY: sk } = process.env;
  if (pk && sk) {
    return { header: `Basic ${Buffer.from(`${pk}:${sk}`).toString('base64')}`, from: 'env' };
  }
  try {
    const cfg = JSON.parse(readFileSync(join(homedir(), '.claude.json'), 'utf8'));
    for (const project of Object.values(cfg.projects ?? {})) {
      for (const [name, server] of Object.entries(project.mcpServers ?? {})) {
        const header = server?.headers?.Authorization;
        if (/langfuse/i.test(name) && header) return { header, from: 'mcp' };
      }
    }
  } catch { /* sin configuración legible no hay credencial */ }
  return null;
}

function host() {
  return (process.env.LANGFUSE_HOST ?? 'https://us.cloud.langfuse.com').replace(/\/$/, '');
}

/** Traza estable por fase: una para el setup, una por capítulo. Sin estado extra. */
function traceIdFor(runId, phase, chapter) {
  const key = phase === 'chapter-loop' ? `ch${String(chapter).padStart(2, '0')}` : phase;
  return createHash('sha256').update(`${runId}:${key}`).digest('hex').slice(0, 32);
}

let input = '';
process.stdin.on('data', (chunk) => { input += chunk; });
process.stdin.on('end', async () => {
  let hook;
  try {
    hook = JSON.parse(input);
  } catch {
    done();
  }

  if (hook.tool_name !== 'Task') done();

  const repoRoot = String(hook.cwd ?? process.cwd()).replace(/\\/g, '/');
  const novelDir = findNovelDir(repoRoot);
  if (!novelDir) done(); // Sin corrida identificable no hay nada que atribuir.

  let state;
  try {
    state = JSON.parse(readFileSync(`${novelDir}/run-state.json`, 'utf8'));
  } catch {
    done();
  }

  // En seco no se llama a ningún modelo, así que no hay gasto que trazar.
  if (state.dryRun === true) done();

  const agentType = hook.tool_input?.subagent_type ?? 'unknown';
  const tokens = collectTokenFields(hook.tool_response);
  const total = tokens.subagent_tokens ?? tokens.totalTokens ?? tokens.total_tokens
    ?? Object.values(tokens).reduce((a, b) => a + b, 0);

  const runId = state.runId ?? `${state.novel}:${state.profile}`;
  const phase = state.phase ?? 'setup';
  const chapter = state.chapter ?? 0;
  const label = phase === 'chapter-loop' ? `ch${String(chapter).padStart(2, '0')}` : phase;
  const now = new Date().toISOString();

  // `usageDetails` es el campo actual; si tu instancia espera el antiguo `usage`,
  // ponle LANGFUSE_USAGE_FIELD=usage y no hay que tocar el hook.
  const usageField = process.env.LANGFUSE_USAGE_FIELD ?? 'usageDetails';

  const batch = [
    {
      id: randomUUID(),
      type: 'trace-create',
      timestamp: now,
      body: {
        id: traceIdFor(runId, phase, chapter),
        name: `${state.novel} ${label}`,
        sessionId: runId,
        tags: ['storymaker', state.profile, phase].filter(Boolean),
        metadata: { novel: state.novel, profile: state.profile, phase, chapter },
      },
    },
    {
      id: randomUUID(),
      type: 'generation-create',
      timestamp: now,
      body: {
        id: randomUUID(),
        traceId: traceIdFor(runId, phase, chapter),
        name: agentType,
        model: modelOf(repoRoot, agentType),
        startTime: now,
        endTime: now,
        [usageField]: { total },
        metadata: {
          node: state.node,
          chapter,
          attempt: state.attempt ?? null,
          counters: state.counters,
          // El sobre solo expone el total, no el reparto entrada/salida. Se guarda en
          // crudo para que se vea qué llegó de verdad si el formato cambia.
          rawTokenFields: tokens,
        },
      },
    },
  ];

  if (SELFTEST) {
    const auth = resolveAuth();
    process.stdout.write(JSON.stringify({
      would_post_to: `${host()}/api/public/ingestion`,
      credential: auth ? `presente (origen: ${auth.from})` : 'NO ENCONTRADA',
      usage_field: usageField,
      batch,
    }, null, 2) + '\n');
    process.exit(0);
  }

  const auth = resolveAuth();
  if (!auth) {
    appendFileSync(`${novelDir}/.langfuse-errors.log`,
      `${now} sin credencial: define LANGFUSE_PUBLIC_KEY y LANGFUSE_SECRET_KEY, o configura el MCP de Langfuse\n`);
    done();
  }

  try {
    const response = await fetch(`${host()}/api/public/ingestion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: auth.header },
      body: JSON.stringify({ batch }),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    if (!response.ok) {
      const detail = (await response.text()).slice(0, 400);
      appendFileSync(`${novelDir}/.langfuse-errors.log`,
        `${now} ${agentType} ${label} HTTP ${response.status}: ${detail}\n`);
    }
  } catch (error) {
    // Langfuse caído, sin red o timeout: se anota y la corrida sigue. Nunca al revés.
    appendFileSync(`${novelDir}/.langfuse-errors.log`,
      `${now} ${agentType} ${label} fallo de red: ${error.message}\n`);
  }

  done();
});
