/**
 * Las cinco rutas de la lectura.
 *
 * **Viven aquí y en un solo sitio.** `RUTAS` las construye para que ninguna
 * página escriba una cadena a mano: una URL repetida en cinco componentes se
 * desincroniza en cuanto alguien toca una.
 *
 * Y no se mueven. `RF-VAL-08` de la spec 001 abre estas URLs desde **fuera de
 * este repositorio**: renombrar `/indice` no rompería nada aquí y dejaría al
 * validador visual comprobando una página de error con cara de éxito.
 */
export const RUTAS = {
  portada: (t: string) => `/l/${t}`,
  indice: (t: string) => `/l/${t}/indice`,
  capitulo: (t: string, n: number) => `/l/${t}/capitulo/${n}`,
  ficha: (t: string) => `/l/${t}/ficha`,
  novedades: (t: string) => `/l/${t}/novedades`,
} as const;

/** Los patrones que registra el router, en el orden en que se declaran. */
export const PATRONES = {
  portada: "/l/:token",
  indice: "/l/:token/indice",
  capitulo: "/l/:token/capitulo/:numero",
  ficha: "/l/:token/ficha",
  novedades: "/l/:token/novedades",
} as const;
