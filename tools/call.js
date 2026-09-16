// La llamada al modelo. Un nodo del diagrama = una query() aislada.
//
// Aquí viven las dos garantías que el prompt de arranque exige que sean ciertas en la
// implementación y no solo en el prompt del agente:
//
//   1. `tools` se fija desde el frontmatter del agente. Nueve de los diez llevan [] y
//      no reciben ninguna herramienta; solo researcher lleva ['WebSearch']. La
//      documentación del SDK es explícita: `tools` restringe qué herramientas existen;
//      `allowedTools` solo auto-aprueba las que ya existen, que no es lo mismo.
//   2. `settingSources: []` aísla la llamada de los ajustes del sistema de ficheros,
//      para que ningún CLAUDE.md ni settings.json amplíe permisos por la puerta de atrás.

import { query } from '@anthropic-ai/claude-agent-sdk';

const ZERO_USAGE = {
  inputTokens: 0, outputTokens: 0, cacheReadTokens: 0, searches: 0, estimatedUsd: 0,
};

/** Contabilidad de gasto de la corrida entera. */
export class Budget {
  constructor(cfg) {
    this.maxUsd = cfg.budget.maxUsd;
    this.maxTokens = cfg.budget.maxTokens ?? Infinity;
    this.onExceed = cfg.budget.onExceed;
    this.maxUsdPerCall = cfg.budget.maxUsdPerCall ?? null;
    this.usd = 0;
    this.inputTokens = 0;
    this.outputTokens = 0;
    this.cacheReadTokens = 0;
    this.searches = 0;
    this.calls = 0;
  }

  get tokens() { return this.inputTokens + this.outputTokens; }

  /** Lo que queda disponible, que es el tope duro de la siguiente llamada. */
  remainingUsd() { return Math.max(0, this.maxUsd - this.usd); }

  exceeded() { return this.usd >= this.maxUsd || this.tokens >= this.maxTokens; }

  record(usage) {
    this.calls += 1;
    this.usd += usage.estimatedUsd ?? 0;
    this.inputTokens += usage.inputTokens ?? 0;
    this.outputTokens += usage.outputTokens ?? 0;
    this.cacheReadTokens += usage.cacheReadTokens ?? 0;
    this.searches += usage.searches ?? 0;
  }

  summary() {
    return {
      calls: this.calls,
      inputTokens: this.inputTokens,
      outputTokens: this.outputTokens,
      cacheReadTokens: this.cacheReadTokens,
      searches: this.searches,
      estimatedUsd: Number(this.usd.toFixed(4)),
      maxUsd: this.maxUsd,
    };
  }
}

/** Respuesta marcador del modo en seco. No llama a ningún modelo: cuesta cero. */
function dryRunResponse({ agent, mode, envelope }) {
  const label = `[DRY-RUN] ${agent.id}${mode ? `:${mode}` : ''}` +
    (envelope.run.chapter ? ` ch${String(envelope.run.chapter).padStart(2, '0')}` : '');

  if (envelope.output?.format === 'json') {
    return {
      text: JSON.stringify(envelope.output.dryRunValue ?? { dryRun: true, agent: agent.id, issues: [] }),
      usage: { ...ZERO_USAGE }, denials: [], dryRun: true,
    };
  }

  // Salida multi-fichero: el marcador tiene que traer la misma forma que la real,
  // porque comprobar esa forma es una de las cosas para las que existe el modo en seco.
  if (envelope.output?.format === 'files') {
    const text = (envelope.output.files ?? ['canon.md'])
      .map((name) => `<<<FILE: ${name}>>>\n${label} · contenido marcador de ${name}.\n`)
      .join('\n');
    return { text, usage: { ...ZERO_USAGE }, denials: [], dryRun: true };
  }

  // Prosa marcador con la forma correcta: párrafos de verdad, contenido identificable.
  const text = Array.from({ length: 3 }, (_, i) =>
    `${label} · párrafo ${i + 1}. Texto marcador escrito sin llamar a ningún modelo. ` +
    `Sirve para recorrer el bucle y comprobar rutas, contadores, compuerta y commits.`,
  ).join('\n\n');

  return { text, usage: { ...ZERO_USAGE }, denials: [], dryRun: true };
}

/**
 * Ejecuta un nodo del diagrama.
 * @returns {{text: string, usage: object, denials: array, dryRun: boolean}}
 */
export async function callAgent({ agent, mode, systemPrompt, envelope, cfg, budget, root }) {
  if (cfg.execution.dryRun) return dryRunResponse({ agent, mode, envelope });

  const model = cfg.execution.models[agent.id] ?? cfg.execution.models.default;

  // Tope duro por llamada: nunca más de lo que queda de presupuesto de la corrida.
  const remaining = budget.remainingUsd();
  const callCap = budget.maxUsdPerCall
    ? Math.min(remaining, budget.maxUsdPerCall)
    : remaining;
  if (callCap <= 0) throw new Error('Presupuesto agotado antes de la llamada; no se gasta más.');

  const options = {
    // ── Permisos al mínimo ────────────────────────────────────────────────────
    tools: agent.tools,          // [] en nueve de diez; ['WebSearch'] solo en researcher
    disallowedTools: ['Bash', 'Read', 'Write', 'Edit', 'NotebookEdit', 'Task'],
    permissionMode: 'dontAsk',   // deniega lo no pre-aprobado en vez de preguntar
    settingSources: [],          // aislamiento: sin CLAUDE.md ni settings del proyecto
    // ── Comportamiento desde fichero de texto ─────────────────────────────────
    systemPrompt: { type: 'custom', prompt: systemPrompt },
    // ── Gasto ─────────────────────────────────────────────────────────────────
    model,
    maxTurns: 1,                 // sin herramientas no hay bucle agéntico: una respuesta
    maxBudgetUsd: callCap,
    cwd: root,
  };

  if (envelope.output?.format === 'json' && envelope.output?.schema) {
    options.outputFormat = { type: 'json_schema', schema: envelope.output.schema };
  }

  let result = null;
  for await (const message of query({ prompt: envelope.userPrompt, options })) {
    if (message.type === 'result') result = message;
  }

  if (!result) throw new Error(`${agent.id}: la consulta terminó sin resultado`);
  if (result.is_error) {
    throw new Error(`${agent.id}: ${result.subtype} — ${result.result ?? 'sin detalle'}`);
  }

  // modelUsage es el campo correcto para contabilidad; usage excluye llamadas auxiliares.
  const usage = { ...ZERO_USAGE };
  for (const m of Object.values(result.modelUsage ?? {})) {
    usage.inputTokens += m.inputTokens ?? 0;
    usage.outputTokens += m.outputTokens ?? 0;
    usage.cacheReadTokens += m.cacheReadInputTokens ?? 0;
    usage.searches += m.webSearchRequests ?? 0;
  }
  usage.estimatedUsd = result.total_cost_usd ?? 0;

  return {
    // Una denegación de permiso significa que un agente intentó usar algo que no tiene.
    // No es ruido: es la señal de que su prompt y sus permisos no coinciden.
    denials: result.permission_denials ?? [],
    text: envelope.output?.format === 'json' && result.structured_output !== undefined
      ? JSON.stringify(result.structured_output)
      : result.result,
    usage,
    dryRun: false,
  };
}
