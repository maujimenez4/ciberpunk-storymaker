/** La API publica de la feature. Se entra por aqui y solo por aqui (§5.2). */
export { Entrevista, type AvanceDeLaNovela } from "./components/Entrevista";
export { API_ENTREVISTA } from "./api/entrevista";
/** Si hay una novela a medias apuntada en este navegador: la navegación lo
 * necesita **al cargar**, antes de que la entrevista pregunte nada. */
export { leerNovelaEnCurso, type NovelaEnCurso } from "./lib/novelaEnCurso";
