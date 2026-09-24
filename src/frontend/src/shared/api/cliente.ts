/**
 * El cliente HTTP de la lectura. **Ningun componente hace `fetch`**
 * (`CLAUDE.md` §7): pasa por aqui o por el `api/` de una feature.
 *
 * **No valida la respuesta, y esta declarado.** Los tipos generados del OpenAPI
 * son una promesa de forma, no una comprobacion: si el backend devuelve `null`
 * donde el esquema decia obligatorio, TypeScript se lo cree. Anadir un
 * validador en tiempo de ejecucion es una dependencia nueva, que es pregunta de
 * §3 punto 7, asi que el riesgo queda dicho en vez de disimulado.
 */
export class ErrorDeLectura extends Error {
  constructor(
    readonly estado: number,
    mensaje: string,
  ) {
    super(mensaje);
  }
}

export interface Peticionario {
  pedir<T>(ruta: string): Promise<T>;
  enviar<T>(ruta: string, cuerpo: unknown): Promise<T>;
}

export const BASE = "/api";

export const clienteHttp: Peticionario = {
  async pedir<T>(ruta: string): Promise<T> {
    const respuesta = await fetch(`${BASE}${ruta}`);
    if (!respuesta.ok) {
      throw new ErrorDeLectura(
        respuesta.status,
        respuesta.status === 404
          ? "Este enlace ya no vale."
          : "No se pudo cargar tu novela.",
      );
    }
    return (await respuesta.json()) as T;
  },

  async enviar<T>(ruta: string, cuerpo: unknown): Promise<T> {
    const respuesta = await fetch(`${BASE}${ruta}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(cuerpo),
    });
    if (!respuesta.ok) {
      throw new ErrorDeLectura(respuesta.status, "No se pudo guardar lo que escribiste.");
    }
    return (await respuesta.json()) as T;
  },
};
