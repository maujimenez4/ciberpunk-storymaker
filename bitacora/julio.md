# Julio

Sesión de verificación, commits y corridas. No escribo código de producción:
compruebo lo que otros terminan y lo subo si está en verde.

## 15:15 · Verificación de referencia del árbol

- **Qué:** `verificar.sh` entero antes de tocar nada, para saber de qué estado se parte.
- **Ficheros:** ninguno. Solo lectura.
- **Estado:** terminado. Las cinco puertas en verde, 398 tests, corrida en seco 10/10.

## 15:26 · Salvo la evidencia de la corrida del 22-sep

- **Qué:** la base de aquella corrida vivía en `%TEMP%` y Windows la iba a barrer. Era la única prueba de la avería que auditó Jose.
- **Ficheros:** `Documents\evidencia-corridas\corrida-real-2026-09-22\` (fuera del repositorio: §15 no deja prosa aquí dentro).
- **Estado:** terminado. Base, log y manuscrito en `.txt`, `.md` y `.pdf`.
- **Ojo:** verifiqué las afirmaciones de Jose contra esa base antes de darlas por buenas. Todas se sostienen: `version_obra.biblia` era `{}` y las capas `canon_relevante`, `estado_en_t` y `memoria_recuperada` fueron constantes en las diez escenas.

## 15:32 · Corrida real de CA-1

- **Qué:** diez escenas contra el CLI de Claude, encargada por `maujimenez4`.
- **Ficheros:** `manuscritos/manuscrito-real.{md,pdf}` y `Documents\evidencia-corridas\corrida-real-2026-09-23\`.
- **Estado:** terminado. 9/10 integradas, 14.181 palabras, 0,9348 USD, código de salida 1.
- **Ojo:** esta corrida **no lleva el cableado del Continuista**. El proceso cargó `corrida.py` antes de que aterrizara, y su base solo tiene filas del escritor. Su «0 defectos» no dice nada sobre continuidad: no lo leáis como que el texto está limpio. Lancé con `--base`, así que esta vez la base sobrevive.

## 15:45 · Commits de la tanda

- **Qué:** cuatro commits subidos a `origin/seed-context-v2-backend-v1`, cada uno verificado antes de subirlo.
- **Ficheros:** `57e6c11` skills de proceso · `1d410b0` exportación a Markdown y PDF · `2193724` el Continuista en el bucle · `9e02d50` la nota de Gustavo sobre medir el umbral en seco.
- **Estado:** terminado.
- **Ojo:** dejé `corrida.py` fuera del commit de la exportación y lo metí en el del Continuista. Pasa `continuista=` y `defectos=` a un `Dependencias` que antes de ese commit no los aceptaba: en el otro habría quedado roto. Paré también un commit con un test en rojo que resultó ser un ciclo TDD a medias, no una avería.

## 16:05 · Verificación del consumo de tokens

- **Qué:** encargo de `maujimenez4`. Medí las ocho capas de las diez escenas contra los topes de §4.1.
- **Ficheros:** ninguno. Solo lectura y una reproducción de `recolectar` sobre la base guardada.
- **Estado:** terminado el diagnóstico; la reparación está sin empezar y sin spec.
- **Ojo:** esto afecta a quien dé por cierto el reparto de §4.1 o la clasificación de RF-CTX-07.
  - `memoria_recuperada` pide entre 20.297 y 23.837 tokens contra un tope de **10.000**: se descarta más de la mitad en cada escena. Lo que guarda `ejecucion` es el valor **después** del recorte, así que del registro no se ve.
  - Me corrijo a mí mismo: dije que el tope estaba «a punto» de morder. Muerde desde el principio.
  - `canon/repository.py:511` hace `SELECT ... FROM fragmento ORDER BY rowid DESC LIMIT 50`. Eso son las últimas 50 escenas enteras: **no hay filtro estructural** por presentes, lugar, hilos abiertos ni rango de capítulos, pese a que dos docstrings afirman que sí. RF-CTX-07 es M y está clasificado T; los únicos tests comprueban el tope y que no vuelva vacío.
  - El límite duro de 100.000 no está ni cerca: la llamada mayor fue de 18.106. Las demás capas van por debajo del 20% de su tope. El problema es el reparto, no el volumen.
  - `ensamblar` devuelve `descartado_por_capa` y el router lo expone, pero el ciclo **no lo persiste**. No queda rastro de lo que se tiró.
- **No toco nada:** §3 punto 7 dice que el presupuesto de contexto se pregunta antes. Está en manos de `maujimenez4`.

## 16:20 · Retengo el push de `1c7dbe1`

- **Qué:** el árbol volvió a verde (444 tests) y hay un commit local sin subir, pero incluye `specs/002-validadores-fallo-cerrado/spec.md`, que Mario tiene bloqueada. No lo empujo.
- **Ficheros:** ninguno. Solo `git`.
- **Estado:** bloqueado, a la espera de que Mario dé la 002 por buena.
- **Ojo:** dos motivos vivos para no subirla. RF-CAL-17 se ha quedado sin criterio de aceptación, y P-1 a P-5 siguen sin firmar con `aprobada_por` vacío mientras el código ya ha contestado cuatro de las cinco. Acordado con Mario que aviso antes de cada push; hoy soy el único que commitea.
- **Ojo 2:** ha aparecido `specs/003-lectura-web/` de otra sesión. Si la reparación del presupuesto de contexto acaba en spec propia, ya no puede ser la 003.

## 16:40 · El Escritor copia frases enteras de la escena anterior

- **Qué:** medí el solape de frases largas (≥8 palabras) entre escenas consecutivas de la corrida real. No es paráfrasis: son frases idénticas.
- **Ficheros:** ninguno. Solo lectura sobre `evidencia-corridas\corrida-real-2026-09-23\obra.db`.
- **Estado:** terminado el hallazgo; sin reparación y sin spec.
- **Ojo:** esto afecta a quien esté juzgando la calidad de la corrida de hoy.
  - es4→es5 9 frases · es5→es6 15 · es8→es9 14 · **es9→es10 34 frases, el 41% de es10**.
  - Nada lo caza. La taxonomía de `definitions.md` §8 no tiene código de repetición, y `ngrama_vetado` (313 filas) se escribe y no la lee nadie — pero eso está **declarado** en RD-13, que dice que su único consumidor es el Editor de línea, fuera de alcance. Es hueco conocido, no avería oculta.
  - Hipótesis, no hallazgo: el Escritor recibe la escena anterior entera en `continuidad_local` y escenas enteras sin filtrar en `memoria_recuperada`. Si se confirma, conecta con lo de los tokens.
- **Corrijo un dato ajeno:** la inconsistencia de las horas de sueño que reportó Jose (77 frente a 56) **no está en la prosa**. El texto dice «cuarenta y dos horas» en es8, es9 y es10, consistente. El desajuste está en el canon extraído, así que es del Extractor, no del Escritor.
