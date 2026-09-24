import type { components } from "./generated/schema";

/**
 * Los tipos de la lectura, **derivados del OpenAPI** y nunca escritos a mano
 * (`CLAUDE.md` §7). Si el backend renombra un campo, esto deja de compilar en
 * vez de fallar en el navegador tres componentes mas alla.
 */
export type Version = components["schemas"]["VersionPublicada"];
export type Capitulo = components["schemas"]["CapituloPublicado"];
export type Ficha = components["schemas"]["FichaDeLectura"];
export type EntradaDeFicha = components["schemas"]["EntradaDeFicha"];
