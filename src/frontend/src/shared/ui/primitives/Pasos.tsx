/**
 * Una secuencia de pasos con el actual marcado. **Aquí la numeración sí es
 * información**: los pasos van en orden y ninguno se salta, así que es una
 * lista ordenada y no un adorno.
 *
 * El actual lleva `aria-current="step"`; los anteriores dicen «hecho» **con
 * texto** (oculto a la vista, que ya ve la marca), no solo con color.
 *
 * `role="list"` explícito: Safari quita la semántica de lista a una `ol` con
 * `list-style: none`, y un lector de pantalla dejaría de contar los pasos.
 */
export function Pasos({
  etiqueta,
  pasos,
  actual,
}: {
  etiqueta: string;
  pasos: readonly string[];
  /** Índice, desde 0, del paso en curso. */
  actual: number;
}) {
  return (
    <ol className="pasos" role="list" aria-label={etiqueta}>
      {pasos.map((paso, indice) => {
        const hecho = indice < actual;
        const esActual = indice === actual;
        return (
          <li
            key={paso}
            className={`pasos__paso${hecho ? " pasos__paso--hecho" : ""}${esActual ? " pasos__paso--actual" : ""}`}
            aria-current={esActual ? "step" : undefined}
          >
            <span className="pasos__marca" aria-hidden="true">
              {hecho ? "✓" : indice + 1}
            </span>
            {paso}
            {hecho ? <span className="solo-lector">, hecho</span> : null}
          </li>
        );
      })}
    </ol>
  );
}
