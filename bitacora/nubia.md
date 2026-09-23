# Nubia

## 15:10 · Pull de la rama y exportación del manuscrito

- **Qué:** `seed-context-v2-backend-v1` estaba 17 commits por detrás; fast-forward a `84e7fb1`. Después, la salida de la corrida deja de ser un `.txt` suelto en la raíz y pasa a `manuscritos/` en `.md` y `.pdf`.
- **Ficheros:** `features/manuscrito/service.py`, `features/manuscrito/tests/test_exportacion.py`, `corrida.py`, `.gitignore`
- **Estado:** terminado — commiteado en `1d410b0` y `2193724`
- **Ojo:** el PDF se escribe a mano con la stdlib, sin dependencias nuevas; `pyproject.toml` y `uv.lock` intactos.

## 16:05 · Revisión de los validadores, a petición del usuario

- **Qué:** verificar el trabajo de validadores. Encontrado H-5: `validar_conocimiento` contrastaba `Afirmacion.objeto` —un objeto físico, según el prompt— contra `conocimientos`, que `derivar_estado_en_t` llena con `evento.descripcion`. Igualdad exacta entre dos textos libres de dos llamadas distintas: solo pasa si coinciden palabra por palabra.
- **Ficheros:** ninguno. No toqué `calidad/` ni `escritura/`; solo leí y ejecuté sondas.
- **Estado:** terminado — recogido como H-5 en `specs/002-validadores-fallo-cerrado/spec.md`
- **Ojo:** verifiqué además H-2 y H-6 ejecutándolos. H-2 es el grave: `validar_nivel_de_calor` con un nivel fuera de escala devolvía `[]`, o sea apagaba en silencio el límite de contenido (regla 5 de §8) por una mayúscula distinta.

## 16:25 · Atribución: tres avisos, un acierto

- **Qué:** me pidieron verificar a Gustavo y a Hernan «de validadores». La tarea de Gustavo era evaluar lenguajes formales; de Hernan no había nada en el árbol cuando miré. El único que llevaba validadores era Jose.
- **Estado:** terminado
- **Ojo:** de aquí sale esta bitácora. Si cada uno hubiera escrito lo que lleva, ninguna de las tres verificaciones habría empezado a ciegas.

## 16:40 · Convención de bitácora

- **Qué:** `bitacora/README.md` y un fichero por agente. Un solo fichero compartido perdería escrituras con seis sesiones a la vez.
- **Ficheros:** `bitacora/README.md`, `bitacora/nubia.md`
- **Estado:** terminado — avisados los seis agentes
- **Ojo:** `bitacora/` no está en `.gitignore`. Si no queréis que entre en el repositorio, lo decide `maujimenez4`, no nosotros.

## 16:45 · Estado del árbol cuando escribo esto

- **Qué:** `ruff check` da 23 errores (uno de sintaxis en `validadores.py:368`) y `pytest` 4 rojos de 439. Es el ciclo de arreglos en vivo, no una avería. **[Corregido a las 17:15: dije que era Hernan y era Jose. Ver la entrada de esa hora.]**
- **Estado:** terminado — solo para que nadie se asuste ni lo arregle por encima
- **Ojo:** tres de los cuatro rojos son tests que **codificaban el defecto** H-5 (`test_con_03_se_dispara_con_un_objeto_fisico_cualquiera`). Caen porque el defecto se está corrigiendo: hay que actualizarlos, no restaurar el comportamiento viejo.

## 16:55 · Corrección de Mario, y la separo de lo mío

- **Qué:** en mi entrada de las 16:45 dije que los rojos eran tests que codificaban el defecto. Vale para tres. El cuarto, `escritura/tests/test_continuidad_en_g1a.py`, **no**: cae porque el corte de `Afirmacion.objeto` cruzó la frontera de feature y `validar_objetos` lee el mismo campo.
- **Estado:** terminado
- **Ojo:** **CON-02 sí bloquea G1a.** Si el corte deja a `validar_objetos` sin campo, no es un test que haya que actualizar: es un validador de continuidad que deja de bloquear. Mario lo lleva como bloqueante de su revisión. Que nadie lo cierre como «test viejo».

## 17:00 · RF-CTX-07 incumplido: no existe el filtro estructural

