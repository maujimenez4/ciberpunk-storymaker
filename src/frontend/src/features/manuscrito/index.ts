/** La API publica de la feature. Se entra por aqui y solo por aqui (§5.2). */
export { API, useCapitulo, useFicha, useVersion } from "./api/lectura";
export { Lectura } from "./components/Lectura";
export { Leer } from "./components/Leer";
export { QuienEsQuien } from "./components/QuienEsQuien";
export { PuertaDeEspera } from "./components/PuertaDeEspera";
export type { Peticion } from "./api/peticion";
export { AjustesDeLectura } from "./components/AjustesDeLectura";
export { useAjustesDeLectura } from "./hooks/useAjustesDeLectura";
export { usePosicion } from "./hooks/usePosicion";
