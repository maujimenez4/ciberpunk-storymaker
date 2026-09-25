# Explainers — un concepto por apartado, breve

**Para qué existe este documento.** El encargo pide «uno por cada concepto del curso aplicado
en el proyecto. **Breves.** Para demostrar que se entiende lo que se aplica, no para copiar
la teoría». Así que cada apartado tiene tres partes y ninguna sobra:

1. **Qué es** — en dos o tres líneas, sin manual.
2. **Cómo se aplica aquí** — el sitio concreto del repositorio, no la idea general.
3. **Qué no da, y estado** — lo que el concepto **no** compra, y si está construido.

La tercera parte es la que demuestra que se entiende. Un concepto del que solo se sabe decir
para qué sirve no se entiende: se ha leído.

**Fecha de corte: 2026-09-24, sobre `bfb5396`.** La versión anterior (`63363e8`) daba por
inexistentes Langfuse, Lean, TLA+, el hook de *policy* y el juez. Los cinco están en código;
cada apartado dice ahora qué falta de verdad. Los apartados 3, 5, 14, 17, 18 y 19 son los que
más cambian, y el 0, el 16 bis y el 25 son nuevos: responden a las preguntas que un revisor
se hace al ver el sistema funcionar.

---

## 0 · Por qué la unidad es la escena y no el capítulo ni la novela

**Qué es.** La unidad atómica de generación: lo que se pide al modelo en una llamada, se
valida, se repara y se versiona como un todo.

**Aquí.** Dos conceptos que a esta escala coinciden 1:1 y no se funden: el **capítulo** es
unidad de **lectura** —donde el lector decide si sigue— y la **escena** es unidad de
**generación** —lo que cabe en una llamada—. Una escena tiene exactamente un POV y un giro de
valor no nulo (`CLAUDE.md` §8, regla 1), y eso la hace **juzgable**: una puerta puede decir
«esta escena no cumple» y citar el pasaje. Todo lo demás se cuelga de ella: el paquete de
contexto, el trabajo, la versión de texto, la traza de Langfuse, el contador de reparaciones
y el registro de en qué capítulo se usó cada hecho.

**Por qué no la novela entera:** no cabe en el presupuesto, y un defecto en doce mil palabras
no se atribuye ni se repara sin reescribirlo todo. **Por qué no el párrafo:** no tiene giro
propio, así que no hay nada que juzgar.

**Qué no da.** Lo que solo existe en el conjunto —una cronología imposible repartida en tres
capítulos impecables, la curva de la novela, los cabos sueltos— **no se ve desde la escena**.
Por eso existen Lean en la publicación y, pendiente, el Auditor de manuscrito.

---

## 1 · Harness

**Qué es.** Todo lo que rodea al modelo para que su salida sea utilizable: quién lo llama,
con qué contexto, qué se valida, qué se guarda y qué pasa cuando falla. El modelo es el
componente barato de sustituir; el harness es el producto.

**Aquí.** Un orquestador determinista en código —`features/escritura/maquina.py`, con tabla
de transiciones explícita—, un ensamblador de contexto que también es código, **ocho de los
diez roles en producción** —faltan el Editor de línea y el Auditor de manuscrito—, dos hooks,
validadores con punto de ejecución declarado, y estado en SQLite. **Ningún agente decide cuál
es el siguiente paso.** El recorrido completo, desde la entrevista hasta el token de lectura,
está dibujado en [`diagramas.md`](diagramas.md) §2.

**Qué no da.** Un harness impecable pasea una escena equivocada por los diez estados
correctos sin inmutarse. Verifica el flujo, no el contenido.

---

## 2 · Orquestación como máquina de estados

**Qué es.** Modelar el trabajo como estados y transiciones explícitas en lugar de una función
que decide sobre la marcha, para que el estado sea consultable, persistible y reanudable.

**Aquí.** Diez estados por capítulo —seis vivos y cuatro terminales— y una máquina por
encima, la de la **novela**, que es la que modela `formal/tla/Harness.tla`. El estado vive en
SQLite y nunca en memoria del proceso: una caída no pierde trabajo, y desde el navegador
tampoco — la pantalla apunta la obra en `localStorage` y, al recargar, vuelve a consultar
`GET /obras/{id}/novela` en vez de abrir otra entrevista (`3f10d77`).

