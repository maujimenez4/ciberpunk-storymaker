/**
 * Los ajustes de lectura: tamaño de letra, interlineado y tema.
 *
 * **Son comodidad de quien lee, no dato del dominio** (RD-01, RD-03): viven en
 * este navegador, no llevan token ni nada del destinatario, y nunca viajan al
 * backend. Una sola clave para todas las novelas, a propósito: quien lee de
 * noche con letra grande quiere lo mismo en la segunda novela que abra.
 */

export const TAMANOS = [
  { valor: "pequeno", etiqueta: "Pequeño", cuerpo: "1rem" },
  { valor: "normal", etiqueta: "Normal", cuerpo: "1.125rem" },
  { valor: "grande", etiqueta: "Grande", cuerpo: "1.25rem" },
  { valor: "muy-grande", etiqueta: "Muy grande", cuerpo: "1.4rem" },
] as const;

export const INTERLINEADOS = [
  { valor: "junto", etiqueta: "Junto", ritmo: "1.5" },
  { valor: "normal", etiqueta: "Normal", ritmo: "1.7" },
  { valor: "amplio", etiqueta: "Amplio", ritmo: "1.9" },
] as const;

/**
 * Tres temas y **ninguno sigue al sistema**: decisión de maujimenez4 del
 * 2026-09-24 («solo que usa el modo claro, no el modo oscuro»). Hubo un
 * `automatico` que quitaba el atributo; quien lo tenga guardado cae a Papel
 * porque ya no es un valor conocido.
 */
export const TEMAS = [
  { valor: "papel", etiqueta: "Papel" },
  { valor: "sepia", etiqueta: "Sepia" },
  { valor: "noche", etiqueta: "Noche" },
] as const;

export type Tamano = (typeof TAMANOS)[number]["valor"];
export type Interlineado = (typeof INTERLINEADOS)[number]["valor"];
export type Tema = (typeof TEMAS)[number]["valor"];

export type Ajustes = { tamano: Tamano; interlineado: Interlineado; tema: Tema };

export const POR_DEFECTO: Ajustes = { tamano: "normal", interlineado: "normal", tema: "papel" };

const CLAVE = "lectura:ajustes";

/**
 * Lo guardado, **validado campo a campo**. Lo que hay en `localStorage` lo puede
 * haber escrito cualquiera; un valor que no es de los conocidos cae a su
 * defecto en vez de llegar a un atributo o a una variable CSS.
 */
export function leerAjustes(): Ajustes {
  let crudo: unknown;
  try {
    const texto = window.localStorage.getItem(CLAVE);
    crudo = texto === null ? null : JSON.parse(texto);
  } catch {
    // Navegación privada: `getItem` **lanza**. O JSON roto. Se lee igual.
    return POR_DEFECTO;
  }
  if (typeof crudo !== "object" || crudo === null) {
    return POR_DEFECTO;
  }
  const guardado = crudo as Record<string, unknown>;
  return {
    tamano: uno(TAMANOS, guardado.tamano) ?? POR_DEFECTO.tamano,
    interlineado: uno(INTERLINEADOS, guardado.interlineado) ?? POR_DEFECTO.interlineado,
    tema: uno(TEMAS, guardado.tema) ?? POR_DEFECTO.tema,
  };
}

export function guardarAjustes(ajustes: Ajustes): void {
  try {
    window.localStorage.setItem(CLAVE, JSON.stringify(ajustes));
  } catch {
    // Que no se pueda recordar no puede impedir leer.
  }
}

/**
 * Los ajustes, sobre `<html>`. El paso normal **quita** la variable en vez de
 * escribir su valor: así manda la hoja de estilos, que es quien sabe el
 * tamaño por defecto (y puede cambiarlo por ancho de pantalla).
 */
export function aplicarAjustes(ajustes: Ajustes, raiz: HTMLElement = document.documentElement): void {
  const tamano = TAMANOS.find((t) => t.valor === ajustes.tamano);
  const interlineado = INTERLINEADOS.find((i) => i.valor === ajustes.interlineado);

  poner(raiz, "--cuerpo", ajustes.tamano === POR_DEFECTO.tamano ? null : (tamano?.cuerpo ?? null));
  poner(
    raiz,
    "--ritmo",
    ajustes.interlineado === POR_DEFECTO.interlineado ? null : (interlineado?.ritmo ?? null),
  );

  raiz.setAttribute("data-tema", ajustes.tema);
}

function poner(raiz: HTMLElement, variable: string, valor: string | null): void {
  if (valor === null) {
    raiz.style.removeProperty(variable);
  } else {
    raiz.style.setProperty(variable, valor);
  }
}

function uno<T extends string>(opciones: readonly { valor: T }[], valor: unknown): T | null {
  return opciones.find((o) => o.valor === valor)?.valor ?? null;
}
