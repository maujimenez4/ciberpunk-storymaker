import { type TouchEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Aviso, Boton, Enlace, Texto } from "@/shared/ui/primitives";

import "../lectura.css";

import { API, useCapitulo, useVersion } from "../api/lectura";
import { idDeCapitulo, usePosicion } from "../hooks/usePosicion";
import { AjustesDeLectura } from "./AjustesDeLectura";
import { PieDeLectura } from "./PieDeLectura";

/**
 * La novela **página a página**, como un lector electrónico: la portada
 * —dedicatoria, novedades, sumario— y después un capítulo por página.
 *
 * Invierte D-06 («se lee bajando»), decisión de `maujimenez4` del 2026-09-25:
 * el scroll infinito no se leía como un libro. Se pasa de página con los
 * botones, con ← → y deslizando; el sumario y los enlaces `#capitulo-N` siguen
 * llevando al capítulo, y se reabre donde ibas (`usePosicion`).
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

  return (
    <Libro
      token={token}
      dedicatoria={version.data.dedicatoria ?? null}
      capitulos={version.data.capitulos ?? []}
    />
  );
}

type CapituloDelIndice = { numero: number; titulo?: string | null; cambiado?: boolean | null };

/** Cuánto hay que deslizar, en píxeles, para que cuente como pasar página. */
const DESLIZAMIENTO_MINIMO = 60;

/** La página 0 es la portada; la N, el capítulo N del índice. */
function Libro({
  token,
  dedicatoria,
  capitulos,
}: {
  token: string;
  dedicatoria: string | null;
  capitulos: CapituloDelIndice[];
}) {
  // Memorizado: `usePosicion` y `ir` dependen de la lista, no de su identidad.
  const numeros = useMemo(() => capitulos.map((c) => c.numero), [capitulos]);
  const { inicial, recordar } = usePosicion(token, numeros);
  const [pagina, setPagina] = useState<number>(() =>
    inicial === null ? 0 : numeros.indexOf(inicial) + 1,
  );
  const toque = useRef<{ x: number; y: number } | null>(null);
  const ultima = capitulos.length;

  const ir = useCallback(
    (destino: number) => {
      const nueva = Math.max(0, Math.min(ultima, destino));
      setPagina(nueva);
      const numero = numeros[nueva - 1];
      if (numero === undefined) {
        window.history.replaceState({}, "", window.location.pathname + window.location.search);
      } else {
        recordar(numero);
      }
      // Una página nueva empieza arriba, como al pasar la hoja.
      document.documentElement.scrollTop = 0;
    },
    [ultima, recordar, numeros],
  );

  const irAlCapitulo = (numero: number) => ir(numeros.indexOf(numero) + 1);

  useEffect(() => {
    function alPulsar(evento: KeyboardEvent) {
      if (evento.altKey || evento.ctrlKey || evento.metaKey || evento.shiftKey) return;
      const destino = evento.target;
      // Escribir una corrección o mover un deslizador no pasa página.
      if (
        destino instanceof Element &&
        destino.closest("input, textarea, select, [contenteditable='true']")
      ) {
        return;
      }
      if (evento.key === "ArrowRight") ir(pagina + 1);
      if (evento.key === "ArrowLeft") ir(pagina - 1);
    }
    window.addEventListener("keydown", alPulsar);
    return () => window.removeEventListener("keydown", alPulsar);
  }, [ir, pagina]);

  const alEmpezarAToca = (evento: TouchEvent) => {
    const t = evento.touches[0];
    toque.current = t ? { x: t.clientX, y: t.clientY } : null;
  };
  const alSoltar = (evento: TouchEvent) => {
    const inicio = toque.current;
    const fin = evento.changedTouches[0];
    toque.current = null;
    if (!inicio || !fin) return;
    const dx = fin.clientX - inicio.x;
    const dy = fin.clientY - inicio.y;
    // Solo un gesto claramente horizontal: bajar leyendo no pasa página.
    if (Math.abs(dx) < DESLIZAMIENTO_MINIMO || Math.abs(dy) > Math.abs(dx) / 2) return;
    ir(dx < 0 ? pagina + 1 : pagina - 1);
  };

  const actual = capitulos[pagina - 1];

  return (
    <article className="lectura" onTouchStart={alEmpezarAToca} onTouchEnd={alSoltar}>
      {actual === undefined ? (
        <div className="lectura__portada">
          {dedicatoria ? <p className="dedicatoria">{dedicatoria}</p> : null}

          <Novedades
            numeros={capitulos.filter((c) => c.cambiado).map((c) => c.numero)}
            onIr={irAlCapitulo}
          />

          <Sumario capitulos={capitulos} onIr={irAlCapitulo} />

          <p className="nota">
            <Enlace href={`/api${API.pdf(token)}`}>Descargar la novela en PDF</Enlace>
          </p>
        </div>
      ) : (
        <CapituloLeido
          key={actual.numero}
          token={token}
          numero={actual.numero}
          total={capitulos.length}
          titulo={actual.titulo}
        />
      )}

      <nav className="paso" aria-label="Pasar página">
        {pagina === 0 ? (
          <Boton className="boton boton--principal paso__siguiente" onClick={() => ir(1)} disabled={ultima === 0}>
            Empezar a leer ›
          </Boton>
        ) : (
          <>
            <Boton variante="discreto" className="boton boton--discreto paso__anterior" onClick={() => ir(pagina - 1)}>
              ‹ Anterior
            </Boton>
            <span className="paso__donde">{`Capítulo ${pagina} de ${ultima}`}</span>
            <Boton
              className="boton boton--principal paso__siguiente"
              onClick={() => ir(pagina + 1)}
              disabled={pagina === ultima}
            >
              Siguiente ›
            </Boton>
          </>
        )}
      </nav>

      {/* Los mandos van abajo y fijos, no arriba: a mitad del capítulo siete,
          cambiar la letra no puede exigir volver al principio. */}
      <div className="lectura__pie">
        <div className="lectura__pie-medida">
          <PieDeLectura token={token} numeros={numeros} />
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
function Novedades({ numeros, onIr }: { numeros: number[]; onIr: (numero: number) => void }) {
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
            <a
              className="enlace"
              href={`#${idDeCapitulo(numero)}`}
              aria-label={`Capítulo ${numero}`}
              onClick={(evento) => {
                evento.preventDefault();
                onIr(numero);
              }}
            >
              {numero}
            </a>
          </span>
        ))}
        .
      </p>
    </aside>
  );
}

/** El índice de la portada. Cada entrada abre la página de su capítulo. */
function Sumario({
  capitulos,
  onIr,
}: {
  capitulos: CapituloDelIndice[];
  onIr: (numero: number) => void;
}) {
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
              onClick={(evento) => {
                // El `href` se queda para copiar el enlace; el clic pasa página.
                evento.preventDefault();
                onIr(capitulo.numero);
              }}
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
