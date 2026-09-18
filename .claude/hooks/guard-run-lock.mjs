#!/usr/bin/env node
// PreToolUse sobre Write/Edit · una sola corrida por novela.
//
// Dos orquestadores sobre el mismo slug se destruyen en silencio: comparten biblia,
// capítulos y un único `run-state.json`, así que cada uno lee el estado que el otro
// acaba de escribir. Pasó de verdad en `within-tolerance` —dos `setup: bible seed`,
// capítulos de dos genealogías mezclados, etiquetas de nodo descolocadas— y no lo
// detectó ningún mecanismo: lo vio un humano leyendo los commits.
//
// El panel ya se niega a lanzar una segunda corrida, pero eso solo cubre lo que lanza
// el panel. Una sesión de Claude Code escribiendo `/novela <perfil>` a mano no pasa por
// ahí. Esta guarda cierra el hueco donde de verdad duele: la escritura en disco.
//
// El dueño del lock es una **sesión**, no un proceso, porque el orquestador y sus nueve
// subagentes son la misma sesión y tienen que poder escribir todos.
//
// Comprobación en seco, sin tocar nada:
//   echo '{"tool_name":"Write","session_id":"s1","cwd":"<repo>",
//          "tool_input":{"file_path":"<repo>/novels/x/chapters/ch01.md"}}' \
//     | node .claude/hooks/guard-run-lock.mjs --selftest

import { readFileSync, writeFileSync, existsSync, appendFileSync } from 'node:fs';
import { hostname } from 'node:os';
import { basename } from 'node:path';

const SELFTEST = process.argv.includes('--selftest');

/**
 * Una corrida callada no está muerta, pero una que lleva diez minutos sin escribir una
 * línea sí lo está casi siempre: el bucle toca disco en cada nodo. Pasado ese plazo el
 * lock se puede reclamar, que es lo que evita que una corrida abortada deje la novela
 * bloqueada para siempre.
 */
const STALE_MS = 10 * 60 * 1000;

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

const readJson = (path) => {
  try { return JSON.parse(readFileSync(path, 'utf8')); } catch { return null; }
};

/** ¿Sigue vivo ese PID? `kill(pid, 0)` no envía señal: solo pregunta. */
function alivePid(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return error.code === 'EPERM'; // Existe, pero es de otro usuario.
  }
}

/**
 * Un lock sigue vigente si su proceso vive —lo escribió el panel— o si alguien lo ha
 * tocado hace poco —lo lleva una sesión, que no tiene PID que consultar desde aquí.
 */
function live(lock) {
  if (!lock) return false;
  if (alivePid(lock.pid)) return true;
  const touched = Date.parse(lock.touchedAt ?? lock.startedAt ?? 0);
  return Number.isFinite(touched) && Date.now() - touched < STALE_MS;
}

