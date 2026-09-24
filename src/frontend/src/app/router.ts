/**
 * Las direcciones de la aplicacion. **Dos, y no cinco** (D-06).
 *
 * Cinco URLs eran la forma natural de una aplicacion web y **la forma
 * equivocada de un regalo**: el enlace se comparte por mensajeria, se reenvia y
 * se pega, y cada direccion de mas es una manera de que alguien reciba la
 * pagina tres sin saber que hay una uno.
 *
 * **Y la entrevista no cuelga del token**, por dos motivos independientes: el
 * token nace con la version publicada, asi que mientras el comprador rellena el
 * formulario **no existe**; y si colgara de el, el enlace del regalo llevaria a
 * lo que el comprador escribio sobre el destinatario, incluido lo que pidio que
 * no apareciera. Imposible cuando se usa, indeseable cuando seria posible.
 */
export const RUTAS = {
  /**
   * **Una sola direccion** (D-07, que sustituye a D-06 en su parte de rutas).
   * El token **deja de ser ruta y pasa a ser parametro**: sigue protegiendo la
   * lectura y sigue siendo lo que se manda de regalo, pero abrirlo no lleva a
   * otra pagina, sino a esta con la pestana de leer ya puesta.
   */
  lectura: (token: string) => `/?token=${encodeURIComponent(token)}`,
  entrevista: () => "/",
} as const;

export const PATRONES = {
  pagina: "/",
} as const;

/**
 * Los tres valores de `?vista=`.
 *
 * **Es superficie de inspeccion** —`RF-VAL-08` de la 001 abre estas pantallas
 * desde fuera del repositorio— **y no forma de compartir**: la aplicacion los
 * lee y **nunca** los escribe en un `href`, con un test que cae si algun enlace
 * lo hace. Sin esa mitad, `?vista=` seria una ruta con otro nombre.
 *
 * La alternativa era que el validador pulsara las pestanas, y se descarto: eso
 * lo acopla a los selectores de esta interfaz, y el dia que una etiqueta cambie
 * abriria otra cosa **y seguiria dando verde**.
 */
export const VISTAS = {
  leer: "leer",
  quienEsQuien: "quien-es-quien",
  entrevista: "entrevista",
} as const;

export type Vista = (typeof VISTAS)[keyof typeof VISTAS];

/** La vista pedida, o la de leer: es para lo que se manda el enlace. */
export function vistaDe(busqueda: string): Vista {
  const pedida = new URLSearchParams(busqueda).get("vista");
  return Object.values(VISTAS).find((v) => v === pedida) ?? VISTAS.leer;
}
