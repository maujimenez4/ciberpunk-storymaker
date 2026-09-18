import { motion } from 'framer-motion';
import { useCountUp } from '../hooks.js';

/* Piezas pequeñas y sin estado propio. Lo que tenga lógica vive en su vista. */

export const fmt = (n) => (typeof n === 'number' ? n.toLocaleString('es') : '—');

export const hhmm = (iso) => {
  try { return new Date(iso).toTimeString().slice(0, 8); } catch { return ''; }
};

export const fecha = (iso) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString('es', { day: 'numeric', month: 'short', year: 'numeric' });
  } catch { return '—'; }
};

export function Pill({ tone = '', children }) {
  return (
    <span className={`pill ${tone}`}>
      <span className="dot" />
      {children}
    </span>
  );
}

/** Tile del monitor. El valor cuenta en vez de saltar; el denominador no se anima. */
export function Tile({ k, value, of, s, count = true }) {
  const shown = useCountUp(count && typeof value === 'number' ? value : 0);
  const body = count && typeof value === 'number' ? fmt(shown) : value;
  return (
    <div className="tile">
      <div className="k">{k}</div>
      <div className="v num">
        {body}
        {of !== undefined && of !== null && <span className="of">/{of}</span>}
      </div>
      <div className="s">{s}</div>
    </div>
  );
}

export function Progress({ value, max, label }) {
  const pct = max > 0 ? Math.min(100, (100 * value) / max) : 0;
  return (
    <div>
      {label && <div className="note" style={{ marginBottom: 4 }}>{label}</div>}
      <div className="bar-track" role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={max}>
        <motion.div
          className="bar-fill"
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.5, ease: [0.2, 0.7, 0.2, 1] }}
        />
      </div>
    </div>
  );
}

/**
 * Tokens por capítulo, una barra por capítulo.
 *
 * Deliberadamente sin ejes ni números: aquí solo importa si una corrida gastó parejo o
 * si hubo un capítulo que se disparó. Para la cifra exacta está el detalle.
 *
 * Con menos de dos capítulos medidos no se dibujan barras: una corrida a la que el hook
 * solo llegó a ver el último capítulo pintaba dos rayas planas y un bloque, que se lee
 * como un gráfico roto y no como lo que es, telemetría incompleta.
 *
 * Pero el hueco se conserva y se explica, en vez de desaparecer. Sin él las tarjetas de
 * una misma fila enseñaban un rectángulo vacío que parecía un estado de carga.
 */
export function Sparkline({ values, measured = true, label = 'Tokens por capítulo' }) {
  const max = Math.max(...values, 1);
  const enough = measured && values.filter((v) => v > 0).length >= 2;

  return (
    <div className="spark-wrap">
      {enough ? (
        <div className="spark" aria-hidden="true">
          {values.map((v, i) => (
            <motion.span
              key={i}
              className="spark-bar"
              initial={{ height: '2%' }}
              animate={{ height: `${Math.max(3, (100 * v) / max)}%` }}
              transition={{ duration: 0.45, delay: i * 0.04, ease: [0.2, 0.7, 0.2, 1] }}
            />
          ))}
        </div>
      ) : (
        <div className="spark spark-empty" aria-hidden="true" />
      )}
      <span className="spark-caption">
        {enough ? label : 'sin desglose por capítulo'}
      </span>
    </div>
  );
}

export function Skeleton({ h = 16, w = '100%', style }) {
  return <div className="sk" style={{ height: h, width: w, ...style }} />;
}

/** Contadores de incidencias. Un cero no se pinta: el ruido tapa lo que sí importa. */
export function Issues({ counts, empty = 'sin incidencias' }) {
  const shown = [
    ['blocker', counts.blocker, 'var(--blocker)'],
    ['warning', counts.warning, 'var(--warn)'],
    ['note', counts.note, 'var(--fg-faint)'],
  ].filter(([, n]) => n > 0);

  if (!shown.length) return <span className="note">{empty}</span>;
  return (
    <span className="issue-row">
      {shown.map(([kind, n, color]) => (
        <span key={kind} className="issue-chip" style={{ color }}>
          <strong className="num">{n}</strong> {kind}
        </span>
      ))}
    </span>
  );
}

/**
 * Trozos de `código` dentro de una línea.
 *
 * Los resúmenes de la biblia citan el canon entre comillas invertidas
 * (`threads.md#dilema-de-la-firma`) y en crudo se leían mal: la comilla de cierre se monta
 * sobre la letra anterior y "certificado`" acaba pareciendo "certificadò".
 */
export function Inline({ text }) {
  return (
    <>
      {String(text ?? '').split(/(`[^`]+`)/g).map((part, i) => (
        part.startsWith('`') && part.endsWith('`') && part.length > 2
          ? <code key={i}>{part.slice(1, -1)}</code>
          : <span key={i}>{part}</span>
      ))}
    </>
  );
}

/** Markdown mínimo: párrafos. Basta, porque lo que se enseña aquí es prosa de novela. */
export function Prose({ text }) {
  const body = (text ?? '').replace(/^---[\s\S]*?\n---\n/, '').trim();
  return (
    <div className="prose">
      {body.split(/\n\n+/).map((p) => p.trim()).filter(Boolean).map((p, i) => (
        /^#{1,6}\s/.test(p)
          ? <h4 key={i}>{p.replace(/^#{1,6}\s+/, '')}</h4>
          : <p key={i}>{p}</p>
      ))}
    </div>
  );
}
