import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

/**
 * El punto de entrada. Todavia no monta router ni proveedores: eso es T3, y
 * esta tarea entrega **lo que rechaza el trabajo mal hecho**, no interfaz.
 */
const raiz = document.getElementById("raiz");
if (!raiz) {
  throw new Error("falta el elemento #raiz en index.html");
}

createRoot(raiz).render(
  <StrictMode>
    <p>Tu novela se esta preparando.</p>
  </StrictMode>,
);
