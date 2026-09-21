// Evaluators deterministas sobre las novelas del repo. Ninguno llama a un modelo y
// ninguno sale a la red: se pueden correr en cada commit sin pensárselo.
//
// Son los cinco primeros de §2.4 de docs/diagnostico-evaluacion.md, que son los que no
// necesitan juicio. Cada uno devuelve una lista de resultados con la misma forma, pensada
// para mandarse tal cual como score de Langfuse:
//
//   { evaluator, target, novela, capitulo, pass, value, detalle }
//
// `target` es **el agente cuya salida se juzga**, no quien detecta el fallo: una longitud
// fuera de rango es de `scene-writer` aunque la mida esto, y un anclaje roto es de
// `continuity-keeper` porque la biblia es suya.
//
// `pass` puede ser `null`: significa "no se pudo juzgar" —un capítulo sin borrador, por
// ejemplo— y esos no cuentan ni a favor ni en contra. Se emiten igualmente, porque un
// evaluator que descarta casos en silencio miente sobre su propia cobertura.

import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { headingsOf, resolveAnchor } from '../dashboard/src/anchors.js';

const ejecutar = promisify(execFile);

/** La misma cuenta que usa guard-prose.mjs para la invariante 4. */
export const contarPalabras = (texto) => (String(texto).match(/\S+/g) ?? []).length;

const leer = (ruta) => readFileSync(ruta, 'utf8');
const leerJson = (ruta) => { try { return JSON.parse(leer(ruta)); } catch { return null; } };

/** Los capítulos finales de una novela, en orden. */
export function capitulosDe(novelDir) {
  const dir = `${novelDir}/chapters`;
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .map((f) => /^ch(\d+)\.md$/.exec(f))
    .filter(Boolean)
    .map((m) => ({ numero: Number(m[1]), fichero: m[0], ruta: `${dir}/${m[0]}` }))
    .sort((a, b) => a.numero - b.numero);
}

const resultado = (base) => ({
  evaluator: base.evaluator,
  target: base.target,
  novela: base.novela,
  capitulo: base.capitulo ?? null,
  pass: base.pass,
  value: base.value,
  detalle: base.detalle,
  dataType: base.dataType ?? 'NUMERIC',
  ...(base.extra ?? {}),
});

// ── 1 · voice-editor-no-anade ────────────────────────────────────────────────────
// Invariante 4. El hook ya lo impide al escribir; esto lo comprueba sobre lo que hay en
// disco, que es lo que de verdad se publicó.

export function voiceEditorNoAnade({ slug, novelDir }) {
  return capitulosDe(novelDir).map(({ numero, ruta }) => {
    const borrador = ruta.replace(/\.md$/, '.draft.md');
    const finales = contarPalabras(leer(ruta));

    if (!existsSync(borrador)) {
      return resultado({
        evaluator: 'voice-editor-no-anade', target: 'voice-editor', novela: slug, capitulo: numero,
        pass: null, value: null, detalle: `no hay borrador ch${String(numero).padStart(2, '0')}.draft.md; nada que comparar`,
      });
    }

    const previas = contarPalabras(leer(borrador));
    const delta = finales - previas;
    return resultado({
      evaluator: 'voice-editor-no-anade', target: 'voice-editor', novela: slug, capitulo: numero,
      pass: delta <= 0, value: delta,
      detalle: `final ${finales} palabras, borrador ${previas} (${delta > 0 ? '+' : ''}${delta})`,
    });
  });
}

// ── 2 · sin-terminos-prohibidos ──────────────────────────────────────────────────
// Invariante 9.
//
// No reimplementa la comprobación: **invoca el propio guard-prose.mjs** con un sobre
// sintético y le pregunta. Así reutiliza no solo `bannedTerms()` sino el emparejado real
// —que vive en el cuerpo del hook, con su `\b` y su bandera unicode, no en la función— y
// no puede desincronizarse de lo que de verdad se impone al escribir.
//
// Se le pasa la ruta del **borrador** con el texto **final** dentro: es la forma de pedirle
// solo la invariante 9. Con la ruta final también correría la 4, y eso acoplaría este
// evaluator con el anterior, que ya la mide y mejor.

