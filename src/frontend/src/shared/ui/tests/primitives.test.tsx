/**
 * T4 · Los primitivos y los tokens, comprobados donde se puede comprobar.
 *
 * `RF-ACC-04` exige contraste **AA** y gana sobre cualquier elección estética.
 * Aquí se comprueba con herramienta, no a ojo.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";

import { Aviso, BarraDeProgreso, Boton, Enlace, Pasos, Texto } from "@/shared/ui/primitives";
import { Pagina } from "@/shared/ui/patterns/Pagina";

describe("los primitivos", () => {
  it("el boton es accesible", async () => {
    const { container } = render(<Boton>Seguir leyendo</Boton>);

    expect(await axe(container)).toHaveNoViolations();
    expect(screen.getByRole("button")).toHaveTextContent("Seguir leyendo");
  });

  it.each([
    [undefined, "boton boton--principal"],
    ["principal", "boton boton--principal"],
    ["secundario", "boton boton--secundario"],
    ["discreto", "boton boton--discreto"],
  ] as const)("el boton con variante %s lleva la clase %s", async (variante, clase) => {
    const { container } = render(<Boton variante={variante}>Empezar otra novela</Boton>);

    const boton = screen.getByRole("button", { name: "Empezar otra novela" });
    expect(boton).toHaveAttribute("class", clase);
    expect(boton).toHaveAttribute("type", "button");
    // Sigue siendo un botón de verdad: llega el foco con el teclado.
    boton.focus();
    expect(boton).toHaveFocus();
    expect(await axe(container)).toHaveNoViolations();
  });

  it("un boton deshabilitado no recibe el foco ni el clic, en cualquier variante", async () => {
    const pulsado = vi.fn();
    render(
      <Boton variante="discreto" disabled onClick={pulsado}>
        Publicar la novela
      </Boton>,
    );

    const boton = screen.getByRole("button", { name: "Publicar la novela" });
    expect(boton).toBeDisabled();
    await userEvent.click(boton);
    expect(pulsado).not.toHaveBeenCalled();
    await userEvent.tab();
    expect(boton).not.toHaveFocus();
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

  it("la barra de progreso dice su valor a un lector de pantalla, no solo con color", async () => {
    const { container } = render(
      <BarraDeProgreso
        etiqueta="Capítulos escritos"
        total={10}
        hechos={2}
        enCurso={3}
        textoDelValor="2 de 10 capítulos terminados"
      />,
    );

    const barra = screen.getByRole("progressbar", { name: "Capítulos escritos" });
    expect(barra).toHaveAttribute("aria-valuemin", "0");
    expect(barra).toHaveAttribute("aria-valuemax", "10");
    expect(barra).toHaveAttribute("aria-valuenow", "2");
    expect(barra).toHaveAttribute("aria-valuetext", "2 de 10 capítulos terminados");
    expect(await axe(container)).toHaveNoViolations();
  });

  it("la barra tiene un tramo por unidad: hechos, el que va en curso y pendientes", () => {
    const { container } = render(
      <BarraDeProgreso etiqueta="Capítulos" total={10} hechos={2} enCurso={3} textoDelValor="" />,
    );

    const tramos = [...container.querySelectorAll("[data-tramo]")].map((t) =>
      t.getAttribute("data-tramo"),
    );
    expect(tramos).toEqual([
      "hecho",
      "hecho",
      "en-curso",
      ...Array<string>(7).fill("pendiente"),
    ]);
  });

  it("los pasos marcan el actual con aria-current y dicen con texto cuáles están hechos", async () => {
    const { container } = render(
      <Pasos etiqueta="Cómo va tu novela" pasos={["Entrevista", "Historia", "Capítulos"]} actual={1} />,
    );

    const items = within(screen.getByRole("list", { name: "Cómo va tu novela" })).getAllByRole(
      "listitem",
    );
    expect(items[1]).toHaveAttribute("aria-current", "step");
    expect(items[0]).not.toHaveAttribute("aria-current");
    expect(items[2]).not.toHaveAttribute("aria-current");
    // «Hecho» se dice con texto, no solo con un color o una marca.
    expect(items[0]).toHaveTextContent(/hecho/i);
    expect(items[2]).not.toHaveTextContent(/hecho/i);
    expect(await axe(container)).toHaveNoViolations();
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

  it("las tres variantes del boton tienen estilo, y todo lo que se toca tiene foco visible", () => {
    for (const variante of ["principal", "secundario", "discreto"]) {
      expect(ESTILOS).toMatch(new RegExp(`\\.boton--${variante}\\s*[,{]`));
    }
    // El foco del campo es el anillo ciruela de 3 px (RF-ACC-01), no el del navegador.
    expect(ESTILOS).toMatch(/\.campo__control:focus-visible\s*\{[^}]*outline:\s*3px solid var\(--acento\)/);
    // Los radios siguen la jerarquía y se usan: píldora, campo, bloque.
    for (const radio of ["--radio-pildora", "--radio-campo", "--radio-bloque"]) {
      expect(ESTILOS).toContain(`border-radius: var(${radio})`);
    }
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
