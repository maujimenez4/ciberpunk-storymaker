import { useState } from "react";

import { Entrevista } from "@/features/entrevista";
import { Leer, QuienEsQuien } from "@/features/manuscrito";
import { Pagina } from "@/shared/ui/patterns/Pagina";
import { Texto } from "@/shared/ui/primitives";

import { VISTAS, type Vista, vistaDe } from "./router";

const PESTANAS = [
  { vista: VISTAS.entrevista, etiqueta: "La entrevista" },
  { vista: VISTAS.leer, etiqueta: "Leer" },
  { vista: VISTAS.quienEsQuien, etiqueta: "Quién es quién" },
] as const;

/**
 * **Una dirección y tres pestañas** (D-07). Se rellena la entrevista, se pulsa,
 * y la pestaña de leer se activa **con la novela dentro**: sin cambiar de
 * dirección, sin perder lo que había en pantalla, sin una segunda carga.
 *
 * El `token` sigue protegiendo la lectura y sigue siendo lo que se manda de
 * regalo; lo que cambia es que abrirlo no lleva a otra página, sino a esta con
 * la pestaña de leer ya puesta.
 *
 * **La pestaña de la entrevista queda visible siempre, y es deliberado.** Lo
 * que protege el brief no es esconder una pestaña —quien sepa manipular la
 * dirección la pediría igual— sino que **ninguna ruta de lectura del backend
 * sirve la entrevista**: comprobado sobre el OpenAPI, las cinco devuelven
 * versión, capítulo, ficha, PDF y versiones. Una separación de interfaz no es
 * una frontera de seguridad, y fingir que lo es sería peor que no tenerla.
 */
export function Paginas() {
  const parametros = new URLSearchParams(window.location.search);
  const [token, setToken] = useState<string | null>(parametros.get("token"));
  const [escribiendo, setEscribiendo] = useState(false);
  const [vista, setVista] = useState<Vista>(
    parametros.get("token") ? vistaDe(window.location.search) : VISTAS.entrevista,
  );

  const hayNovela = token !== null;

  return (
    <Pagina titulo="Tu novela">
      <div className="pestanas" role="tablist" aria-label="Tu novela">
        {PESTANAS.map((pestana) => {
          const desactivada = pestana.vista !== VISTAS.entrevista && !hayNovela;
          return (
            <button
              key={pestana.vista}
              type="button"
              role="tab"
              id={`pestana-${pestana.vista}`}
              aria-selected={vista === pestana.vista}
              aria-controls={`panel-${pestana.vista}`}
              // Una pestaña que se puede pulsar y no lleva a nada enseña una
              // pantalla vacía, y una pantalla vacía se lee como un fallo.
              disabled={desactivada}
              className={vista === pestana.vista ? "pestana pestana--activa" : "pestana"}
              onClick={() => setVista(pestana.vista)}
            >
              {pestana.etiqueta}
            </button>
          );
        })}
      </div>

      <div role="tabpanel" id={`panel-${vista}`} aria-labelledby={`pestana-${vista}`} tabIndex={0}>
        {vista === VISTAS.entrevista ? (
          <>
            <Entrevista
              onNovelaLanzada={() => setEscribiendo(true)}
              onNovelaPublicada={(suyo) => {
                setToken(suyo);
                setEscribiendo(false);
                setVista(VISTAS.leer);
              }}
              onFallo={() => setEscribiendo(false)}
              deshabilitado={escribiendo}
            />
            {escribiendo ? <Escribiendo /> : null}
          </>
        ) : vista === VISTAS.leer && token ? (
          <Leer token={token} />
        ) : token ? (
          <QuienEsQuien token={token} />
        ) : null}
      </div>

    </Pagina>
  );
}

function Escribiendo() {
  return (
    <div className="comprobacion" role="status">
      <Texto>
        Se está escribiendo tu novela. Son diez capítulos, así que tarda un rato.
      </Texto>
    </div>
  );
}
