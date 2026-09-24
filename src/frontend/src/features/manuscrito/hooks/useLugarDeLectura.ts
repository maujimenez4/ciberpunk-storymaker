import { useEffect, useState } from "react";

import { type Medida, ubicar } from "../lib/progreso";
import { idDeCapitulo } from "./usePosicion";

export type Lugar = { numero: number; fraccion: number };

/**
 * En qué capítulo está quien lee y qué parte lleva, **medido en la pantalla**
 * al desplazarse.
 *
 * No sustituye a `usePosicion`: aquella decide dónde **abrir** la novela
 * (fragmento o posición guardada); esta mira dónde **está** el ojo ahora, para
 * el pie. Comparten el `id` de cada capítulo, y nada más.
 *
 * Se mide como mucho una vez por fotograma: el evento de desplazamiento llega
 * decenas de veces por segundo y `getBoundingClientRect` fuerza al navegador a
 * calcular la maquetación.
 *
 * `recargas` es cualquier valor que cambie cuando llega texto nuevo: al
 * pintarse un capítulo, cambian las alturas y hay que volver a medir.
 */
export function useLugarDeLectura(numeros: readonly number[], recargas: unknown): Lugar | null {
  const [lugar, setLugar] = useState<Lugar | null>(() =>
    numeros[0] === undefined ? null : { numero: numeros[0], fraccion: 0 },
  );
  const clave = numeros.join(",");

  useEffect(() => {
    const lista = clave === "" ? [] : clave.split(",").map(Number);
    let pendiente: number | null = null;

    function medir() {
      pendiente = null;
      const medidas: Medida[] = [];
      for (const numero of lista) {
        const seccion = document.getElementById(idDeCapitulo(numero));
        if (seccion) {
          const caja = seccion.getBoundingClientRect();
          medidas.push({ numero, arriba: caja.top, alto: caja.height });
        }
      }
      const nuevo = ubicar(medidas, window.innerHeight);
      // Sin cambio no hay render: al desplazarse dentro del mismo minuto, el
      // pie no tiene por qué pintarse otra vez.
      setLugar((antes) =>
        antes && nuevo && antes.numero === nuevo.numero && antes.fraccion === nuevo.fraccion
          ? antes
          : nuevo,
      );
    }

    function alDesplazar() {
      if (pendiente === null) {
        pendiente = window.requestAnimationFrame(medir);
      }
    }

    medir();
    window.addEventListener("scroll", alDesplazar, { passive: true });
    window.addEventListener("resize", alDesplazar);
    return () => {
      window.removeEventListener("scroll", alDesplazar);
      window.removeEventListener("resize", alDesplazar);
      if (pendiente !== null) {
        window.cancelAnimationFrame(pendiente);
      }
    };
  }, [clave, recargas]);

  return lugar;
}
