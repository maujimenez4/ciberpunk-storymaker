import type { components } from "@/shared/api/generated/schema";

export type Evaluacion = components["schemas"]["EvaluacionSalida"];
export type Contradiccion = components["schemas"]["ContradiccionSalida"];

export const API_ENTREVISTA = {
  abrir: () => "/entrevistas",
  responder: (id: number) => `/entrevistas/${id}/respuestas`,
  cerrar: (id: number) => `/entrevistas/${id}/cerrar`,
} as const;

/** Lo que la pantalla manda al responder. **Dos campos, y esa separacion es la
 * defensa**: `texto_aportado` es contenido no confiable y el servidor lo
 * envuelve en su etiqueta (`CLAUDE.md` §11). Si viajara dentro de `respuestas`,
 * entraria en el prompt como instruccion y **no fallaria nada**. */
export interface Respuestas {
  respuestas: Record<string, string>;
  texto_aportado: string;
}