**Qué no da, y es un hallazgo del proyecto.** La reanudación **relanza el capítulo como
trabajo nuevo, no retoma el trabajo muerto**, porque el ciclo es una sola función que recorre
la máquina entera. Retomar de verdad exige partir el ciclo en pasos direccionables, que es un
refactor. La garantía que carga el peso sigue en pie: **un paso interrumpido se repite
entero, nunca se reanuda a medias**, y la caída tiene señal propia, `proceso_interrumpido`
(`2de6027`), en lugar de disfrazarse de plazo vencido.

---

## 3 · Ingeniería de contexto: el paquete y sus capas

**Qué es.** Decidir, para cada llamada, qué información entra y cuál no — en vez de meter
todo lo que se tenga y confiar en la ventana.

**Aquí.** Ocho capas con **tope propio**: constitucional 5.000, estructural 10.000, canon
20.000, estado en T 15.000, continuidad local 20.000, memoria recuperada 10.000, instrucción
10.000 y reserva 10.000. Suman exactamente 100.000. Si una capa se pasa, se recorta **esa**
—y cada capa sabe qué se va primero: la escena N-2 antes que la N-1, el personaje mencionado
antes que el presente—; si tras recortar no cabe, se lanza `ContextBudgetExceeded` **sin
llamar al modelo**. La reserva existe para que el reintento, que añade el defecto y su cita,
siga cabiendo, y **se vuelve a presupuestar** antes de cada reintento. El desglose por capa
vuelve junto al paquete, se persiste en `ejecucion` y es la salida del span `ensamblador`.

**Qué no da.** Que los números cuadren no dice que el paquete sea el **pertinente**. El fallo
de pertinencia del ensamblado es invisible en la traza y aparece después, como defecto de
continuidad. Está marcado **Descubierto** en `verification.md` §7.

---

## 4 · Presupuesto de tokens: dos techos que no son el mismo

**Qué es.** Un techo **por llamada** acota lo que cabe en un prompt. Un techo
**concurrente** acota la suma de lo que está en vuelo. Son restricciones distintas con el
mismo número.

**Aquí.** El primero lo aplica el Ensamblador al construir el paquete. El segundo es **del
encargo** —«un máximo de 100.000 tokens concurrentes», §7— y lo aplica un portero
(`PresupuestoConcurrente`, `commons/jobs/`) **antes de dar turno**, contando tokens y no
llamadas. Si admitir una llamada pasaría del techo, esa llamada **espera** — nunca se recorta
el paquete para hacerla caber.

**Por qué el segundo importa aunque parezca trivial.** Mientras todo corría en serie, la suma
en vuelo *era* la única llamada, y el encargo se cumplía **por consecuencia, no por regla**:
subir la concurrencia a dos lo habría incumplido sin que fallara un test. Desde `92d2da7`
hay dos llamadas vivas de verdad —el Continuista y el Crítico, apartado 16 bis— y el portero
deja de ser decorativo. Cada turno se pide con los tokens del prompt **más la sobrecarga fija
del CLI**, medida en ~1.200 y declarada en 2.000 (`SOBRECARGA_POR_LLAMADA`,
`verification.md` §5.2).

**Qué no da.** Ninguno de los dos acota el **coste total de una novela**: diez capítulos con
reintentos suman lo que sumen. Es **U** en la clasificación y riesgo abierto declarado. Y la
sobrecarga se midió con una cuenta que inyecta instrucciones propias en cada llamada
(apartado 25): hay que volver a medirla con la cuenta de la corrida (`5a6baa3`).

---

## 5 · Memoria: ledger *append-only*, canon y vistas derivadas

**Qué es.** Guardar los **hechos ocurridos** en un registro que solo crece, y calcular el
estado actual a partir de él, en vez de mantener una tabla de estado que alguien edita.

**Aquí, en tres piezas que conviene no confundir:**

