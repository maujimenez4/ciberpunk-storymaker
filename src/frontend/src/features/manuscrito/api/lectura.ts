import { useQueries, useQuery } from "@tanstack/react-query";

import type { Peticionario } from "@/shared/api/cliente";
import type { Capitulo, Ficha, Version } from "@/shared/api/tipos";

import { usePeticionario } from "@/shared/api/contexto";

/** Las rutas del backend, en un sitio y solo uno. */
export const API = {
  version: (t: string) => `/lectura/${t}`,
  capitulo: (t: string, n: number) => `/lectura/${t}/capitulos/${n}`,
  ficha: (t: string) => `/lectura/${t}/ficha`,
  pdf: (t: string) => `/lectura/${t}/pdf`,
} as const;

export function useVersion(token: string) {
  const peticionario = usePeticionario();
  return useQuery({
    queryKey: ["version", token],
    queryFn: () => peticionario.pedir<Version>(API.version(token)),
  });
}

function opcionesDeCapitulo(peticionario: Peticionario, token: string, numero: number) {
  return {
    queryKey: ["capitulo", token, numero],
    queryFn: () => peticionario.pedir<Capitulo & { texto: string }>(API.capitulo(token, numero)),
  };
}

export function useCapitulo(token: string, numero: number) {
  const peticionario = usePeticionario();
  return useQuery(opcionesDeCapitulo(peticionario, token, numero));
}

/**
 * Varios capítulos a la vez, **con la misma clave que `useCapitulo`**: la
 * caché es una, así que pedirlos aquí no repite ninguna petición que la
 * lectura ya haya hecho.
 */
export function useCapitulos(token: string, numeros: readonly number[]) {
  const peticionario = usePeticionario();
  return useQueries({
    queries: numeros.map((numero) => opcionesDeCapitulo(peticionario, token, numero)),
  });
}

export function useFicha(token: string) {
  const peticionario = usePeticionario();
  return useQuery({
    queryKey: ["ficha", token],
    queryFn: () => peticionario.pedir<Ficha>(API.ficha(token)),
  });
}

export type { Capitulo, Ficha, Peticionario, Version };
