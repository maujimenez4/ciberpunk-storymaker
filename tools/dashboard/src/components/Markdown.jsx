// Markdown mínimo para la biblia: encabezados con `id`, listas y, sobre todo, anclajes
// de canon que llevan a alguna parte.
//
// A mano y no con `marked`: lo que se renderiza aquí sale de ficheros del disco, y un
// renderizador que emite elementos de React no tiene por dónde inyectar nada, mientras
// que uno que emite HTML obliga a sanearlo y a acertar siempre. El panel ya tiene el
// router escrito a mano por la misma razón.

import { headingsOf, stripFrontmatter } from '../anchors.js';

// Un anclaje suelto: `threads.md#dilema-de-la-firma`, con o sin `bible/` delante.
const ANCHOR = /^([\w./-]+\.md)#(.+)$/;

// Code span, negrita, cursiva y anclaje. El orden importa: `**` antes que `*`.
const TOKEN = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*\n]+\*|[\w./-]+\.md#[^\s,;)\]}"'`]+)/;

function Anchor({ file, anchor, ctx }) {
  const label = `${file}#${anchor}`;
  const hit = ctx?.resolve?.(file, anchor) ?? null;

  if (!hit || !ctx?.go) {
    return (
      <code className="anchor dead" title="Este anclaje no resuelve contra ningún encabezado de la biblia">
        {label}
      </code>
    );
  }
  return (
    <button type="button" className="anchor" title={`Ir a ${label}`} onClick={() => ctx.go(hit)}>
      {label}
    </button>
  );
}

/** Los trozos de una línea: código, énfasis y anclajes. */
export function Rich({ text, ctx }) {
  const parts = String(text ?? '').split(TOKEN).filter((p) => p !== '' && p !== undefined);

  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
          const inner = part.slice(1, -1);
          const cite = ANCHOR.exec(inner);
          return cite
            ? <Anchor key={i} file={cite[1]} anchor={cite[2]} ctx={ctx} />
            : <code key={i}>{inner}</code>;
        }
        if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
          return <strong key={i}>{part.slice(2, -2)}</strong>;
        }
        if (part.startsWith('*') && part.endsWith('*') && part.length > 2) {
          return <em key={i}>{part.slice(1, -1)}</em>;
        }
        const cite = ANCHOR.exec(part);
        return cite
          ? <Anchor key={i} file={cite[1]} anchor={cite[2]} ctx={ctx} />
          : <span key={i}>{part}</span>;
      })}
    </>
  );
}

const ITEM = /^\s*(?:[-*]|\d+\.)\s+/;

/**
 * Documento entero.
 *
 * Los `id` no se recalculan aquí: se consumen en orden los que devuelve `headingsOf`, que
 * es también quien alimenta el índice lateral. Con dos implementaciones del mismo slug,
 * el índice y el documento acabarían discrepando en cuanto una cambiara.
 */
export default function Markdown({ text, ctx, base = 3 }) {
  const body = stripFrontmatter(text);
  const ids = headingsOf(text).map((h) => h.id);

  const blocks = [];
  let buffer = [];
  let seen = 0;
  const flush = () => {
    if (buffer.length) blocks.push({ type: 'p', text: buffer.join(' ') });
    buffer = [];
  };

  for (const line of body.split('\n')) {
    const head = /^(#{1,6})\s+(.*)$/.exec(line);
    if (head) {
      flush();
      blocks.push({ type: 'h', level: head[1].length, text: head[2].trim(), id: ids[seen] });
      seen += 1;
      continue;
    }
    if (!line.trim()) { flush(); continue; }
    if (/^\s*---+\s*$/.test(line)) { flush(); blocks.push({ type: 'hr' }); continue; }
    if (ITEM.test(line)) {
      const ordered = /^\s*\d+\.\s+/.test(line);
      flush();
      const last = blocks[blocks.length - 1];
      if (last?.type === 'list' && last.ordered === ordered) last.items.push(line.replace(ITEM, ''));
      else blocks.push({ type: 'list', ordered, items: [line.replace(ITEM, '')] });
      continue;
    }
    buffer.push(line.trim());
  }
  flush();

  return (
    <div className="md">
      {blocks.map((b, i) => {
        if (b.type === 'hr') return <hr key={i} className="md-hr" />;
        if (b.type === 'h') {
          const Tag = `h${Math.min(6, base + b.level - 1)}`;
          return <Tag key={i} id={b.id} className={`md-h md-h${b.level}`}><Rich text={b.text} ctx={ctx} /></Tag>;
        }
        if (b.type === 'list') {
          const Tag = b.ordered ? 'ol' : 'ul';
          return (
            <Tag key={i} className="md-list">
              {b.items.map((it, j) => <li key={j}><Rich text={it} ctx={ctx} /></li>)}
            </Tag>
          );
        }
        return <p key={i}><Rich text={b.text} ctx={ctx} /></p>;
      })}
    </div>
  );
}
