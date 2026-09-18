import { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { getHistory } from '../api.js';
import { go } from '../hooks.js';
import { Pill, Progress, Sparkline, Skeleton, Issues, fmt, fecha } from '../components/ui.jsx';

/**
 * Cómo se lee cada estado.
 *
 * `stale` lo deriva el servidor y no lo escribe nadie: una corrida que ni terminó ni
 * espera decisión y lleva una hora sin tocar el disco. Aquí se llama "interrumpida"
 * porque es lo que es, y decirlo evita que alguien la espere para siempre.
 */
export const ESTADOS = {
  done: { tone: 'done', label: 'Terminada' },
  gate: { tone: 'gate', label: 'En compuerta' },
  running: { tone: 'live', label: 'En curso' },
  stale: { tone: 'flag', label: 'Interrumpida' },
  launched: { tone: 'live', label: 'Lanzada' },
  'never-run': { tone: '', label: 'Sin arrancar' },
};

const FILTROS = [
  { key: 'todas', label: 'Todas' },
  { key: 'done', label: 'Terminadas' },
  { key: 'gate', label: 'En compuerta' },
  { key: 'abierta', label: 'Sin terminar' },
];

function Card({ n, i }) {
  const estado = ESTADOS[n.status] ?? { tone: '', label: n.status };
  const planned = n.progress.planned ?? n.progress.written;

  return (
    <motion.article
      className="novel-card"
      layout
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.34, delay: Math.min(i * 0.045, 0.3), ease: [0.2, 0.7, 0.2, 1] }}
      whileHover={{ y: -3 }}
      tabIndex={0}
      role="link"
      onClick={() => go(`/novela/${encodeURIComponent(n.slug)}`)}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(`/novela/${n.slug}`); } }}
    >
      <header className="novel-card-top">
        <div>
          <h3 className="novel-title">{n.title}</h3>
          <p className="novel-slug">
            {n.slug}{n.profile ? <> · <code>{n.profile}</code></> : null}
          </p>
        </div>
        <Pill tone={estado.tone}>
          {estado.label}{n.status === 'gate' ? ` · cap ${n.gateChapter}` : ''}
        </Pill>
      </header>

      <Progress
        value={n.progress.approved} max={planned}
        label={`${n.progress.approved} de ${planned} capítulos aprobados${
          n.progress.written > n.progress.approved ? ` · ${n.progress.written} escritos` : ''}`}
      />

      <Sparkline values={n.tokensByChapter} measured={n.measured} />

      <footer className="novel-card-foot">
        <span><strong className="num">{fmt(n.words)}</strong> palabras</span>
        <Issues counts={n.issues} />
        <span className="novel-when">{fecha(n.touchedAt)}</span>
      </footer>

      <div className="novel-card-meta">
        {n.measured
          ? <span>{fmt(n.calls)} llamadas · {fmt(n.tokens)} tokens</span>
          : <span className="note">sin telemetría (corrida anterior al hook)</span>}
        {n.manuscript && <span className="novel-badge">manuscrito</span>}
        {n.flagged.length > 0 && (
          <span className="novel-badge flag">
            {n.flagged.length} capítulo{n.flagged.length > 1 ? 's' : ''} marcado{n.flagged.length > 1 ? 's' : ''}
          </span>
        )}
      </div>
    </motion.article>
  );
}

export default function History() {
  const [novels, setNovels] = useState(null);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('todas');
  const [q, setQ] = useState('');

  // Se carga al entrar y con el botón, nunca en bucle: recorrer los capítulos de todas
  // las novelas cada segundo sería absurdo, y aquí nada cambia mientras se mira.
  const load = async () => {
    try {
      setError(null);
      setNovels((await getHistory()).novels);
    } catch (e) {
      setError(e.message);
    }
  };
  useEffect(() => { load(); }, []);

  const shown = useMemo(() => {
    if (!novels) return [];
    const needle = q.trim().toLowerCase();
    return novels.filter((n) => {
      const pasaFiltro = filter === 'todas'
        || (filter === 'abierta' ? n.status !== 'done' : n.status === filter);
      const pasaBusqueda = !needle
        || n.title.toLowerCase().includes(needle)
        || n.slug.toLowerCase().includes(needle)
        || (n.profile ?? '').toLowerCase().includes(needle);
      return pasaFiltro && pasaBusqueda;
    });
  }, [novels, filter, q]);

  return (
    <section>
      <div className="head">
        <h2>Historial</h2>
        <p>Todas las novelas que hay en <code>novels/</code>, terminadas o no. Solo lectura.</p>
      </div>

      <div className="history-bar">
        <div className="chips" role="tablist" aria-label="Filtrar por estado">
          {FILTROS.map((f) => (
            <button
              key={f.key} role="tab" aria-selected={filter === f.key}
              className={`chip ${filter === f.key ? 'on' : ''}`}
              onClick={() => setFilter(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>
        <input
          type="search" value={q} onChange={(e) => setQ(e.target.value)}
          placeholder="Buscar por título, slug o perfil" aria-label="Buscar novela"
          className="history-search"
        />
        <button className="btn-secondary" onClick={load}>Refrescar</button>
      </div>

      {error && <div className="card"><p className="warn-row">No se pudo leer el historial: {error}</p></div>}

      {!novels && !error && (
        <div className="novel-grid">
          {[0, 1, 2].map((i) => (
            <div key={i} className="novel-card">
              <Skeleton h={22} w="62%" />
              <Skeleton h={13} w="40%" style={{ marginTop: 10 }} />
              <Skeleton h={6} style={{ marginTop: 22 }} />
              <Skeleton h={13} w="80%" style={{ marginTop: 22 }} />
            </div>
          ))}
        </div>
      )}

      {novels && (
        <motion.div className="novel-grid" layout>
          <AnimatePresence mode="popLayout">
            {shown.map((n, i) => <Card key={n.slug} n={n} i={i} />)}
          </AnimatePresence>
        </motion.div>
      )}

      {novels && !shown.length && (
        <div className="card">
          <p className="empty">
            {novels.length
              ? 'Ninguna novela encaja con el filtro.'
              : 'No hay ninguna novela todavía. Lanza una corrida desde la pestaña Corrida.'}
          </p>
        </div>
      )}
    </section>
  );
}
