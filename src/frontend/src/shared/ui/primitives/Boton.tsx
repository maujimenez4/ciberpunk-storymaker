import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variante = "principal" | "secundario" | "discreto";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  /**
   * Tres pesos, y uno solo principal por pantalla:
   * - `principal`: la acción de la pantalla, rellena de acento.
   * - `secundario`: se ve, pero no compite con la principal (contorno).
   * - `discreto`: una salida, no el siguiente paso («Empezar otra novela»):
   *   solo texto.
   */
  variante?: Variante;
};

/**
 * Un botón hace algo; un enlace lleva a algún sitio. No se disfrazan el uno del
 * otro: quien navega con teclado o lector de pantalla los distingue, y un
 * enlace con aspecto de botón rompe esa expectativa.
 */
export function Boton({ children, type = "button", variante = "principal", ...resto }: Props) {
  return (
    <button className={`boton boton--${variante}`} type={type} {...resto}>
      {children}
    </button>
  );
}