| Pieza | Qué guarda | Cómo se protege |
| --- | --- | --- |
| **Ledger** (`evento`) | Lo que **pasó** en cada escena: quién, dónde, cuándo, qué supo | Dos disparadores de SQLite impiden `UPDATE` y `DELETE`: es una regla del motor, no una convención |
| **Canon** (`hecho_canon`) | Lo que **es cierto** del mundo: entidad, atributo, valor, origen | Corregir no edita: se escribe un hecho nuevo que **cita al anterior** en `sustituye_a` |
| **Vistas** (`estado_en_t`, `cronologia`) | Lo que se **deriva** de los dos anteriores | No son tablas: no hay nada que editar |

El único que escribe canon y ledger es el **Extractor**, en el paso `EXTRAYENDO`, y solo con
la prosa **aprobada**. Por eso `hecho_usado_en` —en qué capítulo se apoyó cada hecho— es lo
que permitirá regenerar solo lo afectado cuando el Destinatario pida un cambio. Y por eso lo
rechazado vive **aparte**, en `intento_descartado` (`d3b0d88`): si quedara como versión de
texto vigente, el capítulo siguiente lo leería como continuidad.

**Qué no da.** Un ledger honesto no dice si lo que se registró era cierto. El grafo solo sabe
si algo **choca** con lo que ya contiene; un hecho nuevo que no contradice nada **no tiene
contra qué contrastarse**, y entra. Y dos deudas vencen al regenerar: `evento` y
`hecho_canon` no llevan `run_id`.

---

## 6 · Recuperación híbrida (RAG), y por qué el orden importa

**Qué es.** Traer del almacén lo que hace falta para esta llamada, combinando criterios: qué
es estructuralmente pertinente, qué se le parece y qué es reciente.

**Aquí, y en este orden:** filtro estructural —presentes, lugar, hilos abiertos, rango de
capítulos— → orden por afinidad de vectores **sobre el conjunto ya filtrado** → fusión con
recencia. Ordenar por parecido sin filtrar antes trae escenas **parecidas, no pertinentes**.

**Qué no da, dicho sin suavizar.** El vectorizador es **léxico**, no semántico: bolsa de
palabras normalizadas repartidas con `blake2b`. Dos fragmentos que dicen lo mismo con otras
palabras **no se reconocen**. Los documentos dejaron de decir «similitud semántica» y dicen
«afinidad de vectores» por eso.

---

## 7 · Multiagente y separación de roles

**Qué es.** Repartir el trabajo entre roles con prompt, contexto y criterio de éxito
distintos, en lugar de pedirle a uno solo que escriba y se corrija.

**Aquí.** Diez roles diseñados, ocho en producción. El Escritor **solo ve el paquete** y
nunca la base de datos; el Continuista devuelve **códigos con cita**, nunca prosa corregida;
el Crítico **no repara**. La topología es en estrella: ningún agente llama a otro.

**Qué no da.** Los validadores **no fallan de forma independiente**: comparten proveedor, la
redacción de las restricciones duras y —lo más fuerte y menos visible— **la misma entrada**.
Desde el 2026-09-24 comparten además **modelo**: Haiku 4.5 en todos los roles, por coste
(~1,5 USD por novela frente a ~8,8). Regla de lectura: **dos validadores correlacionados
cuentan como uno**.

---

## 8 · Prompts versionados y restricciones duras

**Qué es.** Tratar el prompt como artefacto con versión, no como una cadena que se retoca.

**Aquí.** Viven en `features/<feature>/prompts/`, uno por rol, con nombre versionado, y **no
se editan en sitio**: versión nueva y se cambia la referencia. El caso real: el Arquitecto
describía el tipo de corte con una frase y el esquema la rechazaba; la corrección fue
`arquitecto.v2.md` con los tres literales exactos, sin tocar la v1 (`0513035`). `ejecucion`
guarda el **hash** del fichero, y desde `bfb5396` el mismo trío —`prompt_id`,
`prompt_version`, `prompt_hash`— va en el span de Langfuse de cada rol. Las restricciones
duras se repiten **al principio y al final**, porque el centro del prompt es donde más
información se pierde.

