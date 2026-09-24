/**
 * T4 · Los primitivos y los tokens, comprobados donde se puede comprobar.
 *
 * `RF-ACC-04` exige contraste **AA** y gana sobre cualquier elección estética.
 * Aquí se comprueba con herramienta, no a ojo.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { axe } from "vitest-axe";

import { Aviso, Boton, Enlace, Texto } from "@/shared/ui/primitives";
import { Pagina } from "@/shared/ui/patterns/Pagina";

describe("los primitivos", () => {
  it("el boton es accesible", async () => {
    const { container } = render(<Boton>Seguir leyendo</Boton>);

    expect(await axe(container)).toHaveNoViolations();
    expect(screen.getByRole("button")).toHaveTextContent("Seguir leyendo");
  });

  it("el aviso se anuncia a un lector de pantalla", () => {
    render(<Aviso tono="error">No se pudo cargar</Aviso>);

    expect(screen.getByRole("alert")).toHaveTextContent("No se pudo cargar");
  });

  it("el enlace es un enlace, no un boton disfrazado", () => {
    render(<Enlace href="/l/abc/indice">Volver al indice</Enlace>);

    expect(screen.getByRole("link")).toHaveAttribute("href", "/l/abc/indice");
  });

  it("la prosa se muestra como texto, nunca interpretada: R-2, CA-16", () => {
    const veneno = 'Marta dijo: <script>alert("x")</script> y salio de casa.';

    const { container } = render(<Texto>{veneno}</Texto>);

    expect(container.querySelector("script")).toBeNull();
    expect(screen.getByText(/alert\("x"\)/)).toBeInTheDocument();
  });

  it("una pagina entera con los tokens aplicados no tiene violaciones", async () => {
    const { container } = render(
      <Pagina titulo="El verano del 98">
        <Texto>Marta cruzo el patio sin mirar atras.</Texto>
        <Enlace href="/l/abc/capitulo/2">Seguir leyendo</Enlace>
        <Aviso tono="aviso">Esta version se publico ayer.</Aviso>
      </Pagina>,
    );

    expect(await axe(container)).toHaveNoViolations();
  });
});

describe("los tokens", () => {
  it("el foco visible no se apaga: `RF-ACC-02`", () => {
    /**
     * jsdom **no resuelve `:focus-visible`** con `getComputedStyle`: devuelve
     * vacio para cualquier pseudo-clase, asi que la comprobacion del plan
     * pasaria con el foco quitado. Se comprueba sobre la hoja de estilos, que
     * es donde la regla vive de verdad; el foco sobre el navegador real es de
     * T8, con `axe` sobre las paginas.
     */
    expect(ESTILOS).toContain(":focus-visible");
    expect(ESTILOS).not.toMatch(/outline:\s*(none|0)/);
  });

  it("la medida de linea existe y no es el ancho de la pantalla: `RF-ACC-05`", () => {
    expect(ESTILOS).toContain("--medida");
    expect(ESTILOS).toMatch(/max-inline-size:\s*var\(--medida\)/);
  });

  it("los cuatro tokens del plan estan declarados", () => {
    for (const token of ["--tinta", "--papel", "--acento", "--medida"]) {
      expect(ESTILOS).toContain(`${token}:`);
    }
  });
});

/** Bajo jsdom, `import.meta.url` no es una URL `file:`, así que la hoja se lee
 * desde la raíz del paquete, que es donde `vitest` arranca. */
const ESTILOS = readFileSync(join(process.cwd(), "src", "app", "estilos.css"), "utf8");
