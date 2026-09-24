import { Aviso, Texto } from "@/shared/ui/primitives";

import "../lectura.css";

import { type Ficha, useFicha } from "../api/lectura";
import { idDeCapitulo } from "../hooks/usePosicion";

type Entrada = NonNullable<Ficha["entradas"]>[number];

/**
 * «Quién viaja contigo»: personajes y lugares como etiquetas de equipaje
 * (plan 4, enmienda 1).
 *
 * **El revelado progresivo es del backend** (D-04): una entrada solo llega
 * cuando quien lee ha pasado por el capítulo donde aparece, y lo no revelado
 * **no se envía escondido con CSS** — un `display:none` es un spoiler a un
 * «inspeccionar elemento» de distancia.
 *
 * **Por eso la etiqueta de las pendientes no lleva número.** La maqueta pide
 * un sello «+N», pero la ficha no dice cuántas faltan (RF-FIC-05 no está en el
 * contrato todavía) y deducirlo exigiría recibirlas. Dice, sin contar, dónde
 * está lo que falte; cuando el backend mande la cifra, el sello la llevará.
 *
 * Cambiar de pestaña para ir a un capítulo es de la página, no de la ficha: si
 * quien la monta pasa `onIrACapitulo`, los números son enlaces; si no, texto.
 */
export function QuienEsQuien({
  token,
  onIrACapitulo,
}: {
  token: string;
  onIrACapitulo?: (numero: number) => void;
}) {
  const ficha = useFicha(token);

  if (ficha.isPending) {
    return <Texto>Buscando quién es quién…</Texto>;
  }
  if (ficha.isError || !ficha.data) {
    return <Aviso tono="error">No se pudo cargar la ficha. Vuelve a abrir el enlace.</Aviso>;
  }

  const entradas = ficha.data.entradas ?? [];

  return (
    <section className="viajeros" aria-labelledby="viajeros-titulo">
      <h2 id="viajeros-titulo" className="viajeros__titulo">
        Quién viaja contigo
      </h2>
      <p className="viajeros__entradilla">Aparecen a medida que lees.</p>

      {entradas.length === 0 ? (
        <Texto>Aquí aparecerán los personajes y lugares según vayas leyendo.</Texto>
      ) : (
        <ul className="viajeros__lista">
          {entradas.map((entrada) => (
            <li key={entrada.nombre}>
              <Etiqueta entrada={entrada} onIrACapitulo={onIrACapitulo} />
            </li>
          ))}
          <li>
            <div className="etiqueta etiqueta--pendiente">
              <span className="sello viajeros__sello" aria-hidden="true">
                <span className="sello__cifra">+</span>
              </span>
              <p className="viajeros__pendientes">
                Si falta alguien, te espera en un capítulo que aún no has leído.
              </p>
            </div>
          </li>
        </ul>
      )}
    </section>
  );
}

function Etiqueta({
  entrada,
  onIrACapitulo,
}: {
  entrada: Entrada;
  onIrACapitulo: ((numero: number) => void) | undefined;
}) {
  const capitulos = entrada.capitulos ?? [];
  return (
    <article className="etiqueta">
      <span className="etiqueta__ojal" aria-hidden="true" />
      <div className="etiqueta__cuerpo">
        <h3 className="etiqueta__nombre">{entrada.nombre}</h3>
        {entrada.descripcion ? <p className="etiqueta__descripcion">{entrada.descripcion}</p> : null}
        {capitulos.length > 0 ? (
          <p className="etiqueta__capitulos">
            {capitulos.length === 1 ? "Capítulo " : "Capítulos "}
            {capitulos.map((numero, i) => (
              <span key={numero}>
                {separador(i, capitulos.length)}
                {onIrACapitulo ? (
                  <a
                    className="enlace"
                    href={`#${idDeCapitulo(numero)}`}
                    aria-label={`Capítulo ${numero}`}
                    onClick={() => onIrACapitulo(numero)}
                  >
                    {numero}
                  </a>
                ) : (
                  numero
                )}
              </span>
            ))}
          </p>
        ) : null}
      </div>
    </article>
  );
}

/** «1, 2 y 3»: coma entre los primeros, «y» antes del último. */
function separador(indice: number, total: number): string {
  if (indice === 0) return "";
  return indice === total - 1 ? " y " : ", ";
}
