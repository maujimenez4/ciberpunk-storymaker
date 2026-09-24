import { useCallback, useMemo } from "react";

const PREFIJO = "posicion:";

/**
 * El `id` de la sección de un capítulo, que es también su fragmento. Un solo
 * sitio: el sumario enlaza a él, el pie de lectura lo mide y este módulo lo
 * lee de la URL.
 */
export function idDeCapitulo(numero: number): string {
  return `capitulo-${numero}`;
}

/**
 * Dónde estabas y dónde te mandaron, que **no son lo mismo**.
 *
 * - El **fragmento** (`#capitulo-7`) es para *compartir un punto a propósito*:
 *   «mira lo que pone en el siete».
 * - La **posición guardada** es para *volver donde estabas* al reabrir el
 *   enlace.
 *
 * Confundirlos es lo que hace que una de las dos salga mal, así que hay una
 * regla de precedencia y es la única decisión de este módulo: **si la URL trae
 * fragmento, manda el fragmento.** Alguien te mandó ese punto adrede y llevarte
 * a otro sitio sería ignorarle.
 *
 * Con `/l/{token}/capitulo/7` esto era gratis; con una sola dirección hay que
 * guardarlo (D-06, coste 1).
 */
export function usePosicion(token: string, capitulos: number[]) {
  const disponibles = useMemo(() => new Set(capitulos), [capitulos]);

  const inicial = useMemo(() => {
    const delFragmento = numeroDeFragmento(window.location.hash);
    if (delFragmento !== null) {
      // Un fragmento que esta novela no tiene —`#capitulo-12` en una de diez—
      // **no se corrige en silencio**: se ignora y manda lo guardado. Saltar al
      // principio sin decir nada sería contarle al lector una posición falsa.
      return disponibles.has(delFragmento) ? delFragmento : guardada(token, disponibles);
    }
    return guardada(token, disponibles);
  }, [token, disponibles]);

  const recordar = useCallback(
    (numero: number) => {
      // `replaceState` y **nunca `pushState`**: con `pushState`, el botón atrás
      // del móvil retrocede capítulo a capítulo y deja de servir para salir de
      // la novela, que es lo único para lo que se usa.
      window.history.replaceState({}, "", `#${idDeCapitulo(numero)}`);
      escribir(`${PREFIJO}${token}`, String(numero));
    },
    [token],
  );

  return { inicial, recordar };
}

function numeroDeFragmento(hash: string): number | null {
  const encontrado = /^#capitulo-(\d+)$/.exec(hash);
  return encontrado?.[1] ? Number(encontrado[1]) : null;
}

function guardada(token: string, disponibles: Set<number>): number | null {
  // La clave lleva el token: un mismo teléfono abre dos novelas, y con una
  // clave global la segunda abriría donde iba la primera.
  const valor = leer(`${PREFIJO}${token}`);
  if (valor === null) {
    return null;
  }
  const numero = Number(valor);
  return Number.isInteger(numero) && disponibles.has(numero) ? numero : null;
}

/**
 * En navegación privada o con el almacenamiento bloqueado, `localStorage`
 * **lanza** en vez de devolver `null`. Sin este envoltorio, la lectura entera
 * se cae por no poder recordar una posición, que es lo accesorio.
 */
function leer(clave: string): string | null {
  try {
    return window.localStorage.getItem(clave);
  } catch {
    return null;
  }
}

function escribir(clave: string, valor: string): void {
  try {
    window.localStorage.setItem(clave, valor);
  } catch {
    // Que no se pueda recordar no puede impedir leer.
  }
}