export async function sinTerminosProhibidos({ slug, novelDir, repoRoot, guardProse }) {
  const hook = guardProse ?? `${repoRoot}/.claude/hooks/guard-prose.mjs`;
  const salida = [];

  for (const { numero, ruta } of capitulosDe(novelDir)) {
    const sobre = {
      tool_name: 'Write',
      tool_input: { file_path: ruta.replace(/\.md$/, '.draft.md'), content: leer(ruta) },
    };

    let veredicto = null;
    try {
      const proc = ejecutar('node', [hook], { encoding: 'utf8', timeout: 20000 });
      proc.child.stdin.end(JSON.stringify(sobre));
      veredicto = JSON.parse((await proc).stdout || '{}');
    } catch (error) {
      salida.push(resultado({
        evaluator: 'sin-terminos-prohibidos', target: 'scene-writer', novela: slug, capitulo: numero,
        pass: null, value: null, detalle: `no se pudo consultar a guard-prose: ${error.message}`,
      }));
      continue;
    }

    const motivo = veredicto?.hookSpecificOutput?.permissionDecisionReason ?? '';
    // La 4 la mide el evaluator anterior; aquí solo cuenta la 9.
    const prohibido = /Invariante 9/.test(motivo);
    const termino = prohibido ? (motivo.match(/contiene "([^"]+)"/)?.[1] ?? '(sin identificar)') : null;

    salida.push(resultado({
      evaluator: 'sin-terminos-prohibidos', target: 'scene-writer', novela: slug, capitulo: numero,
      pass: !prohibido, value: prohibido ? 1 : 0,
      detalle: prohibido ? `término prohibido en el texto final: "${termino}"` : 'sin términos prohibidos',
      extra: prohibido ? { termino } : {},
    }));
  }

  return salida;
}

// ── 3 · issues-schema-valido ─────────────────────────────────────────────────────

const PREFIJO_A_ROL = { ck: 'continuity-keeper', tv: 'technical-verifier' };
const SEVERIDADES = new Set(['blocker', 'warning', 'note']);
const DONDE = /^ch\d+ ¶\d+/;

/** Quién escribió una incidencia, según el prefijo de su id. */
export const rolDeIncidencia = (id) => PREFIJO_A_ROL[String(id ?? '').split('-')[0]] ?? 'desconocido';

export function issuesSchemaValido({ slug, novelDir }) {
  const dir = `${novelDir}/notes`;
  if (!existsSync(dir)) return [];
  const salida = [];

  for (const fichero of readdirSync(dir).filter((f) => /-issues\.json$/.test(f)).sort()) {
    const capitulo = Number(/^ch(\d+)-/.exec(fichero)?.[1] ?? 0) || null;
    const informe = leerJson(`${dir}/${fichero}`);

    if (!informe || !Array.isArray(informe.issues)) {
      salida.push(resultado({
        evaluator: 'issues-schema-valido', target: 'desconocido', novela: slug, capitulo,
        pass: false, value: 1, detalle: `${fichero} no es un informe con lista de incidencias`,
      }));
      continue;
    }

    for (const issue of informe.issues) {
      const fallos = [];
      if (!SEVERIDADES.has(issue.severity)) fallos.push(`severity "${issue.severity}" fuera de {blocker,warning,note}`);
      if (!DONDE.test(String(issue.where ?? ''))) fallos.push(`where "${issue.where}" no casa /^ch\\d+ ¶\\d+/`);
      if (!String(issue.fix ?? '').trim()) fallos.push('fix vacío');
      if (!/^(ck|tv)-/.test(String(issue.id ?? ''))) fallos.push(`id "${issue.id}" sin prefijo ck-/tv-`);

      salida.push(resultado({
        evaluator: 'issues-schema-valido', target: rolDeIncidencia(issue.id), novela: slug, capitulo,
        pass: fallos.length === 0, value: fallos.length,
        detalle: fallos.length ? `${issue.id}: ${fallos.join('; ')}` : `${issue.id} válida`,
        extra: { issueId: issue.id ?? null },
      }));
    }
  }

  return salida;
}

// ── 4 · canon-resoluble ──────────────────────────────────────────────────────────
// Una cita rota no es un detalle de formato: es una referencia de canon que no lleva a
// ninguna parte, y quien la sigue se queda sin saber en qué se apoyaba la afirmación.

const CITA = /([A-Za-z0-9_-]+\.md)#([^\s`)\]"“”'<>]+)/g;
const limpiarAncla = (a) => String(a).replace(/[.,;:!?]+$/, '');

/** Los documentos contra los que se resuelve: la biblia, y el dossier si existe. */
function documentosDe(novelDir) {
  const docs = [];
  for (const [dir, existe] of [[`${novelDir}/bible`, true], [`${novelDir}/research`, true]]) {
    if (!existe || !existsSync(dir)) continue;
    for (const f of readdirSync(dir).filter((x) => x.endsWith('.md'))) {
      docs.push({ key: f.replace(/\.md$/, ''), file: f, headings: headingsOf(leer(`${dir}/${f}`)) });
    }
  }
  return docs;
}

/** De dónde salen las citas: la biblia entera, resúmenes incluidos. */
function fuentesDeCita(novelDir) {
  const fuentes = [];
  const dir = `${novelDir}/bible`;
  if (!existsSync(dir)) return fuentes;
  for (const f of readdirSync(dir).filter((x) => x.endsWith('.md'))) fuentes.push({ etiqueta: `bible/${f}`, ruta: `${dir}/${f}` });
  const resumenes = `${dir}/summaries`;
  if (existsSync(resumenes)) {
    for (const f of readdirSync(resumenes).filter((x) => x.endsWith('.md'))) {
      fuentes.push({ etiqueta: `bible/summaries/${f}`, ruta: `${resumenes}/${f}`, capitulo: Number(/^ch(\d+)/.exec(f)?.[1]) || null });
    }
  }
  return fuentes;
}

