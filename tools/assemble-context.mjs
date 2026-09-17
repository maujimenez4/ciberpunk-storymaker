#!/usr/bin/env node
// Ensambla el contexto de un nodo en UN fichero, para que el subagente haga una lectura
// en vez de ocho.
//
// Por qué existe: en la corrida de neon-smoke las 23 llamadas gastaron 181 usos de
// herramienta, casi ocho por llamada, y la mayoría eran `Read`. El orquestador pasaba
// ocho rutas y cada agente abría los ocho ficheros; cada apertura reenvía el contexto
// acumulado. Esto es la invariante 5 tomada en serio: el contexto **se ensambla** —aquí,
// una vez, por quien lleva el estado— en vez de delegar el ensamblado a cada rol, que lo
// hace peor y pagando.
//
// Y ensambla por nodo, no por capítulo: `commit` no necesita la ficha de personajes y
// `val-tv` no necesita la biblia. Cada rol recibe su recorte, no el montón entero.
//
// Uso:
//   node tools/assemble-context.mjs <slug> <nodo> <capítulo>
//   nodos: beat · write · val-ck · val-tv · commit
//
// Escribe novels/<slug>/notes/ch<NN>-ctx-<nodo>.md y devuelve la ruta y su tamaño.

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { loadConfig } from './config.js';

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const NODES = ['beat', 'write', 'val-ck', 'val-tv', 'commit'];

const [slug, node, chapterArg] = process.argv.slice(2);
if (!slug || !NODES.includes(node) || !chapterArg) {
  console.error(`uso: node tools/assemble-context.mjs <slug> <${NODES.join('|')}> <capítulo>`);
  process.exit(1);
}
const chapter = Number(chapterArg);
const NN = String(chapter).padStart(2, '0');
const novel = `${ROOT}/novels/${slug}`;

const read = (relative) => {
  const path = `${novel}/${relative}`;
  return existsSync(path) ? readFileSync(path, 'utf8').trim() : null;
};

