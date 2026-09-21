// Constructores de OTLP HTTP/JSON. Sin dependencias, a propósito.
//
// Langfuse v4 ingiere por OTLP y ofrece un SDK que hace este mapeo solo. No se usa: el
// hook arranca un proceso nuevo **después de cada subagente**, y meter ahí el bootstrap
// del SDK de OpenTelemetry son cientos de milisegundos por llamada más un flush en el
// cierre —el patrón que ya provocó el aborto de libuv documentado en trace-langfuse.mjs—.
// Con `fetch` no hay flush que perder: se espera el POST y se acabó.
//
// El precio es montar el sobre a mano, que es verboso y se equivoca en silencio. Por eso
// todo lo de aquí es puro y sin efectos: lo cubren los tests de tests/hooks/.

import { createHash } from 'node:crypto';

export const OTLP_PATH = '/api/public/otel/v1/traces';

/** OTel exige ids hex de longitud fija: 32 caracteres la traza, 16 el span. */
export const hexId = (seed, bytes) =>
  createHash('sha256').update(String(seed)).digest('hex').slice(0, bytes * 2);

export const traceIdOf = (runId, label) => hexId(`${runId}:${label}`, 16);
export const spanIdOf = (seed) => hexId(seed, 8);
/** La raíz de una traza es derivable desde la traza: los hijos pueden apuntarla sin verla. */
export const rootSpanIdOf = (traceId) => spanIdOf(`${traceId}:root`);

/** OTLP mide en nanosegundos desde epoch, y los quiere como string. */
export const nanos = (ms) => String(BigInt(Math.round(ms)) * 1000000n);

function attrValue(value) {
  if (typeof value === 'boolean') return { boolValue: value };
  if (typeof value === 'number') {
    return Number.isInteger(value) ? { intValue: String(value) } : { doubleValue: value };
  }
  return { stringValue: String(value) };
}

/** Un mapa plano a la lista de atributos de OTLP. Descarta null y undefined. */
export function attributes(map) {
  return Object.entries(map)
    .filter(([, value]) => value !== null && value !== undefined)
    .map(([key, value]) => ({ key, value: attrValue(value) }));
}

/**
 * Un span. `startMs`/`endMs` en milisegundos epoch; si no hay duración fiable, se pasan
 * iguales y se deja constancia en un atributo, porque un cero disfrazado de dato real es
 * peor que un cero declarado.
 */
export function span({ traceId, spanId, parentSpanId, name, startMs, endMs, attrs = {}, error = null }) {
  const out = {
    traceId,
    spanId,
    name,
    kind: 1, // INTERNAL
    startTimeUnixNano: nanos(startMs),
    endTimeUnixNano: nanos(endMs),
    attributes: attributes(attrs),
    status: error ? { code: 2, message: String(error).slice(0, 300) } : { code: 0 },
  };
  if (parentSpanId) out.parentSpanId = parentSpanId;
  return out;
}

export function envelope(spans) {
  return {
    resourceSpans: [{
      resource: { attributes: attributes({ 'service.name': 'storymaker' }) },
      scopeSpans: [{ scope: { name: 'storymaker/trace-langfuse', version: '2' }, spans }],
    }],
  };
}

/**
 * Envía y devuelve qué pasó. No lanza: quien llama decide, y en el hook la decisión es
 * siempre anotar y seguir.
 */
export async function postSpans({ host, authHeader, spans, timeoutMs = 5000 }) {
  try {
    const response = await fetch(`${host}${OTLP_PATH}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: authHeader,
        'x-langfuse-ingestion-version': '4',
      },
      body: JSON.stringify(envelope(spans)),
      signal: AbortSignal.timeout(timeoutMs),
    });
    return { ok: response.ok, status: response.status, body: (await response.text()).slice(0, 600) };
  } catch (error) {
    return { ok: false, status: 0, body: `fallo de red: ${error.message}` };
  }
}
