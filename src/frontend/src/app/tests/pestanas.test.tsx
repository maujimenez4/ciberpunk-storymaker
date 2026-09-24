/**
 * D-07 · Una página, tres pestañas, y el puente entre la primera y la segunda.
 *
 * Se rellena la entrevista, se pulsa, y la pestaña de leer se activa **sin
 * cambiar de dirección**: sin saltar de página, sin perder lo que había en
 * pantalla, sin una segunda carga.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StrictMode } from "react";
import { describe, expect, it } from "vitest";

import { Aplicacion } from "@/app/Aplicacion";
import { VISTAS } from "@/app/router";
import { DobleDeApi, enSecuencia } from "@/shared/api/doble";

function dobleCompleto(extras: Record<string, unknown> = {}) {
  return new DobleDeApi({
    "/entrevistas": { id: 1 },
    "/entrevistas/1/respuestas": { faltantes: [], contradicciones: [] },
    "/entrevistas/1/cerrar": { obra_id: 7 },
    "POST /obras/7/outline": { obra_id: 7, version_obra_id: 1, version: 1, capitulos: [] },
    "POST /obras/7/novela": { obra_id: 7, desde_el_capitulo: 1, terminada: false },
    // `GET` de la misma ruta: la novela ya terminada en la primera consulta,
    // para que el recorrido no espere el intervalo real de cinco segundos.
    "GET /obras/7/novela": {
      obra_id: 7,
      total: 10,
      integrados: 10,
      en_curso: null,
      estado: "terminada",
      motivo: null,
    },
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
  it("las tres estan, y la creacion abre primero", () => {
    // Plan 4 · T3: «La entrevista» se llamaba como algo que ya terminó cuando
    // dentro se enseñaba el progreso. «Creación» vale para las dos cosas.
    abrir("/", dobleCompleto());

    expect(screen.getAllByRole("tab")).toHaveLength(3);
    expect(screen.getByRole("tab", { selected: true })).toHaveAccessibleName(/creación/i);
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

/**
 * Plan 4 · T3 · **Dónde miro si recargo.** El progreso aparecía dentro de una
 * pestaña que se llamaba como algo terminado, y «Leer» y «Quién es quién»
 * salían apagadas sin decir por qué ni cuándo se abren.
 */
describe("la pestana de creacion tras recargar", () => {
  const CLAVE_EN_CURSO = "storymaker.novela-en-curso";
  const ESCRIBIENDO_3 = {
    obra_id: 7,
    total: 10,
    integrados: 2,
    en_curso: 3,
    estado: "escribiendo",
    motivo: null,
  };

  it("con una novela apuntada, abre en creacion y las otras dicen por que estan apagadas", async () => {
    window.localStorage.setItem(
      CLAVE_EN_CURSO,
      JSON.stringify({ obraId: 7, fase: "novela", desde: 1 }),
    );
    const doble = dobleCompleto({ "GET /obras/7/novela": ESCRIBIENDO_3 });
    abrir("/", doble);

    expect(screen.getByRole("tab", { selected: true })).toHaveAccessibleName(/creación/i);
    for (const nombre of [/leer/i, /quién es quién/i]) {
      const pestana = screen.getByRole("tab", { name: nombre });
      expect(pestana).toBeDisabled();
      await waitFor(() =>
        expect(pestana).toHaveAccessibleDescription(
          /se abren? cuando termine la novela.*capítulo 3 de 10/i,
        ),
      );
    }
    // El motivo se ve, no solo se anuncia.
    expect(screen.getByText(/cuando termine la novela/i)).toBeVisible();
    // Sigue la novela apuntada: no abre otra entrevista ni enseña el formulario.
    expect(screen.queryByLabelText(/cómo se llama/i)).toBeNull();
    expect(doble.metodos).not.toContain("POST /entrevistas");
  });

  it("sin novela apuntada, la creacion enseña el formulario", async () => {
    abrir("/", dobleCompleto());

    expect(screen.getByRole("tab", { selected: true })).toHaveAccessibleName(/creación/i);
    expect(await screen.findByLabelText(/cómo se llama/i)).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /leer/i })).toHaveAccessibleDescription(
      /cuando la novela esté escrita/i,
    );
  });

  it("con token, abre en leer aunque haya una novela apuntada", () => {
    window.localStorage.setItem(
      CLAVE_EN_CURSO,
      JSON.stringify({ obraId: 7, fase: "novela", desde: 1 }),
    );
    abrir(`/?token=abc123&vista=${VISTAS.leer}`, dobleCompleto());

    expect(screen.getByRole("tab", { selected: true })).toHaveAccessibleName(/leer/i);
    expect(screen.getByRole("tab", { name: /leer/i })).not.toHaveAttribute("aria-describedby");
  });
});

