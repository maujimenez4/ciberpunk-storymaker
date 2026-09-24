/**
 * Plan 3 · T1 · Una dirección, tres vistas.
 *
 * **D-06.** Cinco URLs eran la forma natural de una aplicación web y la forma
 * equivocada de un regalo: el enlace se comparte por mensajería y se reenvía, y
 * cada dirección de más es una manera de que alguien reciba la página tres sin
 * saber que hay una uno.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Aplicacion } from "@/app/Aplicacion";
import { RUTAS, VISTAS, vistaDe } from "@/app/router";

function abrir(ruta: string) {
  window.history.pushState({}, "", ruta);
  return render(<Aplicacion />);
}

describe("una sola direccion", () => {
  it("la lectura es una ruta y ninguna vista anade otra", () => {
    expect(RUTAS.lectura("T")).toBe("/l/T");
    expect(Object.keys(RUTAS)).toEqual(["lectura", "entrevista"]);
  });

  it.each([VISTAS.leer, VISTAS.quienEsQuien])(
    "la vista %s se alcanza sin cambiar de ruta",
    (vista) => {
      /**
       * Las **de la lectura** son dos. La tercera pantalla —la entrevista— no
       * es una pestaña de aquí: es del comprador y ocurre antes de que exista
       * novela, así que tiene su propia dirección.
       */
      abrir(`/l/T?vista=${vista}`);

      expect(window.location.pathname).toBe("/l/T");
      expect(screen.getByRole("tab", { selected: true })).toBeInTheDocument();
    },
  );

  it("sin `?vista=` se abre leyendo, que es para lo que se manda el enlace", () => {
    expect(vistaDe("")).toBe(VISTAS.leer);
  });

  it("una vista inventada cae en leer y no en una pantalla vacia", () => {
    expect(vistaDe("?vista=loquesea")).toBe(VISTAS.leer);
  });

  it("la aplicacion no escribe `?vista=` en ningun enlace", () => {
    /**
     * Sin este test, `?vista=` **es una ruta con otro nombre**: en cuanto un
     * `href` lo escriba, alguien lo comparte y vuelve el problema que D-06
     * quita. Es superficie de inspección para `RF-VAL-08`, no forma de
     * compartir.
     */
    const { container } = abrir(`/l/T?vista=${VISTAS.quienEsQuien}`);
    const enlaces = [...container.querySelectorAll("a")].map((a) => a.getAttribute("href") ?? "");

    expect(enlaces.filter((h) => h.includes("vista="))).toEqual([]);
  });

  it("la entrevista no cuelga del token", () => {
    /**
     * D-06 corregida: el token nace con la versión publicada y la entrevista
     * ocurre **antes de que exista novela**. Bajo el token sería imposible
     * cuando se usa, e indeseable cuando sería posible — el enlace del regalo
     * llevaría al formulario donde está lo que el comprador pidió que **no**
     * apareciera.
     */
    expect(RUTAS.entrevista()).toBe("/");
    expect(RUTAS.entrevista()).not.toContain("l/");
  });

  it("una direccion que no existe da pagina legible, no pantalla en blanco", () => {
    abrir("/l/T/lo-que-sea");

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/no/i);
  });
});