/** Quita el front matter y el `# Título` de cabecera: en el ensamblado sobran. */
const body = (text) => text.replace(/^---[\s\S]*?\n---\n/, '').replace(/^#\s+.*\n/, '').trim();

/**
 * Extrae las secciones cuyo encabezado casa con `pattern`, desde el encabezado hasta el
 * siguiente del mismo nivel o superior. Así `outline.md` aporta solo el capítulo que toca
 * en vez de la escaleta entera, que es lo que los otros capítulos no tienen que ver.
 */
function sections(text, pattern) {
  if (!text) return null;
  const lines = text.split('\n');
  const out = [];
  let level = 0;
  let taking = false;
  for (const line of lines) {
    const heading = line.match(/^(#{1,6})\s+(.*)$/);
    if (heading) {
      const depth = heading[1].length;
      if (taking && depth <= level) taking = false;
      if (!taking && pattern.test(heading[2])) { taking = true; level = depth; }
    }
    if (taking) out.push(line);
  }
  return out.length ? out.join('\n').trim() : null;
}

/** Solo los encabezados: en el dossier cada `###` ES la afirmación, así que el índice
 *  basta para saber qué está ya cubierto sin arrastrar fuentes ni fechas. */
function headingIndex(text) {
  if (!text) return null;
  const out = text.split('\n')
    .filter((l) => /^#{2,3}\s/.test(l))
    .map((l) => l.replace(/^#{2,3}\s+/, '- '));
  return out.length ? out.join('\n') : null;
}

const state = JSON.parse(readFileSync(`${novel}/run-state.json`, 'utf8'));
const cfg = loadConfig(state.profile, ROOT);
const window = cfg.scope.summaryWindow;

/** Los últimos `window` resúmenes anteriores a N. No se leen capítulos, nunca. */
function summaries() {
  const from = Math.max(1, chapter - window);
  const parts = [];
  for (let i = from; i < chapter; i += 1) {
    const text = read(`bible/summaries/ch${String(i).padStart(2, '0')}.md`);
    if (text) parts.push(`### Resumen del capítulo ${i}\n\n${body(text)}`);
  }
  return parts.length ? parts.join('\n\n') : null;
}

const outlineEntry = () => sections(read('bible/outline.md'), new RegExp(`Cap[íi]tulo\\s+${chapter}\\b`));
const timelineEntry = () => sections(read('bible/timeline.md'), new RegExp(`Cap[íi]tulo\\s+${chapter}\\b`));

// Qué lleva cada nodo. Un bloque con `source: null` se omite del fichero.
const RECIPES = {
  // Planifica: necesita todo el canon y el índice de lo ya investigado, para declarar
  // lagunas sin repetir lo que el dossier ya cubre.
  beat: () => [
    ['Canon', body(read('bible/canon.md') ?? '')],
    ['Mundo', body(read('bible/world.md') ?? '')],
    ['Personajes', body(read('bible/characters.md') ?? '')],
    [`Escaleta — entrada del capítulo ${chapter}`, outlineEntry()],
    ['Cronología', body(read('bible/timeline.md') ?? '')],
    ['Hilos abiertos', body(read('bible/threads.md') ?? '')],
    [`Resúmenes previos (ventana ${window})`, summaries()],
    ['Índice del dossier — qué está YA respaldado', headingIndex(read('research/dossier.md'))],
  ],
  // Escribe: el dossier va entero, con fuentes y fechas, porque es lo único que le
  // autoriza a afirmar un dato.
  write: () => [
    ['Plan de beats', body(read(`notes/ch${NN}-beats.md`) ?? '')],
    ['Notas con fuente del capítulo', read(`research/ch${NN}-notes.md`) && body(read(`research/ch${NN}-notes.md`))],
    ['Canon', body(read('bible/canon.md') ?? '')],
    ['Mundo', body(read('bible/world.md') ?? '')],
    ['Personajes', body(read('bible/characters.md') ?? '')],
    [`Escaleta — entrada del capítulo ${chapter}`, outlineEntry()],
    ['Hilos abiertos', body(read('bible/threads.md') ?? '')],
    [`Resúmenes previos (ventana ${window})`, summaries()],
    ['Dossier — notas con fuente y fecha', body(read('research/dossier.md') ?? '')],
  ],
  // Valida contra canon: no necesita el dossier, que es competencia del verificador.
  'val-ck': () => [
    ['Canon', body(read('bible/canon.md') ?? '')],
    ['Mundo', body(read('bible/world.md') ?? '')],
    ['Personajes', body(read('bible/characters.md') ?? '')],
    [`Escaleta — entrada del capítulo ${chapter}`, outlineEntry()],
    ['Cronología', body(read('bible/timeline.md') ?? '')],
    ['Hilos abiertos', body(read('bible/threads.md') ?? '')],
    [`Resúmenes previos (ventana ${window})`, summaries()],
  ],
  // Verifica afirmaciones: solo notas. La biblia no respalda un dato técnico.
  'val-tv': () => [
    ['Dossier — notas con fuente y fecha', body(read('research/dossier.md') ?? '')],
    ['Notas con fuente del capítulo', read(`research/ch${NN}-notes.md`) && body(read(`research/ch${NN}-notes.md`))],
  ],
  // Actualiza la biblia: solo lo que un capítulo puede mover.
  commit: () => [
    [`Escaleta — entrada del capítulo ${chapter}`, outlineEntry()],
    ['Cronología', body(read('bible/timeline.md') ?? '')],
    ['Hilos abiertos', body(read('bible/threads.md') ?? '')],
    ['Reporte de incidencias', read(`notes/ch${NN}-issues.json`)],
    [`Resúmenes previos (ventana ${window})`, summaries()],
  ],
};

const blocks = RECIPES[node]().filter(([, content]) => content);
const header = [
  '---',
  `context: storymaker/node-context@1`,
  `novel: ${slug}`,
  `node: ${node}`,
  `chapter: ${chapter}`,
  `assembledAt: ${new Date().toISOString()}`,
  '---',
  '',
  `# Contexto ensamblado — ${node} · capítulo ${chapter}`,
  '',
  'Lo ensambla el orquestador en el nodo LOAD. Es **todo** tu contexto de biblia y notas:',
  'no abras los ficheros originales, ya están aquí y recortados a lo que tu nodo necesita.',
  'Los capítulos anteriores no se leen nunca — para eso están los resúmenes.',
  '',
].join('\n');

const out = header + blocks.map(([title, content]) => `## ${title}\n\n${content}`).join('\n\n') + '\n';
const target = `${novel}/notes/ch${NN}-ctx-${node}.md`;
mkdirSync(dirname(target), { recursive: true });
writeFileSync(target, out);

const words = (out.match(/\S+/g) ?? []).length;
console.log(`novels/${slug}/notes/ch${NN}-ctx-${node}.md · ${blocks.length} bloques · ${words} palabras`);
