import type { components } from "@/shared/api/generated/schema";

export type Evaluacion = components["schemas"]["EvaluacionSalida"];
export type Contradiccion = components["schemas"]["ContradiccionSalida"];

export const API_ENTREVISTA = {
  abrir: () => "/entrevistas",
  responder: (id: number) => `/entrevistas/${id}/respuestas`,
  cerrar: (id: number) => `/entrevistas/${id}/cerrar`,
  /** El Arquitecto: premisa, biblia y los diez capitulos. **Sincrono**: espera
   * a la llamada al modelo, asi que tarda. Sin el, la obra no tiene capitulos
   * y lanzar la novela no escribe nada. */
  outline: (obraId: number) => `/obras/${obraId}/outline`,
  /** `POST` lanza la novela (202, trabajo de fondo); `GET` dice como va. */
  novela: (obraId: number) => `/obras/${obraId}/novela`,
  /** **La unica ruta que devuelve el token**, y por eso cierra el recorrido:
   * hasta que existio, el navegador no tenia forma de saber cuando una novela
   * se podia leer. No faltaba una pantalla, faltaba el dato. */
  publicar: (obraId: number) => `/obras/${obraId}/publicar`,
} as const;

/**
 * Lo que devuelve `GET /obras/{obra_id}/novela`: `total` capitulos del outline,
 * `integrados` ya cerrados, `en_curso` el que se escribe ahora y `motivo` cuando
 * `estado` es `"detenida"`. **Generado** del OpenAPI (`CLAUDE.md` §7): la copia
 * escrita a mano que habia aqui era provisional hasta regenerarlo.
 */
export type EstadoDeLaNovela = components["schemas"]["EstadoDeLaNovela"];

/** Lo que la pantalla manda al responder. **Dos campos, y esa separacion es la
 * defensa**: `texto_aportado` es contenido no confiable y el servidor lo
 * envuelve en su etiqueta (`CLAUDE.md` §11). Si viajara dentro de `respuestas`,
 * entraria en el prompt como instruccion y **no fallaria nada**. */
export interface Respuestas {
  respuestas: Record<string, string>;
  texto_aportado: string;
}
