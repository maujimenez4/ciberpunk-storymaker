import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { usePeticionario } from "@/shared/api/contexto";
import { Pagina } from "@/shared/ui/patterns/Pagina";
import { Aviso, Boton, Texto } from "@/shared/ui/primitives";

import { API_ENTREVISTA, type Evaluacion } from "../api/entrevista";

const CAMPOS = [
  { clave: "nombre", etiqueta: "¿Cómo se llama?", tipo: "text" },
  { clave: "edad", etiqueta: "¿Qué edad tiene?", tipo: "text" },
  { clave: "rasgos", etiqueta: "¿Cómo es? Tres o cuatro rasgos", tipo: "text" },
  { clave: "recuerdos", etiqueta: "Un recuerdo que compartáis", tipo: "text" },
  { clave: "tono", etiqueta: "¿Cómo quieres que suene? Divertida, seria, tierna…", tipo: "text" },
  { clave: "vetos", etiqueta: "¿Hay algo que prefieras que no aparezca?", tipo: "text" },
] as const;

/**
 * La primera pantalla: el comprador cuenta a quién va dirigida la novela.
 *
 * **Vive en `/` y no bajo el token** (D-06). El token nace con la versión
 * publicada, así que aquí todavía no existe; y si colgara de él, el enlace del
 * regalo llevaría a lo que el comprador escribió sobre el destinatario —
 * incluido lo que pidió que **no** apareciera.
 */
export function Entrevista() {
  const peticionario = usePeticionario();
  const [valores, setValores] = useState<Record<string, string>>({});
  const [pegado, setPegado] = useState("");
  const [evaluacion, setEvaluacion] = useState<Evaluacion | null>(null);

  const entrevista = useQuery({
    queryKey: ["entrevista"],
    queryFn: () => peticionario.enviar<{ id: number }>(API_ENTREVISTA.abrir(), {}),
  });

  const guardar = useMutation({
    mutationFn: async () => {
      const id = entrevista.data?.id;
      if (id === undefined) throw new Error("la entrevista no está abierta");
      // **Dos campos, y la separación es la defensa.** `texto_aportado` es
      // contenido no confiable y el servidor lo envuelve en su etiqueta
      // (`CLAUDE.md` §11); si viajara dentro de `respuestas` entraría en el
      // prompt como instrucción y no fallaría nada.
      return peticionario.enviar<Evaluacion>(API_ENTREVISTA.responder(id), {
        respuestas: valores,
        texto_aportado: pegado,
      });
    },
    onSuccess: setEvaluacion,
  });

  const listo =
    evaluacion !== null &&
    evaluacion.faltantes.length === 0 &&
    evaluacion.contradicciones.length === 0;

  return (
    <Pagina titulo="Cuéntanos sobre quien va a leerla">
      <Texto>
        Con lo que escribas aquí se escribe la novela. No hace falta que sea
        largo: un par de recuerdos concretos valen más que una lista.
      </Texto>

      <form
        className="formulario"
        onSubmit={(e) => {
          e.preventDefault();
          guardar.mutate();
        }}
      >
        {CAMPOS.map((campo) => (
          <p key={campo.clave} className="campo">
            {/* Etiqueta de verdad y no un `placeholder`: un `placeholder`
                desaparece al escribir y deja al lector de pantalla sin nombre
                que anunciar (`RF-ACC-03`). */}
            <label className="campo__etiqueta" htmlFor={`campo-${campo.clave}`}>
              {campo.etiqueta}
            </label>
            <input
              id={`campo-${campo.clave}`}
              className="campo__control"
              type={campo.tipo}
              value={valores[campo.clave] ?? ""}
              onChange={(e) =>
                setValores((previos) => ({ ...previos, [campo.clave]: e.target.value }))
              }
            />
          </p>
        ))}

        <p className="campo">
          <label className="campo__etiqueta" htmlFor="campo-pegado">
            Si tienes una carta, una anécdota o un mensaje suyo, pega aquí el texto
          </label>
          <textarea
            id="campo-pegado"
            className="campo__control"
            rows={6}
            value={pegado}
            onChange={(e) => setPegado(e.target.value)}
          />
        </p>

        <Boton type="submit">Guardar y comprobar</Boton>
      </form>

      {guardar.isError ? (
        <Aviso tono="error">No se pudo guardar lo que escribiste. Vuelve a intentarlo.</Aviso>
      ) : null}

      {evaluacion ? <Comprobacion evaluacion={evaluacion} /> : null}

      {listo ? <Boton>Escribir la novela</Boton> : null}
    </Pagina>
  );
}

/**
 * Lo que el encargo §1 pide de verdad: **qué falta y qué se contradice**, dicho
 * según se rellena y no al enviar. Una contradicción que aparece al final es
 * una contradicción que ya costó tiempo.
 */
function Comprobacion({ evaluacion }: { evaluacion: Evaluacion }) {
  const nada =
    evaluacion.faltantes.length === 0 && evaluacion.contradicciones.length === 0;

  return (
    <div className="comprobacion" role="status">
      {nada ? (
        <p className="nota">Con esto hay bastante para empezar.</p>
      ) : (
        <>
          {evaluacion.faltantes.length > 0 ? (
            <p className="nota">Falta por contar: {evaluacion.faltantes.join(", ")}.</p>
          ) : null}
          {evaluacion.contradicciones.map((contradiccion) => (
            // Se explica, no se numera: «edad frente a tono» no le dice nada a
            // quien la escribió.
            <p key={contradiccion.campos.join("-")} className="nota">
              {contradiccion.explicacion}
            </p>
          ))}
        </>
      )}
    </div>
  );
}
