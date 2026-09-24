import { skipToken, useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { usePeticionario } from "@/shared/api/contexto";
import { Pagina } from "@/shared/ui/patterns/Pagina";
import { Aviso, Boton, Texto } from "@/shared/ui/primitives";

import { API_ENTREVISTA, type EstadoDeLaNovela, type Evaluacion } from "../api/entrevista";
import { Espera } from "./Espera";

/** Un capitulo tarda unos ocho minutos: preguntar cada cinco segundos basta
 * para que el avance se vea y no carga al servidor. */
const INTERVALO_DE_CONSULTA = 5000;

/** El paso de la cadena en curso, para decir **cual** fallo. */
type Paso = "cerrar" | "outline" | "novela";

const QUE_FALLO: Record<Paso, string> = {
  cerrar: "cerrar la entrevista",
  outline: "preparar la historia",
  novela: "empezar a escribir la novela",
};

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
  intervaloDeConsulta = INTERVALO_DE_CONSULTA,
  ahora = Date.now,
}: {
  onNovelaLanzada?: () => void;
  onNovelaPublicada?: (token: string) => void;
  onFallo?: () => void;
  deshabilitado?: boolean;
  /** Cada cuanto se pregunta como va la novela, en milisegundos. */
  intervaloDeConsulta?: number;
  /** El reloj, inyectado como en el backend: sin el, probar «lleva doce
   * minutos» obligaria a esperar doce minutos. */
  ahora?: () => number;
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
   * El puente, en tres llamadas y **no una**: cerrar valida y crea la obra; el
   * Arquitecto le da premisa, biblia y los diez capitulos; lanzar arranca el
   * trabajo de fondo. Juntarlas dejaria sin saber cual fallo, y por eso se
   * anota el paso antes de cada una.
   *
   * **Sin el outline no hay novela**: la obra se queda con cero capitulos y
   * `/novela` responde 202 sin escribir nada. La primera corrida real lo hizo
   * asi y ningun test lo veia.
   */
  const [paso, setPaso] = useState<Paso | null>(null);
  const [enMarcha, setEnMarcha] = useState<{ obraId: number; intento: number } | null>(null);
  const [detenida, setDetenida] = useState<string | null>(null);
  /** Cuando se cerro la entrevista: desde ahi cuenta «empezó hace». */
  const [desde, setDesde] = useState<number | null>(null);

  const lanzar = useMutation({
    mutationFn: async () => {
      const id = entrevista.data?.id;
      if (id === undefined) throw new Error("la entrevista no esta abierta");
      setPaso("cerrar");
      const obra = await peticionario.enviar<{ obra_id: number }>(
        API_ENTREVISTA.cerrar(id),
        {},
      );
      setDesde(ahora());
      onNovelaLanzada?.();
      setPaso("outline");
      await peticionario.enviar(API_ENTREVISTA.outline(obra.obra_id), {});
      setPaso("novela");
      await peticionario.enviar(API_ENTREVISTA.novela(obra.obra_id), {});
      return obra.obra_id;
    },
    // El intento va en la clave de la consulta: sin el, un segundo intento
    // sobre la misma obra leeria de la cache el «detenida» del primero.
    onSuccess: (obraId) =>
      setEnMarcha((previo) => ({ obraId, intento: (previo?.intento ?? 0) + 1 })),
    // Sin esto, un fallo deja la pantalla en «se esta escribiendo» **para
    // siempre**, que es la peor forma de fallar porque parece que funciona.
    onError: () => onFallo?.(),
  });

  /**
   * **La novela es un trabajo de fondo de hora y media**, y `/novela` responde
   * 202 en cuanto lo arranca. Publicar entonces era publicar una obra sin
   * capitulos. Se pregunta cada `intervaloDeConsulta` y se deja de preguntar
   * en cuanto el estado es final.
   */
  const progreso = useQuery({
    queryKey: ["novela", enMarcha?.obraId, enMarcha?.intento],
    queryFn:
      enMarcha === null
        ? skipToken
        : () => peticionario.pedir<EstadoDeLaNovela>(API_ENTREVISTA.novela(enMarcha.obraId)),
    // Un fallo de red en mitad de hora y media no es un fallo de la novela:
    // se sigue preguntando.
    refetchInterval: (consulta) => {
      const estado = consulta.state.data?.estado;
      return estado === undefined || estado === "escribiendo" ? intervaloDeConsulta : false;
    },
  });

  // Publicar es lo que **da el token**, y sin token no hay nada que leer. Solo
  // cuando la novela esta terminada: si no, se activaria una pestana que no
  // lleva a ningun sitio.
  const publicar = useMutation({
    mutationFn: (obraId: number) =>
      peticionario.enviar<{ token: string }>(API_ENTREVISTA.publicar(obraId), {}),
    onSuccess: (publicada) => onNovelaPublicada?.(publicada.token),
    onError: () => onFallo?.(),
  });
  const { mutate: publicarObra } = publicar;

  const datos = progreso.data;
  useEffect(() => {
    if (enMarcha === null || datos === undefined) return;
    switch (datos.estado) {
      case "escribiendo":
        return;
      case "terminada":
        setEnMarcha(null);
        publicarObra(enMarcha.obraId);
        return;
      case "detenida":
        setEnMarcha(null);
        setDetenida(
          `La novela se detuvo y no se ha publicado. Motivo: ${datos.motivo ?? "no consta"}`,
        );
        onFallo?.();
        return;
      case "sin_outline":
        // El Arquitecto respondio bien y aun asi no hay capitulos: esperar no
        // lo arregla.
        setEnMarcha(null);
        setDetenida("No se pudo escribir la novela: la historia se quedó sin capítulos.");
        onFallo?.();
        return;
    }
  }, [datos, enMarcha, publicarObra, onFallo]);

  /**
   * El reloj de la pantalla. Es un sistema externo y por eso va en un efecto:
   * la consulta devuelve lo mismo durante ocho minutos y, sin esto, «empezó
   * hace» se quedaria quieto ese rato.
   */
  const [instante, setInstante] = useState(ahora);
  const escribiendo = enMarcha !== null;
  useEffect(() => {
    if (!escribiendo) return;
    setInstante(ahora());
    const reloj = setInterval(() => setInstante(ahora()), intervaloDeConsulta);
    return () => clearInterval(reloj);
  }, [escribiendo, ahora, intervaloDeConsulta]);

  const ocupado = lanzar.isPending || enMarcha !== null || publicar.isPending;

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

        {/* Desactivado mientras espera: el Entrevistador tarda segundos, y un
            segundo clic lanzaba otro `POST /respuestas` que moría con
            `database is locked` (596faba). */}
        <Boton type="submit" disabled={guardar.isPending}>
          Guardar y comprobar
        </Boton>
      </form>

      {guardar.isPending ? (
        <p className="nota" role="status">
          Comprobando…
        </p>
      ) : null}

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

      {lanzar.isError ? (
        <Aviso tono="error">
          No se pudo {paso === null ? "empezar la novela" : QUE_FALLO[paso]}. Vuelve a pulsar
          dentro de un momento.
        </Aviso>
      ) : null}

      {publicar.isError ? (
        <Aviso tono="error">
          La novela está escrita, pero no se pudo publicar. Vuelve a pulsar dentro de un
          momento.
        </Aviso>
      ) : null}

      {detenida !== null ? <Aviso tono="error">{detenida}</Aviso> : null}

      {lanzar.isPending && (paso === "cerrar" || paso === "outline") ? (
        <div className="comprobacion" role="status">
          <Texto>
            Preparando la historia: la premisa, los personajes y los diez capítulos. Tarda un
            poco.
          </Texto>
        </div>
      ) : null}

      {(lanzar.isPending && paso === "novela") || enMarcha !== null ? (
        <Espera
          datos={enMarcha !== null ? datos : undefined}
          desde={desde ?? instante}
          instante={instante}
        />
      ) : null}

      {publicar.isPending ? (
        <div className="comprobacion" role="status">
          <Texto>La novela está escrita. Publicándola…</Texto>
        </div>
      ) : null}

      {listo ? (
        <Boton
          onClick={() => {
            setDetenida(null);
            publicar.reset();
            lanzar.mutate();
          }}
          // Desactivado durante **toda** la cadena, consulta incluida: un
          // segundo clic a mitad de la novela cerraria otra vez la entrevista.
          disabled={deshabilitado || ocupado}
        >
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
