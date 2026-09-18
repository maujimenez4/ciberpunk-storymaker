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

import { readFileSync, existsSync, readdirSync, appendFileSync, statSync } from 'node:fs';
import { createHash, randomUUID } from 'node:crypto';
import { homedir } from 'node:os';
import { join } from 'node:path';

const SELFTEST = process.argv.includes('--selftest');
const PING = process.argv.includes('--ping');
const TIMEOUT_MS = 5000;

/** Un hook de telemetría que rompe la corrida es peor que no tener telemetría. */
const done = () => { process.stdout.write('{}'); process.exit(0); };

/**
 * A qué novela pertenece esta llamada.
 *
 * La versión anterior devolvía null en cuanto había más de una novela con estado, y un
 * null aquí apaga el hook **en silencio**: en la segunda corrida no se trazó nada y no
 * hubo ni un error que lo dijera. Con dos novelas en el repo eso pasa de caso raro a
 * caso normal.
 *
 * El orden va de la señal más fiable a la más débil:
 *   1. El encargo al subagente lleva las rutas de su novela. Es indiscutible.
 *   2. Una sola novela con estado: es esa.
 *   3. Varias y ningún indicio: la de estado escrito más recientemente es la que corre.
 */
function findNovelDir(cwd, hint) {
  const base = `${String(cwd ?? '').replace(/\\/g, '/')}/novels`;
  if (!existsSync(base)) return null;
  const slugs = readdirSync(base, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name)
    .filter((n) => existsSync(`${base}/${n}/run-state.json`));
  if (!slugs.length) return null;

  const named = String(hint ?? '').match(/novels[/\\]([^/\\]+)[/\\]/);
  if (named && slugs.includes(named[1])) return `${base}/${named[1]}`;
  if (slugs.length === 1) return `${base}/${slugs[0]}`;

  return `${base}/${slugs
    .map((n) => ({ n, at: statSync(`${base}/${n}/run-state.json`).mtimeMs }))
    .sort((a, b) => b.at - a.at)[0].n}`;
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

/**
 * `--ping`: manda UNA traza mínima y dice qué contestó Langfuse. Existe porque hasta que
 * algo llega de verdad no se sabe si la credencial del MCP sirve también para la API de
 * ingesta —puede ser un bearer de OAuth y no el Basic de clave pública/secreta— ni si el
 * nombre del campo de uso es el que espera esta instancia. Dos segundos contra una
 * corrida entera para descubrir lo mismo.
 *
 *   node .claude/hooks/trace-langfuse.mjs --ping
 */
async function ping() {
  const auth = resolveAuth();
  if (!auth) {
    console.error('Sin credencial. Define LANGFUSE_PUBLIC_KEY y LANGFUSE_SECRET_KEY, o configura el MCP de Langfuse.');
    process.exit(1);
  }
  const now = new Date().toISOString();
  const traceId = createHash('sha256').update(`storymaker-ping:${now}`).digest('hex').slice(0, 32);
  const usageField = process.env.LANGFUSE_USAGE_FIELD ?? 'usageDetails';
  const batch = [
    { id: randomUUID(), type: 'trace-create', timestamp: now,
      body: { id: traceId, name: 'storymaker ping', tags: ['storymaker', 'ping'] } },
    { id: randomUUID(), type: 'generation-create', timestamp: now,
      body: { id: randomUUID(), traceId, name: 'ping', model: 'claude-sonnet-5',
              startTime: now, endTime: now, [usageField]: { total: 1 } } },
  ];

  console.log(`Destino:      ${host()}/api/public/ingestion`);
  console.log(`Credencial:   presente (origen: ${auth.from}), esquema ${auth.header.split(' ')[0]}`);
  console.log(`Campo de uso: ${usageField}`);
  try {
    const response = await fetch(`${host()}/api/public/ingestion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: auth.header },
      body: JSON.stringify({ batch }),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    const text = (await response.text()).slice(0, 600);
    console.log(`Respuesta:    HTTP ${response.status}`);
    console.log(text ? `Cuerpo:       ${text}` : '');
    if (response.ok) {
      console.log(`\nLlegó. Busca la traza "storymaker ping" en tu proyecto (id ${traceId}).`);
    } else if (response.status === 401 || response.status === 403) {
      console.log('\nLa credencial del MCP no vale para la API de ingesta. Saca un par de claves' +
        '\nde proyecto en Langfuse y expórtalas como LANGFUSE_PUBLIC_KEY y LANGFUSE_SECRET_KEY.');
    } else if (response.status === 207 || response.status === 400) {
      console.log(`\nLa credencial vale y el formato no. Mira qué evento rechaza el cuerpo de arriba;` +
        `\nsi se queja del uso, prueba con LANGFUSE_USAGE_FIELD=usage.`);
    }
    process.exit(response.ok ? 0 : 1);
  } catch (error) {
    console.error(`Fallo de red: ${error.message}`);
    process.exit(1);
  }
}

if (PING) { await ping(); }

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
  const novelDir = findNovelDir(repoRoot, hook.tool_input?.prompt);
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

  // Registro local, siempre y antes de la red: es la fuente del panel de resumen y no
  // puede depender de que Langfuse conteste. Una línea por llamada de subagente, que es
  // justo lo que `run-log.jsonl` no consigue por escribirlo el orquestador a mano.
  if (!SELFTEST) {
    try {
      appendFileSync(`${novelDir}/agent-calls.jsonl`, JSON.stringify({
        ts: now, agent: agentType, model: modelOf(repoRoot, agentType),
        node: state.node, phase, chapter, attempt: state.attempt ?? null,
        tokens: total, rawTokenFields: tokens,
      }) + '\n');
    } catch { /* si no se puede escribir, la corrida sigue igual */ }
  }

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

  // Aquí NO se llama a `done()`: un process.exit() con el handle del fetch todavía
  // cerrándose hace que libuv aborte en Windows con "Assertion failed: !(handle->flags
  // & UV_HANDLE_CLOSING)". Se contesta al harness y se deja que el proceso termine solo
  // cuando el socket se cierre. El hook ya no tiene nada que hacer.
  process.stdout.write('{}');
});
