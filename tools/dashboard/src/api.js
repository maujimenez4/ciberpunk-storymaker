// Los ocho endpoints del panel, en un sitio. Nada de fetch suelto en las vistas: cuando
// el servidor cambie un contrato, que haya un único fichero que ajustar.

async function get(path, params) {
  const url = params ? `${path}?${new URLSearchParams(params)}` : path;
  const response = await fetch(url);
  if (!response.ok) {
    // El servidor contesta JSON también en los errores; si no, el status ya dice bastante.
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.error ?? `HTTP ${response.status}`);
  }
  return response.json();
}

async function post(path, body) {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return response.json();
}

export const getMeta = () => get('/api/meta');
export const getState = (novel) => get('/api/state', { novel });

export const getHistory = () => get('/api/history');
export const getNovel = (slug) => get('/api/history/novel', { slug });
export const getText = (slug, chapter) => get('/api/history/text', { slug, chapter });

// La biblia entera en una respuesta: los anclajes se citan entre ficheros y seguir uno
// no debería costar una petición.
export const getBible = (slug) => get('/api/novel/bible', { slug });

export const startRun = (body) => post('/api/run', body);
export const decideGate = (body) => post('/api/gate', body);
