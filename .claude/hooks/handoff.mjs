// El encabezado de traza del encargo. Módulo aparte porque lo cargan el hook y los tests,
// y el hook, al importarse, se queda esperando stdin.
//
// A0 midió que el `node` que guarda `run-state.json` no es de fiar en `PostToolUse`: el
// orquestador ya ha podido mover el estado para cuando corre el hook, y en los datos de
// `within-tolerance` salía `scene-writer` en los nodos BEAT, VAL y VOICE. Agrupar por nodo
// daba basura. El nodo correcto es el del **encargo**, que no cambia después.
//
// Forma, primera línea del prompt del subagente:
//   <!-- storymaker-trace node=COMMIT attempt=1 chapter=7 -->
//
// Si falta o no valida, quien llama cae al estado y lo deja marcado. Un dato dudoso que se
// presenta como bueno es peor que un hueco declarado.

/** Los nodos del diagrama son mayúsculas: BEAT, WRITE, VOICE, VAL2, SEED, COMMIT… */
const NODO = /^[A-Z][A-Z0-9_]{0,15}$/;

const entero = (valor) => (/^\d{1,6}$/.test(String(valor)) ? Number(valor) : null);

export function parseTraceHeader(prompt) {
  const marca = String(prompt ?? '').match(/<!--\s*storymaker-trace\s+([^>]*?)\s*-->/);
  if (!marca) return null;

  const campos = {};
  for (const [, clave, valor] of marca[1].matchAll(/([a-z_]+)=(\S+)/g)) campos[clave] = valor;

  // El nodo es lo único obligatorio: sin él el encabezado no sirve para lo que existe.
  if (!campos.node || !NODO.test(campos.node)) return null;

  return {
    node: campos.node,
    attempt: entero(campos.attempt),
    chapter: entero(campos.chapter),
  };
}
