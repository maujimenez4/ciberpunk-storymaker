/**
 * Lo medido en la primera corrida real: unos ocho minutos por capitulo. **Es
 * una media, no una promesa**, y por eso la pantalla dice «estimacion» junto a
 * cualquier cifra que salga de aqui.
 */
export const MINUTOS_POR_CAPITULO = 8;

const MINUTO = 60_000;

/** «12 min», «1 h 4 min», «menos de un minuto». Redondeo hacia abajo: decir que
 * lleva un minuto mas de lo que lleva no ayuda a nadie a esperar. */
export function duracion(ms: number): string {
  const minutos = Math.floor(Math.max(ms, 0) / MINUTO);
  if (minutos < 1) return "menos de un minuto";
  const horas = Math.floor(minutos / 60);
  const resto = minutos % 60;
  if (horas === 0) return `${resto} min`;
  return resto === 0 ? `${horas} h` : `${horas} h ${resto} min`;
}

/** Lo que falta, contando el capitulo en curso como entero por escribir. */
export function estimacionRestante(total: number, integrados: number): number {
  return Math.max(total - integrados, 0) * MINUTOS_POR_CAPITULO * MINUTO;
}
