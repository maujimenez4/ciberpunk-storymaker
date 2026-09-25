import { useQueryClient } from "@tanstack/react-query";
import { type ReactNode, useState } from "react";

import { Aviso } from "@/shared/ui/primitives";

import "../lectura.css";

import { type Peticion, useRegeneracionEnCurso } from "../api/peticion";
import { EsperaDeRegeneracion } from "./EsperaDeRegeneracion";

type Final = { peticion: Peticion; tokenAnterior: string };

/**
 * RF-ESP-01: con una petición en curso **la lectura no se sirve**. La petición
 * puede ser de este navegador —`peticionId`, la que se acaba de enviar— o de
 * otro —la que dice el backend por `/estado` (H-3)—.
 *
 * Al terminar, la lectura vuelve **sola** (RF-ESP-03) con un aviso de qué pasó:
 * si se publicó, dónde ver la versión de antes; si no, **por qué**, y que se
 * sigue leyendo el texto de siempre (RF-PET-06, CA-7, CA-27).
 */
export function PuertaDeEspera({
  token,
  peticionId = null,
  onPeticionTerminada,
  children,
}: {
  token: string;
  peticionId?: number | null;
  /** Quien monta decide si cambia de enlace: cada tirada tiene su token. */
  onPeticionTerminada?: (peticion: Peticion) => void;
  children: ReactNode;
}) {
  const remota = useRegeneracionEnCurso(token);
  const cliente = useQueryClient();
  const [cerradas, setCerradas] = useState<number[]>([]);
  const [final, setFinal] = useState<Final | null>(null);

  const enCurso = peticionId ?? remota;
  if (enCurso !== null && !cerradas.includes(enCurso)) {
    return (
      <EsperaDeRegeneracion
        token={token}
        peticionId={enCurso}
        onSalir={() => setCerradas((c) => [...c, enCurso])}
        onTerminar={(peticion) => {
          setCerradas((c) => [...c, enCurso]);
          setFinal({ peticion, tokenAnterior: token });
          if (peticion.estado === "atendida") {
            // La portada y los capítulos cacheados son de antes: se piden otra vez.
            void cliente.invalidateQueries();
          }
          onPeticionTerminada?.(peticion);
        }}
      />
    );
  }

  return (
    <>
      {final ? <Resultado final={final} tokenActual={token} /> : null}
      {children}
    </>
  );
}

function Resultado({ final, tokenActual }: { final: Final; tokenActual: string }) {
  const { peticion, tokenAnterior } = final;
  if (peticion.estado === "descartada") {
    return (
      <div className="hoja resultado">
        <Aviso tono="error">
          No se pudo aplicar tu corrección
          {peticion.resultado ? `: ${peticion.resultado}` : "."} Sigues leyendo el texto de siempre.
        </Aviso>
      </div>
    );
  }
  return (
    <div className="hoja resultado" role="status">
      <p className="resultado__texto">
        Tu corrección ya está en la novela. Los capítulos reescritos van marcados en el sumario.
      </p>
      {tokenAnterior !== tokenActual ? (
        <p className="resultado__texto">
          <a className="enlace" href={`/?token=${encodeURIComponent(tokenAnterior)}`}>
            Leer la versión de antes
          </a>
        </p>
      ) : null}
    </div>
  );
}