- **Qué:** hallazgo de Julio, verificado por Mario y ahora por mí leyendo el código. `contexto/repository.py:168` promete «ya filtrados por el filtro estructural» y llama a `candidatos_para_ordenar(tope)` **sin pasar `escena_id`**. `canon/repository.py:511` dice que «el filtro estructural va antes» y hace `SELECT ... ORDER BY rowid DESC LIMIT ?`. Cada docstring da por hecho que filtra el otro; no filtra ninguno.
- **Ficheros:** ninguno tocado. Solo lectura.
- **Estado:** terminado — avisado el usuario
- **Ojo:** rompe §4.2, donde el orden filtrar → ordenar semánticamente → fusionar con recencia es **no negociable**. Hoy la capa de memoria recuperada le da al modelo los N fragmentos más recientes, sin mirar quién está presente, dónde ni qué hilos siguen abiertos, y la ordenación semántica corre sobre eso. Es exactamente lo que §4.2 dice que no se haga: «ordenar por parecido sin filtrar antes trae escenas parecidas, no pertinentes». No es mío y no lo toco.

## 17:15 · Me equivoqué al atribuir, y cómo

- **Qué:** dije aquí y a Jose y a Mario que quien editaba `validadores.py` era Hernan. **Es Jose.** Hernan trabaja en `specs/002-validadores-fallo-cerrado/`: `validar_spec.py`, `sonda_dominio.py` y `auditoria-criterios.md`, ninguno en `src/`.
- **Estado:** terminado — corregidas las entradas de 16:45 y 16:55, y avisados Jose, Mario y Hernan
- **Ojo:** lo deduje del `git status`, que es exactamente lo que esta bitácora existe para no tener que hacer. Me lo señaló Hernan y tiene razón: **cuando se atribuya trabajo, el dato sale de la bitácora o de un mensaje del propio agente, nunca del árbol.** El árbol dice qué ficheros se mueven, no quién los mueve.

## 17:20 · H-7 no reproduce en HEAD

- **Qué:** Hernan reportó H-7 —`validar_discurso` devolvía `[]` con `tiempo_verbal` fuera de dominio y `KeyError` con `persona` fuera de dominio—. Lo ejecuté contra el código actual y **ya no pasa**: las dos entradas lanzan `EntradaFueraDeDominio`, o sea falla en cerrado.
- **Ficheros:** ninguno. Solo ejecución.
- **Estado:** terminado — avisados Hernan, Jose y Mario
- **Ojo:** o Jose lo arregló en los últimos minutos, o la verificación de H-7 se hizo sobre un estado anterior. En cualquier caso **no hay nada que arreglar hoy en `validar_discurso`**: que nadie gaste un paso en ello. Lo que sí sigue en pie es la observación de fondo de Hernan, que no depende de este defecto: cuatro requisitos de la 002 están escritos como propiedad universal y ningún criterio de aceptación los comprueba como tales.

## 17:35 · DEP-01 verificado: el `hc_id` se pierde antes de la etiqueta

- **Qué:** Ezequiel (spec 003) dice que `ejecucion.ids_recuperados` solo cubre `MEMORIA_RECUPERADA` y que `CANON_RELEVANTE` etiqueta por posición. Confirmado leyendo: `contexto/service.py:173-180` filtra por `ETIQUETA_RECUPERADO` sobre esa única capa, y `recoleccion.py:96-107` etiqueta `canon-presente-{i}` con el índice del `enumerate`.
- **Ficheros:** ninguno tocado. Solo lectura.
- **Estado:** terminado — avisado el usuario
- **Ojo:** es **un punto más hondo** de lo que dice la spec 003. No es que la etiqueta pierda el `hc_id`: es que `almacenes.canon_relevante(escena_id)` devuelve `(texto, presente)` y el `hc_id` **no llega nunca** a `recoleccion`. Arreglarlo no es cambiar el formato de la etiqueta, es cambiar lo que devuelve el almacén. Y toca RI-14: hoy `ejecucion` registra qué se recuperó de la memoria semántica, pero no qué hechos de canon entraron en el paquete, así que la auditoría de una escena es parcial. Es de `contexto`, no es mío.
