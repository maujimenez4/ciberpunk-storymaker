import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { startRun, decideGate } from '../api.js';
import { Tile, Pill, Prose, Inline, fmt, hhmm } from '../components/ui.jsx';

const CHAPTER_NODES = ['LOAD', 'BEAT', 'GAP', 'RES1', 'WRITE', 'VOICE', 'VAL', 'REPORT', 'BLOCK', 'GATE', 'COMMIT'];
const SETUP_NODES = ['RES0', 'ARCH', 'PROF', 'SEED'];
const END_NODES = ['COMP', 'EXPORT', 'DONE'];

const SEV = { blocker: 'blocker', warning: 'warn', note: 'faint' };

/** El estado que enseña la píldora de la cabecera. Lo consume `App`. */
export function runStatus(data, offline) {
  if (offline) return { tone: '', text: 'Sin conexión con el panel' };
  if (!data) return { tone: '', text: 'Cargando' };
  if (data.empty) return { tone: '', text: 'Sin novelas' };
  if (data.missing) {
    return data.launched
      ? { tone: 'live', text: 'Lanzada, sin estado aún' }
      : { tone: '', text: 'Sin corrida' };
  }
  if (data.gate) return { tone: 'gate', text: `Compuerta · capítulo ${data.gate.chapter}` };
  if (data.state.phase === 'done') return { tone: 'done', text: 'Terminada' };
  const flagged = (data.state.flagged ?? []).length > 0;
  return { tone: flagged ? 'flag' : 'live', text: `En curso · ${data.state.node}` };
}

/* ---------------------------------------------------------------- Arranque */

