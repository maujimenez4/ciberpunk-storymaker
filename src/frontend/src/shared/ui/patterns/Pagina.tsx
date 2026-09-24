import type { ReactNode } from "react";

/**
 * El marco de cualquier página de la novela: la medida de línea y el título.
 *
 * `main` y un solo `h1` por página, que es lo que permite a un lector de
 * pantalla saltar al contenido. La medida la impone `--medida` en CSS
 * (`RF-ACC-05`), no una clase suelta en cada página.
 */
export function Pagina({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <main className="pagina">
      <h1 className="pagina__titulo">{titulo}</h1>
      {children}
    </main>
  );
}
