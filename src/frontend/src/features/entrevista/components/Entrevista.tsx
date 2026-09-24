import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { usePeticionario } from "@/shared/api/contexto";
import { Pagina } from "@/shared/ui/patterns/Pagina";
import { Aviso, Boton, Texto } from "@/shared/ui/primitives";

import { API_ENTREVISTA, type Evaluacion } from "../api/entrevista";

/**
 * Las claves y las formas son las de `BriefEntrada` (`features/obra/schemas.py`),
 * tal y como `cerrar` las lee planas: `nombre`, `edad`, `rasgos` y
 * `recuerdos_aportados` del destinatario; `genero`, `tono`, `nivel_de_calor`,
 * `elementos_obligatorios` y `vetos` de la obra. **No se traducen aquí**: un
 * nombre distinto se ignora en silencio y una cadena donde va una lista se
 * cuenta como contradicción, y ninguna de las dos cosas falla en ningún sitio.
 */
type Forma = "texto" | "entero" | "lista" | "calor";

const CAMPOS: readonly { clave: string; etiqueta: string; forma: Forma }[] = [
  { clave: "nombre", etiqueta: "¿Cómo se llama?", forma: "texto" },
  { clave: "edad", etiqueta: "¿Qué edad tiene?", forma: "entero" },
  { clave: "rasgos", etiqueta: "¿Cómo es? Tres o cuatro rasgos, separados por comas", forma: "lista" },
  { clave: "recuerdos_aportados", etiqueta: "Un recuerdo que compartáis", forma: "lista" },
  {
    clave: "genero",
    etiqueta: "¿Qué tipo de historia? Romance, aventura, misterio…",
    forma: "texto",
  },
  { clave: "tono", etiqueta: "¿Cómo quieres que suene? Divertida, seria, tierna…", forma: "texto" },
  { clave: "nivel_de_calor", etiqueta: "¿Cuánto romance o intimidad quieres?", forma: "calor" },
  {
    clave: "elementos_obligatorios",
    etiqueta: "¿Qué tiene que aparecer sí o sí? Un lugar, una mascota, un objeto… separados por comas",
    forma: "lista",
  },
  { clave: "vetos", etiqueta: "¿Hay algo que prefieras que no aparezca? Separado por comas", forma: "lista" },
];

const NIVELES_DE_CALOR = [
  { valor: "0", etiqueta: "0 · Ninguno" },
  { valor: "1", etiqueta: "1 · Un beso, como mucho" },
  { valor: "2", etiqueta: "2 · Romántico, sin detalle" },
  { valor: "3", etiqueta: "3 · Con escenas íntimas" },
  { valor: "4", etiqueta: "4 · Explícito" },
];

/**
 * De lo escrito a lo que el brief lee. **Solo viajan las claves con algo
 * dentro**: `cerrar` copia las presentes y cuenta como faltante lo que no
 * está, así que una lista vacía o un `0` por defecto le dirían que el
 * comprador respondió cuando no lo hizo.
 */
function aRespuestas(valores: Record<string, string>): Record<string, unknown> {
  const respuestas: Record<string, unknown> = {};
  for (const campo of CAMPOS) {
    const crudo = (valores[campo.clave] ?? "").trim();
    if (crudo === "") continue;
    respuestas[campo.clave] = convertir(crudo, campo.forma);
  }
  return respuestas;
}

function convertir(crudo: string, forma: Forma): unknown {
  switch (forma) {
    case "texto":
      return crudo;
    case "entero":
    case "calor":
      return Number(crudo);
    case "lista":
      return crudo
        .split(",")
        .map((parte) => parte.trim())
        .filter((parte) => parte !== "");
  }
}

/**
 * La primera pantalla: el comprador cuenta a quién va dirigida la novela.
 *
 * **Vive en `/` y no bajo el token** (D-06). El token nace con la versión
 * publicada, así que aquí todavía no existe; y si colgara de él, el enlace del
 * regalo llevaría a lo que el comprador escribió sobre el destinatario —
 * incluido lo que pidió que **no** apareciera.
 */