/** A qué novela pertenece la ruta que se va a escribir, o null si no es de ninguna. */
function slugOf(cwd, filePath) {
  if (!filePath) return null;
  const path = String(filePath).replace(/\\/g, '/');
  const root = String(cwd ?? '').replace(/\\/g, '/').replace(/\/$/, '');
  // Se acepta tanto la ruta absoluta dentro del repo como la relativa del encargo.
  const rel = root && path.startsWith(`${root}/`) ? path.slice(root.length + 1) : path;
  const match = rel.match(/(?:^|\/)novels\/([^/]+)\//);
  return match ? match[1] : null;
}

/** Rastro de decisiones. Es lo que permite comprobar que la guarda hace lo que dice. */
function note(dir, line) {
  if (SELFTEST) return;
  try {
    appendFileSync(`${dir}/.run-lock.log`, `${new Date().toISOString()} ${line}\n`);
  } catch { /* si no se puede escribir el rastro, la decisión sigue siendo válida */ }
}

let input = '';
process.stdin.on('data', (chunk) => { input += chunk; });
process.stdin.on('end', () => {
  let hook;
  try {
    hook = JSON.parse(input);
  } catch {
    allow(); // Un sobre ilegible no es prueba de nada.
  }

  // Válvula de escape. Una guarda que se equivoca no debe costar una tarde de trabajo:
  // se sale con una variable de entorno y sin editar código.
  if (process.env.STORYMAKER_IGNORE_RUN_LOCK === '1') allow();

  if (!['Write', 'Edit', 'NotebookEdit'].includes(hook.tool_name)) allow();

  const cwd = String(hook.cwd ?? process.cwd());
  const target = hook.tool_input?.file_path ?? hook.tool_input?.notebook_path;
  const slug = slugOf(cwd, target);
  if (!slug) allow(); // Fuera de `novels/<slug>/` no hay nada que proteger aquí.

  const dir = `${cwd.replace(/\\/g, '/')}/novels/${slug}`;
  if (!existsSync(dir)) allow();

  /**
   * Quién escribe.
   *
   * La sesión, no el proceso: el orquestador y sus nueve subagentes comparten sesión y
   * los diez tienen que poder escribir. `transcript_path` es el respaldo por si algún
   * día el sobre no trae `session_id`; sin ninguno de los dos no se puede razonar sobre
   * quién es quién, y entonces esta guarda se aparta en vez de adivinar.
   */
  const me = hook.session_id
    ?? (hook.transcript_path ? basename(String(hook.transcript_path)).replace(/\.jsonl$/, '') : null);
  if (!me) allow();

  const path = `${dir}/run.lock`;
  const lock = readJson(path);
  const stamp = new Date().toISOString();

  const take = (previous, why) => {
    writeFileSync(path, JSON.stringify({
      ...(previous ?? {}),
      lock: 'storymaker/run-lock@1',
      novel: slug,
      sessionId: me,
      startedAt: previous?.startedAt ?? stamp,
      touchedAt: stamp,
      host: hostname(),
    }, null, 2) + '\n');
    note(dir, `${why} sesión=${me.slice(0, 8)}`);
    allow();
  };

  if (!lock) take(null, 'lock creado');

  // Nuestro. El caso normal, una vez por cada escritura de la corrida.
  if (lock.sessionId === me) take(lock, 'latido');

  // El panel escribe el lock antes de lanzar `claude`, así que llega sin sesión: el hijo
  // lo adopta en su primera escritura. Hay una ventana de un par de segundos en la que
  // otra sesión podría adoptarlo primero; entonces el hijo legítimo se encuentra la
  // puerta cerrada y falla en voz alta, que es mejor que dos corridas escribiendo.
  if (!lock.sessionId) take(lock, 'lock del panel adoptado');

  // Huérfano: la corrida que lo dejó ya no existe.
  if (!live(lock)) {
    note(dir, `lock caducado de sesión=${String(lock.sessionId).slice(0, 8)} reclamado`);
    take({ ...lock, pid: undefined, childPid: undefined }, 'lock reclamado');
  }

  // Queda un único caso, y es el que esta guarda existe para impedir.
  note(dir, `DENEGADO a sesión=${me.slice(0, 8)}: lo tiene sesión=${String(lock.sessionId).slice(0, 8)}`);
  const desde = new Date(lock.startedAt ?? stamp).toTimeString().slice(0, 5);
  deny(
    `Ya hay otra corrida escribiendo en "${slug}" (sesión ${String(lock.sessionId).slice(0, 8)}, `
    + `desde las ${desde}). Dos orquestadores sobre la misma novela comparten biblia, `
    + `capítulos y run-state.json, y se sobrescriben en silencio: así se perdió la corrida `
    + `de within-tolerance.\n\n`
    + `Para en vez de insistir. Di al humano que hay dos corridas sobre "${slug}" y que hay `
    + `que parar una. El lock está en novels/${slug}/run.lock y caduca solo a los `
    + `${STALE_MS / 60000} minutos sin actividad.\n\n`
    + `Si sabes con certeza que la otra corrida ya no existe, se puede saltar esta guarda `
    + `con STORYMAKER_IGNORE_RUN_LOCK=1, o borrar el fichero de lock.`,
  );
});
