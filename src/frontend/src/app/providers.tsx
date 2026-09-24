import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

/**
 * El estado de servidor vive en TanStack Query; el de interfaz, en el
 * componente (`CLAUDE.md` §7). No hay store global, y no hace falta: esta
 * aplicación **lee** una novela publicada.
 */
export function crearCliente() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // Una versión publicada es inmutable: no hay por qué volver a pedirla
        // al cambiar de pestaña.
        refetchOnWindowFocus: false,
        staleTime: Infinity,
        retry: 1,
      },
    },
  });
}

export function Proveedores({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={crearCliente()}>{children}</QueryClientProvider>;
}