export function Entrevista({
  onNovelaLanzada,
  onNovelaPublicada,
  onFallo,
  deshabilitado = false,
}: {
  onNovelaLanzada?: () => void;
  onNovelaPublicada?: (token: string) => void;
  onFallo?: () => void;
  deshabilitado?: boolean;
} = {}) {
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
        respuestas: aRespuestas(valores),
        texto_aportado: pegado,
      });
    },
    onSuccess: setEvaluacion,
  });

  /**
   * El puente: cerrar la entrevista da el `obra_id`, y con el se lanza la
   * novela. Son dos llamadas y **no una**: cerrar valida y crea la obra; lanzar
   * arranca el trabajo. Juntarlas dejaria sin saber cual de las dos fallo.
   */
  const escribir = useMutation({
    mutationFn: async () => {
      const id = entrevista.data?.id;
      if (id === undefined) throw new Error("la entrevista no esta abierta");
      const obra = await peticionario.enviar<{ obra_id: number }>(
        API_ENTREVISTA.cerrar(id),
        {},
      );
      onNovelaLanzada?.();
      await peticionario.enviar(API_ENTREVISTA.novela(obra.obra_id), {});
      // Publicar es lo que **da el token**, y sin token no hay nada que leer.
      // Va aqui y no en la pagina porque es el ultimo paso de la misma cadena:
      // si fallara, lo que no debe pasar es que se active una pestana que no
      // lleva a ningun sitio.
      const publicada = await peticionario.enviar<{ token: string }>(
        API_ENTREVISTA.publicar(obra.obra_id),
        {},
      );
      return publicada;
    },
    onSuccess: (publicada) => onNovelaPublicada?.(publicada.token),
    // Sin esto, un fallo deja la pantalla en «se esta escribiendo» **para
    // siempre**, que es la peor forma de fallar porque parece que funciona.
    onError: () => onFallo?.(),
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
            {campo.forma === "calor" ? (
              // Con una opción en blanco por defecto: si se abriera en «0»,
              // viajaría un dato que el comprador no dio.
              <select
                id={`campo-${campo.clave}`}
                className="campo__control"
                value={valores[campo.clave] ?? ""}
                onChange={(e) =>
                  setValores((previos) => ({ ...previos, [campo.clave]: e.target.value }))
                }
              >
                <option value="">Elige uno</option>
                {NIVELES_DE_CALOR.map((nivel) => (
                  <option key={nivel.valor} value={nivel.valor}>
                    {nivel.etiqueta}
                  </option>
                ))}
              </select>
            ) : (
              <input
                id={`campo-${campo.clave}`}
                className="campo__control"
                type="text"
                inputMode={campo.forma === "entero" ? "numeric" : undefined}
                value={valores[campo.clave] ?? ""}
                onChange={(e) =>
                  setValores((previos) => ({ ...previos, [campo.clave]: e.target.value }))
                }
              />
            )}
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

      {entrevista.isError ? (
        // Sin esto, quien abre la pagina con el backend caido rellena el
        // formulario entero y solo se entera al pulsar. El fallo es de antes.
        <Aviso tono="error">
          No se pudo conectar. Comprueba que el servidor está en marcha y vuelve
          a cargar la página.
        </Aviso>
      ) : null}

      {guardar.isError ? (
        <Aviso tono="error">No se pudo guardar lo que escribiste. Vuelve a intentarlo.</Aviso>
      ) : null}

      {evaluacion ? <Comprobacion evaluacion={evaluacion} /> : null}

      {escribir.isError ? (
        <Aviso tono="error">
          No se pudo empezar la novela. Vuelve a pulsar dentro de un momento.
        </Aviso>
      ) : null}

      {listo ? (
        <Boton onClick={() => escribir.mutate()} disabled={deshabilitado || escribir.isPending}>
          Escribir la novela
        </Boton>
      ) : null}
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
