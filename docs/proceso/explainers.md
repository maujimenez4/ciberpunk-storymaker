# Explainers — un concepto por apartado, breve

**Para qué existe este documento.** El encargo pide «uno por cada concepto del curso aplicado
en el proyecto. **Breves.** Para demostrar que se entiende lo que se aplica, no para copiar
la teoría». Así que cada apartado tiene tres partes y ninguna sobra:

1. **Qué es** — en dos o tres líneas, sin manual.
2. **Cómo se aplica aquí** — el sitio concreto del repositorio, no la idea general.
3. **Qué no da, y estado** — lo que el concepto **no** compra, y si está construido.

La tercera parte es la que demuestra que se entiende. Un concepto del que solo se sabe decir
para qué sirve no se entiende: se ha leído.

---

## 1 · Harness

**Qué es.** Todo lo que rodea al modelo para que su salida sea utilizable: quién lo llama,
con qué contexto, qué se valida, qué se guarda y qué pasa cuando falla. El modelo es el
componente barato de sustituir; el harness es el producto.

**Aquí.** Un orquestador determinista en código —`features/escritura/maquina.py`, con tabla
de transiciones explícita y 64 tests—, un ensamblador de contexto que también es código, diez
roles con prompt y criterio propios, validadores con punto de ejecución declarado, y estado
en SQLite. **Ningún agente decide cuál es el siguiente paso.**

**Qué no da.** Un harness impecable pasea una escena equivocada por los diez estados
correctos sin inmutarse. Verifica el flujo, no el contenido.

---

## 2 · Orquestación como máquina de estados

**Qué es.** Modelar el trabajo como estados y transiciones explícitas en lugar de una función
que decide sobre la marcha, para que el estado sea consultable, persistible y reanudable.

**Aquí.** Diez estados por capítulo —seis vivos y cuatro terminales— y una máquina por
encima, la de la **novela**, que es la que se verificará con TLA+. El estado vive en SQLite y
nunca en memoria del proceso: una caída no pierde trabajo.

**Qué no da, y es un hallazgo del proyecto.** La reanudación **relanza el capítulo como
trabajo nuevo, no retoma el trabajo muerto**, porque el ciclo es una sola función que recorre
la máquina entera: volver a entrar con un trabajo que quedó en `VALIDANDO` no lo retoma, lo
empuja por transiciones que no son las suyas. Retomar de verdad exige partir el ciclo en
pasos direccionables, que es un refactor. La garantía que carga el peso sigue en pie: **un
paso interrumpido se repite entero, nunca se reanuda a medias**.

---

## 3 · Ingeniería de contexto: el paquete y sus capas

**Qué es.** Decidir, para cada llamada, qué información entra y cuál no — en vez de meter
todo lo que se tenga y confiar en la ventana.

**Aquí.** Ocho capas con **tope propio**: constitucional 5.000, estructural 10.000, canon
20.000, estado en T 15.000, continuidad local 20.000, memoria recuperada 10.000, instrucción
10.000 y reserva 10.000. Si una capa se pasa, se recorta **esa**; si tras recortar no cabe,
se lanza `ContextBudgetExceeded` **sin llamar al modelo**. El desglose por capa vuelve junto
al paquete y se persiste.

**Qué no da.** Que los números cuadren no dice que el paquete sea el **pertinente**. El fallo
de pertinencia del ensamblado es invisible en la traza y aparece después, como defecto de
continuidad. Está marcado **Descubierto** en `verification.md` §7.

---

## 4 · Presupuesto de tokens: dos techos que no son el mismo

**Qué es.** Un techo **por llamada** acota lo que cabe en un prompt. Un techo
**concurrente** acota la suma de lo que está en vuelo. Son restricciones distintas con el
mismo número.

**Aquí.** El primero lo aplica el Ensamblador al construir el paquete; el segundo lo aplica
el orquestador **antes de dar turno**, contando tokens y no llamadas. Si admitir una llamada
pasaría del techo, esa llamada **espera** — nunca se recorta el paquete para hacerla caber.

