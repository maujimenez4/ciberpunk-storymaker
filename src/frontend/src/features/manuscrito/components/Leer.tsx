import { Aviso, Enlace, Texto } from "@/shared/ui/primitives";

import { API, useCapitulo, useVersion } from "../api/lectura";
import { usePosicion } from "../hooks/usePosicion";

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
    <article>
      {version.data.dedicatoria ? (
        <p className="dedicatoria">{version.data.dedicatoria}</p>
      ) : null}

      <Sumario token={token} capitulos={capitulos} />

      {capitulos.map((capitulo) => (
        <CapituloLeido key={capitulo.numero} token={token} numero={capitulo.numero} titulo={capitulo.titulo} />
      ))}

      <p className="nota">
        <Enlace href={`/api${API.pdf(token)}`}>Descargar la novela en PDF</Enlace>
      </p>
    </article>
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
              href={`#capitulo-${capitulo.numero}`}
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
 */
function CapituloLeido({
  token,
  numero,
  titulo,
}: {
  token: string;
  numero: number;
  titulo?: string | null;
}) {
  const capitulo = useCapitulo(token, numero);

  return (
    <section id={`capitulo-${numero}`} className="capitulo">
      <h2 className="capitulo__titulo">
        <span className="capitulo__numero">Capítulo {numero}</span>
        {titulo ?? ""}
      </h2>
      {capitulo.isPending ? (
        <Texto>…</Texto>
      ) : capitulo.isError || !capitulo.data ? (
        <Aviso tono="error">Este capítulo no se pudo cargar. Vuelve a abrir el enlace.</Aviso>
      ) : (
        parrafos(capitulo.data.texto).map((parrafo, i) => <Texto key={i}>{parrafo}</Texto>)
      )}
    </section>
  );
}

/** La prosa llega con saltos de línea; cada bloque es un párrafo. */
function parrafos(texto: string): string[] {
  return texto.split(/\n\s*\n/).filter((p) => p.trim() !== "");
}