**Qué no da.** Ninguna regla de seguridad puede depender solo del prompt. Edad, nivel de
calor, consentimiento y vetos se validan **además** en código.

---

## 9 · Tools con esquema validado

**Qué es.** Dar al modelo funciones que puede invocar, con la entrada y la salida descritas
por un esquema que se comprueba.

**Aquí, y es una ausencia decidida.** **Ningún agente narrativo recibe herramientas**
(`architecture.md` §3.5.1). Lo que sí se valida con esquema es la **entrada y la salida de
cada rol**: un agente que devuelve algo fuera de su esquema es **un fallo, no una respuesta**.
Y esa validación ha trabajado dos veces contra el modelo real: rechazó una respuesta sobre el
repositorio en vez de sobre la entrevista, y rechazó el outline con el corte mal escrito, que
ahora vuelve **una vez** al Arquitecto con la lista de fallos.

**Qué no da.** Un JSON perfecto puede afirmar una barbaridad. El esquema verifica la forma;
del fondo no dice nada.

---

## 10 · Hooks

**Qué es.** Un punto de enganche declarado, fuera del código que vigila, donde se ejecutan
comprobaciones o políticas.

**Aquí.** Dos, los dos en código: **validación de capítulo** (`HOOK_DE_CAPITULO`) y
**policy** (`calidad/policy.py`, `168461a`), que aplica los vetos y escribe cada decisión
—la permitida también— en el registro de auditoría. El motivo de que sean hooks y no llamadas
dentro del servicio: un guardarraíl que vive dentro del código que vigila **se puede saltar
cambiando ese código sin que nada lo note**; la ausencia de un hook **se ve**.

**Qué no da, y una reserva.** El encargo nombra los hooks junto a `CLAUDE.md` y la skill, que
son artefactos de Claude Code; no hay hooks en `.claude/settings.json` y esa otra lectura no
está razonada en ningún documento (P-31).

---

## 11 · Guardarraíles

**Qué es.** Políticas aplicadas en código que restringen lo que el sistema puede producir,
con independencia de lo que el modelo quiera producir.

**Aquí.** Vetos en **tres ámbitos** —global, obra y brief— comparados sobre texto
**normalizado** —minúsculas, sin acentos, sin la `-s` del plural simple— y **por palabra, no
por subcadena**, para que un nombre corto no salte dentro de una palabra más larga. Una
coincidencia devuelve el capítulo al escritor con el término concreto; agotado el límite, **la
generación se detiene y se informa**, y el término queda en `intento_descartado`.

**Qué no da.** Caza la **palabra**, no la **alusión**. Y el plural en `-es` de las palabras
terminadas en consonante necesita un diccionario, no una regla: está escrito en el docstring
para que nadie lo descubra tarde.

---

## 12 · Inyección de prompt y contenido no confiable

**Qué es.** Que un texto que el sistema no controla acabe en la posición del prompt donde una
instrucción se obedece.

**Aquí la defensa es estructural, no retórica.** No se le pide al modelo que no haga caso
—eso es negociar con el atacante—: el texto entra **marcado como dato**, dentro de un
delimitador, y **nunca se concatena sin esa marca**. La pantalla lo manda en un campo propio,
`texto_aportado`, separado de las respuestas, y es el servidor quien lo envuelve. Además se le
**quitan las etiquetas hasta punto fijo**, porque una sola pasada de borrado puede
**recomponer** la etiqueta que acaba de quitar.

**Qué no da.** La marca dice de dónde viene el texto; **no juzga el texto**. Y el vector que
sigue sin cubrirse es el otro: una instrucción incrustada en la **prosa generada** que el
Extractor consolida como canon. El detalle está en [`red-team-log.md`](red-team-log.md).

---

## 13 · Idempotencia y checkpoint

**Qué es.** Que repetir un paso no duplique escrituras, y que un proceso que muere pueda
continuar desde donde llegó.

