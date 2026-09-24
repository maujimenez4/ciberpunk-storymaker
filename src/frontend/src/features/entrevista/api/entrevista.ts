import type { components } from "@/shared/api/generated/schema";

export type Evaluacion = components["schemas"]["EvaluacionSalida"];
export type Contradiccion = components["schemas"]["ContradiccionSalida"];

export const API_ENTREVISTA = {
  abrir: () => "/entrevistas",
  responder: (id: number) => `/entrevistas/${id}/respuestas`,
  cerrar: (id: number) => `/entrevistas/${id}/cerrar`,
  novela: (obraId: number) => `/obras/${obraId}/novela`,
  /** **La unica ruta que devuelve el token**, y por eso cierra el recorrido:
   * hasta que existio, el navegador no tenia forma de saber cuando una novela
   * se podia leer. No faltaba una pantalla, faltaba el dato. */
  publicar: (obraId: number) => `/obras/${obraId}/publicar`,
} as const;

/** Lo que la pantalla manda al responder. **Dos campos, y esa separacion es la
 * defensa**: `texto_aportado` es contenido no confiable y el servidor lo
 * envuelve en su etiqueta (`CLAUDE.md` §11). Si viajara dentro de `respuestas`,
 * entraria en el prompt como instruccion y **no fallaria nada**. */
export interface Respuestas {
  respuestas: Record<string, string>;
  texto_aportado: string;
}
