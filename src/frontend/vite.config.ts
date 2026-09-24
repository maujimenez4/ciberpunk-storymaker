import { fileURLToPath, URL } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    // El cliente pide a `/api/...` y aqui se reenvia al backend. Asi el codigo
    // no lleva dentro ninguna direccion de maquina, que es lo que permite que
    // el mismo bundle sirva en desarrollo y detras de un proxy de verdad.
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (ruta: string) => ruta.replace(/^\/api/, ""),
      },
    },
  },
  test: {
    // La suite corre **sin backend levantado** (CA-15): la API se sustituye por
    // un doble en T2. Aqui todavia no hay red que doblar.
    environment: "jsdom",
    setupFiles: ["./src/app/tests/preparar.ts"],
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    css: true,
  },
});
