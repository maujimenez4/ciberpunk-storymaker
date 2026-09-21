import { useEffect, useRef, useState } from 'react';
import { getMeta, getState } from './api.js';

/** Las sub-pestañas de una novela. Cualquier otra cosa en la URL cae en la primera. */
const SUBS = ['leer', 'biblia', 'incidencias'];

/**
 * Router de hash. Tres rutas y ninguna dependencia.
 *
 * Es de hash y no de history API porque el servidor sirve el build tal cual: con rutas
 * reales cada recarga profunda dependería de que el fallback del servidor acertara, y
 * esto es un panel local, no una web.
 */
export function useRoute() {
  const read = () => {
    const hash = window.location.hash.replace(/^#\/?/, '');
    const [head, tail, sub] = hash.split('/');
    if (head === 'historial') return { tab: 'historial' };
    if (head === 'novela') {
      const slug = tail ? decodeURIComponent(tail) : null;
      // Sin sub-pestaña en la URL se entra por Leer, que es a lo que se viene.
      return { tab: 'novela', slug, sub: SUBS.includes(sub) ? sub : 'leer' };
    }
    return { tab: 'corrida' };
  };

  const [route, setRoute] = useState(read);
  useEffect(() => {
    const onHash = () => setRoute(read());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  return route;
}

export const go = (path) => { window.location.hash = path; };

/**
 * La última novela abierta.
 *
 * La pestaña Novela necesita un slug y la cabecera no siempre tiene uno a mano: entrar
 * por la pestaña sin haber pasado por Historial tenía que llevar a alguna parte, y la
 * última que se miró es mejor apuesta que la primera del directorio.
 */
const NOVEL_KEY = 'storymaker.novel';
export const rememberNovel = (slug) => {
  try { if (slug) localStorage.setItem(NOVEL_KEY, slug); } catch { /* sin almacenamiento se pierde */ }
};
export const lastNovel = () => {
  try { return localStorage.getItem(NOVEL_KEY); } catch { return null; }
};

/**
 * Lista de novelas y perfiles, y cuál es la que está corriendo.
 *
 * Se refresca en cada tick a propósito: una novela creada después de abrir la página
 * —el caso normal, porque lanzar una corrida crea la suya— tiene que aparecer sola en el
 * desplegable. `pinned` es lo que impide que el seguimiento automático pise una novela
 * que el usuario ha elegido a mano.
 */
export function useMeta(intervalMs = 1000) {
  const [meta, setMeta] = useState({ novels: [], profiles: [], active: null });
  const [novel, setNovel] = useState(null);
  const pinned = useRef(false);

  useEffect(() => {
    let alive = true;
    const pull = async () => {
      try {
        const next = await getMeta();
        if (!alive) return;
        setMeta(next);
        setNovel((current) => {
          if (!pinned.current && next.active) return next.active;
          if (current && next.novels.includes(current)) return current;
          return next.novels[0] ?? null;
        });
      } catch { /* el tick siguiente lo reintenta */ }
    };
    pull();
    const id = setInterval(pull, intervalMs);
    return () => { alive = false; clearInterval(id); };
  }, [intervalMs]);

  return {
    ...meta,
    novel,
    /** Elegir a mano fija la vista: a partir de ahí se deja de seguir a la activa. */
    pick: (slug) => { pinned.current = true; setNovel(slug); },
    /** Lanzar desde el panel devuelve el seguimiento automático a la corrida nueva. */
    follow: (slug) => { pinned.current = false; setNovel(slug); },
  };
}

/**
 * Instantánea de la corrida. El intervalo lo decide quien llama: un segundo mientras se
 * mira el monitor, más espaciado desde las otras pestañas, donde solo alimenta la
 * píldora de estado de la cabecera.
 */
export function useRunState(novel, intervalMs) {
  const [data, setData] = useState(null);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    if (!novel) { setData(null); return undefined; }
    let alive = true;
    const pull = async () => {
      try {
        const next = await getState(novel);
        if (!alive) return;
        setData(next);
        setOffline(false);
      } catch {
        if (alive) setOffline(true);
      }
    };
    pull();
    const id = setInterval(pull, intervalMs);
    return () => { alive = false; clearInterval(id); };
  }, [novel, intervalMs]);

  return { data, offline };
}

/**
 * Cuenta hasta `value` en vez de saltar.
 *
 * Con requestAnimationFrame y no con el motor de animación: es un número, la dependencia
 * no aporta nada aquí, y así el contador no se rompe si la librería cambia de API.
 */
export function useCountUp(value, ms = 420) {
  const [shown, setShown] = useState(value);
  const from = useRef(value);

  useEffect(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const start = from.current;
    if (reduced || start === value) { from.current = value; setShown(value); return undefined; }

    let frame;
    const t0 = performance.now();
    const step = (now) => {
      const p = Math.min(1, (now - t0) / ms);
      const eased = 1 - (1 - p) ** 3;
      setShown(Math.round(start + (value - start) * eased));
      if (p < 1) frame = requestAnimationFrame(step);
      else from.current = value;
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [value, ms]);

  return shown;
}
