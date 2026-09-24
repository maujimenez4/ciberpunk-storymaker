/**
 * `RF-ACC-04`: contraste **AA**, con herramienta y no a ojo, **en los tres
 * temas** (plan 4, T1).
 *
 * **`axe` bajo jsdom no comprueba contraste** y conviene saberlo: la regla
 * `color-contrast` necesita un motor que pinte, y jsdom tampoco resuelve las
 * propiedades personalizadas de una hoja de estilos. Con `axe` aquí, el test
 * pasaría sin mirar. Por eso el ratio se calcula con la fórmula de la WCAG
 * sobre los tokens reales, leídos **del bloque de cada tema** en la hoja.
 *
 * Sobre el navegador de verdad lo vuelve a mirar `axe` en las capturas; esto no
 * lo sustituye: lo adelanta al sitio donde se elige el color.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const ESTILOS = readFileSync(join(process.cwd(), "src", "app", "estilos.css"), "utf8");

/** El cuerpo `{ … }` de la primera regla cuyo selector contiene `selector`. */
function bloque(selector: string): string {
  const inicio = ESTILOS.indexOf(selector);
  if (inicio === -1) throw new Error(`falta el bloque ${selector}`);
  const abre = ESTILOS.indexOf("{", inicio);
  const cierra = ESTILOS.indexOf("}", abre);
  return ESTILOS.slice(abre + 1, cierra);
}