**Qué no da.** Ninguno de los dos acota el **coste total de una novela**: diez capítulos con
reintentos y regeneraciones suman lo que sumen. Es **U** en la clasificación y riesgo abierto
declarado.

---

## 5 · Memoria: ledger *append-only* y vistas derivadas

**Qué es.** Guardar los **hechos ocurridos** en un registro que solo crece, y calcular el
estado actual a partir de él, en vez de mantener una tabla de estado que alguien edita.

**Aquí.** El ledger `evento` es *append-only* —lo sostienen dos disparadores de SQLite, no una
convención—, y `estado_en_t` y `cronologia` son **vistas derivadas**. Corregir un hecho no lo
edita: se escribe uno nuevo que **cita al anterior** en `sustituye_a`.

**Qué no da.** Un ledger honesto no dice si lo que se registró era cierto. El grafo solo sabe
si algo **choca** con lo que ya contiene; un hecho nuevo que no contradice nada **no tiene
contra qué contrastarse**, y entra. Es uno de los seis riesgos descubiertos.

---

## 6 · Recuperación híbrida (RAG), y por qué el orden importa

**Qué es.** Traer del almacén lo que hace falta para esta llamada, combinando criterios: qué
es estructuralmente pertinente, qué se le parece y qué es reciente.

**Aquí, y **en este orden**:** filtro estructural —presentes, lugar, hilos abiertos, rango de
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

**Aquí.** Diez roles. El Escritor **solo ve el paquete** y nunca la base de datos; el
Continuista devuelve **códigos con cita**, nunca prosa corregida; el Crítico **no repara**.

**Qué no da.** Los validadores **no fallan de forma independiente**: comparten proveedor, la
redacción de las restricciones duras y —lo más fuerte y menos visible— **la misma entrada**.
Lo que faltó en el paquete le falta al Escritor y al Continuista a la vez. Regla de lectura:
**dos validadores correlacionados cuentan como uno**.

---

## 8 · Prompts versionados y restricciones duras

**Qué es.** Tratar el prompt como artefacto con versión, no como una cadena que se retoca.

**Aquí.** Viven en `features/<feature>/prompts/`, uno por rol, con nombre versionado
(`escritor.v3.md`), y **no se editan en sitio**: versión nueva y se cambia la referencia.
`ejecucion` guarda el **hash** del fichero, que es lo que hace reproducible la llamada sin un
segundo sistema de versionado. Las restricciones duras se repiten **al principio y al final**,
porque el centro del prompt es donde más información se pierde.

**Qué no da.** Ninguna regla de seguridad puede depender solo del prompt. Edad, nivel de
calor, consentimiento y vetos se validan **además** en código.

---

## 9 · Tools con esquema validado

**Qué es.** Dar al modelo funciones que puede invocar, con la entrada y la salida descritas
por un esquema que se comprueba.

**Aquí, y es una ausencia decidida.** **Ningún agente narrativo recibe herramientas.** Lo que
sí se valida con esquema es la **entrada y la salida de cada rol**: un agente que devuelve
algo fuera de su esquema es **un fallo, no una respuesta**. Y esa validación ya ha trabajado:
el modelo respondió una vez sobre el repositorio en vez de sobre la entrevista, y **lo rechazó
el esquema**.

**Qué no da.** Un JSON perfecto puede afirmar una barbaridad. El esquema verifica la forma;
del fondo no dice nada.

---

## 10 · Hooks

**Qué es.** Un punto de enganche declarado, fuera del código que vigila, donde se ejecutan
comprobaciones o políticas.

**Aquí.** Dos: **validación de capítulo** y **policy**. El motivo de que sean hooks y no
llamadas dentro del servicio es preciso: un guardarraíl que vive dentro del código que vigila
**se puede saltar cambiando ese código sin que nada lo note**; la ausencia de un hook **se
ve**.

**Estado.** Existen `HOOK_DE_CAPITULO` y `PUERTA_G4`. **El hook de policy no existe.**

---

## 11 · Guardarraíles

**Qué es.** Políticas aplicadas en código que restringen lo que el sistema puede producir,
con independencia de lo que el modelo quiera producir.

