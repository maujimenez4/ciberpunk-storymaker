/**
 * D-07 · Una página, tres pestañas, y el puente entre la primera y la segunda.
 *
 * Se rellena la entrevista, se pulsa, y la pestaña de leer se activa **sin
 * cambiar de dirección**: sin saltar de página, sin perder lo que había en
 * pantalla, sin una segunda carga.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { Aplicacion } from "@/app/Aplicacion";
import { VISTAS } from "@/app/router";
import { DobleDeApi } from "@/shared/api/doble";

function dobleCompleto(extras: Record<string, unknown> = {}) {
  return new DobleDeApi({
    "/entrevistas": { id: 1 },
    "/entrevistas/1/respuestas": { faltantes: [], contradicciones: [] },
    "/entrevistas/1/cerrar": { obra_id: 7 },
    "/obras/7/novela": { obra_id: 7, desde_el_capitulo: 1, terminada: true },
    "/obras/7/publicar": { token: "tok-7", ordinal: 1 },
    "/lectura/tok-7": {
      titulo: "El verano del 98",
      ordinal: 1,
      publicada_en: "2026-09-24T10:00:00Z",
      dedicatoria: "Para Marta.",
      capitulos: [{ numero: 1, titulo: "La casa", cambiado: false }],
    },
    "/lectura/tok-7/capitulos/1": { numero: 1, titulo: "La casa", texto: "Olía a sal." },
    ...extras,
  });
}

function abrir(ruta: string, doble: DobleDeApi) {
  window.history.pushState({}, "", ruta);
  return render(<Aplicacion peticionario={doble} />);
}

async function rellenarYPulsar(persona: ReturnType<typeof userEvent.setup>) {
  await persona.type(await screen.findByLabelText(/cómo se llama/i), "Marta");
  await persona.click(screen.getByRole("button", { name: /guardar/i }));
  await persona.click(await screen.findByRole("button", { name: /escribir la novela/i }));
}

describe("una pagina, tres pestanas", () => {
  it("las tres estan, y la entrevista abre primero", () => {
    abrir("/", dobleCompleto());

    expect(screen.getAllByRole("tab")).toHaveLength(3);
    expect(screen.getByRole("tab", { selected: true })).toHaveAccessibleName(/entrevista/i);
  });

  it("sin novela, leer y quien es quien no se pueden pulsar", () => {
    /** Una pestaña que se puede pulsar y no lleva a nada enseña una pantalla
     * vacía, y una pantalla vacía se lee como un fallo. */
    abrir("/", dobleCompleto());

    expect(screen.getByRole("tab", { name: /leer/i })).toBeDisabled();
    expect(screen.getByRole("tab", { name: /quién es quién/i })).toBeDisabled();
  });

  it("con un token en la direccion, la lectura se abre ya puesta", () => {
    // Es lo que se manda de regalo: abrirlo lleva a leer, no al formulario.
    abrir(`/?token=abc123&vista=${VISTAS.leer}`, dobleCompleto());

    expect(screen.getByRole("tab", { selected: true })).toHaveAccessibleName(/leer/i);
    expect(screen.getByRole("tab", { name: /leer/i })).toBeEnabled();
  });
});

describe("el puente", () => {
  it("al pulsar se cierra la entrevista y se lanza la novela", async () => {
    const doble = dobleCompleto();
    const persona = userEvent.setup();
    abrir("/", doble);

    await rellenarYPulsar(persona);

    await waitFor(() => expect(doble.llamadas).toContain("/entrevistas/1/cerrar"));
    expect(doble.llamadas).toContain("/obras/7/novela");
  });

  it("mientras se escribe, lo dice en vez de dejar la pantalla quieta", async () => {
    // Con retraso: sin el, el doble publica en el mismo tic y el aviso no llega
    // a verse. Lo que se comprueba es que **existe mientras dura**.
    const lento = dobleCompleto();
    Object.assign(lento, { opciones: { retraso: 50 } });
    const persona = userEvent.setup();
    abrir("/", lento);

    await rellenarYPulsar(persona);

    // Hay dos regiones `status` a la vez y las dos son legítimas: la
    // comprobación de la entrevista y este aviso. Se busca por su texto.
    expect(await screen.findByText(/se está escribiendo tu novela/i)).toBeInTheDocument();
  });

  it("si lanzar la novela falla, lo dice y se puede reintentar", async () => {
    /** Lo contrario sería quedarse en «se está escribiendo» para siempre, que
     * es la peor forma de fallar: parece que funciona. */
    const doble = dobleCompleto();
    const persona = userEvent.setup();
    abrir("/", doble);
    await persona.type(await screen.findByLabelText(/cómo se llama/i), "Marta");
    await persona.click(screen.getByRole("button", { name: /guardar/i }));
    // La novela no está en el doble: la llamada falla con 404.
    doble.respuestas["/obras/7/novela"] = undefined;

    await persona.click(await screen.findByRole("button", { name: /escribir la novela/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/no se pudo/i);
    expect(screen.getByRole("button", { name: /escribir la novela/i })).toBeEnabled();
  });
});

describe("el recorrido entero", () => {
  it("al terminar se publica y se lee LA NOVELA, no una pestana vacia", async () => {
    /**
     * **El riesgo de este test es que pase sin que haya novela detrás.** Que la
     * pestaña se active no prueba nada: se activaría igual con un token
     * inventado. Por eso se comprueba la cadena entera — que se llamó a
     * `publicar`, que el token salió de ahí, y que la lectura **pidió y pintó**
     * la novela de ese token.
     */
    const doble = dobleCompleto();
    const persona = userEvent.setup();
    abrir("/", doble);

    await rellenarYPulsar(persona);

    await waitFor(() => expect(doble.llamadas).toContain("/obras/7/publicar"));
    await waitFor(() =>
      expect(screen.getByRole("tab", { name: /leer/i })).toBeEnabled(),
    );
    await persona.click(screen.getByRole("tab", { name: /leer/i }));

    // La cadena entera: el token salio de `publicar` y la lectura lo uso.
    expect(doble.llamadas).toContain("/lectura/tok-7");
    expect(await screen.findByText(/Para Marta/)).toBeInTheDocument();
    expect(await screen.findByText(/Olía a sal/)).toBeInTheDocument();
  });

  it("si publicar falla, no se activa una pestana que no lleva a nada", async () => {
    const doble = dobleCompleto();
    doble.respuestas["/obras/7/publicar"] = undefined;
    const persona = userEvent.setup();
    abrir("/", doble);

    await rellenarYPulsar(persona);

    await waitFor(() => expect(doble.llamadas).toContain("/obras/7/publicar"));
    expect(screen.getByRole("tab", { name: /leer/i })).toBeDisabled();
  });
});
