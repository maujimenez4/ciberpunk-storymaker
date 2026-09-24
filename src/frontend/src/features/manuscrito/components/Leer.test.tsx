/**
 * Plan 3 · T2 · La novela entera, continua.
 *
 * Se lee **bajando**, no saltando entre páginas: el sumario lleva a un
 * fragmento de esta misma página.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

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

  it("el sello del margen es adorno, y el número sigue en el título accesible", async () => {
    // Plan 4, enmienda 1: «capítulo / 3 / de 10» como sello. Un lector de
    // pantalla no debe oír el número dos veces, pero tampoco perderlo.
    const { container } = render(<Leer token="T" />, { wrapper: conDoble(novela()) });

    await waitFor(() => expect(container.querySelectorAll("section.capitulo")).toHaveLength(10));
    const tercero = container.querySelector("#capitulo-3");
    const sello = tercero?.querySelector(".sello");
    expect(sello).toHaveAttribute("aria-hidden", "true");
    expect(sello).toHaveTextContent(/cap[ií]tulo\s*3\s*de 10/i);
    expect(
      screen.getByRole("heading", { level: 2, name: /Cap[ií]tulo 3\b.*Capítulo sobre el mar 3/ }),
    ).toBeInTheDocument();
  });

  it("la prosa va en la columna del margen rojo, con el ritmo de libro", async () => {
    render(<Leer token="T" />, { wrapper: conDoble(novela({ capitulos: 1 })) });

    const parrafo = await screen.findByText("La casa olía a sal.");
    expect(parrafo.closest(".margen-rojo")).not.toBeNull();
    expect(parrafo).toHaveClass("prosa");
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

/**
 * Plan 4 · T6 · El pie de lectura.
 *
 * jsdom no pinta, así que las medidas de cada capítulo se fingen: es lo que
 * el navegador diría con la página desplazada hasta ese punto. El texto es
 * **inventado** (RD-04): la misma palabra repetida.
 */
describe("el pie de lectura", () => {
  const ALTO_PANTALLA = window.innerHeight;

  afterEach(() => {
    vi.restoreAllMocks();
  });

  /** Dos capítulos de 1.150 palabras inventadas. */
  function novelaDe1150() {
    const doble = novela({ capitulos: 2 });
    for (const n of [1, 2]) {
      doble.respuestas[`/lectura/T/capitulos/${n}`] = {
        numero: n,
        titulo: `T${n}`,
        texto: Array.from({ length: 1150 }, () => "ola").join(" "),
      };
    }
    return doble;
  }

  /** Finge dónde está cada capítulo respecto a la pantalla. */
  function medidas(porCapitulo: Record<string, { arriba: number; alto: number }>) {
    vi.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(function (
      this: Element,
    ) {
      const m = porCapitulo[this.id] ?? { arriba: 0, alto: 0 };
      const rect = { x: 0, y: m.arriba, width: 500, height: m.alto };
      return {
        ...rect,
        top: m.arriba,
        bottom: m.arriba + m.alto,
        left: 0,
        right: 500,
        toJSON: () => rect,
      } as DOMRect;
    });
  }

  it("a mitad de un capítulo de 1.150 palabras, quedan 3 min", async () => {
    render(<Leer token="T" />, { wrapper: conDoble(novelaDe1150()) });
    await screen.findAllByText(/^ola ola/);

    // El borde inferior de la pantalla, justo en la mitad del capítulo 1.
    medidas({
      "capitulo-1": { arriba: ALTO_PANTALLA - 1000, alto: 2000 },
      "capitulo-2": { arriba: ALTO_PANTALLA + 1000, alto: 2000 },
    });
    fireEvent.scroll(window);

    expect(await screen.findByText("Quedan 3 min en este capítulo")).toBeInTheDocument();
    expect(screen.getByText("25 %")).toBeInTheDocument();
  });

  it("el camino recorrido y el punto donde vas son la misma cifra, dibujada", async () => {
    // Enmienda 1: línea de puntos, lo recorrido sólido y un punto en la
    // posición. Todo `aria-hidden`: el porcentaje ya lo dice en texto.
    const { container } = render(<Leer token="T" />, { wrapper: conDoble(novelaDe1150()) });
    await screen.findAllByText(/^ola ola/);

    medidas({
      "capitulo-1": { arriba: ALTO_PANTALLA - 1000, alto: 2000 },
      "capitulo-2": { arriba: ALTO_PANTALLA + 1000, alto: 2000 },
    });
    fireEvent.scroll(window);
    await screen.findByText("25 %");

    const camino = container.querySelector(".progreso__camino");
    expect(camino).toHaveAttribute("aria-hidden", "true");
    const punto = camino?.querySelector<HTMLElement>(".progreso__punto");
    expect(punto?.style.left).toBe("25%");
  });

  it("al final de la novela, 100 % y el capítulo terminado", async () => {
    render(<Leer token="T" />, { wrapper: conDoble(novelaDe1150()) });
    await screen.findAllByText(/^ola ola/);

    medidas({
      "capitulo-1": { arriba: -5000, alto: 2000 },
      "capitulo-2": { arriba: -2500, alto: 2000 },
    });
    fireEvent.scroll(window);

    expect(await screen.findByText("100 %")).toBeInTheDocument();
    expect(screen.getByText("Terminaste este capítulo")).toBeInTheDocument();
  });

  it("al abrir, sin desplazar, el primer capítulo entero por leer", async () => {
    render(<Leer token="T" />, { wrapper: conDoble(novelaDe1150()) });

    expect(await screen.findByText("Quedan 5 min en este capítulo")).toBeInTheDocument();
    expect(screen.getByText("0 %")).toBeInTheDocument();
  });

  it("no se anuncia en cada desplazamiento: no es una región viva", async () => {
    // Un número que cambia al bajar cada línea, leído en voz alta, taparía la
    // novela que el lector de pantalla está leyendo.
    render(<Leer token="T" />, { wrapper: conDoble(novelaDe1150()) });

    const minutos = await screen.findByText(/^Quedan \d+ min/);
    expect(minutos.closest("[aria-live]")).toBeNull();
    expect(minutos.closest('[role="status"], [role="alert"], [role="progressbar"]')).toBeNull();
  });
});
