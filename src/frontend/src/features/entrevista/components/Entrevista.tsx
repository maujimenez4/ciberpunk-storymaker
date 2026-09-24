import { skipToken, useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { usePeticionario } from "@/shared/api/contexto";
import { Pagina } from "@/shared/ui/patterns/Pagina";
import { Aviso, Boton, Pasos, Texto } from "@/shared/ui/primitives";

import { API_ENTREVISTA, type EstadoDeLaNovela, type Evaluacion } from "../api/entrevista";
import {
  guardarNovelaEnCurso,
  leerNovelaEnCurso,
  olvidarNovelaEnCurso,
  type NovelaEnCurso,
} from "../lib/novelaEnCurso";
import { Espera } from "./Espera";

/** Un capitulo tarda unos ocho minutos: preguntar cada cinco segundos basta
 * para que el avance se vea y no carga al servidor. */
const INTERVALO_DE_CONSULTA = 5000;

/** El paso de la cadena en curso, para decir **cual** fallo. */
type Paso = "cerrar" | "outline" | "novela";

/** Por que la novela dejo de avanzar sin que fallara ninguna llamada. */
type Parada = { tipo: "detenida"; motivo: string | null } | { tipo: "sin_outline" };

/** Lo que ve quien encarga la novela: cuatro pasos y no los cinco de la
 * cadena, porque cerrar la entrevista es parte de la entrevista. */
const ETAPAS = ["Entrevista", "Historia", "Capítulos", "Publicación"] as const;

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
interface Props {
  onNovelaLanzada?: () => void;
  onNovelaPublicada?: (token: string) => void;
  onFallo?: () => void;
  deshabilitado?: boolean;
  /** Cada cuanto se pregunta como va la novela, en milisegundos. */
  intervaloDeConsulta?: number;
  /** El reloj, inyectado como en el backend: sin el, probar «lleva doce
   * minutos» obligaria a esperar doce minutos. */
  ahora?: () => number;
}

export function Entrevista(props: Props = {}) {
  /**
   * **Una ronda por novela.** «Empezar otra novela» no limpia campo a campo:
   * remonta el recorrido entero con la `key`, y todo su estado —respuestas,
   * evaluacion, paso, avisos— vuelve a cero sin que ninguno se quede atras.
   */
  const [ronda, setRonda] = useState(0);
  return (
    <Recorrido
      key={ronda}
      ronda={ronda}
      {...props}
      onEmpezarOtra={() => {
        olvidarNovelaEnCurso();
        setRonda((previa) => previa + 1);
      }}
    />
  );
}

function Recorrido({
  ronda,
  onEmpezarOtra,
  onNovelaLanzada,
  onNovelaPublicada,
  onFallo,
  deshabilitado = false,
  intervaloDeConsulta = INTERVALO_DE_CONSULTA,
  ahora = Date.now,
}: Props & { ronda: number; onEmpezarOtra: () => void }) {
  const peticionario = usePeticionario();
  const [valores, setValores] = useState<Record<string, string>>({});
  const [pegado, setPegado] = useState("");
  const [evaluacion, setEvaluacion] = useState<Evaluacion | null>(null);

  /**
   * **La obra apuntada en el navegador**, si una recarga interrumpio una
   * novela. Con ella no se abre otra entrevista ni se enseña el formulario: se
   * sigue la que ya se esta escribiendo.
   */
  const [obra, setObra] = useState<NovelaEnCurso | null>(leerNovelaEnCurso);
  const [reanudada] = useState(obra !== null);
  const anotar = (novela: NovelaEnCurso) => {
    setObra(novela);
    guardarNovelaEnCurso(novela);
  };

  const entrevista = useQuery({
    queryKey: ["entrevista", ronda],
    queryFn: reanudada
      ? skipToken
      : () => peticionario.enviar<{ id: number }>(API_ENTREVISTA.abrir(), {}),
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
   *
   * `desde` dice por cual empezar. Cada paso que termina se apunta en el
   * navegador, que es lo que permite a una recarga seguir por el siguiente.
   */
  const [paso, setPaso] = useState<Paso | null>(null);
  const [enMarcha, setEnMarcha] = useState<number | null>(obra?.obraId ?? null);
  const [intento, setIntento] = useState(0);
  const [parada, setParada] = useState<Parada | null>(null);

  const lanzar = useMutation({
    mutationFn: async (desde: Paso) => {
      let actual = obra;
      if (desde === "cerrar") {
        const id = entrevista.data?.id;
        if (id === undefined) throw new Error("la entrevista no esta abierta");
        setPaso("cerrar");
        const cerrada = await peticionario.enviar<{ obra_id: number }>(
          API_ENTREVISTA.cerrar(id),
          {},
        );
        actual = { obraId: cerrada.obra_id, fase: "outline", desde: ahora() };
        anotar(actual);
        onNovelaLanzada?.();
      }
      if (actual === null) throw new Error("no hay obra que seguir");
      if (desde !== "novela") {
        setPaso("outline");
        await peticionario.enviar(API_ENTREVISTA.outline(actual.obraId), {});
        actual = { ...actual, fase: "novela" };
        anotar(actual);
      }
      setPaso("novela");
      await peticionario.enviar(API_ENTREVISTA.novela(actual.obraId), {});
      return actual.obraId;
    },
    // El intento va en la clave de la consulta: sin el, un segundo intento
    // sobre la misma obra leeria de la cache el «detenida» del primero.
    onSuccess: (obraId) => {
      setIntento((previo) => previo + 1);
      setEnMarcha(obraId);
    },
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
    queryKey: ["novela", enMarcha, intento],
    queryFn:
      enMarcha === null
        ? skipToken
        : () => peticionario.pedir<EstadoDeLaNovela>(API_ENTREVISTA.novela(enMarcha)),
    // Un fallo de red en mitad de hora y media no es un fallo de la novela:
    // se sigue preguntando.
    refetchInterval: (consulta) => {
      const estado = consulta.state.data?.estado;
      return estado === undefined || estado === "escribiendo" ? intervaloDeConsulta : false;
    },
  });

  // Publicar es lo que **da el token**, y sin token no hay nada que leer. Solo
  // cuando la novela esta terminada: si no, se activaria una pestana que no
  // lleva a ningun sitio. Publicada, ya no hay nada que reanudar.
  const publicar = useMutation({
    mutationFn: (obraId: number) =>
      peticionario.enviar<{ token: string }>(API_ENTREVISTA.publicar(obraId), {}),
    onSuccess: (publicada) => {
      olvidarNovelaEnCurso();
      onNovelaPublicada?.(publicada.token);
    },
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
        publicarObra(enMarcha);
        return;
      case "detenida":
        setEnMarcha(null);
        setParada({ tipo: "detenida", motivo: datos.motivo });
        onFallo?.();
        return;
      case "sin_outline":
        // El Arquitecto respondio bien y aun asi no hay capitulos: esperar no
        // lo arregla.
        setEnMarcha(null);
        setParada({ tipo: "sin_outline" });
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

  // El paso de la cabecera sale del paso de la cadena: el ultimo que se
  // intento, o hasta donde llego la obra apuntada. Tras un fallo se queda en
  // ese, que es donde hay que volver.
  const pasoVisible = paso ?? obra?.fase ?? null;
  const etapa =
    publicar.isPending || publicar.isError
      ? 3
      : enMarcha !== null || pasoVisible === "novela"
        ? 2
        : pasoVisible === "outline"
          ? 1
          : 0;

  const listo =
    evaluacion !== null &&
    evaluacion.faltantes.length === 0 &&
    evaluacion.contradicciones.length === 0;

  const cadena = (
    <>
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

      {parada?.tipo === "detenida" ? (
        <Aviso tono="error">
          La novela se detuvo y no se ha publicado. Motivo: {parada.motivo ?? "no consta"}
        </Aviso>
      ) : null}

      {parada?.tipo === "sin_outline" ? (
        <Aviso tono="error">
          No se pudo escribir la novela: la historia se quedó sin capítulos.
        </Aviso>
      ) : null}

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
          desde={obra?.desde ?? instante}
          instante={instante}
        />
      ) : null}

      {publicar.isPending ? (
        <div className="comprobacion" role="status">
          <Texto>La novela está escrita. Publicándola…</Texto>
        </div>
      ) : null}
    </>
  );

  if (reanudada) {
    return (
      <Pagina titulo="Seguimos con tu novela">
        <Pasos etiqueta="Cómo va tu novela" pasos={ETAPAS} actual={etapa} />
        {cadena}

        {parada?.tipo === "sin_outline" ? (
          <Boton
            onClick={() => {
              setParada(null);
              lanzar.mutate("outline");
            }}
            disabled={ocupado}
          >
            Preparar la historia otra vez
          </Boton>
        ) : null}

        <div className="otra">
          <p className="nota">
            Si prefieres encargar otra, esta seguirá escribiéndose, pero la página dejará de
            seguirla.
          </p>
          <Boton variante="secundario" onClick={onEmpezarOtra}>
            Empezar otra novela
          </Boton>
        </div>
      </Pagina>
    );
  }

  return (
    <Pagina titulo="Cuéntanos sobre quien va a leerla">
      <Pasos etiqueta="Cómo va tu novela" pasos={ETAPAS} actual={etapa} />
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

      {cadena}

      {listo ? (
        <Boton
          onClick={() => {
            setParada(null);
            publicar.reset();
            lanzar.mutate("cerrar");
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
