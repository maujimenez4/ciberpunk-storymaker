import { Aviso, Boton, Enlace, Texto } from "@/shared/ui/primitives";
import { Pagina } from "@/shared/ui/patterns/Pagina";
import { nombreDeCapitulo } from "@/shared/lib/formato";

/**
 * **Andamio para revisar el diseño, no una página del producto.**
 *
 * T4 decide cómo se ve todo lo demás, y eso no se juzga leyendo tokens: se
 * juzga mirándolo. Esta pantalla aplica los primitivos sobre contenido de una
 * novela cualquiera para poder verlo hoy, antes de que existan las páginas
 * reales — que son T5, T6 y T7, y leen datos que el backend aún no publica.
 *
 * Se retira cuando el router de T3 monte las páginas de verdad. Está anotada en
 * las Desviaciones del plan.
 */

const CAPITULOS = [
  "La casa de la playa",
  "Lo que no se dijo en la cena",
  "El coche averiado",
  "Agosto",
];

export function Muestra() {
  return (
    <Pagina titulo="El verano del 98">
      <p className="dedicatoria">
        Para Marta, que siempre volvía la última del agua.
      </p>

      <Texto>
        La casa olía a sal y a cerrado, como cada año, y Marta supo antes de
        encender la luz que nadie había abierto las ventanas desde septiembre.
      </Texto>
      <Texto>
        Dejó la bolsa en el suelo. Fuera todavía quedaba algo de tarde, esa hora
        en que el mar se pone del color de una moneda vieja y el pueblo entero
        parece estar esperando a que pase algo.
      </Texto>
      <Texto>
        No pasó nada. No pasó nada durante tres días, y después pasó todo.
      </Texto>

      <nav aria-label="Capítulos">
        <ol className="indice">
          {CAPITULOS.map((titulo, i) => (
            <li key={titulo}>
              <Enlace href={`#capitulo-${i + 1}`}>
                <span className="indice__numero">{nombreDeCapitulo(i + 1)}</span>
                <span className="indice__titulo">{titulo}</span>
              </Enlace>
            </li>
          ))}
        </ol>
      </nav>

      <Aviso tono="aviso">
        Se regeneraron dos capítulos el 24 de septiembre. Están marcados en el
        índice.
      </Aviso>

      <Aviso tono="error">
        Este enlace ya no vale. Pide uno nuevo a quien te regaló la novela.
      </Aviso>

      <p className="nota">Diez capítulos · 12.400 palabras</p>

      <Boton>Seguir leyendo</Boton>
    </Pagina>
  );
}
