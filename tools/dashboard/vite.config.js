// Build del panel. El root es esta carpeta y el resultado va a `dist/`, que
// `tools/dashboard.mjs` sirve como estático.
//
// En `panel:dev` Vite sirve la UI con recarga en caliente y reenvía `/api` al servidor
// real, que es el único que sabe leer el disco y lanzar corridas. Sin ese proxy el modo
// dev enseñaría la interfaz sin un solo dato.

import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const API_PORT = Number(process.env.STORYMAKER_PANEL_PORT ?? 4173);

// `fileURLToPath` y no `new URL(...).pathname`: en Windows ese pathname es `/C:/…`, con
// una barra delante que Rollup no resuelve.
export default defineConfig({
  root: fileURLToPath(new URL('.', import.meta.url)),
  base: './',
  plugins: [react()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    // El panel es local y de un solo usuario: un sourcemap cuesta nada y ahorra una tarde.
    sourcemap: true,
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': { target: `http://127.0.0.1:${API_PORT}`, changeOrigin: false },
    },
  },
});
