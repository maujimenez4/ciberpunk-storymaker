import { useMemo } from "react";

import "../lectura.css";

import { useCapitulos } from "../api/lectura";
import { useLugarDeLectura } from "../hooks/useLugarDeLectura";
import { contarPalabras, minutosQueQuedan, porcentajeLeido } from "../lib/progreso";

/**
 * El pie de lectura: cuánto de la novela va leído y cuántos minutos quedan
 * del capítulo en curso. Es el gesto más reconocible de un lector electrónico.
 *
 * **No es una región viva, a propósito.** El número cambia con cada línea que
 * se baja; con `aria-live` o `role="status"`, un lector de pantalla lo
 * anunciaría sin parar encima de la novela que está leyendo en voz alta. Queda
 * como texto normal: quien lo quiera saber, llega a él.
 *
 * Las palabras se cuentan del texto que la lectura ya pidió —misma caché, sin
 * peticiones nuevas— y el porcentaje no se enseña hasta tenerlas todas: con
 * la mitad de los capítulos sin llegar, sería un número falso.
 */
export function PieDeLectura({ token, numeros }: { token: string; numeros: readonly number[] }) {
  const capitulos = useCapitulos(token, numeros);
  // `useQueries` devuelve un array nuevo en cada render; lo que cambia de
  // verdad es qué textos han llegado, y eso lo dice esta firma.
  const firma = capitulos.map((c) => c.dataUpdatedAt).join(",");
  const textos = capitulos.map((c) => c.data?.texto ?? null);
  // Contar doce mil palabras en cada desplazamiento sería trabajo tirado.
  const palabras = useMemo(
    () => textos.map((t) => (t === null ? null : contarPalabras(t))),
    // Se recuenta cuando cambia la firma, no cuando cambia la identidad de
    // `textos`, que es nueva en cada render.
    [firma],
  );
  const lugar = useLugarDeLectura(numeros, firma);

  if (!lugar) {
    return null;
  }

  const indice = numeros.indexOf(lugar.numero);
  const delCapitulo = palabras[indice] ?? null;
  const todas = palabras.every((p): p is number => p !== null) ? (palabras as number[]) : null;
  const porcentaje = todas ? porcentajeLeido(todas, indice, lugar.fraccion) : null;
  const minutos = delCapitulo === null ? null : minutosQueQuedan(delCapitulo, lugar.fraccion);

  return (
    <div className="progreso">
      <span className="progreso__minutos">
        {minutos === null
          ? null
          : minutos === 0
            ? "Terminaste este capítulo"
            : `Quedan ${minutos} min en este capítulo`}
      </span>
      {porcentaje === null ? null : (
        <span className="progreso__donde">
          {/* El camino es la misma cifra que el porcentaje, dibujada: se oculta
              al lector de pantalla para no decirla dos veces. Una línea de
              puntos, lo recorrido en tinta de sello y un punto donde vas
              (plan 4, enmienda 1). */}
          <span className="progreso__camino" aria-hidden="true">
            <span
              className="progreso__recorrido"
              style={{ transform: `scaleX(${porcentaje / 100})` }}
            />
            <span className="progreso__punto" style={{ left: `${porcentaje}%` }} />
          </span>
          <span className="progreso__porcentaje">{`${porcentaje}\u00a0%`}</span>
        </span>
      )}
    </div>
  );
}
