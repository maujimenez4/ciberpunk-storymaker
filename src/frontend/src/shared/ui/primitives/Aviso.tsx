import type { ReactNode } from "react";

type Tono = "aviso" | "error";

/**
 * Lo que la interfaz tiene que decir cuando algo no salió como se esperaba.
 *
 * `role="alert"` para que un lector de pantalla lo anuncie sin que haya que ir
 * a buscarlo. Un error dice **qué pasó y qué hacer**, en la voz de la interfaz:
 * no se disculpa y no es vago.
 */
export function Aviso({ tono = "aviso", children }: { tono?: Tono; children: ReactNode }) {
  return (
    <p className={tono === "error" ? "aviso aviso--error" : "aviso"} role="alert">
      {children}
    </p>
  );
}
