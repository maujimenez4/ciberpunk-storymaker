/**
 * Plan 2 · T4–T6 · La petición desde la ficha, la espera y las novedades.
 *
 * Contrato: `/lectura/{token}/peticiones` (RI-09 de la 001 servido por token,
 * ver `api/peticion.ts`). Todos los nombres son **inventados** (RD-04).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { ErrorDeLectura } from "@/shared/api/cliente";
import { ProveedorDeApi } from "@/shared/api/contexto";
import { DobleDeApi, enSecuencia } from "@/shared/api/doble";

import { EsperaDeRegeneracion } from "./EsperaDeRegeneracion";
import { Leer } from "./Leer";
import { PuertaDeEspera } from "./PuertaDeEspera";
import { QuienEsQuien } from "./QuienEsQuien";

function envolver(doble: DobleDeApi) {
  return function Envoltorio({ children }: { children: ReactNode }) {
    const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return (
      <QueryClientProvider client={cliente}>
        <ProveedorDeApi peticionario={doble}>{children}</ProveedorDeApi>
      </QueryClientProvider>
    );
  };
}

const FICHA = {
  entradas: [
    { nombre: "Olvido", tipo: "personaje", descripcion: "Colecciona llaves.", capitulos: [1], hecho_canon_id: 7 },
    { nombre: "El faro viejo", tipo: "lugar", descripcion: "Al norte.", capitulos: [2], hecho_canon_id: 9 },
    { nombre: "Sin id", tipo: "personaje", descripcion: "Todavía sin hecho.", capitulos: [1] },
  ],
};

function conFicha(extra: Record<string, unknown> = {}) {
  return new DobleDeApi({
    "GET /lectura/T/ficha": FICHA,
    "POST /lectura/T/peticiones": { peticion_id: 42, estado: "registrada" },
    ...extra,
  });
}

async function abrirYEscribir(nombre: string, texto: string) {
  fireEvent.click(await screen.findByRole("button", { name: `Corregir este hecho: ${nombre}` }));
  fireEvent.change(screen.getByLabelText("¿Qué debería decir?"), { target: { value: texto } });
}

describe("corregir un hecho desde la ficha", () => {
  it("viaja con el hecho_canon_id aunque el texto hable de otra entrada: CA-8, RF-PET-01", async () => {
    const doble = conFicha();
    const enviada = vi.fn();
    render(<QuienEsQuien token="T" onPeticionEnviada={enviada} />, { wrapper: envolver(doble) });

    await abrirYEscribir("Olvido", "El faro viejo está al sur");
    fireEvent.click(screen.getByRole("button", { name: "Enviar corrección" }));

    await waitFor(() => expect(enviada).toHaveBeenCalledWith(42));
    expect(doble.cuerpos).toEqual([{ hecho_canon_id: 7, texto_pedido: "El faro viejo está al sur" }]);
    expect(doble.metodos).toContain("POST /lectura/T/peticiones");
  });

  it("dos clics mandan una sola petición: R-7", async () => {
    const doble = conFicha();
    render(<QuienEsQuien token="T" />, { wrapper: envolver(doble) });

    await abrirYEscribir("Olvido", "Se llama Olvido Sanz");
    const enviar = screen.getByRole("button", { name: "Enviar corrección" });
    fireEvent.click(enviar);
    fireEvent.click(enviar);

    await waitFor(() => expect(doble.cuerpos).toHaveLength(1));
  });

  it("si el hecho ya cambió, lo dice sin jerga: R-4", async () => {
    const doble = new DobleDeApi({ "GET /lectura/T/ficha": FICHA });
    doble.enviar = () => Promise.reject(new ErrorDeLectura(409, "hecho_sustituido"));
    render(<QuienEsQuien token="T" />, { wrapper: envolver(doble) });

    await abrirYEscribir("Olvido", "Otra cosa");
    fireEvent.click(screen.getByRole("button", { name: "Enviar corrección" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/ha cambiado.*vuelve a abrirla/i);
  });

  it("una entrada sin hecho no ofrece corregir: D-02, no se busca por el nombre", async () => {
    render(<QuienEsQuien token="T" />, { wrapper: envolver(conFicha()) });
    const sinId = (await screen.findByRole("heading", { name: "Sin id" })).closest(".etiqueta");
    expect(within(sinId as HTMLElement).queryByRole("button")).toBeNull();
  });
});

const EN_CURSO = {
  peticion_id: 42,
  estado: "regenerando",
  resultado: null,
  token_resultante: null,
  capitulos: [
    { numero: 2, estado: "hecho" },
    { numero: 5, estado: "escribiendo" },
  ],
};

describe("la espera", () => {
  it("muestra el avance por capítulo con el dato del backend, sin barra: CA-26, RF-ESP-02", async () => {
    const doble = new DobleDeApi({ "GET /lectura/T/peticiones/42": EN_CURSO });
    render(<EsperaDeRegeneracion token="T" peticionId={42} onTerminar={() => {}} onSalir={() => {}} />, {
      wrapper: envolver(doble),
    });

    expect(await screen.findByTestId("cap-2")).toHaveAttribute("data-estado", "hecho");
    expect(screen.getByTestId("cap-5")).toHaveAttribute("data-estado", "escribiendo");
    expect(screen.queryByRole("progressbar")).toBeNull();
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("con una petición en curso la prosa no se sirve, y al acabar sin publicar vuelve con el porqué: CA-7, CA-27", async () => {
    const doble = new DobleDeApi({
      "GET /lectura/T/estado": { peticion_en_curso: null },
      "GET /lectura/T/peticiones/42": enSecuencia(EN_CURSO, {
        ...EN_CURSO,
        estado: "descartada",
        resultado: "la corrección introducía un defecto en el capítulo 5",
      }),
    });
    vi.useFakeTimers({ shouldAdvanceTime: true });
    render(
      <PuertaDeEspera token="T" peticionId={42}>
        <p>La prosa de siempre.</p>
      </PuertaDeEspera>,
      { wrapper: envolver(doble) },
    );

    await screen.findByTestId("cap-2");
    expect(screen.queryByText("La prosa de siempre.")).toBeNull();

    await vi.advanceTimersByTimeAsync(3_500);
    expect(await screen.findByText("La prosa de siempre.")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(/no se pudo aplicar.*capítulo 5/i);
    vi.useRealTimers();
  });

  it("si el backend calla, se ofrece volver a la lectura: CA-28, RF-ESP-05", async () => {
    const doble = new DobleDeApi({}, { fallo: 500 });
    const salir = vi.fn();
    vi.useFakeTimers({ shouldAdvanceTime: true });
    render(<EsperaDeRegeneracion token="T" peticionId={42} onTerminar={() => {}} onSalir={salir} />, {
      wrapper: envolver(doble),
    });

    // Tres reintentos con espera creciente: 2 + 4 + 8 segundos.
    await vi.advanceTimersByTimeAsync(20_000);
    fireEvent.click(await screen.findByRole("button", { name: "Volver a la lectura" }));
    expect(salir).toHaveBeenCalled();
    vi.useRealTimers();
  });
});

describe("novedades", () => {
  function version(cambiados: number[]) {
    const respuestas: Record<string, unknown> = {
      "/lectura/T": {
        ordinal: 2,
        publicada_en: "2026-09-24T10:00:00Z",
        capitulos: [1, 2, 3].map((n) => ({ numero: n, titulo: `T${n}`, cambiado: cambiados.includes(n) })),
      },
    };
    for (const n of [1, 2, 3]) respuestas[`/lectura/T/capitulos/${n}`] = { numero: n, texto: "Sal." };
    return new DobleDeApi(respuestas);
  }

  it("dice qué capítulos se reescribieron, con el dato del backend: RF-IND-02, RF-NOV-01", async () => {
    render(<Leer token="T" />, { wrapper: envolver(version([2, 3])) });
    const aviso = (await screen.findByRole("heading", { name: "Novedades de esta versión" })).closest("aside");
    const enlaces = within(aviso as HTMLElement).getAllByRole("link");
    expect(enlaces.map((a) => a.getAttribute("href"))).toEqual(["#capitulo-2", "#capitulo-3"]);
  });

  it("en la primera versión no hay novedades: RF-IND-03", async () => {
    render(<Leer token="T" />, { wrapper: envolver(version([])) });
    await screen.findByTestId("sumario-1");
    expect(screen.queryByRole("heading", { name: "Novedades de esta versión" })).toBeNull();
  });
});
