/**
 * Plan 3 · T2 · La novela entera, continua.
 *
 * Se lee **bajando**, no saltando entre páginas: el sumario lleva a un
 * fragmento de esta misma página.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { DobleDeApi } from "@/shared/api/doble";

import { ProveedorDeApi } from "@/shared/api/contexto";
import { Leer } from "./Leer";

function novela({
  capitulos = 10,
  dedicatoria = "Para Marta, que siempre volvía la última del agua.",
  cambiados = [] as number[],
} = {}) {
  const respuestas: Record<string, unknown> = {
    "/lectura/T": {
      ordinal: 1,
      publicada_en: "2026-09-24T10:00:00Z",
      dedicatoria,
      capitulos: Array.from({ length: capitulos }, (_, i) => ({
        numero: i + 1,
        titulo: `Capítulo sobre el mar ${i + 1}`,
        cambiado: cambiados.includes(i + 1),
      })),
    },
  };
  for (let n = 1; n <= capitulos; n += 1) {
    respuestas[`/lectura/T/capitulos/${n}`] = {
      numero: n,
      titulo: `Capítulo sobre el mar ${n}`,
      texto: `La casa olía a sal.\n\nNadie había abierto las ventanas desde septiembre ${n}.`,
    };
  }
  return new DobleDeApi(respuestas);
}

function conDoble(doble: DobleDeApi) {
  return function Envoltorio({ children }: { children: ReactNode }) {
    const cliente = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    return (
      <QueryClientProvider client={cliente}>
        <ProveedorDeApi peticionario={doble}>{children}</ProveedorDeApi>
      </QueryClientProvider>
    );
  };
}

describe("la lectura continua", () => {
  it("abre con la dedicatoria, y no es el capitulo cero", async () => {
    /** Regla de dominio 15: la dedicatoria no es prosa del manuscrito. */
    render(<Leer token="T" />, { wrapper: conDoble(novela()) });

    expect(await screen.findByText(/Para Marta/)).toBeInTheDocument();
    expect(screen.queryByText(/Cap[ií]tulo 0/)).toBeNull();
  });

  it("el sumario lleva al fragmento de cada capitulo, no a otra pagina", async () => {
    render(<Leer token="T" />, { wrapper: conDoble(novela()) });

    const enlaces = await screen.findAllByTestId(/^sumario-/);
    expect(enlaces).toHaveLength(10);
    expect(enlaces[3]).toHaveAttribute("href", "#capitulo-4");
  });

  it("marca los cambiados con el dato del backend, sin calcularlo", async () => {
    render(<Leer token="T" />, { wrapper: conDoble(novela({ cambiados: [4, 7] })) });

    expect(await screen.findByTestId("sumario-4")).toHaveAttribute("data-cambiado", "true");
    expect(screen.getByTestId("sumario-5")).toHaveAttribute("data-cambiado", "false");
  });

  it("en una primera version no hay ninguna marca", async () => {
    // RF-IND-03: no hay anterior con la que comparar.
    render(<Leer token="T" />, { wrapper: conDoble(novela()) });

    const enlaces = await screen.findAllByTestId(/^sumario-/);
    expect(enlaces.every((e) => e.getAttribute("data-cambiado") === "false")).toBe(true);
  });

  it("una novela de un capitulo no se rompe", async () => {
    // Foco 5: nada da por hecho que son diez.
    render(<Leer token="T" />, { wrapper: conDoble(novela({ capitulos: 1 })) });

    expect(await screen.findAllByTestId(/^sumario-/)).toHaveLength(1);
  });

  it("los capitulos se pintan en la misma pagina, uno tras otro", async () => {
    const { container } = render(<Leer token="T" />, { wrapper: conDoble(novela()) });

    await waitFor(() => expect(container.querySelectorAll("section.capitulo")).toHaveLength(10));
    expect(container.querySelector("#capitulo-1")).toBeInTheDocument();
    expect(container.querySelector("#capitulo-10")).toBeInTheDocument();
  });

  it("la prosa se muestra como texto y nunca se interpreta", async () => {
    // R-2, CA-16: la prosa viene de un modelo y pasa por una base de datos.
    const veneno = 'Marta dijo: <script>alert("x")</script> y salio.';
    const doble = novela({ capitulos: 1 });
    // `respuestas` es publico desde que el puente necesito mutarlo en un test.
    doble.respuestas["/lectura/T/capitulos/1"] = { numero: 1, titulo: "T", texto: veneno };

    const { container } = render(<Leer token="T" />, { wrapper: conDoble(doble) });

    expect(await screen.findByText(/alert\("x"\)/)).toBeInTheDocument();
    expect(container.querySelector("script")).toBeNull();
  });

  it("un enlace que ya no vale dice que hacer, y no se disculpa", async () => {
    const roto = new DobleDeApi({}, { fallo: 404 });

    render(<Leer token="T" />, { wrapper: conDoble(roto) });

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /Pide uno nuevo a quien te regaló la novela/,
    );
  });

  it("al leer se pueden abrir los ajustes de lectura", async () => {
    // Plan 4 · T5: el botón «Aa» solo existe mientras se lee.
    render(<Leer token="T" />, { wrapper: conDoble(novela()) });

    expect(await screen.findByRole("button", { name: "Ajustes de lectura" })).toBeInTheDocument();
  });

  it("el PDF se puede descargar", async () => {
    // RF-POR-03 conserva esta mitad aunque el indice deje de ser destino.
    render(<Leer token="T" />, { wrapper: conDoble(novela()) });

    expect(await screen.findByRole("link", { name: /PDF/i })).toHaveAttribute(
      "href",
      "/api/lectura/T/pdf",
    );
  });
});
