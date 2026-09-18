import { motion, AnimatePresence, LayoutGroup } from 'framer-motion';
import { useMeta, useRunState, useRoute, go } from './hooks.js';
import Run, { runStatus } from './views/Run.jsx';
import History from './views/History.jsx';
import Novel from './views/Novel.jsx';
import Theme from './components/Theme.jsx';

const TABS = [
  { key: 'corrida', label: 'Corrida', path: '/corrida' },
  { key: 'historial', label: 'Historial', path: '/historial' },
];

function Tabs({ active }) {
  return (
    <div className="tabs" role="tablist" aria-label="Secciones">
      <LayoutGroup id="tabs">
        {TABS.map((t) => (
          <button
            key={t.key} role="tab" className="tab"
            aria-selected={active === t.key}
            onClick={() => go(t.path)}
          >
            {t.label}
            {active === t.key && (
              <motion.span
                className="tab-ink" layoutId="tab-ink"
                transition={{ duration: 0.28, ease: [0.2, 0.7, 0.2, 1] }}
              />
            )}
          </button>
        ))}
      </LayoutGroup>
    </div>
  );
}

export default function App() {
  const route = useRoute();
  const meta = useMeta();

  // Un segundo mientras se mira el monitor; cinco desde las otras pestañas, donde este
  // sondeo solo alimenta la píldora de estado de la cabecera. `snapshot()` lee el texto
  // del capítulo cuando hay compuerta abierta, así que el ritmo no es gratis.
  const { data, offline } = useRunState(meta.novel, route.tab === 'corrida' ? 1000 : 5000);
  const status = runStatus(data, offline);

  // La pestaña de una novela concreta es la de historial: se llega a ella desde ahí.
  const activeTab = route.tab === 'novela' ? 'historial' : route.tab;

  return (
    <>
      <header className="top">
        <div className="bar">
          <span className="mark">
            <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
              <rect x="0" y="0" width="8" height="8" fill="#FF7932" />
              <rect x="10" y="10" width="8" height="8" fill="#FF7932" />
            </svg>
            StoryMaker
          </span>

          <Tabs active={activeTab} />

          {route.tab === 'corrida' && (
            <select
              value={meta.novel ?? ''} onChange={(e) => meta.pick(e.target.value || null)}
              style={{ width: 'auto', minWidth: 150 }} aria-label="Novela"
            >
              {meta.novels.length
                ? meta.novels.map((n) => <option key={n} value={n}>{n}</option>)
                : <option value="">sin novelas</option>}
            </select>
          )}

          <span className="spacer" />

          <Theme />

          <span className={`pill ${status.tone}`}>
            <span className="dot" />
            {status.text}
          </span>
        </div>
      </header>

      <main>
        <AnimatePresence mode="wait">
          <motion.div
            key={route.tab === 'novela' ? `novela:${route.slug}` : route.tab}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.24, ease: [0.2, 0.7, 0.2, 1] }}
          >
            {route.tab === 'historial' && <History />}
            {route.tab === 'novela' && <Novel slug={route.slug} />}
            {route.tab === 'corrida' && <Run meta={meta} data={data} offline={offline} />}
          </motion.div>
        </AnimatePresence>
      </main>
    </>
  );
}
