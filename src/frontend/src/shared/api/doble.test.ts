/**
 * El doble de la API es infraestructura de prueba, y **un doble que no
 * distingue lo que el servidor distingue deja pasar tests que no podrían
 * pasar**. `POST /obras/{id}/novela` lanza la novela y `GET` de la misma ruta
 * dice cómo va: con una sola respuesta por ruta, las dos devolvían lo mismo.
 */
import { describe, expect, it } from "vitest";

import { ErrorDeLectura } from "./cliente";
import { DobleDeApi, enSecuencia } from "./doble";

describe("el doble de la API", () => {
  it("distingue GET de POST sobre la misma ruta", async () => {
    const doble = new DobleDeApi({
      "POST /obras/7/novela": { lanzada: true },
      "GET /obras/7/novela": { estado: "escribiendo" },
    });

    expect(await doble.enviar("/obras/7/novela", {})).toEqual({ lanzada: true });
    expect(await doble.pedir("/obras/7/novela")).toEqual({ estado: "escribiendo" });
  });

  it("sin método en la clave, la ruta sirve a los dos", async () => {
    const doble = new DobleDeApi({ "/entrevistas": { id: 1 } });

    expect(await doble.pedir("/entrevistas")).toEqual({ id: 1 });
    expect(await doble.enviar("/entrevistas", {})).toEqual({ id: 1 });
  });

  it("una secuencia se sirve en orden y repite la última", async () => {
    const doble = new DobleDeApi({
      "GET /obras/7/novela": enSecuencia({ estado: "escribiendo" }, { estado: "terminada" }),
    });

    expect(await doble.pedir("/obras/7/novela")).toEqual({ estado: "escribiendo" });
    expect(await doble.pedir("/obras/7/novela")).toEqual({ estado: "terminada" });
    expect(await doble.pedir("/obras/7/novela")).toEqual({ estado: "terminada" });
  });

  it("anota el método junto a la ruta, además de la ruta sola", async () => {
    const doble = new DobleDeApi({ "/a": 1 });

    await doble.enviar("/a", {});
    await doble.pedir("/a");

    expect(doble.llamadas).toEqual(["/a", "/a"]);
    expect(doble.metodos).toEqual(["POST /a", "GET /a"]);
  });

  it("una ruta sin respuesta falla con 404", async () => {
    const doble = new DobleDeApi({});

    await expect(doble.pedir("/nada")).rejects.toBeInstanceOf(ErrorDeLectura);
  });
});
