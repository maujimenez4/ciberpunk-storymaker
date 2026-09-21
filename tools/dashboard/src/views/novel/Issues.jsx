// Las incidencias de la novela, por capítulo y por severidad.
//
// Salen de `notes/chNN-issues.json` tal como los dejó el reporte, sin recontar nada: los
// `counts` del fichero son los que decidieron si hubo reescritura, y recalcularlos aquí
// solo abriría la puerta a que el panel y la corrida discreparan.

import { useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Inline } from '../../components/ui.jsx';

const SEV = {
  blocker: { tone: 'blocker', label: 'blocker' },
  warning: { tone: 'warn', label: 'warning' },
  note: { tone: 'faint', label: 'note' },
};

export default function Issues({ novel }) {
  const [sev, setSev] = useState('todas');

  const chapters = useMemo(
    () => novel.chapters.filter((c) => c.issues.length > 0),
    [novel.chapters],
  );

  const shown = useMemo(() => chapters
    .map((c) => ({ ...c, visible: sev === 'todas' ? c.issues : c.issues.filter((i) => i.severity === sev) }))
    .filter((c) => c.visible.length > 0), [chapters, sev]);

  const totals = novel.issues;
  const total = totals.blocker + totals.warning + totals.note;

  const FILTROS = [
    { key: 'todas', label: `Todas (${total})` },
    { key: 'blocker', label: `Blocker (${totals.blocker})` },
    { key: 'warning', label: `Warning (${totals.warning})` },
    { key: 'note', label: `Note (${totals.note})` },
  ];

  if (!total) {
    return (
      <div className="card">
        <p className="empty">
          Ningún capítulo de esta novela dejó incidencias. Los validadores pasaron limpios.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="history-bar">
        <div className="chips" role="tablist" aria-label="Filtrar por severidad">
          {FILTROS.map((f) => (
            <button
              key={f.key} role="tab" aria-selected={sev === f.key}
              className={`chip ${sev === f.key ? 'on' : ''}`}
              onClick={() => setSev(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <p className="note" style={{ marginBottom: 'var(--sp-4)' }}>
        Solo un <code>blocker</code> dispara reescritura. <code>warning</code> y{' '}
        <code>note</code> se imprimen en la compuerta y quedan aquí.
      </p>

      <AnimatePresence mode="popLayout">
        {shown.map((c) => (
          <motion.section
            key={c.chapter} layout
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            transition={{ duration: 0.22 }}
            className="issue-group"
          >
            <h4 className="issue-group-head">
              <span className="num">Capítulo {String(c.chapter).padStart(2, '0')}</span>
              {c.title && <span className="issue-group-title">{c.title}</span>}
            </h4>

            {c.visible.map((i, n) => {
              const s = SEV[i.severity] ?? SEV.note;
              return (
                <article key={i.id ?? n} className={`card issue-card sev-${s.tone}`}>
                  <header className="issue-card-top">
                    <span className="pill" style={{ borderColor: `var(--${s.tone})`, color: `var(--${s.tone})` }}>
                      {s.label}
                    </span>
                    {i.id && <code className="issue-id">{i.id}</code>}
                    {i.kind && <span className="note">{i.kind}</span>}
                    <span className="spacer" />
                    {i.where && <span className="note">{i.where}</span>}
                  </header>

                  {i.claim && (
                    <p className="issue-claim"><Inline text={i.claim} /></p>
                  )}
                  {i.canon && (
                    <p className="issue-line">
                      <span className="issue-label">Canon</span>
                      <Inline text={i.canon} />
                    </p>
                  )}
                  {i.fix && (
                    <p className="issue-line">
                      <span className="issue-label">Arreglo</span>
                      <Inline text={i.fix} />
                    </p>
                  )}
                </article>
              );
            })}
          </motion.section>
        ))}
      </AnimatePresence>

      {!shown.length && (
        <div className="card"><p className="empty">Ninguna incidencia con esa severidad.</p></div>
      )}
    </div>
  );
}
