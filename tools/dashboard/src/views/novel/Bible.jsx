// La biblia, en solo lectura.
//
// Solo lectura no es una limitación de la vista: es la invariante 2. La biblia la escribe
// `continuity-keeper` y nadie más, y un panel con un campo de edición aquí rompería el
// canon por un camino que el hook de escritura no vigila.

import { useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { getBible } from '../../api.js';
import { headingsOf, resolveAnchor } from '../../anchors.js';
import Markdown from '../../components/Markdown.jsx';
import { Skeleton } from '../../components/ui.jsx';

export default function Bible({ slug }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [active, setActive] = useState('canon');
  const [target, setTarget] = useState(null);
  const body = useRef(null);

  useEffect(() => {
    let alive = true;
    setData(null);
    setError(null);
    setActive('canon');
    getBible(slug)
      .then((d) => { if (alive) setData(d); })
      .catch((e) => { if (alive) setError(e.message); });
    return () => { alive = false; };
  }, [slug]);

  /**
   * Los documentos con sus encabezados ya resueltos.
   *
   * Los resúmenes se juntan en un documento más porque es como se leen: uno detrás de
   * otro. Cada fichero trae su propio encabezado, así que el índice lateral sale solo.
   */
  const docs = useMemo(() => {
    if (!data) return [];
    const base = data.docs.map((d) => ({ ...d, headings: d.text ? headingsOf(d.text) : [] }));
    const joined = data.summaries.map((s) => s.text).filter(Boolean).join('\n\n');
    return [
      ...base,
      {
        key: 'summaries',
        file: 'summaries/',
        label: 'Resúmenes',
        text: joined || null,
        headings: joined ? headingsOf(joined) : [],
      },
    ];
  }, [data]);

  const doc = docs.find((d) => d.key === active) ?? docs[0] ?? null;

  // Seguir un anclaje puede cambiar de documento, así que el desplazamiento espera a que
  // el documento nuevo esté pintado en vez de buscar un `id` que todavía no existe.
  useEffect(() => {
    if (!target || !doc) return;
    const frame = requestAnimationFrame(() => {
      const el = body.current?.querySelector(`#${CSS.escape(target)}`);
      if (el) {
        el.scrollIntoView({ block: 'start', behavior: 'smooth' });
        el.classList.add('md-hit');
        setTimeout(() => el.classList.remove('md-hit'), 1600);
      }
      setTarget(null);
    });
    return () => cancelAnimationFrame(frame);
  }, [target, doc]);

  const ctx = useMemo(() => ({
    resolve: (file, anchor) => resolveAnchor(docs, file, anchor),
    go: (hit) => { setActive(hit.doc); setTarget(hit.id); },
  }), [docs]);

  if (error) {
    return <div className="card"><p className="warn-row">No se pudo leer la biblia: {error}</p></div>;
  }

  if (!data) {
    return (
      <div className="bible">
        <aside className="bible-nav">
          {[0, 1, 2, 3, 4, 5].map((i) => <Skeleton key={i} h={30} style={{ marginBottom: 6 }} />)}
        </aside>
        <div className="card">
          <Skeleton h={20} w="46%" />
          <Skeleton h={13} style={{ marginTop: 16 }} />
          <Skeleton h={13} style={{ marginTop: 8 }} />
          <Skeleton h={13} w="80%" style={{ marginTop: 8 }} />
        </div>
      </div>
    );
  }

  return (
    <div className="bible">
      <aside className="bible-nav">
        {docs.map((d) => (
          <button
            key={d.key}
            className={`bible-doc ${active === d.key ? 'on' : ''} ${d.text ? '' : 'absent'}`}
            onClick={() => d.text && setActive(d.key)}
            disabled={!d.text}
            title={d.text ? `bible/${d.file}` : `bible/${d.file} — todavía no existe`}
          >
            {d.label}
            {!d.text && <span className="bible-absent">—</span>}
          </button>
        ))}

        {doc?.headings.length > 1 && (
          <div className="bible-outline">
            {doc.headings.filter((h) => h.level >= 2).map((h) => (
              <button
                key={h.id}
                className={`bible-jump lvl${Math.min(h.level, 4)}`}
                onClick={() => setTarget(h.id)}
              >
                {h.label}
              </button>
            ))}
          </div>
        )}
      </aside>

      <motion.div
        key={doc?.key}
        className="card bible-body" ref={body}
        initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22, ease: [0.2, 0.7, 0.2, 1] }}
      >
        {doc?.text
          ? (
            <>
              <p className="bible-path"><code>novels/{slug}/bible/{doc.file}</code> · solo lectura</p>
              <Markdown text={doc.text} ctx={ctx} />
            </>
          )
          : <p className="empty">Este documento de la biblia todavía no existe.</p>}
      </motion.div>
    </div>
  );
}
