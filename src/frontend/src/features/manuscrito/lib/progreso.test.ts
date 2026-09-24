/**
 * Plan 4 · T6 · Cuánto se ha leído y cuánto queda.
 *
 * Todo el texto es **inventado** (RD-04): palabras sueltas repetidas, ningún
 * fragmento de manuscrito.
 */
import { describe, expect, it } from "vitest";

import { contarPalabras, minutosQueQuedan, porcentajeLeido, ubicar } from "./progreso";

const inventado = (palabras: number) => Array.from({ length: palabras }, () => "ola").join(" ");

describe("contar palabras", () => {
  it("cuenta lo que hay entre espacios y saltos de párrafo", () => {
    expect(contarPalabras("La casa olía a sal.\n\nNadie abrió.")).toBe(7);
  });

  it("un texto vacío o en blanco no tiene palabras", () => {
    expect(contarPalabras("")).toBe(0);
    expect(contarPalabras("  \n\n ")).toBe(0);
  });

  it("un capítulo inventado de 1.150 palabras tiene 1.150", () => {
    expect(contarPalabras(inventado(1150))).toBe(1150);
  });
});

describe("los minutos que quedan del capítulo", () => {
  it("con 1.150 palabras a mitad, quedan 3 min (575 / 230 = 2,5, se redondea hacia arriba)", () => {
    expect(minutosQueQuedan(1150, 0.5)).toBe(3);
  });

  it("sin empezar, el capítulo entero", () => {
    expect(minutosQueQuedan(1150, 0)).toBe(5);
  });

  it("al final no queda nada", () => {
    expect(minutosQueQuedan(1150, 1)).toBe(0);
  });

  it("una sola palabra por leer es un minuto, no cero", () => {
    // Decir «terminaste» con texto por delante sería mentir.
    expect(minutosQueQuedan(1150, 1149 / 1150)).toBe(1);
  });

  it("una fracción fuera de rango se acota, no da minutos negativos", () => {
    expect(minutosQueQuedan(1150, 1.4)).toBe(0);
    expect(minutosQueQuedan(1150, -1)).toBe(5);
  });
});

describe("el porcentaje de la novela", () => {
  const diez = Array.from({ length: 10 }, () => 1000);

  it("sin empezar, 0 %", () => {
    expect(porcentajeLeido(diez, 0, 0)).toBe(0);
  });

  it("se pesa por palabras: a mitad del quinto de diez iguales, 45 %", () => {
    expect(porcentajeLeido(diez, 4, 0.5)).toBe(45);
  });

  it("al final, 100 %", () => {
    expect(porcentajeLeido(diez, 9, 1)).toBe(100);
  });

  it("no dice 100 % hasta el final: redondea hacia abajo", () => {
    expect(porcentajeLeido(diez, 9, 0.99)).toBe(99);
  });

  it("capítulos de largo distinto pesan distinto", () => {
    // 1.150 + 2.300 = 3.450 · leídas 1.150 + 1.150 = 2.300 → 66 %.
    expect(porcentajeLeido([1150, 2300], 1, 0.5)).toBe(66);
  });

  it("una novela sin palabras conocidas todavía es 0 %, no NaN", () => {
    expect(porcentajeLeido([0, 0], 1, 0.5)).toBe(0);
  });
});

describe("dónde está quien lee", () => {
  const alto = 800;

  it("el capítulo en curso es el último cuyo título ya pasó la mitad de la pantalla", () => {
    const lugar = ubicar(
      [
        { numero: 1, arriba: -3000, alto: 2000 },
        { numero: 2, arriba: -1000, alto: 2000 },
        { numero: 3, arriba: 1000, alto: 2000 },
      ],
      alto,
    );
    expect(lugar?.numero).toBe(2);
    // Leído hasta el borde inferior de la pantalla: (800 + 1000) / 2000.
    expect(lugar?.fraccion).toBeCloseTo(0.9);
  });

  it("antes del primer capítulo, el primero sin empezar", () => {
    const lugar = ubicar([{ numero: 1, arriba: 900, alto: 2000 }], alto);
    expect(lugar).toEqual({ numero: 1, fraccion: 0 });
  });

  it("con el final del último capítulo en pantalla, está entero", () => {
    const lugar = ubicar(
      [
        { numero: 1, arriba: -5000, alto: 2000 },
        { numero: 2, arriba: -1500, alto: 2000 },
      ],
      alto,
    );
    expect(lugar).toEqual({ numero: 2, fraccion: 1 });
  });

  it("sin medidas (nada pintado aún) no divide por cero", () => {
    const lugar = ubicar(
      [
        { numero: 1, arriba: 0, alto: 0 },
        { numero: 2, arriba: 0, alto: 0 },
      ],
      alto,
    );
    expect(lugar).toEqual({ numero: 1, fraccion: 0 });
  });

  it("sin capítulos, no hay lugar", () => {
    expect(ubicar([], alto)).toBeNull();
  });
});
