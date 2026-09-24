/**
 * T1 · Las tres fronteras de `CLAUDE.md` §5.2, comprobadas por ESLint.
 *
 * **Por qué el test ejecuta ESLint y no lee la configuración.** Comprobar que la
 * regla *está escrita* no prueba que *dispare*: una ruta mal puesta en `target`
 * deja la regla presente y desactivada, y la build sigue verde. Este test es el
 * equivalente de `lint-imports` del backend, y como aquel tiene que verse fallar.
 */
import { execSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { describe, expect, it } from "vitest";

const RAIZ = join(import.meta.dirname, "..", "..", "..");

/**
 * Escribe un fichero, lo pasa por ESLint y devuelve su salida.
 *
 * `destinos` crea los modulos que el fichero importa, y **no es comodidad**:
 * `import/no-restricted-paths` solo dispara sobre un import que el resolver
 * consigue resolver. Si el destino no existe, la regla calla y el test que
 * esperaba un error lo lee como frontera cerrada — un falso verde que dice justo
 * lo contrario de lo que pasa.
 */
function lintDeUnFichero(
  ruta: string,
  contenido: string,
  destinos: Record<string, string> = {},
): string {
  const creados = [ruta, ...Object.keys(destinos)];
  for (const [destino, cuerpo] of Object.entries(destinos)) {
    const absoluto = join(RAIZ, destino);
    mkdirSync(dirname(absoluto), { recursive: true });
    writeFileSync(absoluto, cuerpo);
  }
  const absoluta = join(RAIZ, ruta);
  mkdirSync(dirname(absoluta), { recursive: true });
  writeFileSync(absoluta, contenido);
  try {
    execSync(`pnpm exec eslint "${ruta}"`, { cwd: RAIZ, stdio: "pipe" });
    return "";
  } catch (error) {
    const e = error as { stdout?: Buffer; stderr?: Buffer };
    return String(e.stdout ?? "") + String(e.stderr ?? "");
  } finally {
    for (const creado of creados) {
      rmSync(join(RAIZ, creado), { force: true });
    }
  }
}

describe("las tres fronteras las falla ESLint, no una revision a mano", () => {
  it("shared no puede importar de features", () => {
    const salida = lintDeUnFichero(
      "src/shared/lib/_prueba.ts",
      `import { algo } from "../../features/manuscrito";\nexport const x = algo;\n`,
    );

    expect(salida).toContain("no-restricted-paths");
  });

  it("una feature no puede importar de otra", () => {
    const salida = lintDeUnFichero(
      "src/features/manuscrito/_prueba.ts",
      `import { algo } from "../canon";\nexport const x = algo;\n`,
    );

    expect(salida).toContain("no-restricted-paths");
  });

  it("no se entra a una feature por un fichero interno", () => {
    const salida = lintDeUnFichero(
      "src/app/_prueba.ts",
      `import { P } from "../features/manuscrito/components/Portada";\nexport const x = P;\n`,
      { "src/features/manuscrito/components/Portada.ts": "export const P = null;\n" },
    );

    expect(salida).toContain("no-restricted-paths");
  });

  it("entrar por el index.ts de una feature si esta permitido", () => {
    /**
     * El control negativo, y no es adorno: una zona demasiado ancha cierra
     * también la puerta que `RF-FRO-03` deja abierta a propósito, y los tres
     * tests de arriba seguirían verdes.
     */
    const salida = lintDeUnFichero(
      "src/app/_permitido.ts",
      `import { algo } from "../features/manuscrito";\nexport const x = algo;\n`,
    );

    expect(salida).not.toContain("no-restricted-paths");
  });
});
