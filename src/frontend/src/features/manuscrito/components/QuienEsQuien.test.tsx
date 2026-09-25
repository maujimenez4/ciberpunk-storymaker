/**
 * Plan 4 · enmienda 1 · «Quién viaja contigo».
 *
 * Cada entrada revelada es una etiqueta de equipaje. Lo no revelado **no llega
 * al navegador** (D-04, RF-FIC-04): la ficha no trae ni cuántas faltan, así
 * que la etiqueta de las pendientes no puede dar un número sin inventarlo.
 * Todos los nombres son **inventados** (RD-04).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { ProveedorDeApi } from "@/shared/api/contexto";
import { DobleDeApi } from "@/shared/api/doble";

import { QuienEsQuien } from "./QuienEsQuien";

function conFicha(entradas: unknown[]) {
  const doble = new DobleDeApi({ "/lectura/T/ficha": { entradas } });
  return function Envoltorio({ children }: { children: ReactNode }) {
    const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return (
      <QueryClientProvider client={cliente}>
        <ProveedorDeApi peticionario={doble}>{children}</ProveedorDeApi>
      </QueryClientProvider>
    );
  };
}

const DOS = [
  { nombre: "Olvido", tipo: "personaje", descripcion: "Colecciona llaves sin cerradura.", capitulos: [1, 2, 3] },
  { nombre: "El faro viejo", tipo: "lugar", descripcion: "Nadie sube desde el invierno.", capitulos: [2] },
];

describe("quién viaja contigo", () => {
  it("se presenta como viaje, y dice que aparecen al leer", async () => {
    render(<QuienEsQuien token="T" />, { wrapper: conFicha(DOS) });

    expect(await screen.findByRole("heading", { name: "Quién viaja contigo" })).toBeInTheDocument();
    expect(screen.getByText("Aparecen a medida que lees.")).toBeInTheDocument();
  });

  it("cada entrada revelada es una etiqueta con su nombre, su descripción y sus capítulos", async () => {
    render(<QuienEsQuien token="T" />, { wrapper: conFicha(DOS) });

    const olvido = (await screen.findByRole("heading", { name: "Olvido" })).closest(".etiqueta");
    expect(olvido).not.toBeNull();
    const etiqueta = within(olvido as HTMLElement);
    expect(etiqueta.getByText("Colecciona llaves sin cerradura.")).toBeInTheDocument();
    expect(olvido?.querySelector(".etiqueta__capitulos")).toHaveTextContent(/^Capítulos 1, 2 y 3$/);

    const faro = screen.getByRole("heading", { name: "El faro viejo" }).closest(".etiqueta");
    expect(faro?.querySelector(".etiqueta__capitulos")).toHaveTextContent(/^Capítulo 2$/);
  });

  it("el agujero de la etiqueta es adorno", async () => {
    const { container } = render(<QuienEsQuien token="T" />, { wrapper: conFicha(DOS) });
    await screen.findByRole("heading", { name: "Olvido" });

    const ojales = container.querySelectorAll(".etiqueta__ojal");
    expect(ojales).toHaveLength(2);
    ojales.forEach((o) => expect(o).toHaveAttribute("aria-hidden", "true"));
  });

  it("con quien lo abre, cada capítulo lleva a su sitio en la lectura", async () => {
    // RF-FIC-02: la entrada enlaza a los capítulos. Cambiar de pestaña es de
    // la página, así que se pide por fuera.
    const irA = vi.fn();
    render(<QuienEsQuien token="T" onIrACapitulo={irA} />, { wrapper: conFicha(DOS) });

    const olvido = (await screen.findByRole("heading", { name: "Olvido" })).closest(".etiqueta");
    const enlace = within(olvido as HTMLElement).getByRole("link", { name: "Capítulo 2" });
    expect(enlace).toHaveAttribute("href", "#capitulo-2");
    fireEvent.click(enlace);
    expect(irA).toHaveBeenCalledWith(2);
  });

  it("la etiqueta de las pendientes no inventa un número que la ficha no trae", async () => {
    const { container } = render(<QuienEsQuien token="T" />, { wrapper: conFicha(DOS) });
    await screen.findByRole("heading", { name: "Olvido" });

    const pendiente = container.querySelector(".etiqueta--pendiente");
    expect(pendiente).not.toBeNull();
    expect(pendiente).toHaveTextContent(/capítulo que aún no has leído/);
    expect(pendiente?.textContent).not.toMatch(/\d/);
  });

  it("una entrada sin capítulos leídos no pinta una línea vacía", async () => {
    render(<QuienEsQuien token="T" />, {
      wrapper: conFicha([{ nombre: "Olvido", tipo: "personaje", descripcion: "Algo." }]),
    });

    const olvido = (await screen.findByRole("heading", { name: "Olvido" })).closest(".etiqueta");
    expect(olvido?.querySelector(".etiqueta__capitulos")).toBeNull();
  });

  it("sin nada revelado todavía, lo dice y no parece roto", async () => {
    // CA-18.
    render(<QuienEsQuien token="T" />, { wrapper: conFicha([]) });

    expect(await screen.findByText(/según vayas leyendo/)).toBeInTheDocument();
  });

  it("cada hecho vivo de la entrada ofrece su propia corrección (P-37)", async () => {
    // Sin hecho único la entrada no ofrecía nada: el lector elige el hecho.
    const conHechos = [
      {
        nombre: "Olvido",
        tipo: "personaje",
        descripcion: "",
        capitulos: [1],
        hecho_canon_id: null,
        hechos: [
          { hecho_canon_id: 7, atributo: "ojos", valor: "grises" },
          { hecho_canon_id: 9, atributo: "oficio", valor: "cerrajera" },
        ],
      },
    ];
    render(<QuienEsQuien token="T" />, { wrapper: conFicha(conHechos) });

    const olvido = (await screen.findByRole("heading", { name: "Olvido" })).closest(".etiqueta");
    const etiqueta = within(olvido as HTMLElement);
    expect(etiqueta.getByText("ojos: grises")).toBeInTheDocument();
    expect(etiqueta.getByText("oficio: cerrajera")).toBeInTheDocument();
    expect(etiqueta.getAllByRole("button", { name: /^Corregir este hecho/ })).toHaveLength(2);
    expect(etiqueta.getByRole("button", { name: "Corregir este hecho: Olvido, ojos" })).toBeInTheDocument();
  });
});
