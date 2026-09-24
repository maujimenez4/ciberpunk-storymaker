import { BrowserRouter, Route, Routes } from "react-router-dom";

import { Pagina } from "@/shared/ui/patterns/Pagina";
import { Texto } from "@/shared/ui/primitives";
import type { Peticionario } from "@/shared/api/cliente";
import { ProveedorDeApi } from "@/shared/api/contexto";

import { Paginas } from "./Paginas";
import { Proveedores } from "./providers";

function NoEncontrada() {
  return (
    <Pagina titulo="Esta página no existe">
      <Texto>
        Comprueba el enlace que te dieron. Si lo copiaste de un mensaje, puede
        que se cortara al pegarlo.
      </Texto>
    </Pagina>
  );
}

/**
 * **Una sola dirección** (D-07). Las tres pantallas son pestañas de la misma
 * página: se rellena, se pulsa y se lee sin navegar a ningún sitio.
 */
export function Aplicacion({ peticionario }: { peticionario?: Peticionario }) {
  const arbol = (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Paginas />} />
        <Route path="*" element={<NoEncontrada />} />
      </Routes>
    </BrowserRouter>
  );
  return (
    <Proveedores>
      {peticionario ? (
        <ProveedorDeApi peticionario={peticionario}>{arbol}</ProveedorDeApi>
      ) : (
        arbol
      )}
    </Proveedores>
  );
}
