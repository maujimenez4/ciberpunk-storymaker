import { BrowserRouter, Route, Routes, useParams, useLocation } from "react-router-dom";

import { Entrevista as PantallaDeEntrevista } from "@/features/entrevista";
import { Lectura } from "@/features/manuscrito";
import { ProveedorDeApi } from "@/shared/api/contexto";
import { Pagina } from "@/shared/ui/patterns/Pagina";
import { Texto } from "@/shared/ui/primitives";
import type { Peticionario } from "@/shared/api/cliente";

import { PATRONES, vistaDe } from "./router";
import { Proveedores } from "./providers";

function PaginaDeLectura() {
  const { token = "" } = useParams();
  const { search } = useLocation();
  return <Lectura token={token} vistaInicial={vistaDe(search) === "quien-es-quien" ? "quien-es-quien" : "leer"} />;
}

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

export function Aplicacion({ peticionario }: { peticionario?: Peticionario }) {
  const arbol = (
    <BrowserRouter>
      <Routes>
        <Route path={PATRONES.entrevista} element={<PantallaDeEntrevista />} />
        <Route path={PATRONES.lectura} element={<PaginaDeLectura />} />
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
