import type { ButtonHTMLAttributes, ReactNode } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  /** `secundario` para la acción que no es la de la pantalla: se ve, pero no
   * compite con la principal. */
  variante?: "principal" | "secundario";
};

/**
 * Un botón hace algo; un enlace lleva a algún sitio. No se disfrazan el uno del
 * otro: quien navega con teclado o lector de pantalla los distingue, y un
 * enlace con aspecto de botón rompe esa expectativa.
 */
export function Boton({ children, type = "button", variante = "principal", ...resto }: Props) {
  return (
    <button
      className={variante === "secundario" ? "boton boton--secundario" : "boton"}
      type={type}
      {...resto}
    >
      {children}
    </button>
  );
}