export function canonResoluble({ slug, novelDir }) {
  const docs = documentosDe(novelDir);
  const salida = [];

  // a) Las citas que la biblia se hace a sí misma.
  for (const { etiqueta, ruta, capitulo } of fuentesDeCita(novelDir)) {
    for (const m of leer(ruta).matchAll(CITA)) {
      const ancla = limpiarAncla(m[2]);
      const destino = resolveAnchor(docs, m[1], ancla);
      salida.push(resultado({
        evaluator: 'canon-resoluble', target: 'continuity-keeper', novela: slug, capitulo: capitulo ?? null,
        pass: Boolean(destino), value: destino ? 1 : 0,
        detalle: `${etiqueta} cita ${m[1]}#${ancla}${destino ? '' : ' — no apunta a ningún encabezado'}`,
        extra: { origen: 'bible', cita: `${m[1]}#${ancla}` },
      }));
    }
  }

  // b) El campo `canon` de las incidencias, que es de quien firmó la incidencia.
  const notas = `${novelDir}/notes`;
  if (existsSync(notas)) {
    for (const fichero of readdirSync(notas).filter((f) => /-issues\.json$/.test(f)).sort()) {
      const capitulo = Number(/^ch(\d+)-/.exec(fichero)?.[1] ?? 0) || null;
      for (const issue of leerJson(`${notas}/${fichero}`)?.issues ?? []) {
        if (!issue.canon) continue;
        const m = CITA.exec(issue.canon);
        CITA.lastIndex = 0;
        if (!m) {
          salida.push(resultado({
            evaluator: 'canon-resoluble', target: rolDeIncidencia(issue.id), novela: slug, capitulo,
            pass: false, value: 0, detalle: `${issue.id}: canon "${String(issue.canon).slice(0, 60)}" no tiene forma fichero.md#ancla`,
            extra: { origen: 'issue', issueId: issue.id ?? null },
          }));
          continue;
        }
        const ancla = limpiarAncla(m[2]);
        const destino = resolveAnchor(docs, m[1], ancla);
        salida.push(resultado({
          evaluator: 'canon-resoluble', target: rolDeIncidencia(issue.id), novela: slug, capitulo,
          pass: Boolean(destino), value: destino ? 1 : 0,
          detalle: `${issue.id} cita ${m[1]}#${ancla}${destino ? '' : ' — no apunta a ningún encabezado'}`,
          extra: { origen: 'issue', issueId: issue.id ?? null, cita: `${m[1]}#${ancla}` },
        }));
      }
    }
  }

  return salida;
}

// ── 5 · longitud-en-rango ────────────────────────────────────────────────────────
// La longitud es de quien escribe la escena: `voice-editor` solo quita, así que no puede
// ser responsable de un capítulo que se pasa de largo.

export function longitudEnRango({ slug, novelDir, scope }) {
  const objetivo = scope?.wordsPerChapter ?? null;
  const tolerancia = scope?.wordsTolerance ?? 0.2;

  return capitulosDe(novelDir).map(({ numero, ruta }) => {
    const palabras = contarPalabras(leer(ruta));
    if (!objetivo) {
      return resultado({
        evaluator: 'longitud-en-rango', target: 'scene-writer', novela: slug, capitulo: numero,
        pass: null, value: null, detalle: `sin scope.wordsPerChapter en el perfil; ${palabras} palabras sin objetivo contra el que medir`,
      });
    }
    const desvio = Math.abs(palabras - objetivo) / objetivo;
    const firmado = ((palabras - objetivo) / objetivo) * 100;
    return resultado({
      evaluator: 'longitud-en-rango', target: 'scene-writer', novela: slug, capitulo: numero,
      pass: desvio <= tolerancia, value: Number(desvio.toFixed(4)),
      detalle: `${palabras} palabras, objetivo ${objetivo} (${firmado >= 0 ? '+' : ''}${firmado.toFixed(1)} %, tolerancia ±${(tolerancia * 100).toFixed(0)} %)`,
    });
  });
}

// ── Orquestación ─────────────────────────────────────────────────────────────────

export const EVALUATORS = [
  { nombre: 'voice-editor-no-anade', fn: voiceEditorNoAnade },
  { nombre: 'sin-terminos-prohibidos', fn: sinTerminosProhibidos },
  { nombre: 'issues-schema-valido', fn: issuesSchemaValido },
  { nombre: 'canon-resoluble', fn: canonResoluble },
  { nombre: 'longitud-en-rango', fn: longitudEnRango },
];

export async function evaluarNovela(contexto, nombres = null) {
  const elegidos = nombres ? EVALUATORS.filter((e) => nombres.includes(e.nombre)) : EVALUATORS;
  const salida = [];
  for (const { fn } of elegidos) {
    const filas = await fn(contexto);
    for (const fila of filas) {
      salida.push(contexto.contaminated ? { ...fila, contaminated: true } : fila);
    }
  }
  return salida;
}