**Aquí.** Vetos en **tres ámbitos** —global, obra y brief— comparados sobre texto
**normalizado** —minúsculas, sin acentos, sin la `-s` del plural simple— y **por palabra, no
por subcadena**, para que «ana» no salte dentro de «mañana». Una coincidencia devuelve el
capítulo al escritor con el término concreto; agotado el límite, **la generación se detiene y
se informa**.

**Qué no da.** Caza la **palabra**, no la **alusión**. Y el plural en `-es` de las palabras
terminadas en consonante necesita un diccionario, no una regla: está escrito en el docstring
para que nadie lo descubra tarde.

---

## 12 · Inyección de prompt y contenido no confiable

**Qué es.** Que un texto que el sistema no controla acabe en la posición del prompt donde una
instrucción se obedece.

**Aquí la defensa es estructural, no retórica.** No se le pide al modelo que no haga caso
—eso es negociar con el atacante—: el texto entra **marcado como dato**, dentro de un
delimitador, y **nunca se concatena sin esa marca**. Además se le **quitan las etiquetas
hasta punto fijo**, porque una sola pasada de borrado puede **recomponer** la etiqueta que
acaba de quitar.

**Qué no da.** La marca dice de dónde viene el texto; **no juzga el texto**. Y el vector que
sigue sin cubrirse es el otro: una instrucción incrustada en la **prosa generada** que el
Extractor consolida como canon. El detalle está en [`red-team-log.md`](red-team-log.md).

---

## 13 · Idempotencia y checkpoint

**Qué es.** Que repetir un paso no duplique escrituras, y que un proceso que muere pueda
continuar desde donde llegó.

**Aquí.** La clave de idempotencia **no es el `run_id` solo: es `run_id` + paso + ordinal** —
con el `run_id` a secas, la primera reparación dirigida sería indistinguible de una
repetición y el reintento no llegaría a escribirse. Y **no hay tabla de checkpoint**: el
avance **se deriva** del propio `trabajo`, porque una tabla aparte sería un segundo relato de
lo ocurrido que puede divergir del primero justo tras una caída.

**Qué no da.** La exhaustividad sobre los estados la sostiene **quien escribe los tests**, no
un método. Por eso `spec_tla` cubrirá el mismo requisito por otra vía.

---

## 14 · Reintento dirigido, con tope

**Qué es.** Volver a pedir con **el defecto concreto** en el prompt, en vez de pedir «mejóralo».

**Aquí.** Máximo **dos** reparaciones por capítulo; después, escalado. El reintento lleva el
código del defecto y la **cita del pasaje**. Y el contador es **del capítulo, no del
trabajo**: contarlo por trabajo daría reintentos infinitos, porque bastaría un fallo del
proveedor para que las dos vueltas volvieran a estar disponibles. Avanzar de capítulo **no
consume reintentos**.

**Qué no da.** Cuenta reintentos, no **progreso**: no sabe si los intentos gastados sirvieron
de algo.

---

## 15 · Evals

**Qué es.** Probar el comportamiento del sistema contra un conjunto fijo de casos y un método
de puntuación, para poder decir si un cambio mejora o solo desplaza la salida.

**Aquí, y no existe todavía.** El encargo pide **cinco briefs** —uno adversarial y uno
construido para provocar una incoherencia temporal—, una **tabla** de qué validador pasó por
brief, y **una iteración de *tuning*** con resultados antes y después.

**Qué no da.** Cinco briefs son **cinco puntos**: cubren los modos de fallo que alguien
imaginó al escribirlos, y **el sexto brief —el que traerá un Comprador real— no está
representado**. Una tabla con cinco filas en verde mide la cobertura del conjunto, no la del
sistema.

---

## 16 · LLM-as-judge con rúbrica

**Qué es.** Un modelo puntúa la salida de otro contra criterios escritos, con **puntuación y
justificación por criterio**.

**Aquí.** La rúbrica es un artefacto con nombre y versión, con **anclajes descritos** —qué es
un 1 y qué un máximo—, y cubre continuidad, tono, calidad narrativa y **naturalidad de la
personalización**. Una puntuación sin justificación **no se acepta**.

