import { useEffect, useRef, useState } from "react";

import { Aviso, Boton } from "@/shared/ui/primitives";

import "../lectura.css";

import {
  type CapituloEnRegeneracion,
  type Peticion,
  TERMINADAS,
  TOPE_MS,
  useEstadoDePeticion,
} from "../api/peticion";

const NOMBRES: Record<string, string> = {
  pendiente: "en cola",
  escribiendo: "reescribiéndose",
  hecho: "reescrito",
};

function frase(capitulos: CapituloEnRegeneracion[]): string {
  if (capitulos.length === 0) return "Preparando la corrección…";
  const hechos = capitulos.filter((c) => c.estado === "hecho").length;
  return `Van ${hechos} de ${capitulos.length} ${capitulos.length === 1 ? "capítulo" : "capítulos"} reescritos.`;
}

/**
 * La espera de una regeneración (D-05, RF-ESP-01..05).
 *
 * **La prosa no se sirve** mientras dura, pero esto **es una página y no un
 * modal** (C-1 del plan 2): no atrapa el foco y tiene salida. El avance es **por
 * capítulo con el estado del backend**, tal cual, sin barra inventada
 * (RF-ESP-02).
 *
 * Dos salidas, porque son dos fallos distintos con la misma cara: que el backend
 * **no responda** (RF-ESP-05) y que responda siempre «en curso» (R-3, tope de
 * quince minutos). Salir **no cancela nada**: la regeneración sigue en el
 * backend y la versión vigente nunca dejó de estar ahí.
 */
export function EsperaDeRegeneracion({
  token,
  peticionId,
  onTerminar,
  onSalir,
}: {
  token: string;
  peticionId: number;
  onTerminar: (peticion: Peticion) => void;
  onSalir: () => void;
}) {
  const consulta = useEstadoDePeticion(token, peticionId);
  const [agotada, setAgotada] = useState(false);

  useEffect(() => {
    const reloj = window.setTimeout(() => setAgotada(true), TOPE_MS);
    return () => window.clearTimeout(reloj);
  }, [peticionId]);

  const peticion = consulta.data;
  const terminada = peticion !== undefined && TERMINADAS.includes(peticion.estado);
  // Se avisa una vez, al pasar a terminada; `onTerminar` es de quien monta y
  // cambia de identidad en cada render suyo.
  const avisar = useRef(onTerminar);
  avisar.current = onTerminar;
  useEffect(() => {
    if (terminada && peticion) avisar.current(peticion);
  }, [terminada, peticion]);

  // Pegajoso: una consulta sin datos que vuelve a sondear pasa de «error» a
  // «pendiente», y la salida no puede parpadear con cada intento.
  const [sinRespuesta, setSinRespuesta] = useState(false);
  useEffect(() => {
    if (consulta.isError) setSinRespuesta(true);
    else if (consulta.isSuccess) setSinRespuesta(false);
  }, [consulta.isError, consulta.isSuccess]);

  const capitulos = peticion?.capitulos ?? [];

  return (
    <section className="hoja espera" aria-labelledby="espera-titulo">
      <h2 id="espera-titulo" className="espera__titulo">
        Reescribiendo tu novela
      </h2>
      <p className="espera__entradilla">
        Estamos aplicando tu corrección. La lectura vuelve sola en cuanto termine.
      </p>

      <p className="espera__estado" role="status">
        {sinRespuesta ? "No conseguimos saber cómo va." : frase(capitulos)}
      </p>

      {capitulos.length > 0 ? (
        <ol className="espera__capitulos">
          {capitulos.map((c) => (
            <li
              key={c.numero}
              className="espera__capitulo"
              data-testid={`cap-${c.numero}`}
              data-estado={c.estado}
            >
              <span className="espera__numero">Capítulo {c.numero}</span>
              <span className="espera__marca">{NOMBRES[c.estado] ?? c.estado}</span>
            </li>
          ))}
        </ol>
      ) : null}

      {sinRespuesta || agotada ? (
        <div className="espera__salida">
          <Aviso>
            {sinRespuesta
              ? "El servidor no responde. La corrección sigue su curso; mientras, puedes leer la versión de siempre."
              : "Está tardando más de lo normal. La corrección sigue su curso; mientras, puedes leer la versión de siempre."}
          </Aviso>
          <Boton variante="secundario" onClick={onSalir}>
            Volver a la lectura
          </Boton>
        </div>
      ) : null}
    </section>
  );
}
