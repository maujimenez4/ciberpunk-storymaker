import { Aviso, BarraDeProgreso, Texto } from "@/shared/ui/primitives";

import type { EstadoDeLaNovela } from "../api/entrevista";
import { duracion, estimacionRestante } from "../lib/tiempo";

function avance(datos: EstadoDeLaNovela): string {
  if (datos.en_curso !== null) {
    return `Escribiendo el capítulo ${datos.en_curso} de ${datos.total}.`;
  }
  return `Van ${datos.integrados} de ${datos.total} capítulos.`;
}

/**
 * La pantalla de la hora y media: la novela se escribe en segundo plano y quien
 * la encargó mira esto.
 *
 * **Solo la frase del capítulo va en la región viva.** El tiempo cambia cada
 * pocos segundos, y dentro de `role="status"` un lector de pantalla lo
 * anunciaría cada vez; el capítulo cambia cada ocho minutos, que es justo
 * cuando merece la pena decirlo.
 */
export function Espera({
  datos,
  desde,
  instante,
  atascada = false,
}: {
  datos: EstadoDeLaNovela | undefined;
  /** Cuando empezó la cadena, en milisegundos. */
  desde: number;
  /** El ahora con el que se pinta, en milisegundos. */
  instante: number;
  /** Lleva demasiado sin avanzar. Se avisa y **no se para nada**: puede ser
   * un capitulo largo, y quien decide si esperar es la persona. */
  atascada?: boolean;
}) {
  return (
    <section className="espera" aria-label="Tu novela se está escribiendo">
      <div role="status">
        <Texto>Se está escribiendo tu novela. Son diez capítulos, así que tarda un rato.</Texto>
        {datos !== undefined ? <p className="nota">{avance(datos)}</p> : null}
      </div>

      {datos !== undefined && datos.total > 0 ? (
        <>
          <BarraDeProgreso
            etiqueta="Capítulos de tu novela"
            total={datos.total}
            hechos={datos.integrados}
            enCurso={datos.en_curso}
            textoDelValor={`${datos.integrados} de ${datos.total} capítulos terminados`}
          />
          <p className="nota espera__tiempo">
            Empezó hace {duracion(instante - desde)}.
          </p>
          <p className="nota espera__tiempo">
            Faltan unos {duracion(estimacionRestante(datos.total, datos.integrados))}. Es una
            estimación: cada capítulo tarda unos ocho minutos.
          </p>
        </>
      ) : null}

      {atascada ? (
        <Aviso>
          Lleva mucho en este capítulo; puede que se haya detenido. Seguimos
          comprobándolo. Si en un rato sigue igual, revisa que el servidor esté en marcha.
        </Aviso>
      ) : null}
    </section>
  );
}
