// Commits, archivado del rollback y lectura del historial.
//
// El commit por capítulo lo ejecuta el orquestador, no continuity-keeper (spec §16.3):
// es una operación mecánica, y darle a un agente la capacidad de ejecutar git para
// cumplir una caja del diagrama al pie de la letra sería ampliarle los permisos.

import { execFileSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';

function git(args, root) {
  return execFileSync('git', args, { cwd: root, encoding: 'utf8' }).trim();
}

export function stageAndCommit({ root, paths, subject, body }) {
  for (const p of paths) {
    try {
      git(['add', '--', p], root);
    } catch {
      // Una ruta que no existe (p. ej. notas de investigación que no se generaron)
      // no es un error: el capítulo simplemente no la produjo.
    }
  }
  const staged = git(['diff', '--cached', '--name-only'], root);
  if (!staged) return null;

  const message = body ? `${subject}\n\n${body}` : subject;
  git(['commit', '-m', message], root);
  return git(['rev-parse', '--short', 'HEAD'], root);
}

/** Último commit de capítulo aprobado, para reconstruir el estado (spec §10.1). */
export function lastChapterCommit(root, novel) {
  try {
    const line = git(
      ['log', '--grep', '^ch[0-9][0-9]:', '--extended-regexp', '-1',
        '--format=%h %s', '--', `novels/${novel}`],
      root,
    );
    if (!line) return null;
    const [hash, ...rest] = line.split(' ');
    const subject = rest.join(' ');
    const match = subject.match(/^ch(\d{2}):/);
    return { hash, subject, chapter: match ? Number(match[1]) : null };
  } catch {
    return null;
  }
}

/**
 * Rollback a K: archiva los capítulos K+1..N en vez de borrarlos (spec §11).
 * Git ya los conserva, pero quien hace rollback suele querer reusar un párrafo; y
 * sacarlos de chapters/ impide por construcción que LOAD o el compiler los relean.
 */
export function archiveChapters({ root, novel, fromChapter, toChapter, stamp }) {
  const atticDir = `novels/${novel}/attic/${stamp}`;
  mkdirSync(join(root, atticDir), { recursive: true });

  const moved = [];
  for (let n = fromChapter; n <= toChapter; n += 1) {
    const nn = String(n).padStart(2, '0');
    for (const name of [`ch${nn}.md`, `ch${nn}.draft.md`]) {
      const from = `novels/${novel}/chapters/${name}`;
      try {
        git(['mv', from, `${atticDir}/${name}`], root);
        moved.push(name);
      } catch {
        // El capítulo no existe en el árbol de trabajo: nada que archivar.
      }
    }
  }
  return { atticDir, moved };
}

/** Devuelve la biblia al estado del commit indicado. */
export function restoreBible({ root, novel, commitHash }) {
  git(['checkout', commitHash, '--', `novels/${novel}/bible`], root);
}

export function isRepo(root) {
  try {
    git(['rev-parse', '--is-inside-work-tree'], root);
    return true;
  } catch {
    return false;
  }
}
