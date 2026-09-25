import { type KeyboardEvent, useEffect, useRef, useState } from "react";

import { type AvanceDeLaNovela, Entrevista, leerNovelaEnCurso } from "@/features/entrevista";
import { Leer, PuertaDeEspera, QuienEsQuien, useAjustesDeLectura } from "@/features/manuscrito";
import { Pagina } from "@/shared/ui/patterns/Pagina";

import "./navegacion.css";
import { VISTAS, type Vista, vistaDe } from "./router";

const PESTANAS = [
  { vista: VISTAS.entrevista, etiqueta: "Creación" },
  { vista: VISTAS.leer, etiqueta: "Leer" },
  { vista: VISTAS.quienEsQuien, etiqueta: "Quién es quién" },
] as const;

const ID_DEL_MOTIVO = "pestanas-motivo";

/** Dónde está la novela, visto desde la navegación: sin empezar, en marcha (con
 * o sin avance conocido todavía), o publicada (hay token). */
type Novela = { tipo: "ninguna" } | { tipo: "en-curso"; avance: AvanceDeLaNovela | null };

/** Por qué «Leer» y «Quién es quién» siguen apagadas, y cuándo se abren. */
function motivo(novela: Novela): string {
  if (novela.tipo === "ninguna") {
    return "Leer y Quién es quién se abren cuando la novela esté escrita.";
  }
  const avance = novela.avance;
  if (avance === null) return "Se abren cuando termine la novela.";
  if (avance.enCurso !== null) {
    return `Se abren cuando termine la novela. Va por el capítulo ${avance.enCurso} de ${avance.total}.`;
  }
  return `Se abren cuando termine la novela. Van ${avance.integrados} de ${avance.total} capítulos.`;
}

/**
 * **Una dirección y tres pestañas** (D-07). Se rellena la entrevista, se pulsa,
 * y la pestaña de leer se activa **con la novela dentro**: sin cambiar de
 * dirección, sin perder lo que había en pantalla, sin una segunda carga.
 *
 * La primera se llama **«Creación»** (plan 4, T3) y enseña lo que toque según
 * la fase: el formulario, o el progreso si hay una novela en marcha. Tras una
 * recarga a mitad de novela se abre ahí, y las otras dos dicen **por qué**
 * están apagadas y cuándo se abren, en texto visible y en `aria-describedby`.
 *
 * El `token` sigue protegiendo la lectura y sigue siendo lo que se manda de
 * regalo; lo que cambia es que abrirlo no lleva a otra página, sino a esta con
 * la pestaña de leer ya puesta.
 *
 * **La pestaña de creación queda visible siempre, y es deliberado.** Lo que
 * protege el brief no es esconder una pestaña —quien sepa manipular la
 * dirección la pediría igual— sino que **ninguna ruta de lectura del backend
 * sirve la entrevista**: comprobado sobre el OpenAPI, las cinco devuelven
 * versión, capítulo, ficha, PDF y versiones. Una separación de interfaz no es
 * una frontera de seguridad, y fingir que lo es sería peor que no tenerla.
 */
