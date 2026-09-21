// Cómo se resuelve una cita de canon: el slug de un encabezado y a qué apunta un
// anclaje. Va aparte de `Markdown.jsx` porque no tiene nada de React y porque así se
// puede comprobar con node contra las biblias reales, que es donde están los casos raros.

/**
 * Slug de un encabezado, en la forma que usan los anclajes de la biblia.
 *
 * Conserva los acentos a propósito: los anclajes que escribe `continuity-keeper` los
 * llevan —`threads.md#acreditación-retenida`, `#vía-de-auditar-la-referencia`—, así que
 * plegarlos aquí rompería justo los que sí resuelven.
 */
export const slugify = (text) => String(text ?? '')
  .trim()
  .toLowerCase()
  .replace(/[`*_~]/g, '')
  .replace(/[—–]/g, ' ')
  .replace(/[.,;:!?¿¡()[\]{}"'«»]/g, '')
  .replace(/\s+/g, '-')
  .replace(/-+/g, '-')
  .replace(/^-|-$/g, '');

const fold = (s) => s.normalize('NFD').replace(/[̀-ͯ]/g, '');

export const stripFrontmatter = (text) => String(text ?? '').replace(/^---\n[\s\S]*?\n---\n/, '');

/**
 * Los encabezados de un documento, en orden y con su `id` ya resuelto.
 *
 * El desempate importa: `bible/characters.md` de dead-floor repite el nombre del
 * personaje como `## El técnico` y `### el-tecnico`, y sin sufijo dos secciones acabarían
 * compartiendo `id` y el anclaje saltaría siempre a la primera.
 */
export function headingsOf(text) {
  const out = [];
  const seen = new Map();
  for (const line of stripFrontmatter(text).split('\n')) {
    const match = /^(#{1,6})\s+(.*)$/.exec(line);
    if (!match) continue;
    const label = match[2].trim();
    const base = slugify(label);
    const hits = seen.get(base) ?? 0;
    seen.set(base, hits + 1);
    out.push({ level: match[1].length, label, id: hits ? `${base}-${hits}` : base });
  }
  return out;
}

/**
 * A qué encabezado apunta `fichero.md#ancla`, si es que apunta a alguno.
 *
 * Tres intentos, porque en el disco conviven tres formas. `continuity-keeper` escribe
 * unas veces el encabezado ya en kebab-case (`### dilema-de-la-firma`, en dead-floor) y
 * otras en prosa (`### Acreditación retenida`, en neon-smoke). Y hay anclajes que son
 * solo el principio del encabezado: `threads.md#reloj-de-la-ciudad` apunta a
 * `### Reloj de la ciudad — mecanismo de invalidación retroactiva`.
 *
 * Lo que no resuelve devuelve null y se pinta apagado. Un enlace que no lleva a ninguna
 * parte sería peor que la cita en crudo: escondería que esa referencia del canon está
 * rota, que es justo lo que alguien mirando la biblia quiere ver.
 */
export function resolveAnchor(docs, file, anchor) {
  const name = String(file).replace(/^.*\//, '').replace(/\.md$/, '');
  const doc = docs.find((d) => d.key === name || d.file === `${name}.md`);
  if (!doc) return null;

  const want = String(anchor).toLowerCase();
  const heads = doc.headings ?? [];

  const exact = heads.find((h) => h.id === want);
  if (exact) return { doc: doc.key, id: exact.id };

  const byPrefix = heads.filter((h) => h.id.startsWith(`${want}-`));
  if (byPrefix.length === 1) return { doc: doc.key, id: byPrefix[0].id };

  const loose = fold(want);
  const folded = heads.filter((h) => fold(h.id) === loose || fold(h.id).startsWith(`${loose}-`));
  return folded.length === 1 ? { doc: doc.key, id: folded[0].id } : null;
}
