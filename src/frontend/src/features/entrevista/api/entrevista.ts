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
 * Lo que devuelve `GET /obras/{obra_id}/novela`.
 *
 * **Escrito a mano, y a proposito provisional**: el modelo del backend es
 * `EstadoDeLaNovela` (`src/backend/app/features/escritura/`) y se estaba
 * construyendo a la vez que esta pantalla, contra este mismo contrato. Cuando
 * se regenere `openapi.json`, esto pasa a ser
 * `components["schemas"]["EstadoDeLaNovela"]` (`CLAUDE.md` §7).
 */
export interface EstadoDeLaNovela {
  obra_id: number;
  /** Capitulos del outline. */
  total: number;
  /** Capitulos ya integrados. */
  integrados: number;
  /** El capitulo que se esta escribiendo ahora, si hay uno. */
  en_curso: number | null;
  estado: "sin_outline" | "escribiendo" | "terminada" | "detenida";
  /** Por que se detuvo, cuando `estado` es `"detenida"`. */
  motivo: string | null;
}

/** Lo que la pantalla manda al responder. **Dos campos, y esa separacion es la
 * defensa**: `texto_aportado` es contenido no confiable y el servidor lo
 * envuelve en su etiqueta (`CLAUDE.md` §11). Si viajara dentro de `respuestas`,
 * entraria en el prompt como instruccion y **no fallaria nada**. */
export interface Respuestas {
  respuestas: Record<string, string>;
  texto_aportado: string;
}
