import type { ButtonHTMLAttributes, ReactNode } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & { children: ReactNode };

/**
 * Un botón hace algo; un enlace lleva a algún sitio. No se disfrazan el uno del
 * otro: quien navega con teclado o lector de pantalla los distingue, y un
 * enlace con aspecto de botón rompe esa expectativa.
 */
export function Boton({ children, type = "button", ...resto }: Props) {
  return (
    <button className="boton" type={type} {...resto}>
      {children}
    </button>
  );
}
