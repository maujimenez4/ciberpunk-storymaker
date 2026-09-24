import { type KeyboardEvent, type ReactNode, useEffect, useId, useRef, useState } from "react";

import "../lectura.css";

import { useAjustesDeLectura } from "../hooks/useAjustesDeLectura";
import { type Ajustes, INTERLINEADOS, TAMANOS, TEMAS } from "../lib/ajustes";

/**
 * El panel «Aa»: tamaño, interlineado y tema.
 *
 * Es el gesto de un lector electrónico y **no un formulario**: no hay «guardar»,
 * cada elección se aplica al pulsarla y se ve detrás del panel.
 *
 * - Al abrir, el foco entra en el panel; mientras está abierto no se escapa;
 *   Escape lo cierra y devuelve el foco al botón (RF-ACC-01, RF-ACC-02).
 * - Las opciones son **radios de verdad** agrupados con `fieldset`: el lector de
 *   pantalla dice «Tamaño de letra, Grande, 3 de 4», y las flechas recorren el
 *   grupo sin programar nada.
 */
export function AjustesDeLectura() {
  const { ajustes, cambiar } = useAjustesDeLectura();
  const [abierto, setAbierto] = useState(false);
  const boton = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const envoltorio = useRef<HTMLDivElement>(null);
  const idPanel = useId();

  function cerrar({ devolverFoco }: { devolverFoco: boolean }) {
    setAbierto(false);
    if (devolverFoco) {
      boton.current?.focus();
    }
  }

  // Al abrir, el foco entra: en la opción elegida del primer grupo.
  useEffect(() => {
    if (abierto) {
      primeroEnfocable(panel.current)?.focus();
    }
  }, [abierto]);

  // Pulsar fuera cierra, sin robar el foco a lo que se pulsó.
  useEffect(() => {
    if (!abierto) {
      return;
    }
    function fuera(evento: PointerEvent) {
      if (!envoltorio.current?.contains(evento.target as Node)) {
        setAbierto(false);
      }
    }
    document.addEventListener("pointerdown", fuera);
    return () => document.removeEventListener("pointerdown", fuera);
  }, [abierto]);

  function alPulsarTecla(evento: KeyboardEvent<HTMLDivElement>) {
    if (evento.key === "Escape") {
      evento.stopPropagation();
      cerrar({ devolverFoco: true });
      return;
    }
    if (evento.key === "Tab") {
      atraparFoco(evento, panel.current);
    }
  }

  return (
    <div className="ajustes" ref={envoltorio}>
      <button
        ref={boton}
        type="button"
        className="ajustes__boton"
        aria-label="Ajustes de lectura"
        aria-expanded={abierto}
        aria-controls={abierto ? idPanel : undefined}
        onClick={() => setAbierto((antes) => !antes)}
      >
        Aa
      </button>

      {abierto ? (
        <div
          ref={panel}
          id={idPanel}
          className="ajustes__panel"
          role="dialog"
          aria-modal="true"
          aria-label="Ajustes de lectura"
          onKeyDown={alPulsarTecla}
        >
          <Grupo leyenda="Tamaño de letra" clase="ajustes__grupo--tamano">
            {TAMANOS.map((t, i) => (
              <Opcion
                key={t.valor}
                nombre="tamano"
                valor={t.valor}
                elegida={ajustes.tamano === t.valor}
                alElegir={() => cambiar({ tamano: t.valor })}
              >
                {/* Se ve la letra creciendo; se oye el nombre del paso. */}
                <span aria-hidden="true" className={`ajustes__muestra ajustes__muestra--${i + 1}`}>
                  A
                </span>
                <span className="ajustes__oculto">{t.etiqueta}</span>
              </Opcion>
            ))}
          </Grupo>

          <Grupo leyenda="Interlineado">
            {INTERLINEADOS.map((l) => (
              <Opcion
                key={l.valor}
                nombre="interlineado"
                valor={l.valor}
                elegida={ajustes.interlineado === l.valor}
                alElegir={() => cambiar({ interlineado: l.valor })}
              >
                {l.etiqueta}
              </Opcion>
            ))}
          </Grupo>

          <Grupo leyenda="Tema">
            {TEMAS.map((t) => (
              <Opcion
                key={t.valor}
                nombre="tema"
                valor={t.valor}
                elegida={ajustes.tema === t.valor}
                alElegir={() => cambiar({ tema: t.valor })}
              >
                <span aria-hidden="true" className={`ajustes__tema ajustes__tema--${t.valor}`} />
                {t.etiqueta}
              </Opcion>
            ))}
          </Grupo>

          <button
            type="button"
            className="ajustes__cerrar"
            onClick={() => cerrar({ devolverFoco: true })}
          >
            Cerrar
          </button>
        </div>
      ) : null}
    </div>
  );
}

function Grupo({
  leyenda,
  clase,
  children,
}: {
  leyenda: string;
  clase?: string;
  children: ReactNode;
}) {
  return (
    <fieldset className={clase ? `ajustes__grupo ${clase}` : "ajustes__grupo"}>
      <legend className="ajustes__leyenda">{leyenda}</legend>
      <div className="ajustes__opciones">{children}</div>
    </fieldset>
  );
}

function Opcion({
  nombre,
  valor,
  elegida,
  alElegir,
  children,
}: {
  nombre: keyof Ajustes;
  valor: string;
  elegida: boolean;
  alElegir: () => void;
  children: ReactNode;
}) {
  return (
    <label className="ajustes__opcion">
      <input
        type="radio"
        className="ajustes__radio"
        name={`ajustes-${nombre}`}
        value={valor}
        checked={elegida}
        onChange={alElegir}
      />
      <span className="ajustes__pildora">{children}</span>
    </label>
  );
}

/**
 * Lo que recibe el Tab dentro del panel. De cada grupo de radios solo entra el
 * elegido, como hace el navegador: las flechas se mueven dentro del grupo.
 */
function enfocables(panel: HTMLElement | null): HTMLElement[] {
  if (!panel) {
    return [];
  }
  return Array.from(panel.querySelectorAll<HTMLElement>("button, input")).filter(
    (el) => !(el instanceof HTMLInputElement && el.type === "radio" && !el.checked),
  );
}

function primeroEnfocable(panel: HTMLElement | null): HTMLElement | undefined {
  return enfocables(panel)[0];
}

function atraparFoco(evento: KeyboardEvent<HTMLElement>, panel: HTMLElement | null) {
  const lista = enfocables(panel);
  const primero = lista[0];
  const ultimo = lista[lista.length - 1];
  if (!primero || !ultimo) {
    return;
  }
  const activo = document.activeElement;
  if (evento.shiftKey && (activo === primero || !panel?.contains(activo))) {
    evento.preventDefault();
    ultimo.focus();
  } else if (!evento.shiftKey && (activo === ultimo || !panel?.contains(activo))) {
    evento.preventDefault();
    primero.focus();
  }
}