**Qué no da, y por eso no bloquea.** Puntúa contra los criterios **enunciados**: la calidad que
nadie supo enunciar no se puntúa. Y la única forma de saber cuánto vale es medir su
**distancia** con una revisión humana que use la misma rúbrica — lo que mide la distancia
entre dos jueces, **no que alguno acierte**.

**Estado:** no existe. Fue una decisión (**P-B**): construir hoy un componente que por regla
propia no puede parar nada sería peor que declararlo pendiente.

---

## 17 · Observabilidad y trazas

**Qué es.** Instrumentar el sistema para que su trayectoria sea visible y consultable después,
agrupada por algo que signifique algo.

**Aquí.** Una **sesión por novela** —no por ejecución—, que abarca la entrevista, la
generación y **todas las regeneraciones posteriores**: si no, una regeneración aparece
desconectada de la novela que modifica. Cada rol, un span; cada validador, un *score*.

**El coste, declarado y no disimulado.** Suben el prompt renderizado y la traza, **y con ellos
el manuscrito**, porque cinco de los diez roles reciben la prosa **como entrada**: su prompt
renderizado **es** el capítulo. Los datos personales del Destinatario viajan a un servicio
externo. Es una decisión sobre datos de un tercero, está fechada y atribuida, y **fuera de
Langfuse no sale nada**.

**Estado:** Langfuse no está en el código. Lo que sí existe es el dato que alimentaría las
trazas: `ejecucion` guarda plantilla con su hash, versión de biblia, IDs recuperados por
capa, modelo, semilla, tokens **previstos y reales** y coste derivado.

---

## 18 · Verificación formal (Lean 4)

**Qué es.** Demostrar matemáticamente que algo cumple una propiedad **para todas las entradas
posibles**, no para las que alguien probó.

**Aquí, y sobre la historia, no sobre el código.** De la cronología en SQLite se genera un
fichero Lean con eventos, momento, presentes, lugar y fechas de nacimiento, y se demuestran al
menos dos invariantes. **Es una puerta:** si `lake build` falla, **la versión no se publica**.

**Por qué no lo cubre la puerta de escena:** una cronología imposible puede estar repartida en
tres capítulos, cada uno impecable por separado. Nadie miente; las fechas no encajan al
ponerlas juntas.

**Qué no da.** Demuestra las invariantes **escritas**: si la invariante es la equivocada, la
demostración es correcta y la historia está mal. Y demuestra sobre el **fichero generado**, no
sobre la prosa: lo que el capítulo dice y nunca llegó a la biblia, Lean no lo ve.

**Estado:** no existe.

---

## 19 · Comprobación de modelos (TLA+ / TLC)

**Qué es.** Explorar **exhaustivamente** los estados alcanzables de un sistema para
comprobar invariantes que los tests solo tocan por muestreo.

**Aquí, y sobre el harness, no sobre la historia.** Tres invariantes de seguridad y una de
*liveness*, sobre un modelo pequeño —cinco capítulos, dos reintentos— con su configuración en
el repositorio.

**Un detalle de modelado que ya está decidido y evita un contraejemplo tonto:** de
`VALIDANDO_CAPITULO` salen **dos** flechas hacia `ESCRIBIENDO_CAPITULO` y no son la misma
acción. `Reparar` rehace el mismo capítulo e **incrementa** el contador; `SiguienteCapitulo`
pasa al capítulo N+1 y **no lo toca**. Modelarlas como una sola tiene una consecuencia
concreta y absurda: avanzar de capítulo consumiría reintentos y **una novela de diez
capítulos se detendría sola** sin que hubiera fallado nada.

**Qué no da.** Verifica **la especificación, no el código**. Que TLC no encuentre
contraejemplo no dice que el orquestador implemente esa máquina: esa correspondencia es una
lectura humana, y es el eslabón más débil de la cadena.

**Estado:** no existe.

---

## 20 · Clasificación T / A / I / D / U

**Qué es.** Dar a cada requisito **una letra** según el método que lo establece: Test,
Análisis, Inspección, Demostración o **no verificable**.

