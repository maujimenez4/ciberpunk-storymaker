import type { Peticionario } from "./cliente";
import { ErrorDeLectura } from "./cliente";

/**
 * Varias respuestas para la misma ruta, servidas en orden; la última se repite.
 * Es lo que hace falta para probar una consulta periódica: «escribiendo»,
 * «escribiendo», «terminada».
 */
export class Secuencia {
  private siguiente = 0;
  readonly respuestas: readonly unknown[];

  constructor(respuestas: readonly unknown[]) {
    this.respuestas = respuestas;
  }

  servir(): unknown {
    const respuesta = this.respuestas[Math.min(this.siguiente, this.respuestas.length - 1)];
    this.siguiente += 1;
    return respuesta;
  }
}

export function enSecuencia(...respuestas: unknown[]): Secuencia {
  return new Secuencia(respuestas);
}

type Metodo = "GET" | "POST";

/**
 * El doble de la API. **La suite pasa sin backend levantado** (`CA-15`), y esto
 * es lo que lo hace cierto: la red se sustituye entera, no se intercepta.
 *
 * Una clave puede llevar el método delante (`"GET /obras/7/novela"`) cuando la
 * misma ruta significa dos cosas: `POST` lanza la novela y `GET` dice cómo va.
 * Sin método, la ruta sirve a los dos.
 */
export class DobleDeApi implements Peticionario {
  readonly llamadas: string[] = [];
  /** Las mismas llamadas con su método delante, en orden. */
  readonly metodos: string[] = [];
  /** Lo que se envio, en orden. Es lo que permite comprobar **como** viaja un
   * dato y no solo que la pantalla no reviente. */
  readonly cuerpos: unknown[] = [];

  constructor(
    readonly respuestas: Record<string, unknown>,
    private readonly opciones: { retraso?: number; fallo?: number } = {},
  ) {}

  async pedir<T>(ruta: string): Promise<T> {
    return this.responder<T>("GET", ruta);
  }

  async enviar<T>(ruta: string, cuerpo: unknown): Promise<T> {
    this.cuerpos.push(cuerpo);
    return this.responder<T>("POST", ruta);
  }

  private async responder<T>(metodo: Metodo, ruta: string): Promise<T> {
    this.llamadas.push(ruta);
    this.metodos.push(`${metodo} ${ruta}`);
    if (this.opciones.retraso) {
      await new Promise((seguir) => setTimeout(seguir, this.opciones.retraso));
    }
    if (this.opciones.fallo) {
      throw new ErrorDeLectura(this.opciones.fallo, "fallo de prueba");
    }
    const clave = `${metodo} ${ruta}`;
    let respuesta = clave in this.respuestas ? this.respuestas[clave] : this.respuestas[ruta];
    if (respuesta instanceof Secuencia) respuesta = respuesta.servir();
    if (respuesta === undefined) {
      throw new ErrorDeLectura(404, "Este enlace ya no vale.");
    }
    return respuesta as T;
  }
}
