import { BrowserRouter, Route, Routes } from "react-router-dom";

import { Pagina } from "@/shared/ui/patterns/Pagina";
import { Texto } from "@/shared/ui/primitives";

import { Muestra } from "./Muestra";
import { PATRONES } from "./router";
import { Proveedores } from "./providers";

/**
 * El árbol de la aplicación: proveedores, router y las cinco rutas.
 *
 * **Las páginas de verdad son T5, T6 y T7**, y leen datos que el backend
 * todavía no publica (T9 de la Fase 4). Hasta entonces cada ruta responde con
 * lo que sabe decir hoy, que no es lo mismo que responder en blanco: `CA-21`
 * pide que las cinco **respondan**, y una ruta registrada que pinta nada
 * cumpliría el criterio sin que nadie viera nada.
 */

function Preparando({ titulo }: { titulo: string }) {
  return (
    <Pagina titulo={titulo}>
      <Texto>
        Esta parte de tu novela todavía se está preparando. Vuelve con el enlace
        que te dieron dentro de un rato.
      </Texto>
    </Pagina>
  );
}

/**
 * **El estado vacío de las novedades, y no es un andamio.**
 *
 * La desviación que quedó abierta en este plan preguntaba qué responde esta
 * ruta mientras la Fase 3 no exista. La respuesta es que **ya tiene un estado
 * propio y permanente**: `RF-IND-03` dice que en la primera versión publicada
 * no hay marca de cambio, porque no hay ninguna anterior con la que comparar.
 * Es decir, toda novela recién regalada abre aquí y lee exactamente esto,
 * también cuando la Fase 3 esté hecha. Lo que la Fase 3 añade es el otro caso.
 */
function Novedades() {
  return (
    <Pagina titulo="Novedades">
      <Texto>
        Esta es la primera versión de tu novela, así que no hay nada que
        comparar todavía. Si pides un cambio, aquí verás qué capítulos se
        reescribieron.
      </Texto>
    </Pagina>
  );
}

function NoEncontrada() {
  return (
    <Pagina titulo="Esta página no existe">
      <Texto>
        Comprueba el enlace que te dieron. Si lo copiaste de un mensaje, puede
        que se cortara al pegarlo.
      </Texto>
    </Pagina>
  );
}

export function Aplicacion() {
  return (
    <Proveedores>
      <BrowserRouter>
        <Routes>
          <Route path={PATRONES.portada} element={<Preparando titulo="Tu novela" />} />
          <Route path={PATRONES.indice} element={<Preparando titulo="Capítulos" />} />
          <Route path={PATRONES.capitulo} element={<Preparando titulo="Capítulo" />} />
          <Route path={PATRONES.ficha} element={<Preparando titulo="Quién es quién" />} />
          <Route path={PATRONES.novedades} element={<Novedades />} />
          {/**
           * **El andamio de T4, y solo en desarrollo.** La muestra de diseño no
           * es una página del producto: si se quedara accesible en producción
           * pasaría a serlo sin que nadie la especificara. `import.meta.env.DEV`
           * la deja fuera del `build`, así que no puede quedarse por descuido.
           * Se retira del todo cuando T5, T6 y T7 pinten las páginas reales.
           */}
          {import.meta.env.DEV && <Route path="/muestra" element={<Muestra />} />}
          <Route path="*" element={<NoEncontrada />} />
        </Routes>
      </BrowserRouter>
    </Proveedores>
  );
}
