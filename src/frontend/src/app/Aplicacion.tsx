import { BrowserRouter, Route, Routes, useParams, useLocation } from "react-router-dom";

import { Lectura, ProveedorDeApi } from "@/features/manuscrito";
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

/**
 * La entrevista, del **comprador**, antes de que exista novela.
 *
 * Vive en la raiz y **no bajo el token**: el token nace con la version
 * publicada, asi que aqui todavia no existe; y si colgara de el, el enlace del
 * regalo llevaria a lo que el comprador escribio sobre el destinatario. Es T5 y
 * se escribe con D-06 corregida delante.
 */
function Entrevista() {
  return (
    <Pagina titulo="Cuéntanos sobre quien va a leerla">
      <Texto>
        Aquí se recogerán los datos con los que se escribe la novela. Todavía no
        está lista.
      </Texto>
    </Pagina>
  );
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
        <Route path={PATRONES.entrevista} element={<Entrevista />} />
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
