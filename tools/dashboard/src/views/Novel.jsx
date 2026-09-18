import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { getNovel, getText } from '../api.js';
import { go } from '../hooks.js';
import { Pill, Progress, Skeleton, Issues, Prose, Inline, fmt, fecha } from '../components/ui.jsx';
import { ESTADOS } from './History.jsx';

const SEV = { blocker: 'blocker', warning: 'warn', note: 'faint' };

/**
 * Una fila del acordeón.
 *
 * El resumen que se despliega es el de `bible/summaries/`, no un extracto del capítulo:
 * es lo único que los capítulos siguientes llegaron a saber de este, así que es lo que
 * de verdad explica por qué la novela siguió como siguió.
 */
function Chapter({ slug, c, open, onToggle }) {
  const [text, setText] = useState(null);
  const [loading, setLoading] = useState(false);

  const leer = async () => {
    if (text) { setText(null); return; }
    setLoading(true);
    try {
      setText((await getText(slug, c.chapter)).text);
    } catch (e) {
      setText(`No se pudo leer el capítulo: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`chapter ${open ? 'open' : ''}`}>
      <button className="chapter-head" onClick={onToggle} aria-expanded={open}>
        <span className="chapter-n num">{String(c.chapter).padStart(2, '0')}</span>
        <span className="chapter-title">{c.title ?? <em className="note">sin título en el manuscrito</em>}</span>
        <span className="chapter-meta">
          <span className="num">{fmt(c.words)} pal</span>
          <Issues counts={c.counts} empty="" />
        </span>
        <motion.span className="chapter-caret" animate={{ rotate: open ? 90 : 0 }} transition={{ duration: 0.2 }}>
          ›
        </motion.span>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="body"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.28, ease: [0.2, 0.7, 0.2, 1] }}
            style={{ overflow: 'hidden' }}
          >
            <div className="chapter-body">
              <h4 className="chapter-label">Resumen en la biblia</h4>
              {c.summary
                ? <p className="chapter-summary"><Inline text={c.summary} /></p>
                : <p className="empty">Este capítulo no tiene resumen en <code>bible/summaries/</code>.</p>}

              {c.issues.length > 0 && (
                <>
                  <h4 className="chapter-label">Incidencias</h4>
                  <table className="data">
                    <thead>
                      <tr><th>id</th><th>Severidad</th><th>Dónde</th><th>Qué</th></tr>
                    </thead>
                    <tbody>
                      {c.issues.map((i, n) => (
                        <tr key={i.id ?? n}>
                          <td className="num">{i.id ?? ''}</td>
                          <td>
                            <span className="pill" style={{
                              borderColor: `var(--${SEV[i.severity] ?? 'faint'})`,
                              color: `var(--${SEV[i.severity] ?? 'faint'})`,
                            }}>{i.severity}</span>
                          </td>
                          <td>{i.where ?? ''}</td>
                          <td><Inline text={i.fix ?? i.claim ?? ''} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}

              <div className="chapter-actions">
                <button className="btn-secondary" onClick={leer} disabled={loading}>
                  {loading ? 'Cargando…' : text ? 'Cerrar el capítulo' : 'Leer el capítulo'}
                </button>
                {c.hasDraft && <span className="note">hay un <code>.draft.md</code> previo a voice-editor</span>}
              </div>

              <AnimatePresence>
                {text && (
                  <motion.div
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    transition={{ duration: 0.25 }}
                    className="reader"
                  >
                    <Prose text={text} />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Manuscript({ slug }) {
  const [text, setText] = useState(null);
  const [loading, setLoading] = useState(false);

  const leer = async () => {
    if (text) { setText(null); return; }
    setLoading(true);
    try {
      setText((await getText(slug, 'all')).text);
    } catch (e) {
      setText(`No se pudo leer el manuscrito: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card" style={{ marginTop: 'var(--sp-4)' }}>
      <div className="chapter-actions" style={{ marginTop: 0 }}>
        <button className="btn-secondary" onClick={leer} disabled={loading}>
          {loading ? 'Cargando…' : text ? 'Cerrar el manuscrito' : 'Leer el manuscrito completo'}
        </button>
        <span className="note"><code>out/manuscript.md</code></span>
      </div>
      <AnimatePresence>
        {text && (
          <motion.div
            initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }} className="reader"
          >
            <Prose text={text} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function Novel({ slug }) {
  const [n, setN] = useState(null);
  const [error, setError] = useState(null);
  const [open, setOpen] = useState(null);

  useEffect(() => {
    let alive = true;
    setN(null);
    setError(null);
    getNovel(slug)
      .then((d) => { if (alive) setN(d); })
      .catch((e) => { if (alive) setError(e.message); });
    return () => { alive = false; };
  }, [slug]);

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
          <div className="s"><Issues counts={n.issues} /></div>
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

      <div className="head" style={{ marginTop: 'var(--sp-8)' }}>
        <h3>Capítulos</h3>
        <p>Despliega uno para ver su resumen de la biblia y sus incidencias.</p>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {n.chapters.length ? n.chapters.map((c) => (
          <Chapter
            key={c.chapter} slug={n.slug} c={c}
            open={open === c.chapter}
            onToggle={() => setOpen(open === c.chapter ? null : c.chapter)}
          />
        )) : (
          <p className="empty" style={{ padding: 'var(--sp-6)' }}>
            Esta novela no tiene capítulos escritos todavía.
          </p>
        )}
      </div>

      {n.manuscript && <Manuscript slug={n.slug} />}

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
