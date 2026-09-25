import { useMutation, useQuery } from "@tanstack/react-query";
import { useRef } from "react";

import { ErrorDeLectura } from "@/shared/api/cliente";
import { usePeticionario } from "@/shared/api/contexto";
import type { EntradaDeFicha } from "@/shared/api/tipos";

/*
 * La petición de cambio y su regeneración, **por el token** (D-01, RNF-SEG-01).
 *
 * **Tipos escritos a mano, y es provisional.** El contrato es el de
 * `specs/001-backend-v1/plan-5-peticion.md` T7–T8 (RI-09): cuerpo
 * `{ hecho_canon_id, texto_pedido }`, respuesta 202 `{ peticion_id, estado }`.
 * Plan 5 T8 lo monta en `/obras/{obra_id}/peticiones`, pero quien lee **solo
 * tiene el token** y el router de lectura no acepta `obra_id` en ninguna ruta:
 * aquí se consume `/lectura/{token}/peticiones`, que es lo que el backend tiene
 * que exponer. Cuando el OpenAPI lo publique, estos tipos se derivan de
 * `schema.d.ts` como los de `shared/api/tipos.ts` y esto se borra.
 */

/** La entrada de la ficha **con su hecho**. El OpenAPI de hoy no lo trae; hasta
 * que lo traiga, la entrada sin `hecho_canon_id` no ofrece corregir. */
export type EntradaCorregible = EntradaDeFicha & {
  hecho_canon_id?: number | null;
  /** P-37: los hechos vivos de la entrada. Cada uno se corrige por su id. */
  hechos?: HechoDeFicha[];
};

/** Un hecho vivo de una entrada de la ficha: lo que el lector puede corregir. */
export type HechoDeFicha = { hecho_canon_id: number; atributo: string; valor: string };

export type PeticionAceptada = { peticion_id: number; estado: string };

export type EstadoDeLaPeticion = "registrada" | "regenerando" | "atendida" | "descartada";

export type CapituloEnRegeneracion = {
  numero: number;
  /** El del backend, tal cual: `pendiente` · `escribiendo` · `hecho`. */
  estado: string;
};

export type Peticion = {
  peticion_id: number;
  estado: EstadoDeLaPeticion;
  /** Por qué no se aplicó, o qué se publicó (RF-PET-06, RF-PET-07 de la 001). */
  resultado: string | null;
  capitulos: CapituloEnRegeneracion[];
  /** El enlace de la tirada nueva: cada versión publicada tiene el suyo. */
  token_resultante: string | null;
};

export type EstadoDeLaLectura = { peticion_en_curso: number | null };

export const API_PETICION = {
  crear: (t: string) => `/lectura/${t}/peticiones`,
  una: (t: string, id: number) => `/lectura/${t}/peticiones/${id}`,
  estado: (t: string) => `/lectura/${t}/estado`,
} as const;

export const TERMINADAS: readonly EstadoDeLaPeticion[] = ["atendida", "descartada"];

/** El hecho que se corrige ya no es el vigente (R-4): lo corrigió otro antes. */
export function esHechoCambiado(error: unknown): boolean {
  return error instanceof ErrorDeLectura && error.estado === 409;
}

/**
 * RF-PET-01. La petición viaja con el `hecho_canon_id` de la entrada, **no con
 * el texto**: el texto dice qué debería poner, el id dice qué se corrige (D-02).
 *
 * R-7: un mismo hecho con el mismo texto **no se reenvía** en esta sesión. El
 * botón deshabilitado tapa el doble clic; esto tapa el reenvío.
 */
export function usePedirCambio(token: string) {
  const peticionario = usePeticionario();
  const enviadas = useRef(new Set<string>());
  const mutacion = useMutation({
    mutationFn: ({ hechoId, texto }: { hechoId: number; texto: string }) =>
      peticionario.enviar<PeticionAceptada>(API_PETICION.crear(token), {
        hecho_canon_id: hechoId,
        texto_pedido: texto,
      }),
  });
  const pedir = (hechoId: number, texto: string, alAceptar?: (peticionId: number) => void) => {
    const clave = `${hechoId}\u0000${texto}`;
    if (mutacion.isPending || enviadas.current.has(clave)) return;
    enviadas.current.add(clave);
    mutacion.mutate(
      { hechoId, texto },
      {
        onError: () => enviadas.current.delete(clave),
        onSuccess: (aceptada) => alAceptar?.(aceptada.peticion_id),
      },
    );
  };
  return { pedir, mutacion };
}

/** Cada cuánto se pregunta, y el tope de la espera (R-3): no cancela nada, solo
 * ofrece salir. La regeneración sigue en el backend, que es donde vive. */
export const SONDEO_MS = 3_000;
export const TOPE_MS = 15 * 60_000;

/** RF-ESP-02. El avance por capítulo, con el dato del backend. */
export function useEstadoDePeticion(token: string, peticionId: number) {
  const peticionario = usePeticionario();
  return useQuery({
    queryKey: ["peticion", token, peticionId],
    queryFn: () => peticionario.pedir<Peticion>(API_PETICION.una(token, peticionId)),
    refetchInterval: (consulta) => {
      const estado = consulta.state.data?.estado;
      return estado && TERMINADAS.includes(estado) ? false : SONDEO_MS;
    },
    // RF-ESP-05: espera creciente, y agotado el intento se ofrece salir.
    retry: 3,
    retryDelay: (intento) => Math.min(1_000 * 2 ** intento, 8_000),
  });
}

/**
 * H-3. ¿Hay una regeneración en curso **que este navegador no pidió**? Quien
 * abrió el enlace en otro teléfono no tiene el id de la petición.
 *
 * Si el backend no lo sabe decir —404, caído— **se degrada a «no»**: no poder
 * saberlo no puede impedir leer.
 */
export function useRegeneracionEnCurso(token: string): number | null {
  const peticionario = usePeticionario();
  const consulta = useQuery({
    queryKey: ["estado-de-lectura", token],
    queryFn: () => peticionario.pedir<EstadoDeLaLectura>(API_PETICION.estado(token)),
    retry: false,
  });
  return consulta.data?.peticion_en_curso ?? null;
}
