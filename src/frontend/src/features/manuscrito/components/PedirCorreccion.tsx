import { type FormEvent, useEffect, useId, useRef, useState } from "react";

import { Aviso, Boton } from "@/shared/ui/primitives";

import { esHechoCambiado, usePedirCambio } from "../api/peticion";

/**
 * «Corregir este hecho», desde la etiqueta de la ficha (D-02, RF-PET-01/02).
 *
 * **No es un modal**: se despliega dentro de la etiqueta, así que no hay foco que
 * atrapar ni que devolver, y la página sigue navegable (RF-PET-04). El botón que
 * lo abre lleva el nombre de la entrada —«Corregir Olvido»—, porque diez botones
 * que dicen «Corregir» no se distinguen con un lector de pantalla.
 *
 * **Lo que viaja es el `hecho_canon_id`**, no lo que se escribe: si el texto
 * habla de otra entrada, se corrige igual esta (CA-8).
 */
export function PedirCorreccion({
  token,
  hechoId,
  nombre,
  onEnviada,
}: {
  token: string;
  hechoId: number;
  nombre: string;
  onEnviada?: (peticionId: number) => void;
}) {
  const [abierto, setAbierto] = useState(false);
  const [texto, setTexto] = useState("");
  const { pedir, mutacion } = usePedirCambio(token);
  const id = useId();
  const campo = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (abierto) campo.current?.focus();
  }, [abierto]);

  if (!abierto) {
    return (
      <Boton
        variante="discreto"
        className="boton boton--discreto corregir__abrir"
        aria-label={`Corregir este hecho: ${nombre}`}
        onClick={() => setAbierto(true)}
      >
        Corregir este hecho
      </Boton>
    );
  }

  const alEnviar = (evento: FormEvent) => {
    evento.preventDefault();
    const limpio = texto.trim();
    if (limpio === "") return;
    pedir(hechoId, limpio, onEnviada);
  };

  const enviando = mutacion.isPending || mutacion.isSuccess;

  return (
    <form className="corregir" onSubmit={alEnviar} aria-label={`Corregir ${nombre}`}>
      <label htmlFor={id} className="corregir__etiqueta">
        ¿Qué debería decir?
      </label>
      <textarea
        id={id}
        ref={campo}
        className="corregir__campo"
        rows={3}
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
        disabled={enviando}
        required
      />
      <p className="corregir__nota">
        Se reescribirán los capítulos que cuentan esto. Mientras tanto, la lectura se detiene.
      </p>

      {mutacion.isError ? (
        <Aviso tono="error">
          {esHechoCambiado(mutacion.error)
            ? "Esta entrada ha cambiado desde que abriste la ficha. Vuelve a abrirla y pídelo otra vez."
            : "No se pudo enviar la corrección. Prueba de nuevo en un momento."}
        </Aviso>
      ) : null}

      <div className="corregir__acciones">
        <Boton type="submit" disabled={enviando || texto.trim() === ""}>
          {enviando ? "Enviando…" : "Enviar corrección"}
        </Boton>
        <Boton variante="discreto" onClick={() => setAbierto(false)} disabled={enviando}>
          Cancelar
        </Boton>
      </div>
    </form>
  );
}
