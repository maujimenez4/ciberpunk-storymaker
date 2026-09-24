import type { Peticionario } from "./cliente";
import { ErrorDeLectura } from "./cliente";

/**
 * El doble de la API. **La suite pasa sin backend levantado** (`CA-15`), y esto
 * es lo que lo hace cierto: la red se sustituye entera, no se intercepta.
 */
export class DobleDeApi implements Peticionario {
  readonly llamadas: string[] = [];

  constructor(
    private readonly respuestas: Record<string, unknown>,
    private readonly opciones: { retraso?: number; fallo?: number } = {},
  ) {}

  async pedir<T>(ruta: string): Promise<T> {
    this.llamadas.push(ruta);
    if (this.opciones.retraso) {
      await new Promise((seguir) => setTimeout(seguir, this.opciones.retraso));
    }
    if (this.opciones.fallo) {
      throw new ErrorDeLectura(this.opciones.fallo, "fallo de prueba");
    }
    const respuesta = this.respuestas[ruta];
    if (respuesta === undefined) {
      throw new ErrorDeLectura(404, "Este enlace ya no vale.");
    }
    return respuesta as T;
  }
}
