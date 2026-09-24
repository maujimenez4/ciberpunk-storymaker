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
  it("hay una direccion, y el token es parametro", () => {
    /** D-07: el token deja de ser ruta. Sigue siendo lo que protege la lectura
     * y lo que se manda de regalo; lo que cambia es que abrirlo no lleva a otra
     * pagina. */
    expect(RUTAS.lectura("T")).toBe("/?token=T");
    expect(RUTAS.entrevista()).toBe("/");
  });

  it.each([VISTAS.leer, VISTAS.quienEsQuien])(
    "la vista %s se alcanza sin cambiar de direccion",
    (vista) => {
      abrir(`/?token=T&vista=${vista}`);

      expect(window.location.pathname).toBe("/");
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
    const { container } = abrir(`/?token=T&vista=${VISTAS.quienEsQuien}`);
    const enlaces = [...container.querySelectorAll("a")].map((a) => a.getAttribute("href") ?? "");

    expect(enlaces.filter((h) => h.includes("vista="))).toEqual([]);
  });

  it("la entrevista no necesita token", () => {
    /**
     * Ocurre **antes de que exista novela**, asi que no puede pedir un token
     * que todavia no existe. Lo que protege el brief no es esconderla: es que
     * **ninguna ruta de lectura del backend sirve la entrevista** —comprobado
     * sobre el OpenAPI: las cinco devuelven version, capitulo, ficha, PDF y
     * versiones—. Una separacion de interfaz no es una frontera de seguridad.
     */
    expect(RUTAS.entrevista()).toBe("/");
    expect(RUTAS.entrevista()).not.toContain("token");
  });

  it("una direccion que no existe da pagina legible, no pantalla en blanco", () => {
    abrir("/lo-que-sea");

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/no/i);
  });
});
