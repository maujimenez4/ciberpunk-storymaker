import { createContext, useContext, type ReactNode } from "react";

import { clienteHttp, type Peticionario } from "@/shared/api/cliente";

/**
 * Quien habla con la red se **inyecta**, igual que en el backend se inyectan el
 * reloj y el cliente de modelo. Es lo que permite que la suite corra sin
 * levantar nada (`CA-15`) sin una rama «si es prueba» dentro del cliente.
 */
const Contexto = createContext<Peticionario>(clienteHttp);

export function ProveedorDeApi({
  peticionario,
  children,
}: {
  peticionario: Peticionario;
  children: ReactNode;
}) {
  return <Contexto.Provider value={peticionario}>{children}</Contexto.Provider>;
}

export function usePeticionario(): Peticionario {
  return useContext(Contexto);
}
