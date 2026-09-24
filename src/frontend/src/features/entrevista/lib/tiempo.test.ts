/**
 * Plan 4 · Enmienda 1 · El tiempo del viaje dicho en una frase. Las cifras se
 * escriben con su unidad entera («24 minutos», «1 hora y 4 minutos»): es una
 * frase para leer, no una etiqueta de panel.
 */
import { describe, expect, it } from "vitest";

import { duracionLarga, frasesDelViaje } from "./tiempo";

const MINUTO = 60_000;

describe("duracionLarga", () => {
  it.each([
    [0, "menos de un minuto"],
    [59_000, "menos de un minuto"],
    [MINUTO, "1 minuto"],
    [24 * MINUTO, "24 minutos"],
    [60 * MINUTO, "1 hora"],
    [64 * MINUTO, "1 hora y 4 minutos"],
    [121 * MINUTO, "2 horas y 1 minuto"],
    [180 * MINUTO, "3 horas"],
  ])("%d ms se dice «%s»", (ms, texto) => {
    expect(duracionLarga(ms)).toBe(texto);
  });
});

describe("frasesDelViaje", () => {
  it("con las dos cifras en minutos, la segunda no repite la unidad", () => {
    expect(frasesDelViaje(24 * MINUTO, 56 * MINUTO)).toBe(
      "Salió hace 24 minutos y le quedan unos 56.",
    );
  });

  it("si lo que queda pasa de la hora, lo dice entero y como aproximación", () => {
    expect(frasesDelViaje(12 * MINUTO, 64 * MINUTO)).toBe(
      "Salió hace 12 minutos y le quedan cerca de 1 hora y 4 minutos.",
    );
  });

  it("recién salida, no promete «unos menos de un minuto»", () => {
    expect(frasesDelViaje(0, 80 * MINUTO)).toBe(
      "Salió hace menos de un minuto y le quedan cerca de 1 hora y 20 minutos.",
    );
  });
});
