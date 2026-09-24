type Tramo = "hecho" | "en-curso" | "pendiente";

function tramoDe(posicion: number, hechos: number, enCurso: number | null): Tramo {
  if (posicion <= hechos) return "hecho";
  if (posicion === enCurso) return "en-curso";
  return "pendiente";
}

/**
 * Un avance que se cuenta **por unidades**, no por porcentaje: un tramo por
 * unidad, los hechos llenos, el que va en curso marcado y el resto en blanco.
 *
 * Sin lógica de negocio: no sabe qué es un capítulo. Quien la usa le da el
 * nombre (`etiqueta`) y la frase que un lector de pantalla dirá en lugar del
 * número (`textoDelValor`); el color **nunca** es el único que lo dice.
 *
 * `enCurso` es la posición, contada desde 1, de la unidad que se está haciendo.
 */
export function BarraDeProgreso({
  etiqueta,
  total,
  hechos,
  enCurso = null,
  textoDelValor,
}: {
  etiqueta: string;
  total: number;
  hechos: number;
  enCurso?: number | null;
  textoDelValor: string;
}) {
  const posiciones = Array.from({ length: Math.max(total, 0) }, (_, i) => i + 1);
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
      {posiciones.map((posicion) => {
        const tramo = tramoDe(posicion, hechos, enCurso);
        return (
          <span key={posicion} className={`barra__tramo barra__tramo--${tramo}`} data-tramo={tramo} />
        );
      })}
    </div>
  );
}