function Start({ meta, data }) {
  const [brief, setBrief] = useState('');
  const [profile, setProfile] = useState('');
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!profile && meta.profiles.length) setProfile(meta.profiles[0]);
  }, [meta.profiles, profile]);

  const launch = async () => {
    if (busy) return;
    setBusy(true);
    setMsg({ text: 'Lanzando…' });
    try {
      const result = await startRun({ profile, brief });
      if (result.ok) {
        setMsg({ text: `Corrida lanzada sobre ${result.slug}. El monitor la sigue desde aquí.` });
        meta.follow(result.slug);
      } else {
        setMsg({ text: result.error, bad: true });
      }
    } catch (error) {
      setMsg({ text: error.message, bad: true });
    } finally {
      setBusy(false);
    }
  };

  return (
    <section>
      <div className="head">
        <h2>Arranque</h2>
        <p>Escribe el brief y lanza el bucle. El brief es la única entrada: premisa, personajes, tono y restricciones.</p>
      </div>
      <div className="card">
        <div className="two">
          <div>
            <label htmlFor="brief">Brief de la novela</label>
            <textarea
              id="brief" spellCheck={false} value={brief}
              onChange={(e) => setBrief(e.target.value)}
              placeholder={'# Título\n\n## Premisa\n…\n\n## Protagonista\n…\n\n## Tono y registro\n…\n\n## Restricciones\n…'}
            />
            <p className="note" style={{ marginTop: 8 }}>
              Si lo dejas vacío se conserva el <code>brief.md</code> que ya exista.
            </p>
            <BriefOnDisk data={data} />
          </div>
          <div className="grid">
            <div>
              <label htmlFor="profile">Perfil</label>
              <select id="profile" value={profile} onChange={(e) => setProfile(e.target.value)}>
                {meta.profiles.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            {data?.scope && (
              <div className="tile">
                <div className="k">Alcance</div>
                <div className="s">
                  {data.scope.chapters} capítulos · {data.scope.acts} acto{data.scope.acts > 1 ? 's' : ''} ·{' '}
                  {data.scope.wordsPerChapter} palabras por capítulo
                </div>
              </div>
            )}
            <div>
              <button
                className="btn-primary" style={{ width: '100%' }}
                disabled={busy || Boolean(data?.lock?.alive)} onClick={launch}
              >
                Iniciar corrida
              </button>
              {data?.lock?.alive && (
                <p className="note" style={{ marginTop: 10 }}>
                  Hay una corrida viva sobre <strong>{data.novel}</strong> (PID{' '}
                  {data.lock.childPid ?? data.lock.pid}). Dos corridas sobre la misma novela
                  se pisan la biblia y los capítulos.
                </p>
              )}
              <AnimatePresence>
                {msg && (
                  <motion.p
                    className={`note ${msg.bad ? 'warn-row' : ''}`} style={{ marginTop: 10 }}
                    initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                  >
                    {msg.text}
                  </motion.p>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/**
 * Enseña el brief que hay en disco. Un brief de una línea suele significar que se pegó
 * un resumen en vez del documento, y eso condiciona la novela entera: aquí se ve antes
 * de gastar la corrida, no después.
 */
function BriefOnDisk({ data }) {
  if (!data) return null;
  const b = data.brief;
  if (!b) {
    return (
      <div className="tile" style={{ marginTop: 'var(--sp-3)' }}>
        <div className="k">Brief en disco</div>
        <div className="s" style={{ color: 'var(--warn)' }}>
          No hay ninguno. Sin brief el bucle para en el arranque.
        </div>
      </div>
    );
  }
  return (
    <div className="tile" style={{ marginTop: 'var(--sp-3)' }}>
      <div className="k">Brief en disco · {data.novel}</div>
      <div className="v num" style={{ fontSize: 20 }}>
        {b.words} <span style={{ fontSize: 13, fontWeight: 400, color: 'var(--fg-muted)' }}>palabras</span>
      </div>
      <div className="s">
        {b.sections.length ? `Secciones: ${b.sections.join(' · ')}` : 'Sin secciones (##)'}
      </div>
      {b.sections.length < 3 && (
        <div className="s" style={{ color: 'var(--warn)', marginTop: 6 }}>
          Parece un resumen, no un brief. Un brief lleva premisa, protagonista, antagonismo,
          mundo, tono y restricciones en secciones.
        </div>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------- Compuerta */

function Gate({ data }) {
  const [notes, setNotes] = useState('');
  const [to, setTo] = useState(1);
  const [msg, setMsg] = useState(null);
  const g = data?.gate;
  if (!g) return null;

  const why = { 'act-end': 'Fin de acto', flagged: 'Capítulo marcado', 'every-chapter': 'Cada capítulo' };
  const issues = g.issues?.issues ?? [];

  // presentUnit: `act` enseña el acto entero; si no, solo el capítulo que se juzga.
  const units = g.presentUnit === 'act' && g.act?.length
    ? g.act.filter((c) => c.text)
    : [{ chapter: g.chapter, text: g.chapterText }];

  const decide = async (action) => {
    setMsg({ text: 'Enviando…' });
    try {
      const result = await decideGate({
        profile: data.state?.profile, action, notes, rollbackTo: Number(to),
      });
      setMsg(result.ok
        ? { text: `Decisión ${result.action} sobre el capítulo ${result.chapter}. La corrida se ha relanzado.` }
        : { text: result.error, bad: true });
      if (result.ok) setNotes('');
    } catch (error) {
      setMsg({ text: error.message, bad: true });
    }
  };

  return (
    <motion.section initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
      <div className="head">
        <h2>Compuerta</h2>
        <p>La corrida paró aquí y espera tu decisión. El estado está en disco: al decidir se relanza y continúa.</p>
      </div>
      <div className="card gate-card">
        <div className="gate-top">
          <span className="eyebrow">Capítulo {g.chapter} · {why[g.reason] ?? g.reason}</span>
          {g.flagged && <Pill>Marcado</Pill>}
        </div>

        {issues.length ? (
          <table className="data">
            <thead>
              <tr><th>id</th><th>Severidad</th><th>Dónde</th><th>Qué</th></tr>
            </thead>
            <tbody>
              {issues.map((i, n) => (
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
        ) : <p className="note" style={{ color: '#8FA5B4' }}>Ninguna incidencia abierta.</p>}

        <div className="gate-prose">
          {units.map((u) => (
            <div key={u.chapter}>
              <h4 className="gate-chapter-head">Capítulo {u.chapter}</h4>
              <Prose text={u.text} />
            </div>
          ))}
        </div>

        <div className="gate-actions">
          <div className="grid" style={{ flex: '1 1 260px' }}>
            <div>
              <label htmlFor="gateNotes">Notas para revisar (obligatorias si eliges revisar)</label>
              <textarea
                id="gateNotes" style={{ minHeight: 92 }} value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Qué no funciona y qué habría que cambiar."
              />
            </div>
          </div>
          <div className="grid" style={{ flex: '0 0 auto', alignContent: 'start' }}>
            <button className="btn-primary" onClick={() => decide('approve')}>Aprobar</button>
            <button className="btn-ghost" onClick={() => decide('revise')}>Revisar con notas</button>
            <div style={{ display: 'flex', gap: 'var(--sp-2)', alignItems: 'center' }}>
              <button className="btn-ghost" style={{ flex: 1 }} onClick={() => decide('rollback')}>Rollback a</button>
              <input
                type="number" min={1} max={Math.max(1, g.chapter - 1)} value={to}
                onChange={(e) => setTo(e.target.value)} style={{ width: 66 }}
                aria-label="Capítulo de rollback"
              />
            </div>
          </div>
        </div>
        {msg && (
          <p className="note" style={{ color: msg.bad ? '#E8705F' : '#C7D2D9' }}>{msg.text}</p>
        )}
      </div>
    </motion.section>
  );
}

/* ---------------------------------------------------------------- Monitor */

function Tiles({ data }) {
  const s = data.state;
  const lim = s.limits ?? {};
  const c = s.counters ?? {};
  const phase = s.phase === 'chapter-loop' ? 'Capítulos' : s.phase === 'setup' ? 'Setup' : 'Terminada';
  return (
    <div className="tiles">
      <Tile k="Fase" value={phase} s={`nodo ${s.node}`} count={false} />
      <Tile k="Capítulo" value={s.chapter} of={data.scope?.chapters ?? '—'} s={`aprobados: ${s.lastApprovedChapter}`} />
      <Tile k="Reescrituras" value={c.rewrites ?? 0} of={lim.maxRewrites ?? '—'} s="por blocker" />
      <Tile k="Investigación" value={c.researchRounds ?? 0} of={lim.maxResearchRounds ?? '—'} s="rondas" />
      <Tile
        k="Llamadas" value={data.totals.calls}
        s={data.totals.tokens ? `${(data.totals.tokens / 1000).toFixed(0)}k tokens` : 'sin tokens registrados'}
      />
    </div>
  );
}

/** Matriz capítulo × nodo. Una fila por capítulo hace visible que esto es un bucle. */
function Matrix({ data }) {
  const s = data.state;
  const chapters = data.scope?.chapters ?? Math.max(s.chapter, s.lastApprovedChapter, 1);
  const flagged = new Set(s.flagged ?? []);

  const visited = {};
  for (const row of data.timeline) {
    const key = row.phase === 'chapter-loop' ? `ch${row.chapter}` : 'setup';
    (visited[key] ??= new Set()).add(row.node);
  }

  // `active` significa "trabajando ahora mismo", y una corrida terminada no trabaja.
  //
  // Antes la última condición era `scope === 'end' && s.phase === 'done'`, que es justo
  // al revés: pintaba EXPORT en naranja latiendo **porque** la corrida había acabado. El
  // resultado era una novela con la píldora en "Terminada" y la matriz pareciendo que
  // seguía exportando, y no había forma de saber cuál de las dos decía la verdad.
  const running = s.phase !== 'done';
  const isActive = (scope, node) => running && s.node === node && (
    (scope === 'setup' && s.phase === 'setup')
    || (scope === `ch${s.chapter}` && s.phase === 'chapter-loop')
  );

  const cell = (scope, node, chapterDone) => {
    const done = chapterDone || visited[scope]?.has(node);
    const cls = ['cell'];
    if (isActive(scope, node)) cls.push('active');
    else if (done) cls.push('done');
    if (scope.startsWith('ch') && flagged.has(Number(scope.slice(2)))) cls.push('flagged');
    return <td key={node}><span className={cls.join(' ')}>{node}</span></td>;
  };

  const width = Math.max(CHAPTER_NODES.length, SETUP_NODES.length, END_NODES.length);
  const pad = (n) => Array.from({ length: width - n }, (_, i) => <td key={`pad${i}`} />);

  return (
    <div className="matrix">
      <table>
        <thead>
          <tr>
            <th className="row">Fase</th>
            {CHAPTER_NODES.map((n) => <th key={n}>{n}</th>)}
          </tr>
        </thead>
        <tbody>
          <tr>
            <td className="row">Setup</td>
            {SETUP_NODES.map((n) => cell('setup', n, s.lastApprovedChapter > 0 || s.phase !== 'setup'))}
            {pad(SETUP_NODES.length)}
          </tr>
          {Array.from({ length: chapters }, (_, i) => i + 1).map((i) => (
            <tr key={i}>
              <td className="row">Capítulo {i}{flagged.has(i) ? ' ·' : ''}</td>
              {CHAPTER_NODES.map((n) => cell(`ch${i}`, n, i <= s.lastApprovedChapter))}
            </tr>
          ))}
          <tr>
            <td className="row">Cierre</td>
            {/* DONE no es un paso del bucle: en el diagrama es el artefacto final
                (`manuscript.md`). Por eso `novela.md` acaba en EXPORT y nunca escribe
                `node: "DONE"`. Se marca cumplido si el manuscrito existe de verdad. */}
            {END_NODES.map((n) => cell('end', n, n === 'DONE'
              ? Boolean(data.manuscript)
              : s.phase === 'done'))}
            {pad(END_NODES.length)}
          </tr>
        </tbody>
      </table>
    </div>
  );
}

/* ---------------------------------------------------------------- Resumen */

function Agents({ data }) {
  if (!data.agents.length) {
    return <p className="empty">Ninguna llamada registrada todavía.</p>;
  }
  const max = Math.max(...data.agents.map((a) => a.calls));
  return (
    <>
      <table className="data">
        <thead>
          <tr><th>Agente</th><th className="r">Llamadas</th><th className="r">Tokens</th><th>Nodos</th></tr>
        </thead>
        <tbody>
          {data.agents.map((a) => (
            <tr key={a.agent}>
              <td>
                <span style={{ fontWeight: 500 }}>{a.agent}</span>
                <div className="bar-track">
                  <motion.div
                    className="bar-fill"
                    initial={{ width: 0 }} animate={{ width: `${(100 * a.calls) / max}%` }}
                    transition={{ duration: 0.5, ease: [0.2, 0.7, 0.2, 1] }}
                  />
                </div>
              </td>
              <td className="r num">{a.calls}</td>
              <td className="r num">{a.tokens ? fmt(a.tokens) : '—'}</td>
              <td style={{ color: 'var(--fg-muted)', fontSize: 13 }}>
                {Object.entries(a.nodes).map(([n, c]) => (c > 1 ? `${n}×${c}` : n)).join(', ')}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="note" style={{ marginTop: 'var(--sp-4)' }}>
        {data.derived
          ? 'Deducido del recorrido de nodos: esta corrida es anterior al hook de trazado, así que no hay tokens por llamada. Las corridas nuevas los traen.'
          : <>Medido por el hook <code>PostToolUse</code>, una línea por subagente en <code>agent-calls.jsonl</code>.</>}
      </p>
    </>
  );
}

function Timeline({ data }) {
  if (!data.timeline.length) return <p className="empty">Sin recorrido registrado.</p>;
  const rows = [...data.timeline].reverse().slice(0, 18);
  return (
    <ul className="timeline">
      <AnimatePresence initial={false}>
        {rows.map((r, i) => {
          const detail = r.phase === 'chapter-loop' ? `capítulo ${r.chapter}` : r.phase === 'done' ? 'cierre' : 'setup';
          const c = r.counters ?? {};
          const extra = c.rewrites ? ` · reescritura ${c.rewrites}` : c.researchRounds ? ` · ronda ${c.researchRounds}` : '';
          return (
            <motion.li
              key={`${r.ts}-${r.node}-${i}`} layout
              initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }}
              transition={{ duration: 0.22 }}
            >
              <span className="t">{hhmm(r.ts)}</span>
              <span className="n">{r.node}</span>
              <span className="d">{detail + extra}</span>
            </motion.li>
          );
        })}
      </AnimatePresence>
    </ul>
  );
}

/* ---------------------------------------------------------------- Vista */

export default function Run({ meta, data, offline }) {
  const missing = !data || data.empty || data.missing;

  return (
    <>
      <Start meta={meta} data={data} />
      <Gate data={data} />

      <section>
        <div className="head">
          <h2>Monitor</h2>
          <p>Se actualiza solo cada segundo. Una fila por capítulo, porque esto es un bucle.</p>
        </div>

        {missing ? (
          <div className="card">
            <p className="empty">
              {offline
                ? 'Sin conexión con el panel. ¿Sigue vivo el proceso de tools/dashboard.mjs?'
                : data?.launched
                  ? 'Corrida lanzada. Esperando a que el bucle escriba run-state.json. Si la salida del proceso sigue vacía al cabo de un minuto, algo falló al arrancar.'
                  : 'Esta novela no tiene run-state.json. Lanza una corrida para empezar.'}
            </p>
          </div>
        ) : (
          <>
            <Tiles data={data} />
            <div className="card" style={{ marginTop: 'var(--sp-4)' }}>
              <Matrix data={data} />
              <p className="note" style={{ marginTop: 'var(--sp-4)' }}>
                <span className="eyebrow" style={{ fontSize: 11 }}>Leyenda</span>
                {'  '}naranja, nodo en curso · sólido, recorrido · tenue, pendiente · borde rojo, capítulo marcado
              </p>
              {data.state.phase === 'done' && (
                <p className="note" style={{ marginTop: 'var(--sp-2)' }}>
                  {data.manuscript
                    ? <>Corrida terminada. El manuscrito está en <code>out/manuscript.md</code>.</>
                    : <span className="warn-row">
                        La corrida se dio por terminada pero no hay <code>out/manuscript.md</code>:
                        COMP no llegó a producirlo. Revisa la salida del proceso.
                      </span>}
                </p>
              )}
            </div>
          </>
        )}
      </section>

      <section>
        <div className="head">
          <h2>Resumen</h2>
          <p>Cuántas llamadas hizo cada agente y qué pasó en cada nodo.</p>
        </div>
        <div className="two">
          <div className="card">
            <h3 style={{ marginBottom: 'var(--sp-4)' }}>Llamadas por agente</h3>
            {missing ? <p className="empty">Sin corrida.</p> : <Agents data={data} />}
          </div>
          <div className="grid">
            <div className="card">
              <h3 style={{ marginBottom: 'var(--sp-3)' }}>Recorrido</h3>
              {missing ? <p className="empty">Sin corrida.</p> : <Timeline data={data} />}
            </div>
            <div className="card">
              <h3 style={{ marginBottom: 'var(--sp-3)' }}>Salida del proceso</h3>
              <pre className="console">{data?.consoleTail || 'Sin corrida lanzada desde este panel.'}</pre>
              {(data?.errors ?? []).length > 0 && (
                <div className="errors">
                  <strong>Trazado a Langfuse con errores:</strong>
                  {data.errors.map((e, i) => <div key={i}><code>{e}</code></div>)}
                </div>
              )}
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