**Aquí.** La clave de idempotencia **no es el `run_id` solo: es `run_id` + paso + ordinal** —
con el `run_id` a secas, la primera reparación dirigida sería indistinguible de una
repetición—. Y **no hay tabla de checkpoint**: el avance **se deriva** del propio `trabajo`,
porque una tabla aparte sería un segundo relato de lo ocurrido que puede divergir del primero
justo tras una caída. `POST /obras/{id}/novela` pide siempre el primer capítulo no integrado,
así que lanzarla dos veces reanuda en vez de duplicar.

**Qué no da.** La exhaustividad sobre los estados la sostiene **quien escribe los tests**, no
un método. Por eso `ReanudacionIntegra` la comprueba también TLC, por otra vía.

---

## 14 · Reintento dirigido, con tope

**Qué es.** Volver a pedir con **el defecto concreto** en el prompt, en vez de pedir «mejóralo».

**Aquí.** Máximo **dos** reparaciones por capítulo; después, `ESCALADA`, y la novela se
detiene. El reintento lleva el código del defecto y la **cita del pasaje**. El contador es
**del capítulo, no del trabajo**: contarlo por trabajo daría reintentos infinitos, porque
bastaría un fallo del proveedor para recuperar las dos vueltas. Avanzar de capítulo **no
consume reintentos**. El Arquitecto tiene su propio tope, **uno**, que acota el coste del
outline a dos llamadas.

**Lo nuevo, y era lo que impedía decidir.** Hasta el plan 8, un capítulo escalado **no dejaba
nada que revisar**: las versiones rechazadas se borraban para no contaminar la continuidad.
Ahora cada intento rechazado queda con su texto, sus códigos y sus citas en
`intento_descartado`, y se lee en `GET /trabajos/{id}/intentos` (`d3b0d88`, `7e44901`). Es lo
que distingue «el modelo escribió mal tres veces» de «un validador rechaza siempre».

**Qué no da.** Cuenta reintentos, no **progreso**: no sabe si los intentos gastados sirvieron
de algo.

---

## 15 · Evals

**Qué es.** Probar el comportamiento del sistema contra un conjunto fijo de casos y un método
de puntuación, para poder decir si un cambio mejora o solo desplaza la salida.

**Aquí, y no existe todavía.** Es una de las dos condiciones eliminatorias del encargo. Pide
**cinco briefs** —uno adversarial y uno construido para provocar una incoherencia temporal—,
una **tabla** de qué validador pasó por brief, y **una iteración de *tuning*** con resultados
antes y después. Depende de poder generar novelas reales, y eso depende del apartado 25.

**Qué no da.** Cinco briefs son **cinco puntos**: cubren los modos de fallo que alguien
imaginó al escribirlos, y **el sexto brief —el que traerá un Comprador real— no está
representado**. Una tabla con cinco filas en verde mide la cobertura del conjunto, no la del
sistema.

---

## 16 · LLM-as-judge con rúbrica

**Qué es.** Un modelo puntúa la salida de otro contra criterios escritos, con **puntuación y
justificación por criterio**.

**Aquí.** El Crítico puntúa cada capítulo contra `RUBRICA_V1` —continuidad, tono, arco,
coherencia de personajes, ritmo y **naturalidad de la personalización**—, con anclajes
descritos y una justificación por criterio; una puntuación sin justificación **no se acepta**
(`0d0f4df`). Corre en producción (`4f35669`) y cada criterio sube a Langfuse como su propia
serie, `juez_con_rubrica.<criterio>` (`057eea4`), que es lo que la iteración de *tuning*
necesita comparar.

**Qué no da, y por eso no bloquea.** Puntúa contra los criterios **enunciados**. La única
forma de saber cuánto vale es medir su **distancia** con una revisión humana con la misma
rúbrica —cuyo servicio no existe— y eso mide la distancia entre dos jueces, **no que alguno
acierte**. Y hoy comparte modelo con quien escribe, así que esa distancia **saldrá mejor de lo
que el sistema merece**: está dicho en `CLAUDE.md` §4 y la constante `MODELO_JUEZ` sigue
separada para revertirlo con una línea.

---

## 16 bis · Por qué los dos jueces pueden solaparse

**Qué es.** Ejecutar a la vez dos llamadas que no dependen la una de la otra.

