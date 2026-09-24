import js from "@eslint/js";
import importPlugin from "eslint-plugin-import";
import tseslint from "typescript-eslint";

/**
 * Las tres fronteras de `CLAUDE.md` §5.2, impuestas por la herramienta.
 *
 * No se revisan a mano: `import/no-restricted-paths` las falla en la build, que
 * es el equivalente de `lint-imports` en el backend.
 */
export default tseslint.config(
  { ignores: ["dist", "src/shared/api/generated"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    plugins: { import: importPlugin },
    settings: {
      "import/resolver": { typescript: { project: "./tsconfig.json" } },
    },
    rules: {
      // `CLAUDE.md` §7: nada de `any` en codigo de produccion.
      "@typescript-eslint/no-explicit-any": "error",
      "import/no-restricted-paths": [
        "error",
        {
          zones: [
            {
              target: "./src/shared",
              from: "./src/features",
              message: "shared nunca importa de features (RF-FRO-01)",
            },
            {
              target: "./src/features/manuscrito",
              from: "./src/features/canon",
              message: "las features no se importan entre si (RF-FRO-02)",
            },
            {
              target: "./src/features/canon",
              from: "./src/features/manuscrito",
              message: "las features no se importan entre si (RF-FRO-02)",
            },
            {
              // La cuarta zona prohibe la carpeta **entera** y exceptua los
              // `index.ts`, que es literalmente lo que dice `RF-FRO-03`.
              //
              // No es `from: "./src/features/*/!(index.ts)"`: esa fue la primera
              // redaccion y **implementaba a medias la regla que enuncia**,
              // porque el `*` casa un solo segmento y dejaba pasar
              // `features/manuscrito/components/Portada.tsx`, que es la forma
              // habitual de saltarse un `index.ts`.
              //
              // Y **`except` no admite comodin**: el plan escribia
              // `except: ["*/index.ts"]` y con eso la regla bloquea **tambien**
              // la entrada legitima por el `index.ts`, es decir cierra la unica
              // puerta que `RF-FRO-03` deja abierta. Medido con los dos casos:
              // con el comodin, interno y `index` salen los dos bloqueados; con
              // la lista, solo el interno. Cada feature se nombra, y el coste es
              // que una feature nueva no entra sin anadirse aqui — falla
              // **cerrada**, que es el lado bueno en el que fallar.
              target: "./src/app",
              from: "./src/features",
              except: ["manuscrito/index.ts", "canon/index.ts"],
              message: "se entra a una feature solo por su index.ts (RF-FRO-03)",
            },
          ],
        },
      ],
    },
  },
);