export function Paginas() {
  // El tema y el tamaño que se eligieron en «Aa» valen para toda la página, no
  // solo para «Leer»: quien leyó de noche no quiere volver a la creación en claro.
  useAjustesDeLectura();
  const parametros = new URLSearchParams(window.location.search);
  const [token, setToken] = useState<string | null>(parametros.get("token"));
  const [escribiendo, setEscribiendo] = useState(false);
  const [vista, setVista] = useState<Vista>(
    parametros.get("token") ? vistaDe(window.location.search) : VISTAS.entrevista,
  );
  const [novela, setNovela] = useState<Novela>(() =>
    leerNovelaEnCurso() === null ? { tipo: "ninguna" } : { tipo: "en-curso", avance: null },
  );

  const [peticion, setPeticion] = useState<number | null>(null);
  const [destino, setDestino] = useState<number | null>(null);

  /**
   * P-24: un capítulo de la ficha lleva a ese capítulo **en Leer**. El
   * fragmento se escribe antes de cambiar de pestaña —así `usePosicion` lo toma
   * como el punto al que te mandaron— y se baja hasta él cuando la sección
   * exista: la lectura se monta al cambiar de pestaña y carga después.
   */
  const irACapitulo = (numero: number) => {
    window.history.replaceState({}, "", `${window.location.search}#capitulo-${numero}`);
    setDestino(numero);
    setVista(VISTAS.leer);
  };
  useEffect(() => {
    if (destino === null || vista !== VISTAS.leer) return;
    let intentos = 0;
    const reloj = window.setInterval(() => {
      const seccion = document.getElementById(`capitulo-${destino}`);
      intentos += 1;
      if (seccion || intentos > 50) {
        window.clearInterval(reloj);
        seccion?.scrollIntoView?.();
        setDestino(null);
      }
    }, 100);
    return () => window.clearInterval(reloj);
  }, [destino, vista]);

  const hayNovela = token !== null;
  const disponibles = PESTANAS.filter((p) => p.vista === VISTAS.entrevista || hayNovela);

  /**
   * Las pestañas por referencia, para mover el foco con las flechas: el patrón
   * de WAI-ARIA (RF-ACC-02) quiere **una** parada de tabulación —la activa— y
   * flechas, Inicio y Fin dentro. La activación es automática: cambiar de
   * pestaña no carga nada caro que obligue a confirmar con Intro.
   */
  const botones = useRef(new Map<Vista, HTMLButtonElement>());
  const alPulsarTecla = (evento: KeyboardEvent<HTMLDivElement>) => {
    const indice = disponibles.findIndex((p) => p.vista === vista);
    const ultimo = disponibles.length - 1;
    const destino =
      evento.key === "ArrowRight"
        ? indice === ultimo ? 0 : indice + 1
        : evento.key === "ArrowLeft"
          ? indice <= 0 ? ultimo : indice - 1
          : evento.key === "Home"
            ? 0
            : evento.key === "End"
              ? ultimo
              : null;
    if (destino === null) return;
    evento.preventDefault();
    const siguiente = disponibles[destino];
    if (siguiente === undefined) return;
    setVista(siguiente.vista);
    botones.current.get(siguiente.vista)?.focus();
  };

  // El avance solo se guarda si la novela sigue en curso: una respuesta que
  // llegue tras «empezar otra» no debe resucitar el motivo.
  const alAvanzar = (avance: AvanceDeLaNovela) =>
    setNovela((previa) => (previa.tipo === "en-curso" ? { tipo: "en-curso", avance } : previa));

  return (
    <Pagina titulo="Tu novela">
      <div className="navegacion">
        <div
          className="pestanas"
          role="tablist"
          aria-label="Tu novela"
          onKeyDown={alPulsarTecla}
        >
          {PESTANAS.map((pestana) => {
            const desactivada = pestana.vista !== VISTAS.entrevista && !hayNovela;
            const activa = vista === pestana.vista;
            return (
              <button
                key={pestana.vista}
                ref={(nodo) => {
                  if (nodo) botones.current.set(pestana.vista, nodo);
                  else botones.current.delete(pestana.vista);
                }}
                type="button"
                role="tab"
                id={`pestana-${pestana.vista}`}
                aria-selected={activa}
                aria-controls={`panel-${pestana.vista}`}
                aria-describedby={desactivada ? ID_DEL_MOTIVO : undefined}
                tabIndex={activa ? 0 : -1}
                // Una pestaña que se puede pulsar y no lleva a nada enseña una
                // pantalla vacía, y una pantalla vacía se lee como un fallo.
                disabled={desactivada}
                className={activa ? "pestana pestana--activa" : "pestana"}
                onClick={() => setVista(pestana.vista)}
              >
                {pestana.etiqueta}
              </button>
            );
          })}
        </div>

        {!hayNovela ? (
          <p id={ID_DEL_MOTIVO} className="navegacion__motivo">
            {motivo(novela)}
          </p>
        ) : null}
      </div>

      <div role="tabpanel" id={`panel-${vista}`} aria-labelledby={`pestana-${vista}`} tabIndex={0}>
        {vista === VISTAS.entrevista ? (
          <Entrevista
            onNovelaLanzada={() => {
              setEscribiendo(true);
              setNovela({ tipo: "en-curso", avance: null });
            }}
            onAvance={alAvanzar}
            onNovelaOlvidada={() => setNovela({ tipo: "ninguna" })}
            onNovelaPublicada={(suyo) => {
              setToken(suyo);
              setEscribiendo(false);
              setNovela({ tipo: "ninguna" });
              setVista(VISTAS.leer);
            }}
            onFallo={() => setEscribiendo(false)}
            deshabilitado={escribiendo}
          />
        ) : vista === VISTAS.leer && token ? (
          <PuertaDeEspera
            token={token}
            peticionId={peticion}
            onPeticionTerminada={(resultado) => {
              setPeticion(null);
              // Cada tirada tiene su enlace: si la corrección se publicó con uno
              // nuevo, se pasa a él sin recargar. `replaceState` y no
              // `pushState`, igual que la posición: atrás es para salir.
              const nuevo = resultado.token_resultante;
              if (resultado.estado === "atendida" && nuevo && nuevo !== token) {
                window.history.replaceState({}, "", `/?token=${encodeURIComponent(nuevo)}`);
                setToken(nuevo);
              }
            }}
          >
            <Leer token={token} />
          </PuertaDeEspera>
        ) : token ? (
          <QuienEsQuien
            token={token}
            onIrACapitulo={irACapitulo}
            onPeticionEnviada={(id) => {
              setPeticion(id);
              setVista(VISTAS.leer);
            }}
          />
        ) : null}
      </div>
    </Pagina>
  );
}
