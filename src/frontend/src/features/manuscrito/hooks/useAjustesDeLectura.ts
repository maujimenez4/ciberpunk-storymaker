import { useCallback, useEffect, useState } from "react";

import { type Ajustes, aplicarAjustes, guardarAjustes, leerAjustes } from "../lib/ajustes";

/**
 * Los ajustes de lectura, leídos del navegador y **aplicados a `<html>`** al
 * montar y en cada cambio.
 *
 * Se exporta por el `index.ts` para que la aplicación pueda llamarlo al
 * arrancar —que el tema no parpadee en «Creación»—; hoy lo llama la vista de
 * leer, que es donde se eligen.
 *
 * Al desmontar **no se deshace**: el tema elegido es de quien lee, no de la
 * pestaña, y apagar la noche al pasar a «Quién es quién» sería un fogonazo.
 */
export function useAjustesDeLectura() {
  const [ajustes, setAjustes] = useState<Ajustes>(leerAjustes);

  // `<html>` es un sistema externo a React: sincronizarlo es lo que es un efecto.
  useEffect(() => {
    aplicarAjustes(ajustes);
  }, [ajustes]);

  const cambiar = useCallback(
    (parcial: Partial<Ajustes>) => {
      // Se guarda en el manejador, no en el actualizador de estado: ese debe
      // ser puro, y React puede llamarlo dos veces.
      const nuevos = { ...ajustes, ...parcial };
      setAjustes(nuevos);
      guardarAjustes(nuevos);
    },
    [ajustes],
  );

  return { ajustes, cambiar };
}
