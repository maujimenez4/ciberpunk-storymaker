/**
 * La novela en curso sobrevive a una recarga porque se apunta en el navegador.
 *
 * **Y la página tiene que funcionar igual si el navegador no deja apuntar**:
 * una ventana privada, datos bloqueados o una cuota llena hacen que
 * `localStorage` falle o lance. Perder la reanudación es aceptable; perder la
 * novela por un `throw` en el render, no.
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import { guardarNovelaEnCurso, leerNovelaEnCurso, olvidarNovelaEnCurso } from "./novelaEnCurso";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("la novela en curso, apuntada en el navegador", () => {
  it("lo que se guarda se lee igual", () => {
    guardarNovelaEnCurso({ obraId: 7, fase: "novela", desde: 1234 });

    expect(leerNovelaEnCurso()).toEqual({ obraId: 7, fase: "novela", desde: 1234 });
  });

  it("olvidarla la borra", () => {
    guardarNovelaEnCurso({ obraId: 7, fase: "outline", desde: 1 });
    olvidarNovelaEnCurso();

    expect(leerNovelaEnCurso()).toBeNull();
  });

  it("algo que no tiene su forma se ignora, no se cree", () => {
    for (const basura of ["{no es json", '{"obraId":"7"}', '{"obraId":7,"fase":"otra","desde":1}', "null"]) {
      window.localStorage.setItem("storymaker.novela-en-curso", basura);
      expect(leerNovelaEnCurso()).toBeNull();
    }
  });

  it("si el navegador no deja leer ni escribir, no lanza", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("bloqueado", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("llena", "QuotaExceededError");
    });
    vi.spyOn(Storage.prototype, "removeItem").mockImplementation(() => {
      throw new DOMException("bloqueado", "SecurityError");
    });

    expect(() => guardarNovelaEnCurso({ obraId: 7, fase: "novela", desde: 1 })).not.toThrow();
    expect(leerNovelaEnCurso()).toBeNull();
    expect(() => olvidarNovelaEnCurso()).not.toThrow();
  });
});
