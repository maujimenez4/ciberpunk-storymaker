import { useState } from "react";

import { Pagina } from "@/shared/ui/patterns/Pagina";

import { Leer } from "./Leer";
import { QuienEsQuien } from "./QuienEsQuien";

const PESTANAS = [
  { vista: "leer", etiqueta: "Leer" },
  { vista: "quien-es-quien", etiqueta: "Quién es quién" },
] as const;

type Vista = (typeof PESTANAS)[number]["vista"];

/**
 * La página de la lectura: una dirección, y dentro las vistas.
 *
 * Las pestañas son `tab`/`tablist`/`tabpanel` de verdad y no `div` con
 * `onClick`: un lector de pantalla anuncia cuál está activa y cuántas hay, y el
 * teclado las recorre. `RF-ACC-02`.
 *
 * **La entrevista no está aquí.** Es del comprador y ocurre antes de que exista
 * novela, así que vive en su propia dirección (`router.ts`).
 */
export function Lectura({ token, vistaInicial }: { token: string; vistaInicial: Vista }) {
  const [vista, setVista] = useState<Vista>(vistaInicial);

  return (
    <Pagina titulo="Tu novela">
      <div className="pestanas" role="tablist" aria-label="Vistas de la novela">
        {PESTANAS.map((pestana) => (
          <button
            key={pestana.vista}
            type="button"
            role="tab"
            id={`pestana-${pestana.vista}`}
            aria-selected={vista === pestana.vista}
            aria-controls={`panel-${pestana.vista}`}
            className={vista === pestana.vista ? "pestana pestana--activa" : "pestana"}
            onClick={() => setVista(pestana.vista)}
          >
            {pestana.etiqueta}
          </button>
        ))}
      </div>

      <div
        role="tabpanel"
        id={`panel-${vista}`}
        aria-labelledby={`pestana-${vista}`}
        tabIndex={0}
      >
        {vista === "leer" ? <Leer token={token} /> : <QuienEsQuien token={token} />}
      </div>
    </Pagina>
  );
}
