import type { ReactNode } from "react";

/**
 * Un párrafo de prosa.
 *
 * **Siempre como texto, nunca interpretado** (R-2, CA-16). React escapa el
 * contenido por defecto; lo que hace falta es **no** deshacerlo: en este
 * fichero no hay `dangerouslySetInnerHTML` y no debe haberlo nunca. La prosa
 * viene de un modelo y pasa por una base de datos: es contenido, no marcado.
 */
export function Texto({ children }: { children: ReactNode }) {
  return <p className="prosa">{children}</p>;
}