**Aquí.** El Continuista y el Crítico reciben **la misma prosa**, no se leen entre sí y
escriben resultados distintos. Y el Crítico **no decide nada**: su juicio no entra en la
puerta. Así que el Crítico arranca a la vez que el Continuista, y la puerta G1a solo espera al
Continuista (`92d2da7`). El capítulo, en cambio, **no** se solapa con el siguiente: el
capítulo N+1 necesita el canon y el resumen que produce el N.

**Las tres condiciones que lo hacen seguro, y que son la parte que se entiende o no:**

1. **Se cuenta.** El Crítico pide su propio turno al portero, con su prompt más la
   sobrecarga. El techo concurrente del apartado 4 es el que manda.
2. **No espera.** Pide turno con `espera_maxima=0`: quien lo pide ya retiene el turno del
   capítulo, y esperar otro con el suyo retenido es la forma en que dos obras acaban
   bloqueándose la una a la otra. Si no cabe, el Crítico corre **después, en serie**, como antes.
3. **No tumba nada.** Si el Crítico devuelve basura, queda en su span y el capítulo sigue: que
   un capítulo cayera o no dependería, si no, de si había hueco en el techo.

**Qué no da.** El paralelismo **no acorta la novela a la mitad**: le quita una espera de juez
por intento. La cadena de diez capítulos sigue siendo secuencial.

---

## 17 · Observabilidad y trazas

**Qué es.** Instrumentar el sistema para que su trayectoria sea visible y consultable después,
agrupada por algo que signifique algo.

**Aquí, cableado.** Una **sesión por obra**, derivada de `obra_id`. Dentro, **una traza por
unidad de trabajo**: `outline`, `capitulo N · <run_id>` y `publicacion`. Dentro de cada traza,
**un span por rol** —`planificador`, `ensamblador`, `escritor`, `policy`, `continuista`,
`puerta_g1a`, `critico`, `extractor`, `arquitecto`, `cronologia_lean`, `puerta_g4`—, y los
roles con modelo llevan la plantilla que los produjo. **Un *score* por validador** y uno por
criterio del juez. El observador es uno por proceso, hace `flush` al apagar y llega
**blindado**: si Langfuse se cae, la novela se escribe igual. Dibujo en
[`diagramas.md`](diagramas.md) §7.

**El coste, declarado.** Suben el prompt renderizado y la salida, **y con ellos el
manuscrito**, porque cinco de los diez roles reciben la prosa **como entrada**. Los datos del
Destinatario viajan a un servicio externo por decisión fechada; **fuera de Langfuse no sale
nada**.

**Qué no da, y estado.** Nada de esto se ha visto contra una **instancia real**: los tests usan
un cliente falso con la forma del SDK. La entrevista **no tiene traza**, porque corre antes de
que exista la obra de la que se deriva la sesión; es una decisión abierta (`architecture.md`
§9.2.1). Y el coste imputado se queda corto cuando la caché acierta (P-18).

---

## 18 · Verificación formal (Lean 4)

**Qué es.** Demostrar matemáticamente que algo cumple una propiedad **para todas las entradas
posibles**, no para las que alguien probó.

**Aquí, y sobre la historia, no sobre el código.** Al publicar, la vista `cronologia` se
convierte en un fichero Lean (`manuscrito/lean/generador.py`) y se comprueban dos invariantes:
**`sinUbicuidad`** —nadie en dos lugares a la vez— y **`sinReaparecidos`** —nadie aparece
después de un evento que lo excluye—. **Es una puerta, y la única que bloquea en la
publicación:** si falla, `CronologiaIncoherente` detiene `publicar` con un `409` y no se crea
versión (`4c6ff5c`). Si Lean no está instalado **tampoco se publica** —que falte la herramienta
no puede degradar a «entregamos sin comprobar»— y no se emite *score*, porque un cero sería
inventado.

**Por qué no lo cubre la puerta de escena:** una cronología imposible puede estar repartida en
tres capítulos, cada uno impecable por separado. Nadie miente; las fechas no encajan al
ponerlas juntas.

