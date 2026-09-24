/**
 * Cuánto se ha leído y cuánto queda: la aritmética del pie de lectura.
 *
 * Funciones puras, sin DOM: el componente mide y estas cuentan. Así la cuenta
 * se prueba con números y no con un navegador fingido.
 */

/** Velocidad de lectura en silencio de un adulto, en palabras por minuto. */
export const PALABRAS_POR_MINUTO = 230;

export function contarPalabras(texto: string): number {
  const limpio = texto.trim();
  return limpio === "" ? 0 : limpio.split(/\s+/).length;
}

/**
 * Minutos que quedan del capítulo, **redondeados hacia arriba**: con una sola
 * palabra por leer queda un minuto, no cero, porque decir «terminaste» con
 * texto por delante sería mentir.
 */
export function minutosQueQuedan(palabras: number, fraccionLeida: number): number {
  const quedan = palabras * (1 - acotar(fraccionLeida));
  // El redondeo se hace sobre palabras enteras: la resta en coma flotante deja
  // restos como 1e-13 que, hacia arriba, serían un minuto fantasma.
  return Math.ceil(Math.round(quedan) / PALABRAS_POR_MINUTO);
}

/**
 * Porcentaje de la novela leído, **pesado por palabras** y no por capítulos:
 * un capítulo de 1.500 palabras pesa más que uno de 1.000.
 *
 * Redondea hacia abajo: no dice 100 % hasta que no queda nada.
 */
export function porcentajeLeido(
  palabrasPorCapitulo: readonly number[],
  indiceActual: number,
  fraccion: number,
): number {
  const total = palabrasPorCapitulo.reduce((suma, p) => suma + p, 0);
  if (total === 0) {
    return 0;
  }
  const anteriores = palabrasPorCapitulo.slice(0, indiceActual).reduce((suma, p) => suma + p, 0);
  const leidas = anteriores + (palabrasPorCapitulo[indiceActual] ?? 0) * acotar(fraccion);
  return leidas >= total ? 100 : Math.floor((leidas / total) * 100);
}

export type Medida = { numero: number; arriba: number; alto: number };

/**
 * En qué capítulo está quien lee y qué parte lleva, a partir de dónde está
 * cada capítulo respecto a la pantalla (`arriba` relativo a su borde
 * superior, como `getBoundingClientRect`).
 *
 * - **El capítulo en curso** es el último cuyo principio ya pasó la mitad de
 *   la pantalla: con el título del siguiente asomando abajo, todavía se está
 *   leyendo el anterior.
 * - **Lo leído** llega hasta el borde inferior de la pantalla: lo que se ve ya
 *   está al alcance del ojo.
 * - Un capítulo sin alto (sin pintar todavía) no cuenta: dividir por cero
 *   daría un porcentaje que no significa nada.
 */
export function ubicar(
  capitulos: readonly Medida[],
  altoPantalla: number,
): { numero: number; fraccion: number } | null {
  const primero = capitulos[0];
  if (!primero) {
    return null;
  }
  let actual: Medida | null = null;
  for (const capitulo of capitulos) {
    if (capitulo.alto > 0 && capitulo.arriba <= altoPantalla / 2) {
      actual = capitulo;
    }
  }
  if (!actual) {
    return { numero: primero.numero, fraccion: 0 };
  }
  return {
    numero: actual.numero,
    fraccion: acotar((altoPantalla - actual.arriba) / actual.alto),
  };
}

function acotar(fraccion: number): number {
  return Math.min(1, Math.max(0, fraccion));
}
