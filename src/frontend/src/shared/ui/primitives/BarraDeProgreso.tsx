import type { CSSProperties } from "react";

type Tramo = "hecho" | "en-curso" | "pendiente";

function tramoDe(posicion: number, hechos: number, enCurso: number | null): Tramo {
  if (posicion <= hechos) return "hecho";
  if (posicion === enCurso) return "en-curso";
  return "pendiente";
}

/**
 * Hasta qué parada llega lo recorrido, contando desde 0 y con la meta en
 * `total`: hasta la que va en curso, o hasta la meta si ya está todo hecho, o
 * hasta la última hecha.
 */
function recorridoHasta(total: number, hechos: number, enCurso: number | null): number {
  if (hechos >= total) return total;
  if (enCurso !== null) return enCurso - 1;
  return Math.max(hechos - 1, 0);
}

/**
 * Un avance que se cuenta **por unidades**, no por porcentaje. En el cuaderno
 * de viaje (plan 4, enmienda 1) es un **mapa de ruta**: una parada por unidad
 * sobre una línea de puntos, lo recorrido en rojo de sello, las hechas en
 * estilográfica, la que va en curso sellada con su número y una bandera en la
 * meta.
 *
 * Sin lógica de negocio: no sabe qué es un capítulo. Quien la usa le da el
 * nombre (`etiqueta`) y la frase que un lector de pantalla dirá en lugar del
 * número (`textoDelValor`); el color **nunca** es el único que lo dice. El
 * dibujo entero es `aria-hidden`: lo que se oye es el `progressbar`.
 *
 * `enCurso` es la posición, contada desde 1, de la unidad que se está haciendo.
 */
export function BarraDeProgreso({
  etiqueta,
  total,
  hechos,
  enCurso = null,
  textoDelValor,
  salida = "Salida",
  meta = "Publicación",
}: {
  etiqueta: string;
  total: number;
  hechos: number;
  enCurso?: number | null;
  textoDelValor: string;
  /** El nombre del principio del camino. */
  salida?: string;
  /** El nombre del final del camino, bajo la bandera. */
  meta?: string;
}) {
  const unidades = Math.max(total, 0);
  const posiciones = Array.from({ length: unidades }, (_, i) => i + 1);
  const ruta = {
    "--paradas": unidades + 1,
    "--recorrido": recorridoHasta(unidades, hechos, enCurso),
  } as CSSProperties;
  return (
    <div
      className="barra"
      role="progressbar"
      aria-label={etiqueta}
      aria-valuemin={0}
      aria-valuemax={total}
      aria-valuenow={hechos}
      aria-valuetext={textoDelValor}
    >
      <div className="barra__ruta" style={ruta} aria-hidden="true">
        {posiciones.map((posicion) => {
          const tramo = tramoDe(posicion, hechos, enCurso);
          return (
            <span
              key={posicion}
              className={`barra__tramo barra__tramo--${tramo}${tramo === "en-curso" ? " sello" : ""}`}
              data-tramo={tramo}
            >
              {tramo === "en-curso" ? posicion : null}
            </span>
          );
        })}
        <span className="barra__meta">
          <svg
            aria-hidden="true"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M4 20V5h11l-2 4 2 4H4" />
          </svg>
        </span>
      </div>
      <div className="barra__extremos" aria-hidden="true">
        <span>{salida}</span>
        <span>{meta}</span>
      </div>
    </div>
  );
}