**Qué no da.** Demuestra las invariantes **escritas**, sobre el **fichero generado** y no
sobre la prosa. Las **fechas de nacimiento no entran** a propósito —hoy solo el destinatario
tiene fecha, y no es un personaje del fichero (P-27)—, así que la edad contra la fecha no se
comprueba. El fallo termina en un `409` y **no vuelve a ningún rol como *feedback***, que es lo
que pide el encargo (P-28). Y todavía no ha cazado un caso real: solo fallos provocados en test.

---

## 19 · Comprobación de modelos (TLA+ / TLC)

**Qué es.** Explorar **exhaustivamente** los estados alcanzables de un sistema para
comprobar invariantes que los tests solo tocan por muestreo.

**Aquí, y sobre el harness, no sobre la historia.** `formal/tla/Harness.tla`: quince
acciones, tres invariantes de seguridad más `TypeOK`, una propiedad de acción y una de
*liveness*, sobre el modelo pequeño de `harness.cfg` —cinco capítulos, dos reintentos—. TLC
en verde: 65.601 estados distintos en unos tres segundos. Corre en desarrollo, no en cada
novela. Los cuatro contraejemplos que hay son **de laboratorio**, provocados rompiendo el
modelo para ver caer cada propiedad; ninguno real.

**La correspondencia con el código, que es la pregunta que hay que hacerse.** Que TLC no
encuentre contraejemplo no dice nada si la especificación modela otro sistema. Aquí esa
correspondencia está **mecanizada a medias**: `formal/tla/correspondencia.toml` empareja cada
acción con los símbolos del código que la implementan, y `test_correspondencia_tla.py` falla
si una transición del código no está reclamada, si un símbolo no existe o si una acción
prevista empieza a existir sin que la tabla se entere (`e76ab85`). Y mide `transitar`
**ejecutándolo**, no leyendo su tabla: cuando la leía, veinte de treinta y una transiciones eran
invisibles.

**Qué no da.** Que la acción **haga** lo que su nombre dice sigue siendo inspección humana. La
terminación depende de una hipótesis de equidad fuerte sobre `Aprobar`, y está clasificada
como condicional. Y tres acciones —la regeneración— están modeladas y no tienen código.

---

## 20 · Clasificación T / A / I / D / U

**Qué es.** Dar a cada requisito **una letra** según el método que lo establece: Test,
Análisis, Inspección, Demostración o **no verificable**.

**Aquí.** Existe para que los requisitos que nadie puede comprobar queden **visibles en vez de
darse por supuestos**. Un segundo método que refuerza se anota junto a la principal y **no la
sustituye**.

**Lo que hoy es U, nombrado:** la calidad narrativa, la calibración del Crítico, la
pertinencia de la memoria recuperada, que un hecho nuevo deba entrar en el canon, el coste
total de una novela y **que el Destinatario se reconozca**. Una U sin marcar es una
afirmación que se hace sin pruebas.

---

## 21 · TDD y las puertas del proceso

**Qué es.** Escribir el test **y verlo fallar** antes del código; un test que nunca se vio
fallar no prueba nada.

**Aquí.** Rojo → verde → refactor, con el test **en el mismo commit** que el código. Y cuatro
puertas por encima: Spec, Plan, Código y Cierre, con las dos primeras abiertas por **una
persona en un commit suyo** — ningún agente aprueba. Los commits del plan 8 dicen qué rojo se
vio y qué ablación se hizo: quitar la llamada del Escritor a `span.prompt` pone rojos los dos
tests del ciclo (`bfb5396`).

**Un detalle que el proyecto aprendió pagándolo:** cuando un módulo no existe, `pytest` **no
imprime FAIL**, imprime `1 error during collection` y `collected 0 items`. El rojo hay que
tomarlo en dos tiempos para verlo **contado**.

**Y lo que ningún doble podía ver.** La primera corrida contra el modelo real destapó cuatro
defectos que la suite, con dobles por diseño, no tenía forma de ver (`26efa68`), y después
otros seis entre la pantalla y el Arquitecto. Los dobles prueban el contrato que uno imaginó;
el proveedor real prueba el que existe.

---

## 22 · Tests de mutación, hechos a mano

**Qué es.** Romper el código a propósito y comprobar que la suite lo detecta. Miden **la
suite**, no el código.

