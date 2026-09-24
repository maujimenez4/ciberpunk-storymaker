/**
 * Lo medido en la primera corrida real: unos ocho minutos por capitulo. **Es
 * una media, no una promesa**, y por eso la pantalla dice «estimacion» junto a
 * cualquier cifra que salga de aqui.
 */
export const MINUTOS_POR_CAPITULO = 8;

const MINUTO = 60_000;

function minutosDe(ms: number): number {
  return Math.floor(Math.max(ms, 0) / MINUTO);
}

function plural(n: number, singular: string, varios: string): string {
  return `${n} ${n === 1 ? singular : varios}`;
}

/** «24 minutos», «1 hora y 4 minutos», «menos de un minuto»: con la unidad
 * entera, porque va dentro de una frase. Redondeo hacia abajo: decir que lleva
 * un minuto mas de lo que lleva no ayuda a nadie a esperar. */
export function duracionLarga(ms: number): string {
  const minutos = minutosDe(ms);
  if (minutos < 1) return "menos de un minuto";
  const horas = Math.floor(minutos / 60);
  const resto = minutos % 60;
  if (horas === 0) return plural(resto, "minuto", "minutos");
  const enHoras = plural(horas, "hora", "horas");
  return resto === 0 ? enHoras : `${enHoras} y ${plural(resto, "minuto", "minutos")}`;
}

/**
 * Cuanto lleva y cuanto le queda, en **una** frase (maqueta D-Progreso).
 *
 * Con las dos cifras en minutos, la segunda no repite la unidad («hace 24
 * minutos y le quedan unos 56»). Pasada la hora se dice entera y con «cerca
 * de»: «unos 1 hora» no es castellano.
 */
export function frasesDelViaje(transcurrido: number, restante: number): string {
  const lleva = duracionLarga(transcurrido);
  const queda = minutosDe(restante);
  const lequedan =
    queda < 1
      ? "menos de un minuto"
      : queda >= 60
        ? `cerca de ${duracionLarga(restante)}`
        : minutosDe(transcurrido) >= 1 && minutosDe(transcurrido) < 60
          ? `unos ${queda}`
          : `unos ${duracionLarga(restante)}`;
  return `Salió hace ${lleva} y le quedan ${lequedan}.`;
}

/** Lo que falta, contando el capitulo en curso como entero por escribir. */
export function estimacionRestante(total: number, integrados: number): number {
  return Math.max(total - integrados, 0) * MINUTOS_POR_CAPITULO * MINUTO;
}