/** RF-ACC-02 · El patrón de pestañas de WAI-ARIA: se entra con Tab a la activa
 * y se cambia con las flechas, Inicio y Fin; las apagadas se saltan. */
describe("las pestanas con teclado", () => {
  it("las flechas pasan de una pestana a otra y vuelven por el otro extremo", async () => {
    const persona = userEvent.setup();
    abrir(`/?token=abc123&vista=${VISTAS.leer}`, dobleCompleto());

    await persona.tab();
    expect(screen.getByRole("tab", { name: /leer/i })).toHaveFocus();

    await persona.keyboard("{ArrowRight}");
    const quien = screen.getByRole("tab", { name: /quién es quién/i });
    expect(quien).toHaveFocus();
    expect(quien).toHaveAttribute("aria-selected", "true");

    await persona.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: /creación/i })).toHaveFocus();

    await persona.keyboard("{ArrowLeft}");
    expect(quien).toHaveFocus();

    await persona.keyboard("{Home}");
    expect(screen.getByRole("tab", { name: /creación/i })).toHaveFocus();
    await persona.keyboard("{End}");
    expect(quien).toHaveFocus();
  });

  it("solo la pestana activa esta en el orden de tabulacion", () => {
    abrir(`/?token=abc123&vista=${VISTAS.leer}`, dobleCompleto());

    expect(screen.getByRole("tab", { name: /leer/i })).toHaveAttribute("tabindex", "0");
    expect(screen.getByRole("tab", { name: /creación/i })).toHaveAttribute("tabindex", "-1");
  });

  it("sin novela, las flechas no se paran en las pestanas apagadas", async () => {
    const persona = userEvent.setup();
    abrir("/", dobleCompleto());

    await persona.tab();
    const creacion = screen.getByRole("tab", { name: /creación/i });
    expect(creacion).toHaveFocus();
    await persona.keyboard("{ArrowRight}");
    expect(creacion).toHaveFocus();
    expect(creacion).toHaveAttribute("aria-selected", "true");
  });
});

describe("el puente", () => {
  it("al pulsar se cierra la entrevista, se prepara la historia y se lanza la novela", async () => {
    const doble = dobleCompleto();
    const persona = userEvent.setup();
    abrir("/", doble);

    await rellenarYPulsar(persona);

    await waitFor(() => expect(doble.metodos).toContain("POST /obras/7/novela"));
    expect(doble.metodos.indexOf("POST /obras/7/outline")).toBeGreaterThan(
      doble.metodos.indexOf("POST /entrevistas/1/cerrar"),
    );
    expect(doble.metodos.indexOf("POST /obras/7/novela")).toBeGreaterThan(
      doble.metodos.indexOf("POST /obras/7/outline"),
    );
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
    doble.respuestas["POST /obras/7/novela"] = undefined;

    await persona.click(await screen.findByRole("button", { name: /escribir la novela/i }));

    // Dice **qué paso** falló: con el outline a medias este test pasaba igual
    // leyendo «no se pudo» de otro fallo.
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /no se pudo empezar a escribir la novela/i,
    );
    expect(screen.getByRole("button", { name: /escribir la novela/i })).toBeEnabled();
  });
});

describe("una entrevista por carga de pagina", () => {
  it("en StrictMode, como en main.tsx, se abre exactamente una", async () => {
    /**
     * La entrevista se abría con `useQuery` sobre un `POST`, y cada `POST
     * /entrevistas` crea una fila: en desarrollo, con StrictMode montando dos
     * veces, salían dos. La segunda quedaba huérfana en la base.
     */
    const doble = dobleCompleto();
    const persona = userEvent.setup();
    window.history.pushState({}, "", "/");
    render(
      <StrictMode>
        <Aplicacion peticionario={doble} />
      </StrictMode>,
    );

    await persona.type(await screen.findByLabelText(/cómo se llama/i), "Marta");
    await persona.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByText(/hay bastante para empezar/i)).toBeInTheDocument();

    expect(doble.metodos.filter((m) => m === "POST /entrevistas")).toHaveLength(1);
  });

  it("si abrirla falla, no se reintenta sola: un POST que falla puede haber creado la fila", async () => {
    /**
     * Con el backend escribiendo una novela, SQLite contesta a veces `database
     * is locked` (596faba). Reintentar un `POST` a ciegas es la otra forma de
     * abrir dos: el primero pudo guardar la fila antes de fallar. Se dice que
     * falló y se deja que la persona recargue.
     */
    const doble = dobleCompleto({ "/entrevistas": enSecuencia(undefined, { id: 1 }) });
    window.history.pushState({}, "", "/");
    render(
      <StrictMode>
        <Aplicacion peticionario={doble} />
      </StrictMode>,
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(/no se pudo conectar/i);
    await new Promise((seguir) => setTimeout(seguir, 1500));
    expect(doble.metodos.filter((m) => m === "POST /entrevistas")).toHaveLength(1);
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
