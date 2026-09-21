// La pestaña de una novela: su cabecera y tres sub-pestañas.
//
// La cabecera —estado, capítulos, palabras, coste— se queda fuera de las sub-pestañas
// porque describe la novela entera y no cambia al pasar de Leer a Biblia. Lo mismo vale
// para el coste por agente, que va al pie.

import { useEffect, useState } from 'react';
import { motion, AnimatePresence, LayoutGroup } from 'framer-motion';
import { getNovel } from '../api.js';
import { go, rememberNovel } from '../hooks.js';
import { Pill, Progress, Skeleton, Issues as IssueCounts, fmt, fecha } from '../components/ui.jsx';
import { ESTADOS } from './History.jsx';
import Read from './novel/Read.jsx';
import Bible from './novel/Bible.jsx';
import IssueList from './novel/Issues.jsx';

const SUBS = [
  { key: 'leer', label: 'Leer' },
  { key: 'biblia', label: 'Biblia' },
  { key: 'incidencias', label: 'Incidencias' },
];

function SubTabs({ slug, active }) {
  return (
    <div className="subtabs" role="tablist" aria-label="Secciones de la novela">
      <LayoutGroup id="subtabs">
        {SUBS.map((s) => (
          <button
            key={s.key} role="tab" aria-selected={active === s.key}
            className={`subtab ${active === s.key ? 'on' : ''}`}
            onClick={() => go(`/novela/${encodeURIComponent(slug)}/${s.key}`)}
          >
            {s.label}
            {active === s.key && (
              <motion.span
                className="subtab-ink" layoutId="subtab-ink"
                transition={{ duration: 0.26, ease: [0.2, 0.7, 0.2, 1] }}
              />
            )}
          </button>
        ))}
      </LayoutGroup>
    </div>
  );
}

export default function Novel({ slug, sub = 'leer', novels = [] }) {
  const [n, setN] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => { rememberNovel(slug); }, [slug]);

  useEffect(() => {
    if (!slug) { setN(null); return undefined; }
    let alive = true;
    setN(null);
    setError(null);
    getNovel(slug)
      .then((d) => { if (alive) setN(d); })
      .catch((e) => { if (alive) setError(e.message); });
    return () => { alive = false; };
  }, [slug]);

  // Entrar por la pestaña sin haber abierto ninguna novela nunca.
  if (!slug) {
    return (
      <section>
        <div className="head">
          <h2>Novela</h2>
          <p>Elige una novela para leerla, consultar su biblia y revisar sus incidencias.</p>
        </div>
        <div className="card">
          {novels.length
            ? (
              <div className="chips">
                {novels.map((s) => (
                  <button key={s} className="chip" onClick={() => go(`/novela/${encodeURIComponent(s)}`)}>{s}</button>
                ))}
              </div>
            )
            : <p className="empty">No hay ninguna novela en <code>novels/</code> todavía.</p>}
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section>
        <button className="btn-secondary" onClick={() => go('/historial')}>← Historial</button>
        <div className="card" style={{ marginTop: 'var(--sp-4)' }}>
          <p className="warn-row">No se pudo abrir «{slug}»: {error}</p>
        </div>
      </section>
    );
  }

  if (!n) {
    return (
      <section>
        <Skeleton h={34} w="44%" />
        <Skeleton h={16} w="28%" style={{ marginTop: 12 }} />
        <div className="card" style={{ marginTop: 'var(--sp-6)' }}>
          <Skeleton h={54} />
          <Skeleton h={54} style={{ marginTop: 8 }} />
        </div>
      </section>
    );
  }

  const estado = ESTADOS[n.status] ?? { tone: '', label: n.status };
  const planned = n.progress.planned ?? n.progress.written;

  return (
    <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <button className="btn-secondary" onClick={() => go('/historial')}>← Historial</button>

      <div className="novel-head">
        <div>
          <h2>{n.title}</h2>
          <p className="novel-slug">
            {n.slug}{n.profile ? <> · <code>{n.profile}</code></> : null}
            {n.startedAt ? ` · empezada el ${fecha(n.startedAt)}` : ''}
          </p>
        </div>
        <Pill tone={estado.tone}>
          {estado.label}{n.status === 'gate' ? ` · cap ${n.gateChapter}` : ''}
        </Pill>
      </div>

      <div className="tiles">
        <div className="tile">
          <div className="k">Capítulos</div>
          <div className="v num">{n.progress.approved}<span className="of">/{planned}</span></div>
          <div className="s">{n.progress.written} escritos</div>
        </div>
        <div className="tile">
          <div className="k">Palabras</div>
          <div className="v num">{fmt(n.words)}</div>
          <div className="s">
            {n.progress.written ? `${fmt(Math.round(n.words / n.progress.written))} por capítulo` : '—'}
          </div>
        </div>
        <div className="tile">
          <div className="k">Llamadas</div>
          <div className="v num">{n.measured ? fmt(n.calls) : '—'}</div>
          <div className="s">{n.measured ? `${fmt(n.tokens)} tokens` : 'sin telemetría'}</div>
        </div>
        <div className="tile">
          <div className="k">Incidencias</div>
          <div className="v num">{n.issues.blocker + n.issues.warning + n.issues.note}</div>
          <div className="s"><IssueCounts counts={n.issues} /></div>
        </div>
        <div className="tile">
          <div className="k">Última actividad</div>
          <div className="v" style={{ fontSize: 19 }}>{fecha(n.touchedAt)}</div>
          <div className="s">{n.node ? `nodo ${n.node}` : '—'}</div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 'var(--sp-4)' }}>
        <Progress value={n.progress.approved} max={planned} label="Progreso aprobado" />
        {n.brief && (
          <p className="note" style={{ marginTop: 'var(--sp-4)' }}>
            Brief de {n.brief.words} palabras
            {n.brief.sections.length ? ` · ${n.brief.sections.join(' · ')}` : ' · sin secciones'}
          </p>
        )}
      </div>

      <SubTabs slug={n.slug} active={sub} />

      <AnimatePresence mode="wait">
        <motion.div
          key={sub}
          initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.22, ease: [0.2, 0.7, 0.2, 1] }}
        >
          {sub === 'leer' && <Read slug={n.slug} novel={n} />}
          {sub === 'biblia' && <Bible slug={n.slug} />}
          {sub === 'incidencias' && <IssueList novel={n} />}
        </motion.div>
      </AnimatePresence>

      {n.agents.length > 0 && (
        <>
          <div className="head" style={{ marginTop: 'var(--sp-8)' }}>
            <h3>Coste por agente</h3>
            <p>De <code>agent-calls.jsonl</code>, la línea por subagente que escribe el hook.</p>
          </div>
          <div className="card">
            <table className="data">
              <thead>
                <tr><th>Agente</th><th className="r">Llamadas</th><th className="r">Tokens</th></tr>
              </thead>
              <tbody>
                {n.agents.map((a) => (
                  <tr key={a.agent}>
                    <td style={{ fontWeight: 500 }}>{a.agent}</td>
                    <td className="r num">{a.calls}</td>
                    <td className="r num">{fmt(a.tokens)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </motion.section>
  );
}
