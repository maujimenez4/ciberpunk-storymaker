// Leer la novela: un capítulo a la vez, de los aprobados y solo de los aprobados.
//
// Se lee `chapters/chNN.md`, que es la salida de `voice-editor`, nunca el `.draft.md`
// anterior: el borrador existe en disco pero no es el capítulo, y enseñarlo aquí haría
// pasar por texto de la novela algo que no llegó a serlo.

import { useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { getText } from '../../api.js';
import { Prose, Skeleton, fmt } from '../../components/ui.jsx';

/** El manuscrito ya ensamblado por `compiler`, para leerlo de un tirón. */
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
      {text && <div className="reader"><Prose text={text} /></div>}
    </div>
  );
}

const SIZE_KEY = 'storymaker.readerSize';
const SIZES = [16, 18, 20, 22];

const readSize = () => {
  try {
    const saved = Number(localStorage.getItem(SIZE_KEY));
    return SIZES.includes(saved) ? saved : 18;
  } catch {
    return 18;
  }
};

export default function Read({ slug, novel }) {
  /**
   * Aprobado es `chapter <= lastApprovedChapter`, no "existe el fichero".
   *
   * Un capítulo escrito que espera en la compuerta ya está en `chapters/`, y contarlo
   * aquí enseñaría como definitivo un texto que todavía puede reescribirse entero.
   */
  const approved = useMemo(
    () => novel.chapters.filter((c) => c.chapter <= (novel.progress.approved ?? 0)),
    [novel.chapters, novel.progress.approved],
  );
  const flagged = useMemo(() => new Set(novel.flagged ?? []), [novel.flagged]);

  const [at, setAt] = useState(0);
  const [text, setText] = useState(null);
  const [error, setError] = useState(null);
  const [size, setSize] = useState(readSize);
  const cache = useRef(new Map());
  const top = useRef(null);

  useEffect(() => { setAt(0); }, [slug]);

  useEffect(() => {
    try { localStorage.setItem(SIZE_KEY, String(size)); } catch { /* sin almacenamiento se pierde */ }
  }, [size]);

  const current = approved[at] ?? null;
  const chapter = current?.chapter ?? null;

  // El texto pedido se guarda: ir y volver entre dos capítulos es el gesto normal aquí,
  // y no tiene sentido releer el disco cada vez que alguien pulsa «anterior».
  useEffect(() => {
    if (chapter === null) { setText(null); return undefined; }
    const key = `${slug}:${chapter}`;
    if (cache.current.has(key)) { setText(cache.current.get(key)); setError(null); return undefined; }

    let alive = true;
    setText(null);
    setError(null);
    getText(slug, chapter)
      .then((d) => { if (alive) { cache.current.set(key, d.text); setText(d.text); } })
      .catch((e) => { if (alive) setError(e.message); });
    return () => { alive = false; };
  }, [slug, chapter]);

  useEffect(() => { top.current?.scrollIntoView({ block: 'nearest' }); }, [chapter]);

  useEffect(() => {
    const onKey = (e) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const tag = document.activeElement?.tagName;
      if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') return;
      if (e.key === 'ArrowLeft') setAt((i) => Math.max(0, i - 1));
      if (e.key === 'ArrowRight') setAt((i) => Math.min(approved.length - 1, i + 1));
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [approved.length]);

  if (!approved.length) {
    const escritos = novel.progress.written ?? 0;
    return (
      <div className="card">
        <p className="empty">
          {escritos > 0
            ? `Esta novela tiene ${escritos} capítulo${escritos > 1 ? 's' : ''} escrito${escritos > 1 ? 's' : ''}, pero ninguno aprobado todavía. Aquí solo se leen los aprobados.`
            : 'Esta novela no tiene capítulos escritos todavía.'}
        </p>
      </div>
    );
  }

  return (
    <div className="read" ref={top}>
      <div className="read-bar">
        <div className="read-nav">
          <button className="btn-secondary" onClick={() => setAt(at - 1)} disabled={at === 0}>
            ← Anterior
          </button>
          <select
            value={at} onChange={(e) => setAt(Number(e.target.value))}
            aria-label="Capítulo" style={{ width: 'auto', minWidth: 190 }}
          >
            {approved.map((c, i) => (
              <option key={c.chapter} value={i}>
                {String(c.chapter).padStart(2, '0')} · {c.title ?? 'sin título'}{flagged.has(c.chapter) ? ' ⚑' : ''}
              </option>
            ))}
          </select>
          <button
            className="btn-secondary"
            onClick={() => setAt(at + 1)}
            disabled={at >= approved.length - 1}
          >
            Siguiente →
          </button>
        </div>

        <span className="spacer" />

        <div className="read-size" role="group" aria-label="Tamaño de letra">
          {SIZES.map((s) => (
            <button
              key={s} className={`chip ${size === s ? 'on' : ''}`}
              aria-pressed={size === s} onClick={() => setSize(s)}
              title={`Cuerpo de ${s} píxeles`}
            >
              <span style={{ fontSize: 9 + (s - SIZES[0]) }}>A</span>
            </button>
          ))}
        </div>
      </div>

      <p className="note read-hint">
        Las flechas ← y → cambian de capítulo. El tema claro u oscuro se elige en la cabecera.
      </p>

      <motion.article
        key={chapter}
        className="card read-card"
        initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.24, ease: [0.2, 0.7, 0.2, 1] }}
      >
        <header className="read-head">
          <div>
            <p className="read-n num">Capítulo {String(chapter).padStart(2, '0')}</p>
            <h3 className="read-title">{current.title ?? <em className="note">sin título en el manuscrito</em>}</h3>
          </div>
          <div className="read-meta">
            {flagged.has(chapter) && (
              <span className="novel-badge flag" title="Marcado durante la corrida: quedó señalado para revisión">
                ⚑ marcado
              </span>
            )}
            <span className="num">{fmt(current.words)} palabras</span>
          </div>
        </header>

        {error && <p className="warn-row">No se pudo leer el capítulo: {error}</p>}

        {!text && !error && (
          <div style={{ marginTop: 'var(--sp-6)' }}>
            <Skeleton h={14} /><Skeleton h={14} style={{ marginTop: 10 }} />
            <Skeleton h={14} w="88%" style={{ marginTop: 10 }} />
          </div>
        )}

        {text && (
          <div className="read-prose" style={{ '--read-size': `${size}px` }}>
            <Prose text={text} />
          </div>
        )}
      </motion.article>

      {novel.manuscript && <Manuscript slug={slug} />}
    </div>
  );
}
