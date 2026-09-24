import { createContext, useContext, type ReactNode } from "react";

import { clienteHttp, type Peticionario } from "./cliente";

/**
 * Vive en `shared/` y no en una feature **porque lo usan dos**: la lectura y la
 * entrevista. Las features no se importan entre si (§5.2 regla 2), asi que lo
 * comun baja aqui -- y la primera version de esto lo tenia en `manuscrito`, de
 * donde `entrevista` habria tenido que importarlo.
 *
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
