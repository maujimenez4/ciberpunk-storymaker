import type { AnchorHTMLAttributes, ReactNode } from "react";

type Props = AnchorHTMLAttributes<HTMLAnchorElement> & {
  href: string;
  children: ReactNode;
};

/** Lleva a otro sitio de la novela. Sin flecha al final: el subrayado ya dice
 * que se puede tocar, y la flecha es el adorno que se quita. */
export function Enlace({ href, children, ...resto }: Props) {
  return (
    <a className="enlace" href={href} {...resto}>
      {children}
    </a>
  );
}
