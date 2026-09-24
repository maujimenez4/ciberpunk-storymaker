import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "./estilos.css";
import { Aplicacion } from "./Aplicacion";

const raiz = document.getElementById("raiz");
if (!raiz) {
  throw new Error("falta el elemento #raiz en index.html");
}

createRoot(raiz).render(
  <StrictMode>
    <Aplicacion />
  </StrictMode>,
);
