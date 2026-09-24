/**
 * La novela que se está escribiendo, apuntada en el navegador para que una
 * recarga no la pierda.
 *
 * **Solo lo que hace falta para reanudar**: la obra, hasta dónde llegó la
 * cadena y cuándo empezó. Nada de lo que el comprador escribió: eso ya está en
 * el servidor, y dejarlo en el navegador sería dejarlo donde cualquiera que
 * use el mismo equipo lo puede leer.
 *
 * Es una comodidad de este navegador, no estado de verdad: el estado de la
 * novela lo tiene el servidor y se vuelve a preguntar. Por eso **cada acceso va
 * en try/catch** y un fallo se traga: sin almacenamiento, la página funciona
 * igual y solo pierde la reanudación.
 */

/** `outline`: la entrevista está cerrada y la historia puede no estar hecha.
 * `novela`: la historia está hecha y la novela lanzada o por lanzar. */
export type Fase = "outline" | "novela";

export interface NovelaEnCurso {
  obraId: number;
  fase: Fase;
  /** Cuándo se cerró la entrevista, en milisegundos. */
  desde: number;
}

const CLAVE = "storymaker.novela-en-curso";

function esNovelaEnCurso(valor: unknown): valor is NovelaEnCurso {
  if (typeof valor !== "object" || valor === null) return false;
  const v = valor as Record<string, unknown>;
  return (
    typeof v.obraId === "number" &&
    Number.isInteger(v.obraId) &&
    (v.fase === "outline" || v.fase === "novela") &&
    typeof v.desde === "number"
  );
}

export function leerNovelaEnCurso(): NovelaEnCurso | null {
  try {
    const crudo = window.localStorage.getItem(CLAVE);
    if (crudo === null) return null;
    const valor: unknown = JSON.parse(crudo);
    return esNovelaEnCurso(valor) ? valor : null;
  } catch {
    return null;
  }
}

export function guardarNovelaEnCurso(novela: NovelaEnCurso): void {
  try {
    window.localStorage.setItem(CLAVE, JSON.stringify(novela));
  } catch {
    // Sin almacenamiento no hay reanudación, y es todo lo que se pierde.
  }
}

export function olvidarNovelaEnCurso(): void {
  try {
    window.localStorage.removeItem(CLAVE);
  } catch {
    // Idem: si no se pudo escribir, tampoco hay nada que borrar.
  }
}
