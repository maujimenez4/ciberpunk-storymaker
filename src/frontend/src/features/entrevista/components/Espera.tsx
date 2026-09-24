import { Aviso, BarraDeProgreso } from "@/shared/ui/primitives";

import type { EstadoDeLaNovela } from "../api/entrevista";
import { estimacionRestante, frasesDelViaje } from "../lib/tiempo";

/** La frase del capítulo. La metáfora del viaje decora; lo que se dice es
 * «capítulo», que es lo que la persona está esperando. */
function avance(datos: EstadoDeLaNovela): string {
  if (datos.en_curso !== null) {
    return `Va por el capítulo ${datos.en_curso} de ${datos.total}.`;
  }
  return `Van ${datos.integrados} de ${datos.total} capítulos.`;
}

/**
 * La pantalla de la hora y media: la novela se escribe en segundo plano y quien
 * la encargó mira el mapa de ruta (maqueta D-Progreso).
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
    <section className="viaje" aria-label="Por dónde va tu novela">
      <p className="viaje__estado" role="status">
        {datos !== undefined ? avance(datos) : "Arrancando el primer capítulo…"}
      </p>

      {datos !== undefined && datos.total > 0 ? (
        <>
          <BarraDeProgreso
            etiqueta="Capítulos de tu novela"
            total={datos.total}
            hechos={datos.integrados}
            enCurso={datos.en_curso}
            textoDelValor={`${datos.integrados} de ${datos.total} capítulos terminados`}
          />
          <p className="viaje__tiempo">
            {frasesDelViaje(instante - desde, estimacionRestante(datos.total, datos.integrados))}{" "}
            Es una estimación: cada capítulo tarda unos ocho. Puedes cerrar la página; al volver,
            seguirá aquí.
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
