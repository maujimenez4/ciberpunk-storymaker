import { useEffect, useState } from 'react';
import { motion, LayoutGroup } from 'framer-motion';

/**
 * Selector de tema.
 *
 * El CSS ya traía `:root[data-theme="dark"]` y `[data-theme="light"]` desde la versión de
 * un solo fichero, pero nadie ponía nunca ese atributo: eran reglas muertas y el tema lo
 * decidía el sistema y solo el sistema. Esto las pone a funcionar.
 *
 * `auto` no escribe el atributo, así que vuelve a mandar la media query del sistema.
 */
const MODES = [
  { key: 'auto', label: 'Auto', title: 'Seguir al sistema' },
  { key: 'light', label: 'Claro', title: 'Forzar tema claro' },
  { key: 'dark', label: 'Oscuro', title: 'Forzar tema oscuro' },
];

const KEY = 'storymaker.theme';

export function applyTheme(mode) {
  if (mode === 'auto') document.documentElement.removeAttribute('data-theme');
  else document.documentElement.setAttribute('data-theme', mode);
}

/** Lee la preferencia antes del primer pintado, para no enseñar un parpadeo de tema. */
export function readTheme() {
  try {
    const saved = localStorage.getItem(KEY);
    return MODES.some((m) => m.key === saved) ? saved : 'auto';
  } catch {
    return 'auto';
  }
}

export default function Theme() {
  const [mode, setMode] = useState(readTheme);

  useEffect(() => {
    applyTheme(mode);
    try { localStorage.setItem(KEY, mode); } catch { /* sin almacenamiento se pierde */ }
  }, [mode]);

  return (
    <div className="theme" role="group" aria-label="Tema">
      <LayoutGroup id="theme">
        {MODES.map((m) => (
          <button
            key={m.key} className="theme-btn" title={m.title}
            aria-pressed={mode === m.key} onClick={() => setMode(m.key)}
          >
            {mode === m.key && (
              <motion.span
                className="theme-on" layoutId="theme-on"
                transition={{ duration: 0.26, ease: [0.2, 0.7, 0.2, 1] }}
              />
            )}
            <span className="theme-label">{m.label}</span>
          </button>
        ))}
      </LayoutGroup>
    </div>
  );
}
