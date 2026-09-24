import { Aviso, Texto } from "@/shared/ui/primitives";

import { useFicha } from "../api/lectura";

/**
 * Personajes y lugares.
 *
 * **T4 le da contenedor; el revelado progresivo es del plan 2** (D-04): una
 * entrada solo se muestra cuando quien lee ha pasado por el capitulo donde
 * aparece, y lo no revelado **no se envia escondido con CSS** — un
 * `display:none` es un spoiler a un «inspeccionar elemento» de distancia.
 */
export function QuienEsQuien({ token }: { token: string }) {
  const ficha = useFicha(token);

  if (ficha.isPending) {
    return <Texto>Buscando quién es quién…</Texto>;
  }
  if (ficha.isError || !ficha.data) {
    return <Aviso tono="error">No se pudo cargar la ficha. Vuelve a abrir el enlace.</Aviso>;
  }

  const entradas = ficha.data.entradas ?? [];
  if (entradas.length === 0) {
    return <Texto>Aquí aparecerán los personajes y lugares según vayas leyendo.</Texto>;
  }

  return (
    <dl className="ficha">
      {entradas.map((entrada) => (
        <div key={entrada.nombre} className="ficha__entrada">
          <dt className="ficha__nombre">{entrada.nombre}</dt>
          <dd className="ficha__descripcion">{entrada.descripcion}</dd>
        </div>
      ))}
    </dl>
  );
}
