/**
 * T3 · Las cinco rutas, y que no se muevan.
 *
 * **Este test parece tonto y no lo es.** Congela un contrato que vive **fuera de
 * este repositorio**: `RF-VAL-08` de la spec 001 abre estas URLs. Cambiar
 * `/indice` por `/contenidos` no rompería nada aquí y dejaría al validador
 * visual comprobando una página de error con cara de éxito.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Aplicacion } from "@/app/Aplicacion";
import { RUTAS } from "@/app/router";

function abrir(ruta: string) {
  window.history.pushState({}, "", ruta);
  return render(<Aplicacion />);
}

describe("las rutas son estables", () => {
  it("son exactamente las que el validador visual del backend abre", () => {
    expect(RUTAS.portada("T")).toBe("/l/T");
    expect(RUTAS.indice("T")).toBe("/l/T/indice");
    expect(RUTAS.capitulo("T", 4)).toBe("/l/T/capitulo/4");
    expect(RUTAS.ficha("T")).toBe("/l/T/ficha");
    expect(RUTAS.novedades("T")).toBe("/l/T/novedades");
  });
});

describe("las cinco rutas responden", () => {
  /**
   * `CA-21` pide que **las cinco respondan**, y eso incluye la de novedades,
   * que esta fase declara que no hace. Una ruta registrada que pinta en blanco
   * cumpliría el criterio sin que nadie vea nada: es el modo de fallo por vacío
   * que este proyecto lleva persiguiendo todo el día. Se comprueba que cada una
   * dice algo legible.
   */
  it.each([
    ["la portada", RUTAS.portada("T")],
    ["el indice", RUTAS.indice("T")],
    ["un capitulo", RUTAS.capitulo("T", 4)],
    ["la ficha", RUTAS.ficha("T")],
    ["las novedades", RUTAS.novedades("T")],
  ])("%s pinta un encabezado con texto", (_nombre, ruta) => {
    abrir(ruta);

    expect(screen.getByRole("heading", { level: 1 }).textContent).not.toBe("");
  });

  it("una ruta que no existe da pagina legible, no pantalla en blanco", () => {
    abrir("/l/T/lo-que-sea");

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/no/i);
  });

  it("las novedades de una primera version dicen que no hay ninguna", () => {
    /**
     * No es un andamio: es el **estado vacío** del producto y es permanente.
     * `RF-IND-03` dice que en la primera versión publicada no hay marca de
     * cambio porque no hay anterior con la que comparar, así que esta página
     * seguirá diciendo esto mismo cuando la Fase 3 la llene.
     */
    abrir(RUTAS.novedades("T"));

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/novedades/i);
    expect(screen.getByText(/primera versión/i)).toBeInTheDocument();
  });
});