function token(cuerpo: string, nombre: string): string {
  const encontrado = new RegExp(`${nombre}:\\s*(#[0-9a-f]{6})\\b`, "i").exec(cuerpo);
  if (!encontrado?.[1]) throw new Error(`falta el token ${nombre}`);
  return encontrado[1].toLowerCase();
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

const TOKENS = [
  "--papel",
  "--tinta",
  "--tinta-suave",
  "--guarda",
  "--acento",
  "--acento-texto",
  "--fondo-campo",
  // Enmienda 1 («Cuaderno de viaje»): el rojo de los sellos y de las leyendas
  // de bloque. Las leyendas son texto, así que se mide como texto.
  "--sello",
  // La línea roja del margen del cuaderno. Es decorativa y no se mide, pero
  // tiene que existir en cada tema: la usan `.hoja` y `.margen-rojo`.
  "--margen",
] as const;

function paleta(cuerpo: string): Record<(typeof TOKENS)[number], string> {
  return Object.fromEntries(TOKENS.map((t) => [t, token(cuerpo, t)])) as Record<
    (typeof TOKENS)[number],
    string
  >;
}

/**
 * Papel es el `:root` sin atributo (y `[data-tema="papel"]` comparte bloque);
 * Sepia y Noche tienen el suyo. Noche aparece dos veces —elegida a mano y
 * seguida del sistema oscuro— y el test exige que digan lo mismo.
 */
const TEMAS = {
  papel: bloque(':root[data-tema="papel"]'),
  sepia: bloque(':root[data-tema="sepia"]'),
  noche: bloque(':root[data-tema="noche"]'),
} as const;

describe.each(Object.entries(TEMAS))("el contraste del tema %s", (_tema, cuerpo) => {
  const p = paleta(cuerpo);

  it.each([
    ["la prosa sobre el papel", p["--tinta"], p["--papel"]],
    ["los metadatos y notas sobre el papel", p["--tinta-suave"], p["--papel"]],
    ["los enlaces y el boton secundario sobre el papel", p["--acento"], p["--papel"]],
    ["el texto del boton principal sobre el acento", p["--acento-texto"], p["--acento"]],
    ["la prosa de un aviso sobre la guarda", p["--tinta"], p["--guarda"]],
    ["los metadatos sobre la guarda", p["--tinta-suave"], p["--guarda"]],
    ["un enlace dentro de un aviso", p["--acento"], p["--guarda"]],
    ["lo que se escribe en un campo", p["--tinta"], p["--fondo-campo"]],
    ["una leyenda de bloque o un sello sobre el papel", p["--sello"], p["--papel"]],
    ["una leyenda de bloque sobre la hoja del cuaderno", p["--sello"], p["--guarda"]],
    ["un titulo en tinta de estilografica sobre la hoja", p["--acento"], p["--guarda"]],
  ])("%s pasa AA de texto (4.5:1)", (_nombre, frente, fondo) => {
    expect(ratio(frente, fondo)).toBeGreaterThanOrEqual(4.5);
  });

  it.each([
    ["el anillo de foco sobre el papel", p["--acento"], p["--papel"]],
    ["el anillo de foco sobre la guarda", p["--acento"], p["--guarda"]],
    ["el borde de un campo sobre su fondo", p["--tinta-suave"], p["--fondo-campo"]],
    ["el tramo de la barra sobre la guarda", p["--acento"], p["--guarda"]],
    ["lo recorrido en el mapa de ruta sobre el papel", p["--sello"], p["--papel"]],
    ["una parada hecha del mapa sobre el papel", p["--acento"], p["--papel"]],
  ])("%s pasa AA de componente (3:1)", (_nombre, frente, fondo) => {
    expect(ratio(frente, fondo)).toBeGreaterThanOrEqual(3);
  });
});

describe("los temas", () => {
  it("Papel es el de la maqueta aprobada (enmienda 1, «Cuaderno de viaje»)", () => {
    expect(paleta(TEMAS.papel)).toMatchObject({
      "--papel": "#e6e0d2",
      "--tinta": "#2a2a2e",
      "--tinta-suave": "#5f5a50",
      "--acento": "#243a5e",
      "--acento-texto": "#f1ece0",
      "--guarda": "#f1ece0",
      "--fondo-campo": "#fbf8f1",
      "--sello": "#9b3b32",
      "--margen": "#d3a8a0",
    });
  });

  it("sin atributo, el claro es Papel: comparten el mismo bloque", () => {
    expect(ESTILOS).toMatch(/(^|\n):root,\s*:root\[data-tema="papel"\]\s*\{/);
  });

  it("el sistema en oscuro no cambia el tema: sin elegir, siempre Papel", () => {
    // Decisión de maujimenez4 (2026-09-24, «solo que usa el modo claro, no el
    // modo oscuro»): revierte la decisión 2 del plan 4. Noche existe, pero solo
    // si se elige en «Aa»; el modo del sistema no manda.
    expect(ESTILOS).not.toContain("prefers-color-scheme: dark");
    expect(ESTILOS).not.toContain(":root:not([data-tema])");
  });

  it("Sepia no es nunca el tema por defecto", () => {
    // Su bloque lleva un solo selector: solo se aplica si alguien lo elige.
    expect(ESTILOS).toMatch(/(^|\n):root\[data-tema="sepia"\]\s*\{/);
    expect(paleta(TEMAS.papel)).not.toEqual(paleta(TEMAS.sepia));
  });

  /**
   * Enmienda 1 del plan 4 **revierte** la decisión 1 (interfaz en sans aparte):
   * en el cuaderno de viaje una sans rompía el papel, así que libro e interfaz
   * hablan en Spectral y los títulos y sellos en Sorts Mill Goudy.
   */
  it("el libro y la interfaz van en Spectral, y los titulos en Sorts Mill Goudy", () => {
    expect(ESTILOS).toMatch(/--fuente-libro:\s*Spectral/);
    expect(ESTILOS).toMatch(/--fuente-interfaz:\s*Spectral/);
    expect(ESTILOS).toMatch(/--fuente-titulo:\s*"Sorts Mill Goudy"/);
  });

  it("las dos familias se cargan, y las anteriores ya no", () => {
    const importacion = /@import url\("([^"]+)"\)/.exec(ESTILOS)?.[1] ?? "";
    expect(importacion).toContain("family=Spectral:");
    expect(importacion).toContain("family=Sorts+Mill+Goudy:");
    expect(ESTILOS).not.toMatch(/Literata|Atkinson/);
  });
});
