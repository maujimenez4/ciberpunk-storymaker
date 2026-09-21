// Envío de los resultados de `npm run evals` a Langfuse: una traza por ejecución y un
// score por resultado.
//
// La traza la monta OTLP con los mismos constructores que usa el hook de telemetría
// (.claude/hooks/otlp.mjs). Los scores NO van por OTLP —Langfuse v4 no los ingiere por
// ahí— sino por POST /api/public/scores, que es un endpoint aparte con su propia forma.
//
// ── Sobre `metadata` en un score ──────────────────────────────────────────────────
// La guía de migración lista traceId, observationId, name, value, dataType y comment.
// **No lista metadata.** Aquí se manda igualmente, porque si el endpoint la rechaza lo
// dirá con un 4xx y eso se sabe en una llamada; pero novela, capítulo y target van
// TAMBIÉN en el `comment`, que sí está en el contrato. Si la metadata no cuaja, no se
// pierde la coordenada: se pierde la posibilidad de filtrar por ella.
//
// ── Un nombre, un tipo ────────────────────────────────────────────────────────────
// Cada resultado produce **un score BOOLEAN** con el nombre del evaluator, donde 1 es
// "pasa" y 0 es "no pasa", siempre y para todos. Y, solo donde el número dice algo que el
// booleano no, **un segundo score NUMERIC con otro nombre**.
//
// La primera versión mandaba la medida bajo el nombre del evaluator, así que el mismo
// nombre salía NUMERIC en un evaluator y BOOLEAN en otro. Eso rompe cualquier agregación:
// un nombre de score es una serie, y una serie no puede cambiar de tipo. De paso se
// arregla la dirección, que antes tampoco era uniforme —en `canon-resoluble` 1 era bueno y
// en `sin-terminos-prohibidos` 1 era malo—: ahora 1 es bueno en todos.