**Aquí.** La herramienta está **aplazada**, así que el proyecto lo hace a mano: se quita la
validación y **el test que la cubre tiene que caer — su test y solo el suyo**.

**Qué ha encontrado.** **Nueve restricciones sobre las que ningún test podía caer** y **ocho
tests que pasaban por el motivo equivocado**. Y una lección de método: **una mutación que no
tumba nada es información, no permiso para seguir** — a veces es defensa redundante y a veces
un agujero real. En TLA+ pasó lo mismo: quitar una guarda no dio contraejemplo porque era
redundante, no porque el invariante fuera vacuo (`formal/tla/README.md` §5).

---

## 23 · Skills y subagentes

**Qué es.** Instrucciones empaquetadas y reutilizables para el agente de código, y agentes
auxiliares a los que se les reparte trabajo.

**Aquí.** Quince skills en `.claude/skills/`, commiteadas, con su procedencia, commit exacto y
licencia en `SOURCES.md`; dos son propias —`clarificar-spec` y `coherencia-docs`—. La regla:
**una skill no entra sin tres filas** —en `SOURCES.md`, en `CLAUDE.md` §13 y en
`architecture.md` §7.2—; sin las tres **no está instalada: está copiada**. Y subagentes
repartidos por olas, con la regla de «un agente por fichero dentro de la ola».

**Qué no da, y es el hallazgo de proceso más repetido.** El reparto por fichero **corta las
tareas justo por donde pasa el cable**: la juntura entre dos features no es de ninguna de las
dos tareas, y la acaba cerrando el integrador. Falta además un registro por subagente con
propósito y resultado (`specs/estado-del-entregable.md`).

---

## 24 · Inspección visual automatizada (browser MCP)

**Qué es.** Abrir el artefacto en un navegador real y comprobar sobre el renderizado lo que el
código fuente no dice.

**Aquí son dos cosas distintas y conviene no fundirlas:** (a) el **validador visual** de la
puerta G4, que es **código conduciendo un navegador y no un agente**, y cuyo resultado
bloquea; y (b) el **agente de código**, que recibe la herramienta por `.claude/mcp.json` —hoy
declara Playwright MCP— y cuyo resultado es una observación.

**Qué no da.** Comprueba que **algo** se ve, no que sea lo correcto: un índice con once
entradas para diez capítulos renderiza perfectamente.

**Estado:** la lectura web existe y `.claude/mcp.json` también; **el validador en código no**,
y ningún uso real del MCP está documentado todavía (P-30).

---

## 25 · Por qué el problema del nombre es del entorno y no del sistema

**Qué es.** Distinguir un defecto del producto de una restricción del sitio donde se ejecuta.

**Qué pasó.** El outline real salía con el protagonista como `[NOMBRE_ANONIMIZADO]`. La primera
hipótesis era de producto: trabajar con un marcador y sustituir el nombre al servir. Antes de
construirla se midió (`src/backend/scripts/sonda_nombre.py`, `38924c3`): una llamada real al
Arquitecto con el brief de ejemplo, contando sin imprimir. **Con la cuenta de trabajo, el
nombre real salía cero veces, y un nombre inventado también, con trece marcas de
anonimización.**

**Por qué eso lo decide.** Si hasta un nombre inventado se borra, no es el modelo ni el código:
son **instrucciones de la organización de esa cuenta**, que se aplican a toda llamada. El
marcador no lo habría esquivado, así que no se construyó —dos tareas del plan 8 no se
ejecutaron, con la desviación registrada—. Las mismas instrucciones inflan cada llamada, y por
eso la sobrecarga del CLI se declara medida con esa cuenta y pendiente de remedir.

**Qué se hace, y qué no da.** La novela se genera con una **cuenta personal**, sin esas
instrucciones, repitiendo antes la sonda. La restricción queda declarada: *el sistema no puede
escribir nombres propios con una cuenta cuya organización obliga a anonimizarlos*. Lo que la
sonda **no** demuestra es que con la otra cuenta salga bien: eso lo dirá la sonda repetida, y
hasta entonces P-19 sigue abierto.
