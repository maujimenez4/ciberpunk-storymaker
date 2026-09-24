/**
 * Plan 3 · T3 · Dónde estabas y dónde te mandaron.
 *
 * Los tres primeros casos del foco de revisión del plan viven aquí: fragmento
 * imposible, dos novelas en un teléfono y almacenamiento bloqueado.
 */
import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { usePosicion } from "./usePosicion";

const DIEZ = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

afterEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
  window.history.replaceState({}, "", "/l/T");
});

describe("la precedencia", () => {
  it("si la URL trae fragmento, manda el fragmento", () => {
    /** Alguien te mandó ese punto adrede: llevarte a otro sitio es ignorarle. */
    localStorage.setItem("posicion:T", "3");
    window.history.replaceState({}, "", "/l/T#capitulo-7");

    const { result } = renderHook(() => usePosicion("T", DIEZ));

    expect(result.current.inicial).toBe(7);
  });

  it("sin fragmento, se vuelve donde lo dejaste", () => {
    localStorage.setItem("posicion:T", "3");

    const { result } = renderHook(() => usePosicion("T", DIEZ));

    expect(result.current.inicial).toBe(3);
  });

  it("sin nada de lo anterior, se empieza por el principio", () => {
    const { result } = renderHook(() => usePosicion("T", DIEZ));

    expect(result.current.inicial).toBeNull();
  });
});

describe("lo que no puede romper la lectura", () => {
  it("un fragmento que esta novela no tiene no deja la pagina en blanco", () => {
    // Foco 1: `#capitulo-12` en una novela de diez.
    window.history.replaceState({}, "", "/l/T#capitulo-12");

    const { result } = renderHook(() => usePosicion("T", [1, 2, 3]));

    expect(result.current.inicial).toBeNull();
  });

  it("dos novelas en el mismo telefono no se pisan", () => {
    // Foco 3: sin el token en la clave, la segunda abre donde iba la primera.
    localStorage.setItem("posicion:T", "3");

    const { result } = renderHook(() => usePosicion("OTRA", DIEZ));

    expect(result.current.inicial).toBeNull();
  });

  it("con el almacenamiento bloqueado se lee igual", () => {
    // Foco 2: en navegación privada `localStorage` **lanza**, no devuelve null.
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("denied");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("denied");
    });

    const { result } = renderHook(() => usePosicion("T", DIEZ));

    expect(result.current.inicial).toBeNull();
    expect(() => act(() => result.current.recordar(2))).not.toThrow();
  });

  it("una posicion guardada que ya no existe se ignora", () => {
    // La novela se republicó con menos capítulos.
    localStorage.setItem("posicion:T", "9");

    const { result } = renderHook(() => usePosicion("T", [1, 2]));

    expect(result.current.inicial).toBeNull();
  });
});

describe("recordar", () => {
  it("no apila historial: el boton atras sirve para salir de la novela", () => {
    /** Con `pushState`, «atrás» retrocede capítulo a capítulo y deja de servir
     * para lo único que se usa en un móvil: salir. */
    const largo = window.history.length;
    const { result } = renderHook(() => usePosicion("T", DIEZ));

    act(() => result.current.recordar(4));

    expect(window.history.length).toBe(largo);
    expect(window.location.hash).toBe("#capitulo-4");
  });

  it("lo recordado sobrevive a cerrar y volver", () => {
    const { result } = renderHook(() => usePosicion("T", DIEZ));
    act(() => result.current.recordar(6));
    window.history.replaceState({}, "", "/l/T");

    const segunda = renderHook(() => usePosicion("T", DIEZ));

    expect(segunda.result.current.inicial).toBe(6);
  });
});
