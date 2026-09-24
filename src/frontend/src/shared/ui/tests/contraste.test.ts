/**
 * T4 · paso 5 · `RF-ACC-04`: contraste **AA**, con herramienta y no a ojo.
 *
 * **`axe` bajo jsdom no comprueba contraste** y conviene saberlo: la regla
 * `color-contrast` necesita un motor que pinte, así que en la suite de
 * `primitives.test.tsx` esa comprobación **no corre** — pasa sin mirar. Es el
 * mismo modo de fallo que este proyecto lleva persiguiendo todo el día, y por
 * eso el ratio se calcula aquí con la fórmula de la WCAG sobre los tokens
 * reales, leídos de la hoja de estilos.
 *
 * Sobre el navegador de verdad lo vuelve a mirar T8, que es donde `axe` sí
 * puede. Esto no lo sustituye: lo adelanta al sitio donde se elige el color.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const ESTILOS = readFileSync(join(process.cwd(), "src", "app", "estilos.css"), "utf8");

function token(nombre: string): string {
  const encontrado = new RegExp(`${nombre}:\\s*(#[0-9a-f]{6})`, "i").exec(ESTILOS);
  if (!encontrado?.[1]) throw new Error(`falta el token ${nombre}`);
  return encontrado[1];
}

/** Luminancia relativa de la WCAG 2.2. */
function luminancia(hex: string): number {
  const canales = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const [r, g, b] = canales.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r! + 0.7152 * g! + 0.0722 * b!;
}

function ratio(uno: string, otro: string): number {
  const [claro, oscuro] = [luminancia(uno), luminancia(otro)].sort((a, b) => b - a);
  return (claro! + 0.05) / (oscuro! + 0.05);
}

describe("el contraste de la paleta", () => {
  const papel = token("--papel");
  const guarda = token("--guarda");

  it.each([
    ["la prosa sobre el papel", token("--tinta"), papel],
    ["los metadatos sobre el papel", token("--tinta-suave"), papel],
    ["los enlaces sobre el papel", token("--acento"), papel],
    ["el texto del boton sobre el acento", papel, token("--acento")],
    ["la prosa sobre la guarda de un aviso", token("--tinta"), guarda],
    ["los metadatos sobre la guarda", token("--tinta-suave"), guarda],
  ])("%s pasa AA", (_nombre, frente, fondo) => {
    expect(ratio(frente, fondo)).toBeGreaterThanOrEqual(4.5);
  });
});