import { createHash } from 'node:crypto';
import { readFileSync, existsSync, mkdirSync, writeFileSync, appendFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { traceIdOf, rootSpanIdOf, span, envelope, postSpans } from '../../.claude/hooks/otlp.mjs';

export const EVALS_VERSION = 'evals@1';

/**
 * Versión del **esquema de scores**: cómo se traduce un resultado a scores, no qué mide.
 *
 * Entra en el `evalRunId`, así que cambiarla da traza nueva. Tiene que ser así: con
 * `scores@1` un resultado daba un score con el nombre del evaluator y tipo variable, y con
 * `scores@2` da un veredicto BOOLEAN más, a veces, una medida NUMERIC aparte. Los mismos
 * números contados de otra forma no pueden convivir en una traza, porque una serie con dos
 * codificaciones distintas no se puede leer.
 */
export const SCORES_SCHEMA = 'scores@2';
const SCORES_PATH = '/api/public/scores';

/**
 * Credenciales.
 *
 * Duplica a propósito la lógica de `trace-langfuse.mjs`, donde `resolveAuth()` no está
 * exportada y el módulo, al importarse, se queda escuchando stdin. Es el segundo ayudante
 * que hace falta fuera de un hook —el primero fue `bannedTerms()`—; el arreglo de fondo es
 * sacarlos a un módulo compartido, y eso es tocar hooks. Mientras tanto, esto.
 */
export function resolveAuth(env = process.env) {
  const { LANGFUSE_PUBLIC_KEY: pk, LANGFUSE_SECRET_KEY: sk } = env;
  if (pk && sk) return { header: `Basic ${Buffer.from(`${pk}:${sk}`).toString('base64')}`, from: 'env' };
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

export const hostOf = (env = process.env) =>
  (env.LANGFUSE_HOST ?? 'https://us.cloud.langfuse.com').replace(/\/$/, '');

/**
 * Identidad de una ejecución de evals.
 *
 * Sale de lo que identifica la **medición**: la huella de los resultados y la versión de
 * los evaluators. Ni un reloj ni el commit.
 *
 * El reloj queda descartado por lo obvio: cada ejecución duplicaría los mismos 67 scores y
 * la idempotencia sería decorativa. El commit se descartó después, y por lo mismo: atarlo
 * al commit hace que tocar un README produzca traza nueva y reenvíe 67 scores idénticos.
 * Lo que interesa comparar es cuándo cambia una medida, no cuándo cambia el repo.
 *
 * Así, volver a correr los evals sin que nada cambie cae en la misma traza y no manda
 * nada; cambiar una novela, o la lógica de un evaluator, da traza nueva. El commit viaja
 * igualmente, como metadata de la raíz, para saber sobre qué se midió.
 */
export function evalRunIdOf({ evaluatorsSha, results, schema = SCORES_SCHEMA }) {
  const huella = results
    .map((r) => `${r.evaluator}|${r.novela}|${r.capitulo}|${r.target}|${r.pass}|${r.value}`)
    .sort()
    .join('\n');
  return createHash('sha256')
    .update(`${schema}\n${evaluatorsSha ?? 'sin-version'}\n${huella}`)
    .digest('hex').slice(0, 16);
}

/**
 * Desglose por nombre y tipo, y si algún nombre mezcla tipos.
 *
 * Lo segundo no debería poder pasar —`scoresOf` da BOOLEAN al nombre del evaluator y
 * NUMERIC a las medidas, que son nombres distintos— pero se comprueba sobre los scores
 * reales y no sobre el razonamiento, que es de donde salió el fallo de `scores@1`.
 */
export function desgloseDe(scores) {
  const cuenta = new Map();
  for (const s of scores) {
    const clave = `${s.name}\u0000${s.dataType}`;
    cuenta.set(clave, (cuenta.get(clave) ?? 0) + 1);
  }
  const filas = [...cuenta.entries()].map(([clave, n]) => {
    const [name, dataType] = clave.split('\u0000');
    return { name, dataType, n };
  }).sort((a, b) => a.name.localeCompare(b.name) || a.dataType.localeCompare(b.dataType));

  const tipos = new Map();
  for (const f of filas) tipos.set(f.name, [...(tipos.get(f.name) ?? []), f.dataType]);
  const mezclados = [...tipos.entries()].filter(([, t]) => t.length > 1)
    .map(([name, t]) => ({ name, tipos: t }));

  return { filas, mezclados, total: scores.length };
}

export const traceIdOfRun = (evalRunId) => traceIdOf(evalRunId, 'evals');

/**
 * Evaluators cuyo número informa de algo que el booleano no dice, con el nombre del score
 * NUMERIC que lo lleva. Los que faltan no están por olvido:
 *
 *   - `sin-terminos-prohibidos` y `canon-resoluble` tienen valor 0/1, que es el booleano
 *     otra vez. Un segundo score sería el mismo dato con otro nombre.
 *   - `issues-schema-valido` sí entra, aunque no estaba en tus ejemplos: distingue una
 *     incidencia con un campo mal de otra con los cuatro, y eso es información de verdad.
 *     Si te sobra, se quita borrando una línea de aquí.
 */
export const MEDIDAS = {
  'voice-editor-no-anade': 'voice-editor-delta-palabras',
  'longitud-en-rango': 'longitud-desviacion',
  'issues-schema-valido': 'issues-violaciones',
};

/**
 * Clave estable de un score.
 *
 * Lleva el nombre del score y su `dataType` además de las coordenadas, porque de un mismo
 * resultado salen ahora dos scores y sin eso compartirían id. Y lleva el discriminador
 * —origen y cita, o el id de la incidencia— porque un capítulo puede tener varias citas de
 * canon, y sin él todas colisionarían en uno.
 */
function claveDe(r, nombre, dataType) {
  return [
    r.evaluator, r.target, r.novela, r.capitulo ?? '-', nombre, dataType,
    r.origen ?? '-', r.cita ?? r.issueId ?? '-',
  ].join('|');
}

/**
 * Los scores de una tanda de resultados.
 *
 * Los `pass === null` no se mandan: un score necesita un número, y "no se pudo juzgar" no
 * lo es. Se devuelven aparte para poder decir cuántos quedaron fuera en vez de que
 * desaparezcan sin más.
 */
export function scoresOf({ evalRunId, results }) {
  const traceId = traceIdOfRun(evalRunId);
  const vistos = new Map();
  const scores = [];
  const omitidos = [];

  const idDe = (r, nombre, dataType) => {
    // Un mismo (evaluator, novela, capítulo, target) puede repetirse —varias citas en el
    // mismo capítulo—, así que la clave lleva un ordinal para no colisionar.
    const base = claveDe(r, nombre, dataType);
    const n = (vistos.get(base) ?? 0) + 1;
    vistos.set(base, n);
    const clave = n > 1 ? `${base}#${n}` : base;
    return createHash('sha256').update(`${traceId}:${clave}`).digest('hex').slice(0, 32);
  };

  for (const r of results) {
    if (r.pass === null || r.value === null || r.value === undefined) {
      omitidos.push(r);
      continue;
    }

    const donde = [r.novela, r.capitulo ? `ch${String(r.capitulo).padStart(2, '0')}` : null]
      .filter(Boolean).join(' ');
    // Las coordenadas van también aquí porque `comment` sí está en el contrato del
    // endpoint y `metadata` puede no estarlo.
    const comment = `${r.pass ? '✓' : '✗'} ${donde} · target=${r.target}${r.contaminated ? ' · corrida contaminada' : ''} · ${r.detalle}`;
    const metadata = {
      novela: r.novela,
      capitulo: r.capitulo,
      target: r.target,
      pass: r.pass,
      contaminated: Boolean(r.contaminated),
      ...(r.origen ? { origen: r.origen } : {}),
    };

    // El veredicto, siempre y con el nombre del evaluator. 1 es pasa, en todos.
    scores.push({
      id: idDe(r, r.evaluator, 'BOOLEAN'),
      traceId,
      name: r.evaluator,
      value: r.pass ? 1 : 0,
      dataType: 'BOOLEAN',
      comment,
      metadata,
    });

    // La medida, solo donde dice algo que el veredicto no.
    const medida = MEDIDAS[r.evaluator];
    if (medida) {
      scores.push({
        id: idDe(r, medida, 'NUMERIC'),
        traceId,
        name: medida,
        value: Number(r.value),
        dataType: 'NUMERIC',
        comment,
        metadata,
      });
    }
  }

  return { traceId, scores, omitidos };
}

/** El span raíz de la ejecución. Uno solo: los scores cuelgan de la traza, no de spans. */
export function rootSpanOf({ evalRunId, novels, summary, evaluatorsSha, commit, startMs, endMs }) {
  const traceId = traceIdOfRun(evalRunId);
  const contaminadas = novels.filter((n) => n.contaminated).map((n) => n.slug);

  return span({
    traceId,
    spanId: rootSpanIdOf(traceId),
    name: 'storymaker evals',
    startMs,
    endMs,
    attrs: {
      'langfuse.trace.name': 'storymaker evals',
      'langfuse.session.id': evalRunId,
      'langfuse.trace.tags': JSON.stringify(['storymaker', 'evals']),
      'langfuse.trace.metadata.evaluators_version': EVALS_VERSION,
      'langfuse.trace.metadata.evaluators_sha': evaluatorsSha ?? null,
      'langfuse.trace.metadata.commit': commit ?? null,
      'langfuse.trace.metadata.novelas': JSON.stringify(novels.map((n) => n.slug)),
      'langfuse.trace.metadata.contaminadas': JSON.stringify(contaminadas),
      'langfuse.trace.metadata.hay_contaminadas': contaminadas.length > 0,
      'langfuse.observation.type': 'span',
      'langfuse.observation.input': JSON.stringify({
        novelas: novels.map((n) => ({ slug: n.slug, perfil: n.perfil, contaminated: n.contaminated })),
        evaluators_version: EVALS_VERSION,
      }),
      'langfuse.observation.output': JSON.stringify(summary ?? []),
    },
  });
}

// ── Marcas de envío ──────────────────────────────────────────────────────────────
// Langfuse v4 no deduplica de forma fiable. El id determinista del score es la primera
// línea de defensa; esto es la segunda, y la única que no depende de que el otro lado
// haga algo. Un fallo NO se reintenta solo: tras un timeout no se sabe si entró.

const sentDir = (repoRoot) => `${repoRoot}/.trace/sent`;
export const sentPath = (repoRoot, id) => `${sentDir(repoRoot)}/${id}`;
export const yaEnviado = (repoRoot, id) => existsSync(sentPath(repoRoot, id));

export function marcarEnviado(repoRoot, id) {
  try {
    mkdirSync(sentDir(repoRoot), { recursive: true });
    writeFileSync(sentPath(repoRoot, id), new Date().toISOString());
  } catch { /* lo peor que pasa es un duplicado; no se rompe nada */ }
}

export function anotarError(repoRoot, linea) {
  try { appendFileSync(`${repoRoot}/.langfuse-errors.log`, `${new Date().toISOString()} evals ${linea}\n`); } catch { /* nada */ }
}

// ── Envío ────────────────────────────────────────────────────────────────────────

export async function postScore({ host, authHeader, score, timeoutMs = 5000 }) {
  try {
    const response = await fetch(`${host}${SCORES_PATH}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: authHeader },
      body: JSON.stringify(score),
      signal: AbortSignal.timeout(timeoutMs),
    });
    return {
      ok: response.ok,
      status: response.status,
      body: (await response.text()).slice(0, 400),
      retryAfterHeader: response.headers.get('retry-after'),
    };
  } catch (error) {
    return { ok: false, status: 0, body: `fallo de red: ${error.message}` };
  }
}

/** Cuánto pide esperar un 429. El cuerpo lo dice; la cabecera es el respaldo. */
export function segundosDeEspera(respuesta, porDefecto = 60) {
  try {
    const n = JSON.parse(respuesta.body ?? '{}')?.details?.retryAfterSeconds;
    if (Number.isFinite(n) && n >= 0) return n;
  } catch { /* seguimos con la cabecera */ }
  const cabecera = Number(respuesta.retryAfterHeader);
  return Number.isFinite(cabecera) && cabecera >= 0 ? cabecera : porDefecto;
}

export async function enviarRaiz({ repoRoot, host, authHeader, root, timeoutMs = 5000 }) {
  if (yaEnviado(repoRoot, root.spanId)) return { ok: true, saltado: true, status: 0, body: 'ya enviada' };
  const r = await postSpans({ host, authHeader, spans: [root], timeoutMs });
  if (r.ok) marcarEnviado(repoRoot, root.spanId);
  else anotarError(repoRoot, `raíz ${root.spanId} HTTP ${r.status}: ${r.body}`);
  return { ...r, saltado: false };
}

/**
 * Manda los scores por debajo del límite del endpoint.
 *
 * El primer envío completo mandó los 91 seguidos y el servidor cortó en el trigésimo:
 * `{"code":"rate_limited","details":{"retryAfterSeconds":56,"limit":30}}`. Treinta por
 * minuto. Así que aquí hay dos frenos, y el segundo es el que de verdad garantiza el
 * límite:
 *
 *   - un espaciado fijo entre envíos (2,5 s → 24/min), que evita el 429 en el caso normal;
 *   - una ventana deslizante que no deja pasar más de `maxPorVentana` en `ventanaMs`,
 *     que lo garantiza aunque el espaciado se quede corto.
 *
 * Ante un 429 se espera lo que pida el servidor más un segundo y se reintenta **ese**
 * score, porque no llegó. Cualquier otro error no se reintenta: un 400 volvería a ser 400.
 *
 * El reloj y la espera se inyectan para poder probar todo esto sin que pase el tiempo.
 */
export async function enviarScores({
  repoRoot, host, authHeader, scores, timeoutMs = 5000, limite = Infinity,
  intervaloMs = 2500, ventanaMs = 60000, maxPorVentana = 29, maxEsperas = 3,
  ahora = () => Date.now(),
  esperar = (ms) => new Promise((r) => setTimeout(r, ms)),
  progreso = null,
}) {
  const salida = { enviados: 0, saltados: 0, fallidos: 0, detenido: false, motivo: null, detalles: [] };
  const pendientes = scores.slice(0, limite);
  const ventana = [];
  let ultimo = null;
  let esperasSeguidas = 0;

  /** Frena hasta que mandar otra sea seguro, y apunta el envío en la ventana. */
  async function ritmo() {
    if (ultimo !== null) {
      const falta = intervaloMs - (ahora() - ultimo);
      if (falta > 0) await esperar(falta);
    }
    for (;;) {
      const corte = ahora() - ventanaMs;
      while (ventana.length && ventana[0] <= corte) ventana.shift();
      if (ventana.length < maxPorVentana) break;
      await esperar(ventana[0] + ventanaMs - ahora() + 1);
    }
    const t = ahora();
    ventana.push(t);
    ultimo = t;
  }

  for (let i = 0; i < pendientes.length; i += 1) {
    const score = pendientes[i];
    if (yaEnviado(repoRoot, score.id)) {
      salida.saltados += 1;
      continue;
    }

    for (;;) {
      await ritmo();
      const r = await postScore({ host, authHeader, score, timeoutMs });

      if (r.ok) {
        marcarEnviado(repoRoot, score.id);   // marca SOLO tras 2xx
        salida.enviados += 1;
        esperasSeguidas = 0;
        salida.detalles.push({ id: score.id, name: score.name, ok: true, status: r.status });
        break;
      }

      if (r.status === 429) {
        if (esperasSeguidas >= maxEsperas) {
          salida.detenido = true;
          salida.motivo = `${maxEsperas} esperas seguidas sin pasar del límite; quedan ${pendientes.length - i} por mandar`;
          anotarError(repoRoot, `detenido por ritmo: ${salida.motivo}`);
          return salida;
        }
        esperasSeguidas += 1;
        const segundos = segundosDeEspera(r) + 1;
        progreso?.({ ...salida, restantes: pendientes.length - i, esperando: segundos, name: score.name });
        await esperar(segundos * 1000);
        continue;  // el mismo score: no llegó
      }

      // Cualquier otro error no se reintenta.
      salida.fallidos += 1;
      anotarError(repoRoot, `score ${score.name} ${score.id} HTTP ${r.status}: ${r.body}`);
      salida.detalles.push({ id: score.id, name: score.name, ok: false, status: r.status, body: r.body });
      break;
    }

    progreso?.({ ...salida, restantes: pendientes.length - i - 1, esperando: 0, name: score.name });
  }

  return salida;
}

export const envelopeDe = (root) => envelope([root]);