**Aquí.** Existe para que los requisitos que nadie puede comprobar queden **visibles en vez de
darse por supuestos**. Un segundo método que refuerza se anota junto a la principal y **no la
sustituye**: un refuerzo no convierte en verificado lo que la letra principal deja pendiente.

**Lo que hoy es U, nombrado:** la calidad narrativa, la calibración del Crítico, la
pertinencia de la memoria recuperada, que un hecho nuevo deba entrar en el canon, el coste
total de una novela y **que el Destinatario se reconozca**. Nombrarlos es el sentido del
ejercicio: una U sin marcar es una afirmación que se hace sin pruebas.

---

## 21 · TDD y las puertas del proceso

**Qué es.** Escribir el test **y verlo fallar** antes del código; un test que nunca se vio
fallar no prueba nada.

**Aquí.** Rojo → verde → refactor, con el test **en el mismo commit** que el código, escrito
contra el criterio de aceptación y no contra la implementación que uno ya tiene en la cabeza.
Y cuatro puertas por encima: Spec, Plan, Código y Cierre, con las dos primeras abiertas por
**una persona en un commit suyo** — ningún agente aprueba.

**Un detalle que el proyecto aprendió pagándolo:** cuando un módulo no existe, `pytest` **no
imprime FAIL**, imprime `1 error during collection` y `collected 0 items`. El rojo hay que
tomarlo en dos tiempos —primero el `ImportError`, después con las firmas vacías— para verlo
**contado**. Un recuento que no cuadra con lo que imprime `pytest` es el que deja pasar un
test que nunca llegó a recogerse.

---

## 22 · Tests de mutación, hechos a mano

**Qué es.** Romper el código a propósito y comprobar que la suite lo detecta. Miden **la
suite**, no el código.

**Aquí.** La herramienta está **aplazada**, así que el proyecto lo hace a mano con la regla de
`CA-6`: se quita la validación y **el test que la cubre tiene que caer — su test y solo el
suyo**.

**Qué ha encontrado, que es lo que justifica el apartado.** **Nueve restricciones sobre las
que ningún test podía caer** y **ocho tests que pasaban por el motivo equivocado**. Y una
lección de método: **una mutación que no tumba nada es información, no permiso para seguir** —
a veces es defensa redundante y a veces es un agujero real, y hay que mirar cuál.

---

## 23 · Skills y subagentes

**Qué es.** Instrucciones empaquetadas y reutilizables para el agente de código, y agentes
auxiliares a los que se les reparte trabajo.

**Aquí.** Ocho skills en `.claude/skills/`, commiteadas, con su procedencia, commit exacto y
licencia en `SOURCES.md`. La regla del proyecto: **una skill no entra sin tres filas** —en
`SOURCES.md`, en la tabla de `CLAUDE.md` §13 y en `architecture.md` §7.2—; sin las tres **no
está instalada: está copiada**. Y **veinticinco subagentes** repartidos en tres fases, con la
regla de «un agente por fichero dentro de la ola».

**Qué no da, y es el hallazgo de proceso más repetido del proyecto.** El reparto por fichero
**corta las tareas justo por donde pasa el cable**: la juntura entre dos features no es de
ninguna de las dos tareas, y la acaba cerrando el integrador. Ha pasado en las cinco olas de
dos fases. La regla dice «un agente por fichero **dentro de la ola**» y **no dice qué pasa
cuando la juntura vive en fichero ajeno**.

---

## 24 · Inspección visual automatizada (browser MCP)

**Qué es.** Abrir el artefacto en un navegador real y comprobar sobre el renderizado lo que el
código fuente no dice.

**Aquí serían dos cosas distintas y conviene no fundirlas:** (a) el **validador visual** de la
puerta G4, que es **código conduciendo un navegador y no un agente**, y cuyo resultado
bloquea; y (b) el **agente de código**, que sí recibe la herramienta por `.claude/mcp.json`, y
cuyo resultado es una observación.

**Qué no da.** Comprueba que **algo** se ve, no que sea lo correcto: un índice con once
entradas para diez capítulos renderiza perfectamente.

**Estado:** ninguno de los dos existe. No hay lectura web que abrir ni `.claude/mcp.json`.
