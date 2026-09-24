/**
 * Plan 4 · T5 · El panel «Aa»: tamaño, interlineado y tema.
 *
 * Es comodidad de quien lee, no dato del dominio (RD-01, RD-03): vive en el
 * navegador, y si el navegador no deja guardarlo, se lee igual.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AjustesDeLectura } from "./AjustesDeLectura";

const html = document.documentElement;

afterEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
  html.removeAttribute("data-tema");
  html.style.removeProperty("--cuerpo");
  html.style.removeProperty("--ritmo");
});

async function abrir() {
  const usuario = userEvent.setup();
  const montado = render(<AjustesDeLectura />);
  await usuario.click(screen.getByRole("button", { name: "Ajustes de lectura" }));
  return Object.assign(usuario, { desmontar: montado.unmount });
}

describe("el tema", () => {
  it("elegir Noche pone data-tema en <html>", async () => {
    const usuario = await abrir();

    await usuario.click(screen.getByRole("radio", { name: "Noche" }));

    expect(html).toHaveAttribute("data-tema", "noche");
  });

  it("no hay opción «Automático»: el sistema ya no manda", async () => {
    // maujimenez4, 2026-09-24: «solo que usa el modo claro, no el modo oscuro».
    await abrir();

    expect(screen.queryByRole("radio", { name: "Automático" })).not.toBeInTheDocument();
    expect(screen.getAllByRole("radio", { name: /papel|sepia|noche/i })).toHaveLength(3);
  });

  it("sin elegir nada, es Papel", () => {
    render(<AjustesDeLectura />);

    expect(html).toHaveAttribute("data-tema", "papel");
  });

  it("quien guardó «automatico» con la versión anterior vuelve a Papel", () => {
    localStorage.setItem("lectura:ajustes", '{"tema":"automatico"}');

    render(<AjustesDeLectura />);

    expect(html).toHaveAttribute("data-tema", "papel");
  });
});

describe("la letra", () => {
  it("un paso de tamaño cambia --cuerpo", async () => {
    const usuario = await abrir();

    await usuario.click(screen.getByRole("radio", { name: "Grande" }));

    expect(html.style.getPropertyValue("--cuerpo")).toBe("1.25rem");
  });

  it("un paso de interlineado cambia --ritmo", async () => {
    const usuario = await abrir();

    await usuario.click(screen.getByRole("radio", { name: "Amplio" }));

    expect(html.style.getPropertyValue("--ritmo")).toBe("1.9");
  });
});

describe("lo que se recuerda", () => {
  it("sobrevive a cerrar y volver a abrir la novela", async () => {
    const usuario = await abrir();
    await usuario.click(screen.getByRole("radio", { name: "Noche" }));
    await usuario.click(screen.getByRole("radio", { name: "Muy grande" }));
    usuario.desmontar();
    html.removeAttribute("data-tema");
    html.style.removeProperty("--cuerpo");

    // Una recarga: el componente vuelve a montarse con el DOM limpio.
    render(<AjustesDeLectura />);

    expect(html).toHaveAttribute("data-tema", "noche");
    expect(html.style.getPropertyValue("--cuerpo")).toBe("1.4rem");
  });

  it("con el almacenamiento bloqueado se abre con los valores por defecto", async () => {
    // En navegación privada `localStorage` **lanza**, no devuelve null.
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("denied");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("denied");
    });

    const usuario = await abrir();

    expect(screen.getByRole("radio", { name: "Papel" })).toBeChecked();
    // Tamaño e interlineado, los dos en su paso normal.
    const normales = screen.getAllByRole("radio", { name: "Normal" });
    expect(normales).toHaveLength(2);
    normales.forEach((radio) => expect(radio).toBeChecked());
    await usuario.click(screen.getByRole("radio", { name: "Noche" }));
    expect(html).toHaveAttribute("data-tema", "noche");
  });

  it("un valor guardado que no es de los conocidos se ignora", () => {
    localStorage.setItem("lectura:ajustes", '{"tema":"<script>","tamano":99}');

    render(<AjustesDeLectura />);

    // Cae al defecto, que desde el 2026-09-24 es Papel y no «sin atributo».
    expect(html).toHaveAttribute("data-tema", "papel");
    expect(html.style.getPropertyValue("--cuerpo")).toBe("");
  });
});

describe("el teclado", () => {
  it("al abrir, el foco entra en el panel", async () => {
    await abrir();

    expect(screen.getByRole("dialog", { name: "Ajustes de lectura" })).toContainElement(
      document.activeElement as HTMLElement,
    );
  });

  it("Escape cierra y devuelve el foco al botón «Aa»", async () => {
    const usuario = await abrir();

    await usuario.keyboard("{Escape}");

    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.getByRole("button", { name: "Ajustes de lectura" })).toHaveFocus();
  });

  it("el foco no se escapa del panel mientras está abierto", async () => {
    const usuario = await abrir();
    const panel = screen.getByRole("dialog");

    for (let i = 0; i < 20; i += 1) {
      await usuario.tab();
      expect(panel).toContainElement(document.activeElement as HTMLElement);
    }
  });

  it("el botón dice si el panel está abierto", async () => {
    await abrir();

    expect(screen.getByRole("button", { name: "Ajustes de lectura" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
  });
});
