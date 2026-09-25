import { Aviso, Enlace, Texto } from "@/shared/ui/primitives";

import "../lectura.css";

import { API, useCapitulo, useVersion } from "../api/lectura";
import { idDeCapitulo, usePosicion } from "../hooks/usePosicion";
import { AjustesDeLectura } from "./AjustesDeLectura";
import { PieDeLectura } from "./PieDeLectura";

/**
 * La novela entera, continua. Dedicatoria, sumario y los capítulos encadenados.
 *
 * **Se lee bajando, no saltando entre páginas** (D-06): el sumario lleva a un
 * fragmento de esta misma página, no a otra dirección.
 */
export function Leer({ token }: { token: string }) {
  const version = useVersion(token);

  if (version.isPending) {
    return <Texto>Abriendo tu novela…</Texto>;
  }
  if (version.isError || !version.data) {
    return (
      <Aviso tono="error">
        Este enlace ya no vale. Pide uno nuevo a quien te regaló la novela.
      </Aviso>
    );
  }

  const capitulos = version.data.capitulos ?? [];

  return (
    <article className="lectura">
      {version.data.dedicatoria ? (
        <p className="dedicatoria">{version.data.dedicatoria}</p>
      ) : null}

      <Novedades numeros={capitulos.filter((c) => c.cambiado).map((c) => c.numero)} />

      <Sumario token={token} capitulos={capitulos} />

      {capitulos.map((capitulo) => (
        <CapituloLeido
          key={capitulo.numero}
          token={token}
          numero={capitulo.numero}
          total={capitulos.length}
          titulo={capitulo.titulo}
        />
      ))}

      <p className="nota">
        <Enlace href={`/api${API.pdf(token)}`}>Descargar la novela en PDF</Enlace>
      </p>

      {/* Los mandos van abajo y fijos, no arriba: a mitad del capítulo siete,
          cambiar la letra no puede exigir volver al principio. */}
      <div className="lectura__pie">
        <div className="lectura__pie-medida">
          <PieDeLectura token={token} numeros={capitulos.map((c) => c.numero)} />
          <AjustesDeLectura />
        </div>
      </div>
    </article>
  );
}

/**
 * Qué cambió respecto a la tirada anterior (RF-IND-02, RF-NOV-01), con la marca
 * `cambiado` **que da el backend**. En la primera versión no hay ninguna y esto
 * no se pinta (RF-IND-03): «nada ha cambiado» en un regalo recién abierto no
 * informa de nada.
 */
function Novedades({ numeros }: { numeros: number[] }) {
  if (numeros.length === 0) return null;
  return (
    <aside className="hoja novedades" aria-labelledby="novedades-titulo">
      <h2 id="novedades-titulo" className="novedades__titulo">
        Novedades de esta versión
      </h2>
      <p className="novedades__texto">
        {numeros.length === 1 ? "Se reescribió el capítulo " : "Se reescribieron los capítulos "}
        {numeros.map((numero, i) => (
          <span key={numero}>
            {i === 0 ? "" : i === numeros.length - 1 ? " y " : ", "}
            <a className="enlace" href={`#${idDeCapitulo(numero)}`} aria-label={`Capítulo ${numero}`}>
              {numero}
            </a>
          </span>
        ))}
        .
      </p>
    </aside>
  );
}

function Sumario({
  token,
  capitulos,
}: {
  token: string;
  capitulos: { numero: number; titulo?: string | null; cambiado?: boolean | null }[];
}) {
  const { recordar } = usePosicion(
    token,
    capitulos.map((c) => c.numero),
  );

  return (
    <nav aria-label="Capítulos">
      <ol className="indice">
        {capitulos.map((capitulo) => (
          <li key={capitulo.numero}>
            <a
              className="enlace"
              href={`#${idDeCapitulo(capitulo.numero)}`}
              data-testid={`sumario-${capitulo.numero}`}
              data-cambiado={String(Boolean(capitulo.cambiado))}
              onClick={() => recordar(capitulo.numero)}
            >
              <span className="indice__numero">Capítulo {capitulo.numero}</span>
              <span className="indice__titulo">{capitulo.titulo ?? ""}</span>
              {/* La marca la da el backend (`RF-IND-02`): el navegador **no la
                  calcula**, porque comparar textos aquí daría otra respuesta que
                  la del servidor y ninguna de las dos sería la buena. */}
              {capitulo.cambiado ? <span className="indice__marca"> · reescrito</span> : null}
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}

/**
 * Un capítulo.
 *
 * `content-visibility: auto` en `.capitulo` deja que el navegador **salte el
 * renderizado** de lo que no se ve. No se virtualiza, y el motivo no es la
 * dependencia: **rompería Ctrl+F**, y en un libro buscar una frase es una
 * función que el lector espera.
 *
 * **El sello es adorno, el número no** (plan 4, enmienda 1). «capítulo 3 de 10»
 * va estampado en el margen y se oculta al lector de pantalla; el número que se
 * oye es el del título, que sigue ahí aunque no se vea. La línea «Tercera
 * parada» es otra forma de decir lo mismo, y también se calla.
 */
function CapituloLeido({
  token,
  numero,
  total,
  titulo,
}: {
  token: string;
  numero: number;
  total: number;
  titulo?: string | null;
}) {
  const capitulo = useCapitulo(token, numero);
  const parada = nombreDeParada(numero);

  return (
    <section id={idDeCapitulo(numero)} className="capitulo">
      <div className="sello capitulo__sello" aria-hidden="true">
        <span className="sello__linea">capítulo</span>
        <span className="sello__cifra">{numero}</span>
        <span className="sello__linea">de {total}</span>
      </div>
      <div className="margen-rojo capitulo__columna">
        {parada ? (
          <p className="capitulo__parada" aria-hidden="true">
            {parada}
          </p>
        ) : null}
        <h2 className="capitulo__titulo">
          <span className="capitulo__numero">Capítulo {numero}. </span>
          {titulo ?? ""}
        </h2>
        {capitulo.isPending ? (
          <Texto>…</Texto>
        ) : capitulo.isError || !capitulo.data ? (
          <Aviso tono="error">Este capítulo no se pudo cargar. Vuelve a abrir el enlace.</Aviso>
        ) : (
          parrafos(capitulo.data.texto).map((parrafo, i) => <Texto key={i}>{parrafo}</Texto>)
        )}
      </div>
    </section>
  );
}

const PARADAS = [
  "Primera",
  "Segunda",
  "Tercera",
  "Cuarta",
  "Quinta",
  "Sexta",
  "Séptima",
  "Octava",
  "Novena",
  "Décima",
] as const;

/** «Tercera parada». Más allá de diez no se inventa ordinal: se omite. */
function nombreDeParada(numero: number): string | null {
  const ordinal = PARADAS[numero - 1];
  return ordinal ? `${ordinal} parada` : null;
}

/** La prosa llega con saltos de línea; cada bloque es un párrafo. */
function parrafos(texto: string): string[] {
  return texto.split(/\n\s*\n/).filter((p) => p.trim() !== "");
}
