# Registro de iteraciones — causa y efecto

**Qué es este documento.** Lo que el encargo pide con estas palabras: «qué cambió tras cada
eval o contraejemplo de TLC o Lean, y por qué. **No un diario, sino un log de decisiones con
causa y efecto.**»

**Al día a 2026-09-24**, con todo lo posterior a `63363e8` —cuando se escribió la primera
versión— comprobado contra `git show` y el código.

**Y lo primero que hay que decir es lo que falta, porque si no este documento engaña.**

> **No hay una sola fila originada en una eval.** No existe `evals/` y **no se ha generado
> ninguna novela de principio a fin** (la cuota de la cuenta se agotó; `storymaker.db` tiene
> cero capítulos). Las evals se reducen a dos o tres novelas por plazo, decisión declarada en
> `trade-offs.md`. **Sí hay ya filas de TLC y de Lean** (§H e §I), pero ninguna es un
> contraejemplo **real**: son los que se provocaron a propósito para ver fallar a los
> verificadores. Lo que sí hay en cantidad es lo que disparó **la primera corrida real
> contra el proveedor** (§J) y **la medición antes de arreglar** (§K).

**De dónde sale.** De las tablas de **Desviaciones** de los planes de `specs/001-backend-v1/`
y `specs/002-frontend/`, que se escriben **antes de seguir, no después** (`CLAUDE.md` §3.4),
y de los mensajes de commit, que llevan el rojo visto y el porqué. Allí está el detalle;
aquí está la extracción con la forma que el encargo pide: **qué lo destapó → qué cambió →
por qué**, con el commit que lo prueba.

**Qué se ha dejado fuera.** Las filas de coordinación pura —un *worktree* que arranca en el
commit equivocado, veinte veces— y las que solo anotan dónde vive un fichero. Están en los
planes. Aquí queda lo que **cambió una decisión, un requisito, un documento o una regla del
proceso**.

---

## Las causas, y cuántas veces disparó cada una

Las seis primeras (A–F) se contaron sobre los tres primeros planes del backend; las de H a L
entraron después de `63363e8` y se cuentan por filas de este documento.

| Causa | Qué es | Veces | Lo más caro que encontró |
| --- | --- | --- | --- |
| **A · Mutación deliberada** (`CA-6`) | Se quita la validación y se comprueba que cae **su** test y solo el suyo | ~20 | **Nueve restricciones sobre las que ningún test podía caer** y **ocho tests verdes por el motivo equivocado** |
| **B · Las puertas de la build** | `ruff`, `mypy`, `lint-imports`, Alembic, sobre código que la suite daba por bueno | 12 | Un renombrado a medias con la **suite entera en verde** |
| **C · Ejecutar contra el servidor de verdad** | Levantar la aplicación y llamarla, en vez de fiarse de la suite | 6 | Un endpoint que **respondía y no dejaba una fila en disco** |
| **D · Cruce contra el encargo y entre documentos** | Leer el texto del encargo al lado del nuestro | 9 | Un techo del encargo **que nadie contaba** |
| **E · Junturas del reparto** | Trabajo que vive entre dos tareas y no es de ninguna | 7 olas | Una regla del proceso que **no dice qué hacer** cuando la juntura está en fichero ajeno |
| **F · Un agente corrige una cita o un supuesto** | El subagente va a comprobar en vez de creerse el encargo | 5 | Una regla de dominio que, **al pie de la letra, prohibía guardar el nombre del Destinatario** |
| **H · TLC** | Correr el modelo de la máquina y romperlo a propósito | 6 | Que la terminación **no la sostiene la cota de reintentos**, como decía el plan, sino una hipótesis de equidad |
| **I · Lean** | Generar la cronología, compilarla y ver cerrar la puerta | 4 | Un invariante que el encargo sugiere y **el esquema no puede decidir** |
| **J · La primera corrida real** | Conectar con el proveedor y, después, lanzar desde la pantalla | 11 | Un Arquitecto que **no sabía para quién era la novela** |
| **K · Medir antes de arreglar** (plan 8) | Una sonda o un script contra el modelo real, o leer el código, antes de tocarlo | 5 | Que el nombre anonimizado **no lo produce ni el modelo ni el código**, sino la cuenta |
| **L · Revisión de una persona** | Lo que ningún test juzga (clase U): que la lectura apetezca | 3 | Una dirección visual implementada y **sustituida** tras verla |

---

## A · Lo que encontró romper el código a propósito

**La técnica.** `CA-6` dice que no basta con que el test pase: **si se desactiva la validación
y el test sigue verde, el test no comprobaba nada**. Es el sustituto a mano de los tests de
mutación, que están aplazados.

**La regla de lectura que salió de usarla:** *una mutación que no tumba nada es información,
no permiso para seguir.* A veces es defensa redundante y a veces es un agujero; hay que mirar
cuál.

| Qué lo destapó | Qué cambió | Por qué |
| --- | --- | --- |
| Mutar el censo de la capa de memoria **no tumbaba lo que debía** | El rango del filtro estructural pasa de «hasta el capítulo en curso» a `numero - 1`, y entra un test propio | Una escena **comparte lugar y presentes consigo misma**, así que era siempre candidata de su propio filtro: la rama «el filtro no deja nada» **no ocurría nunca** y el test estaba verde por otra cosa |
| Anular la detección de vetos tumbaba **ocho** tests, seis ajenos | Se separan las palancas de rechazo: extensión fuera de rango para el límite de reparaciones, nombre mal escrito para la inmutabilidad del texto | La palabra vetada era **la única forma de provocar un rechazo** en casi toda la suite, así que esos tests no distinguían «el límite funciona» de «la detección funciona» |
| Mutar `defectos_bloqueantes` a vacío **no tumbaba nada** | Se dejan las dos defensas y entra el test que **sí** discrimina: que los códigos que el ciclo entrega a `canon` son los que emitió la puerta | No era rama muerta: hay **dos paredes** para «un capítulo rechazado no deja rastro», y quitar una no se nota porque la otra sigue |
| Quitar `variantes` del conjunto aceptado **no cambiaba** el resultado de `CA-16` | Entra un caso con **misma forma normalizada y otra grafía** —«Ivan» por «Iván»—, que es el único en que `variantes` decide | «Mari» y «María» **no comparten forma normalizada**, así que el validador nunca las comparaba: la declaración del canon **no hacía ningún trabajo** y el test la tapaba |
| Neutralizar la exclusión del diálogo **no tumbaba** su test | Se alarga la línea de diálogo hasta que sus marcas superan a las de la narración | La comparación es por **dominancia**: una línea corta no cambia quién domina, así que el test comprobaba la aritmética, no la exclusión |
| Quitar el `obra_id` del filtro de `siguiente_capitulo` dejaba **la suite entera en verde** | Entra `test_el_siguiente_capitulo_no_es_el_de_otra_obra` | **Ninguna otra obra de la suite tenía outline**, así que el caso de dos obras planificadas a la vez no estaba cubierto: el orquestador de una obra podía recibir el capítulo 1 de otra |
| Borrar `registrar_checkpoint` del bucle **no rompía nada** | Se encadena su valor de vuelta: sin la llamada ya no hay checkpoint que devolver | El avance **se deriva** de `trabajo`, así que releerlo al final daba el mismo número aunque nadie hubiera anotado: una línea que el requisito exige y **ningún test sostenía** |
| Devolver el `capitulo_id` en lugar del `numero_de_capitulo` **no tumbaba nada** | Los tests se rehacen sobre una **segunda** obra | En una base recién creada los `id` son 1..10 **y los `numero` también**. `GET /trabajos/{id}` habría dicho «capítulo 47» de una novela de diez sin que fallara nada |
| Cuatro mutaciones vivas en la reanudación | Dos tests nuevos y **dos cambios de diseño**: una sola puerta, movida delante de la primera escritura | `reanudar` comprobaba dos veces lo mismo y descartaba los trabajos vivos **antes** de pasar por la puerta. Las dos cosas estaban **razonadas en el docstring y las dos razones eran falsas** |
| `hecho.usado_en and` no tumbaba nada al quitarlo | **Se retira**, en vez de dejarlo de adorno | Era código muerto: el bucle de dentro ya no recorre nada sobre una tupla vacía. **Una condición que no puede fallar hace creer que algo está protegido por ella** |
| Quitar `sustituye_a` del escritor de canon no rompía nada | Entran dos tests de **comportamiento**, uno con una cadena de tres correcciones | Había test de la **columna** y ninguno del comportamiento |
| Quitar la comprobación de dimensión no rompía su test | El test pasa a exigir el mensaje con `match` | **NumPy lanza igual** su propio error al multiplicar: lo que la guarda aporta no es el fallo, es **decir qué dimensiones eran** |
| Una mutación **reventó** el SQL en vez de fallar | Se rehace la mutación quitando la cláusula entera | **Una mutación que revienta no prueba que el test discrimine**: los tests caían por el error, no por el fallo que debían detectar |
| Un caso parametrizado seguía verde al quitar su guarda | Se cambia el dato del caso: «los unos y los otros» por «y el de la» | «otros» normaliza a «otro», que **tiene contenido**: el caso no probaba lo que su nombre decía |

**El recuento, que es el valor de esta sección:** **nueve** restricciones sobre las que ningún
test podía caer, y **ocho** tests que pasaban por el motivo equivocado. Los dos últimos los
encontró la mutación, **no la lectura**.

**Después de `63363e8` la técnica pasó a ser rutina de cada commit**, y sigue encontrando:

| Qué lo destapó | Qué cambió | Por qué | Commit |
| --- | --- | --- | --- |
| Desconectar el hook de policy —`recibidos = []`— | Se deja como evidencia de que el hook existe: caen **tres** tests de `escritura` | `CLAUDE.md` §11 pide que la ausencia de un hook **se vea**. Dicho no bastaba; visto, sí | `168461a` |
| Un test que leía la columna nueva con `select(Obra)` **pasaba sin la columna** | Pasa a leer por SQL crudo | El mapa de identidad devolvía el objeto recién tocado en memoria. Se pilló porque los otros dos fallaban y ese no, **y la asimetría no cuadraba** | `edb8edc` |
| El `CheckConstraint` de `elementos_obligatorios` tumbó **27 tests en ocho ficheros** | Se rehacen los 27 | Ninguno estaba mal: todos daban por buena la premisa que P-2 quita —una obra sin nada que cubrir— | `eae8893`, `0d25b26` |
| Quitar una a una trece piezas del cableado de Langfuse | Cada una tumba un test; con el observador sin blindar cae el de R-1 | Sin esa ablación, «el ciclo emite sus *scores*» habría sido una afirmación sobre el cableado, no sobre lo que llega al span | `ca347dc` |
| Conectar al Continuista y al Crítico: dos tests caen con `RespuestaNoPreparada` | Se le da respuesta al doble | **Un test que empieza a fallar cuando conectas algo es la prueba de que antes no estaba conectado** | `bab4dd7`, `4f35669` |

---

## B · Lo que encontraron las puertas y la suite no

| Qué lo destapó | Qué cambió | Por qué |
| --- | --- | --- |
| `ruff` (F821) y `mypy` tras un renombrado, **con la suite en verde** | Se añaden los `import` que faltaban | Python 3.14 evalúa las anotaciones de forma **diferida**: un nombre sin importar en una firma **no revienta en ejecución**. Es el argumento de «las puertas antes que el dominio», cobrado con intereses |
| `ruff format` reescribía documentación y skills vendorizadas | `extend-exclude` con los tres árboles de prosa | `ruff` formatea los bloques de código dentro de Markdown: reescribía skills clavadas a un commit *upstream* y **código equivocado a propósito** dentro de `specs/` |
| `mypy` estricto exigía `-> None` a los tests | `files = ["src/backend/app"]` con `exclude` de tests | `files` **no expande comodines**: la frontera hay que trazarla con `exclude`, que sí es una expresión regular. Un test es una aserción, no una interfaz |
| `lint-imports` no arrancaba, por dos motivos | Entra `build-system` (hatchling) e `include_external_packages=True` | El proyecto era virtual y `app` no era importable; `pytest` lo salvaba con su `pythonpath` e `import-linter` no tiene equivalente. **Los dos contratos eran correctos: faltaba la línea que los hace correr** |
| `--autogenerate` de Alembic emitió una migración **vacía** | `import app.features.obra.modelos` en `env.py` | Solo ve lo que esté en `Base.metadata`. **Y lo que se evitó no fue solo la migración que faltaba:** el siguiente `--autogenerate` habría visto esas cuatro tablas como sobrantes y habría generado su `drop_table` |
| `--autogenerate` **no emite `CheckConstraint`** sobre tablas que ya existen | Se escriben a mano, con su `downgrade`, **y con un test sobre la base migrada** | Sin eso, `create_all` tenía las restricciones y **la base de la instalación no**, y nada lo habría dicho. Ocurrió tres veces en tres fases |
| El andamiaje de `alembic init` no pasaba las puertas del repositorio | Se moderniza la plantilla y se añaden `post_write_hooks` con `ruff` | Para que **toda** migración nazca pasando las puertas, no solo la primera: si no, un agente se encuentra `ruff` en rojo por un fichero que no escribió |
| El primer test async fallaba por `greenlet` en Apple Silicon | `sqlalchemy[asyncio]>=2.0` | SQLAlchemy declara `greenlet` bajo un marcador que enumera `aarch64`, `amd64`, `x86_64`… **y no `arm64`** |
| Una columna `NOT NULL` sobre una tabla con filas | `server_default='{}'`, con test sobre la base migrada | En modo *batch* SQLite **recrea** la tabla, y las filas viejas entrarían con `NULL` |

---

## C · Lo que solo se ve ejecutando contra el servidor

**El patrón, repetido en las tres fases:** *lo que no se ejecuta contra el servidor no está
comprobado.* Una afirmación que solo es cierta dentro de la suite es una afirmación falsa con
un test verde delante.

| Qué lo destapó | Qué cambió | Por qué |
| --- | --- | --- |
| Llamar a `POST /obras/{id}/outline` contra la aplicación levantada | Entra el `commit` que faltaba, **y un test que abre otra sesión** sobre el mismo motor | Los tests comparten la sesión del cliente, así que **lo escrito y sin confirmar se lee igual de bien que lo confirmado**. El servicio era el único con endpoint que no confirmaba |
| Llamar a los tres endpoints de la entrevista | Se declara el hueco: la única implementación de `ClienteModelo` al cerrar la fase era el doble, y los endpoints **responden 500** | Ninguna tarea tenía asignado el cliente real. **Se descartó traducirlo a un 501 amable:** una respuesta ordenada lo habría hecho más fácil de no ver |
| Un `curl` que respondió 200 con `"paths": {}` | Se repite en otro puerto | El puerto seguía ocupado por un `uvicorn` de otra ola **sirviendo la aplicación sin rutas**, y el nuevo había muerto con «address already in use» en su propio log, que nadie mira |
| Un test que **pasaba en verde con los tres endpoints sin escribir** | Se le añade la comprobación del cuerpo | Miraba solo el código de estado, y sin ruta registrada **FastAPI ya devuelve 404 por su cuenta** |
| Un test que nació en verde antes de existir su módulo | Se anota que el ciclo rojo→verde lo demuestran los otros | Es un guardaespaldas de regresión legítimo, **pero un recuento que lo incluya como prueba del ciclo cuenta de más** |
| Verificar en vivo un endpoint que **llama al proveedor** | Se anota como error del integrador | Gastó cuota haciendo lo que se les había prohibido a doce agentes. **La comprobación en vivo contra un endpoint que llama al modelo no es gratis** |

---

## D · Lo que cambió al leer el encargo al lado del nuestro

**Es la causa que más caro habría salido no disparar**, porque afecta a requisitos firmados.

| Qué lo destapó | Qué cambió | Por qué |
| --- | --- | --- |
| Leer «100.000 tokens **concurrentes**» del encargo §7 | Entra un **segundo techo** y el requisito que lo comprueba contando **tokens, no llamadas** | Habíamos cambiado su palabra por la nuestra y razonado sobre la nuestra. Con la concurrencia en 1 los dos números coincidían: **se cumplía por consecuencia, no por regla**, y subirla a dos habría incumplido el encargo **sin que fallara ningún test** |
| Escribir el plan de la Fase 1 y preguntarse dónde vive una entrevista anterior a su obra | **P-07:** se retira «un fichero por obra» y la spec **vuelve a firma** | El encargo solo obliga a SQLite; «un fichero por obra» era glosa nuestra, y contradecía `serie` y `comprador`, que cruzan obras. **No es aditivo: retira algo firmado** |
| Leer §5b: «revisión humana… **con la misma rúbrica**» | **P-05:** el Comprador **acepta**; el Autor **calibra** | De un sí o un no no sale ninguna comparación por criterio: con el Comprador como único revisor, **el encargo quedaba incumplido** |
| Cruzar `verification.md` contra el encargo | **Dos veredictos se invierten:** verificación formal y comprobación de modelos pasan de «No aplicable» a **obligatorias** | El argumento anterior era bueno **para otra pregunta**: hablaba de demostrar sobre el **código**. El encargo pregunta sobre la **historia** y sobre el **harness** |
| Releer la condición de caducidad de la comprobación de modelos | Se escribe que **caducó por donde no se esperaba** | La condición escrita era «si aparece concurrencia real». No apareció concurrencia: aparecieron publicación, checkpoint y regeneración. **La condición que se escribe es la que uno imagina** |
| Releer «hasta que exista la calibración» en G1b | La condición pasa a exigir **correlación medida y firmada** | La redacción anterior **se habría disparado sola** en cuanto llegara la revisión humana obligatoria, y G1b habría pasado a bloquear sin que nadie lo decidiera |
| `architecture.md` §3.7 contra §3.3 | Gana §3.3: la reanudación **relanza, no retoma** | Las dos frases no podían ser ciertas a la vez, y solo una era implementable con el ciclo que hay |
| `architecture.md` §3.10 contra el primer contrato de `import-linter` | El motor de la máquina **baja** de `commons/jobs/` a `features/escritura/` | La máquina persiste en `trabajo`, que es de la feature, y `commons/` no puede importar de una feature. **Aquí gana el código y el documento se corrige** |
| Comprobar qué hace de verdad el vectorizador | La búsqueda **deja de llamarse «semántica»** en dos documentos | Es una señal léxica: dos fragmentos que dicen lo mismo con otras palabras no se reconocen. **Se corrige la palabra, no el código**, porque meter un proveedor de *embeddings* contradiría una decisión firmada |

**Y una que volvió a firma, y se reabrió:** la Fase 3 añadió `POST /obras/{obra_id}/novela`
sin fila en la spec. Se firmó como `RI-15` en la v3.3, con `CA-33` a **dieciséis** endpoints
(`b39771c`), sabiendo que seguía sin cumplirse. Desde entonces han entrado
`GET /obras/{id}/novela` y `GET /trabajos/{id}/intentos`, que la spec no nombra, y siguen
faltando otros que sí nombra: **P-3 está reabierto** y es cambio de requisito con firma.

---

## E · Lo que cambió la forma de repartir el trabajo

| Qué lo destapó | Qué cambió | Por qué |
| --- | --- | --- |
| Tres conflictos al integrar la ola 2 de la Fase 1, señalados por tres de los cuatro agentes | **Se mantiene** la tabla de Desviaciones compartida y la resuelve el integrador | Partirla en un fichero por tarea **rompe el registro en trozos que nadie lee juntos**, y el conflicto es barato y siempre del mismo tipo: filas que se concatenan |
| Resolver un conflicto concatenando los dos lados **rompió el código** | La heurística pasa a valer **por tipo de fichero, no por conflicto** | Conservar ambos lados es correcto para una tabla de filas y **equivocado para Python**: produjo un `__init__.py` con prosa dentro y `SyntaxError` |
| Cinco olas en las que la juntura entre dos features no era de nadie | Regla nueva para los planes que quedan: **o las junturas tienen dueño explícito desde el plan, o se declara que las cierra el integrador** | La regla decía «un agente por fichero **dentro de la ola**» y **no decía qué pasa cuando la juntura vive en fichero ajeno**. Lo que no vale es descubrirlo al integrar |
| El `__init__.py` de una feature sin dueño, que tres agentes dejaron sin tocar **a propósito** | Se exporta al integrar, y **entra en la tabla de dueños** para la fase siguiente | Los tres hicieron lo correcto: tres agentes tocando el mismo fichero en la misma ola es el conflicto que la regla existe para impedir |
| Un criterio de aceptación asignado a una tarea que **no podía cerrarlo** | Se reasigna, y se cierra en la fase siguiente | Le faltaban una consulta y un sitio donde persistir, y **dos de las tres cosas estaban fuera de su alcance de ficheros** |
| El mismo aviso propagado a dos agentes **era falso** | Se comprueba en el intérprete y se sustituye por un test | «Añadir un miembro a un `Protocol` lo vuelve abstracto y revienta la suite» **no es cierto**: la subclase hereda el cuerpo vacío y **devuelve `None` en silencio**. El peligro era peor que el que estaba escrito |

---

## F · Cuando un agente fue a comprobar en vez de creerse el encargo

**Son cinco, y son la mejor señal de que el proceso funciona:** la instrucción que recibió el
subagente estaba mal y el subagente lo dijo.

| Qué pasó | Qué cambió |
| --- | --- |
| Se le pasó la **regla de dominio 4 en su forma antigua** —«todo hecho de canon cita la escena que lo estableció»— | El agente fue al repositorio, encontró la forma vigente —los de `origen: brief` **no la tienen y no deben inventarla**— y la implementó en las dos mitades. Su frase: *«si hubiera seguido el encargo al pie de la letra, habría prohibido guardar el nombre del Destinatario»* |
| Se citó `definitions.md` **§7** para los parámetros de discurso | El agente corrigió que están en **§5**, y tenía razón. Se corrige la cita |
| El plan anunciaba «**12 FAIL**» para un módulo que no existía | El agente demostró que `pytest` imprime `1 error during collection` y **cero FAIL**, y tomó el rojo en dos tiempos para verlo **contado** |
| El plan daba por probada R-3 «por los dos lados» | El agente señaló que **el escenario que de verdad rompe un contador global es el capítulo sano que costó dos vueltas y se integró**, y escribió ese test. Y añadió un tercer lado que el plan no nombraba: el relanzamiento de un `FALLIDA` |
| El plan pedía meter `FALLIDA` en el conjunto que detiene la novela | El agente lo resolvió mejor: `FALLIDA` es **relanzable** por documento, así que la regla correcta es exigir que **no quede ningún capítulo anterior sin integrar** — que no mira la causa y **se desbloquea sola** |

---

## G · Supuestos sobre herramientas que resultaron falsos

| Supuesto | Realidad | Qué cambió |
| --- | --- | --- |
| «El SDK habla con el proveedor» | **Lanza el binario `claude`**. Se creyó que había que instalarlo aparte; `claude_agent_sdk` **trae el suyo** | P-15 se reformula: lo que falta no es el binario, es comprobar al arrancar que **la cuenta está autenticada** (`6d930f4`) |
| «`setting_sources=None` es ninguna fuente» | **Es todas**: el CLI cargaba el `CLAUDE.md` del repositorio en el prompt del Entrevistador | `setting_sources=[]`, y P-1 se cierra (`bf0edc8`). Ver `red-team-log.md` §3 |
| «Playwright ya está en el proyecto» | Solo figuraba en `.claude/mcp.json`, que el backend no puede importar | El PDF se firma con `playwright` como dependencia **declarada** (`24a915f`) |
| «`lint-imports` y `test_fronteras.py` miran lo mismo» | Uno daba verde y el otro cazaba un import diferido de `escritura` a `escena` | Se arregla la frontera, y queda abierto **cuál de los dos calla** (`8950062`) |
| «`TARIFAS` por constante de rol vale» | Al unificar los roles en Haiku, dos claves iguales dejaban **una sola entrada**: toda llamada se habría imputado a la tarifa de Opus | Se indexa por el nombre literal del modelo (`b80e911`) |
| «El contador local es local» | `tiktoken` **descarga su vocabulario** la primera vez | Declarado: el contador de producción en una máquina sin red y sin caché falla al primer `contar()` |
| «La semilla hace reproducible la llamada» | El proveedor **no la admite** | Se registra por requisito y **no se promete reproducibilidad de la prosa**: lo reproducible es el paquete |
| «Aprobada es instalada» | NumPy estaba aprobada en bloque y **no en `pyproject.toml`** | Se instala, y queda el aviso: en las fases siguientes esa distancia se llama **Langfuse, Lean y Playwright** |
| «Los topes por capa no agotan el techo» | Los ocho suman **exactamente 100.000** | No se escribe la comprobación redundante —sería una rama que ningún test puede poner en rojo— y entra **un test de la identidad aritmética** |
| «El `.env` que da el panel de Langfuse usa `LANGFUSE_HOST`» | Usa `LANGFUSE_BASE_URL`, y con él el observador caía en `ObservadorNulo` **sin un error** | `HOST` se rellena con `BASE_URL` si falta (`3ad1d85`) |

---

## H · Lo que dijo TLC

`formal/tla/Harness.tla` existe desde la Fase 7. **Ninguna de estas filas es un contraejemplo
de la máquina real**: son lo que TLC dijo mientras se escribía el modelo y al romperlo a
propósito. Lo que enseñaron fue sobre todo **sobre el plan**.

| Qué lo destapó | Qué cambió | Por qué | Commit |
| --- | --- | --- | --- |
| TLC: `Deadlock reached`, 404 estados, con cinco capítulos validados en `VALIDANDO_CAPITULO` | Se corre con `-deadlock` **y se anota antes de seguir** que la bandera se retira cuando la máquina esté entera | T1 entrega media máquina y **una media máquina hace deadlock por construcción**: la acción que continúa era de T2. Sin la nota, quien cogiera T2 habría dado por bueno un verde que no lo era | `4f0e728` |
| TLC: deadlock en `PUBLICADA` con cero peticiones | **No se aplica** el arreglo que el plan prescribía —aflojar la guarda de `Fin`— | Habría metido en la especificación **un permiso que la máquina terminada no debe tener**: quedarse quieta con una petición de cambio sin atender. La bandera se retira en T3, y ahí la máquina cierra sin ella | `bd58307`, `c5585a1` |
| Escribir la *liveness* que pide el encargo §5d | Entra `CONFIGURANDO → DETENIDA` al agotarse las rondas, **en el documento y no como hipótesis del modelo** | El bucle de la entrevista no tenía cota. Acotarlo solo en el `.tla` habría hecho que TLC demostrara la propiedad sobre un modelo distinto de producción **justo donde podía fallar**. Queda declarado que no tiene requisito ni código | `248e8a4`, `1c2d7d9` |
| Las cuatro ablaciones de T4 | S1 se declara **redundante, no vacía**; la terminación pasa de «T» a **condicional** | Integrar y validar son el mismo evento en el modelo, así que la guarda de S1 no puede cambiar nada. Y el plan decía que reiniciar el contador rompe la terminación: **no la rompe**; la sostiene `SF_vars(Aprobar)`, y con `WF_vars` TLC da *«Temporal properties were violated»* | `c5585a1`, `3957573` |
| Añadir `PROCESO_INTERRUMPIDO` al código y ver el test de correspondencia **seguir en verde** | `transiciones_reales()` llama a `transitar` sobre todo el alfabeto en vez de leer `_TRANSICIONES` | **20 de 31 transiciones** no pasaban por la tabla que el test comparaba. Una nota en el `.toml` lo decía en prosa, y **una nota no es una comprobación** | `e76ab85` |
| La correspondencia daba 7/7 con la puerta de Lean ya aterrizada | Si el módulo previsto existe y la función no, rojo | La fila apuntaba a un nombre **inventado al declararla**, que no iba a existir nunca: dejó de vigilar en el momento en que se escribió | `1e3b295` |

---

## I · Lo que dijo Lean

`manuscrito/lean/` genera el fichero desde la vista `cronologia` y lo compila en cada
publicación. **Ningún fallo real todavía**: no hay novela con la que fallar.

| Qué lo destapó | Qué cambió | Por qué | Commit |
| --- | --- | --- | --- |
| Escribir el generador | El invariante de orden temporal que el encargo §5c sugiere **no se escribe**, y el aviso va **en la cabecera del fichero generado**, con un test que lo exige | `evento.tiempo_historia` es texto libre y no hay en el esquema ninguna magnitud ordenable de tiempo de historia. Un invariante sobre el índice emitido comprobaría que **el discurso avanza**, que es cierto por construcción: verde sin probar nada. Necesita cambio de esquema, y eso lo decide una persona | `b6b1463` |
| Quitar la llamada a Lean de `publicar` | Caen cuatro de los cinco tests de la puerta; restaurada, pasan | `CA-21` pide que Lean **impida publicar**, no que avise. Y `sinReaparecidos` usa `<` y no `≤`, con su test: **quien muere está en la escena de su muerte** | `4c6ff5c` |
| Seis tests de Lean **se saltaban** en una máquina con Lean instalado | La puerta mira el PATH y, si no, `~/.elan/bin`; el `skipif` pregunta **lo mismo que la puerta** | `shutil.which("lean")` daba `None`: la suite decía verde y, en producción, **toda publicación se habría bloqueado** por «falta Lean» | `4c6ff5c` |
| Cruzar la plantilla Lean contra el brief B3 de las evals | P-27 abierto, para decisión de una persona antes de las evals | La plantilla no lleva fechas de nacimiento —con razón: solo el destinatario tiene fecha y no es un `Personaje`—, pero **B3 estaba diseñado para que lo cazara ese invariante**. Tal como está, B3 no fallaría donde el plan dice | `6d930f4` |

---

## J · Lo que destapó la primera corrida real

**El patrón, en una frase:** los once estaban **entre piezas**, y los once eran invisibles con
dobles, porque un doble devuelve lo que el test le pone. Las cuatro primeras son de conectar
el backend con el proveedor; el resto, de lanzar la novela **desde la pantalla**.

| Qué lo destapó | Qué cambió | Por qué | Commit |
| --- | --- | --- | --- |
| La entrevista murió con `SalidaMalFormada` sobre un JSON impecable **dentro de una valla de markdown** | `commons/llm/json_de_modelo.py` para los cinco agentes, que crece dos veces en la misma corrida —valla sin cerrar, resumen debajo de la valla— | «Devuelve solo JSON» en el prompt baja la frecuencia, no la lleva a cero, y §10 dice que ninguna regla depende de que el modelo obedezca | `26efa68` |
| Sobre el brief de ejemplo, el Entrevistador devolvía `faltantes: ["extension"]` | `entrevistador.v2.md`, con tres tests de correspondencia prompt ↔ esquema en las dos direcciones | La v1 pedía un campo que `BriefEntrada` no tiene, y el modelo obedecía: **la obra no se podía crear** | `26efa68` |
| El Arquitecto tituló «Novela para `[DESTINATARIO_PERSONALIZADO]`» con personajes inventados | `como_brief()` pasa destinatario, rasgos, recuerdos y elementos obligatorios, con `LEFT JOIN` | Le llegaban cuatro campos. **La regla de dominio 11 era incumplible por construcción**: lo que no llega al Arquitecto no puede estar en el outline | `26efa68` |
| Cada fallo de esquema era un diagnóstico a ciegas | `SalidaMalFormada` guarda el motivo además del crudo | Los dos diagnósticos de la primera fila salieron de haber hecho esto | `26efa68` |
| El formulario enviaba seis cadenas planas | Los campos, las claves y los tipos que `BriefEntrada` exige; solo viajan las claves con algo dentro | `respuestas` es un diccionario abierto a propósito, así que **nada fallaba**: `recuerdos` en vez de `recuerdos_aportados` se ignoraba en silencio | `e275c8e` |
| Cuatro de seis `POST /respuestas` en `500`: `database is locked` | RI-02 confirma lo guardado **antes** de llamar al modelo; la pantalla desactiva el botón mientras espera | La transacción de escritura quedaba abierta durante toda la llamada, y el segundo clic —que llega porque el primero tarda— moría en el `busy_timeout` | `596faba`, `a045100` |
| La pantalla publicaba en cuanto `/novela` respondía `202`, **sin haber llamado al Arquitecto** | `GET /obras/{id}/novela` dice por dónde va, y la cadena es cerrar → outline → novela → consultar → publicar solo con `terminada` | Sin outline hay cero capítulos y `/novela` responde `202` sin escribir nada. Y un test viejo seguía verde **porque el 404 venía del outline y no de la novela** | `d887bb0`, `38a260d` |
| Publicar una obra con cero capítulos salía bien con Lean instalado | `ObraSinCapitulos`, **antes** de Lean | `_capitulos_listos` buscaba un capítulo sin puerta y con cero no encontraba ninguno; Lean con cero eventos no objeta. Salía **una versión publicada en blanco con su enlace repartible** | `b0871ac` |
| El cliente generado no conocía `/publicar` | `openapi.json` regenerado desde la app | El contrato del frontend iba por detrás del backend. Volvió a pasar con `TipoDeCorte` (`7e44901`), y por eso **P-23** pide un test que compare el fichero con la app | `ee5a265` |
| El outline rechazado **en los diez capítulos**: `tipo_de_corte_final: string_too_long` | `TipoDeCorte` con tres literales, `arquitecto.v2.md` y **una** reparación dirigida con la lista de fallos | `definitions.md` §4.1 ya decía que el corte es uno de tres; ni el prompt ni el esquema lo cerraban, y el modelo lo describía con una frase | `0513035` |
| Cada carga de página abría dos entrevistas | Sin reintentos ni recargas en esa consulta | Es un `POST` montado sobre `useQuery`: con la base ocupada, reintentar a ciegas un `POST` que quizá ya guardó **crea otra fila** | `a935a27` |

---

## K · Medir antes de arreglar (plan 8)

El plan 8 (`4e0ce06`) se escribió para que la primera novela real sirviera. **Su primera
decisión fue sondear antes de construir**, y eso cambió dos de sus tareas.

| Qué lo destapó | Qué cambió | Por qué | Commit |
| --- | --- | --- | --- |
| `sonda_nombre.py`: una llamada real al Arquitecto con el brief de ejemplo. El nombre real, **0 apariciones**; un nombre inventado, **0 apariciones y 13 marcas `ANONIMIZADO`** | **T2 y T3 —el marcador del destinatario— no se ejecutan.** La novela se genera con una cuenta sin esas instrucciones, repitiendo antes la sonda | Anonimiza **cualquier** nombre de persona: son instrucciones de la organización de la **cuenta de trabajo**, no el modelo ni el código. El marcador acordado no lo habría esquivado | `38924c3` |
| `medir_sobrecarga.py`: seis llamadas reales | `SOBRECARGA_POR_LLAMADA = 2_000`; los 33.000–49.000 de `RELEVO.md` **no se reproducen** | Se midieron ~1.200 tokens fijos por llamada, con y sin caché. Con esa cifra **el techo concurrente no es la restricción real**, y `CLAUDE.md` §4.1 no cambia. Y se anota que la medida se hizo con la cuenta de trabajo y **hay que repetirla** con la de la corrida | `092e319`, `5a6baa3` |
| La escalada del capítulo 1: tres intentos rechazados **sin un solo código de defecto** | Tabla `intento_descartado`, `GET /trabajos/{id}/intentos`, el juicio del Crítico se conserva al escalar, `causa_fallo` a 200 | Con los datos de entonces no se distinguía «el modelo escribió mal tres veces» de «un validador rechaza siempre». **La revisión humana era un estado al que se llegaba y del que no se salía** | `d3b0d88`, `7e44901`, `cda23f1`, `c8ecb22` |
| ~8 minutos por capítulo, con Continuista y Crítico en serie | El Crítico arranca a la vez **si su turno cabe** en el techo sumado; si no, en serie | No decide nada, así que solaparlo es gratis. Nadie espera turno reteniendo el suyo (`espera_maxima=0`), y un Crítico que devuelve basura **ya no tumba el intento**, ni en paralelo ni en serie | `92d2da7` |
| Leer `commons/observabilidad/` (P-22) | El criterio del juez en el nombre del *score*; un observador por proceso con `flush` al apagar; plantilla, versión y hash en cada span de rol | Los seis criterios llegaban con el mismo nombre —justo lo que `RF-JUZ-05` compara—, lo último de una corrida se perdía, y sin versión de plantilla **el *tuning* no tiene «antes» con el que comparar** | `057eea4`, `dced524`, `bfb5396` |

**Un defecto conocido, sin arreglar todavía:** el Escritor, el Continuista y el Crítico
comparten cliente, y `_completar_ejecucion` lee `escritor.cliente.ultimo_consumo` **después**
de que hayan corrido los dos jueces (`escritura/service.py`, al cerrar el intento). La fila de
`ejecucion` del Escritor guarda el consumo de la última llamada de juez, no el suyo. Se dice
aquí porque afecta a la cifra que el *tuning* compara.

---

## K bis · Lo que dijo la primera corrida de evals (2026-09-24, noche)

| Causa | Cambio | Por qué | Commit |
| --- | --- | --- | --- |
| **Eval B3**: el capítulo 1 escaló con 812, 141 y 621 palabras (`EST-02`); el segundo intento ni siquiera era prosa, comentaba la reparación | `escritor.v2` con la extensión como restricción dura, y la reparación de `EST-02` dice cuántas palabras faltan en vez de citar el capítulo entero | El prompt v1 no pedía extensión y la reparación ordenaba «dejar intacto todo lo demás». **Iteración de tuning con antes y después:** `evals/tuning.md` — con v2, 5 de 5 capítulos aprobados (4 con una reparación) | `35cca58` |
| Evals B1 y B5: el Arquitecto olvidó un beat obligatorio (`revelacion_interior`, `gran_gesto`) → 409 sin segunda oportunidad | Un reintento dirigido también para las reglas de planificación (beats, giros, numeración, discurso) | El reintento solo cubría salidas mal formadas | `609a781` |
| Tres outlines en 500: `database is locked` con cinco obras a la vez | El ciclo confirma antes de cada llamada al modelo; Planificador y Arquitecto cierran la lectura antes de esperar; `busy_timeout` 30 s; la novela se reanuda sola ante un cerrojo | SQLite es de un escritor: el ciclo retenía la escritura el capítulo entero, y en WAL una lectura vieja que escribe falla al instante | `324e801`, `d09ddfa`, `350911d` |
| Langfuse sin trazas en producción | Adaptador al SDK v4 (`start_as_current_observation`, `propagate_attributes`) | Se escribió contra la v3 y solo se probó con un doble: el blindaje se tragaba el `AttributeError` | `e7beabc` |
| Langfuse con coste 0 | Tokens y coste en una **generación** hija de cada rol | El panel ignora coste y tokens sobre un span | `74e6bfb` |
| El Extractor tumbaba la novela con el capítulo ya aprobado | Reintento dirigido del Extractor | Una salida mal formada no tenía segunda oportunidad | `78e2246` |
| Eval B4: el Entrevistador **detectó** que vetar «hospital» choca con el elemento obligatorio «la cafetería de Valdecilla» | Ninguno: **es el resultado esperado** | Contradicción de brief cazada antes de escribir (§1 del encargo) | — |

---

## L · Lo que decidió una persona al verlo

**La apariencia es U**: ningún test juzga que una lectura apetezca. Aquí la causa es la
revisión, y el efecto, una decisión firmada.

| Qué lo destapó | Qué cambió | Por qué | Commit |
| --- | --- | --- | --- |
| La primera dirección visual, vista en la app | Se aprueba al verla, con dos tests de accesibilidad **rehechos**: `axe` bajo jsdom no mide contraste y `:focus-visible` sale vacío | Los dos pasaban **sin haber mirado un solo color** ni el foco. Entra el cálculo del ratio WCAG sobre los tokens del CSS | `94fff2a` |
| La misma dirección, implementada entera | Enmienda 1 del plan 4: «Cuaderno de viaje», elegida entre cuatro | Se pidió algo más *vintage*. La enmienda cambia color, tipografía y ornamento y **no toca tareas, tests ni navegación** | `d5207bd`, `dbf2bda` |
| La página vista en un sistema en modo oscuro salió en «Noche» sola | Siempre «Papel» salvo que se elija otro tema | Revierte la decisión 2 del plan 4 (tema según el sistema), y queda anotado en la enmienda | `cd2f38c` |

---

## Qué ha enseñado este registro, dicho de una vez

1. **Una restricción sobre la que ningún test puede caer no protege nada, y aparece sola.** Van
   nueve en dos fases. No se detectan leyendo: se detectan rompiendo.
2. **Lo que solo es cierto dentro de la suite no es cierto.** Tres afirmaciones de cierre de la
   Fase 1 y dos de la Fase 2 cayeron al levantar el servidor.
3. **Un requisito «cerrado» puede estar cerrado por su mitad.** Pasó con la extracción de
   hechos del texto libre, con los identificadores por capa, con el validador de continuidad
   y con los *scores* de Langfuse. La corrección siempre fue la misma: **decirlo, no darlo por
   bueno**.
4. **Cambiar la palabra del encargo por la nuestra y razonar sobre la nuestra** es el error más
   caro que se ha cometido, y se cometió dos veces: con «concurrentes» y con «un fichero por
   obra».
5. **El reparto por fichero corta por donde pasa el cable.** Siete olas, siempre igual.
6. **Una condición de caducidad escrita sigue necesitando que alguien la relea**, porque la
   condición que se escribe es la que uno imagina.
7. **Un doble no puede ver lo que vive entre piezas.** Once defectos de la primera corrida real,
   con más de novecientos tests en verde delante. La suite prueba cada pieza contra lo que su
   autor imaginó que le llegaría.
8. **Medir antes de arreglar ahorra construir lo que no sirve.** Una llamada de sonda evitó
   implementar un marcador que no habría resuelto nada, y seis llamadas evitaron diseñar la
   concurrencia alrededor de una cifra que no se reproduce.
9. **Un verificador formal enseña primero sobre el plan.** Dos pasos del plan de TLA+ no podían
   pasar tal como estaban escritos, y su argumento de *liveness* era falso. Lo encontró TLC.

---

## Lo que este registro todavía no puede tener

Y conviene que esté escrito, porque es exactamente lo que el encargo pedía y hoy no está:

- ~~Ninguna iteración disparada por una eval.~~ **Ya hay una** (§K bis y `evals/tuning.md`):
  `escritor` v1 → v2 por `EST-02`, con antes y después medidos sobre la base.
- **Ningún contraejemplo real de TLC.** Los de §H son de laboratorio, y `formal/README.md` lo
  dice.
- **Ningún caso real de Lean.** Falta la fila que el encargo §5c pide explícitamente: **una
  incoherencia real que el validador formal detecte y los otros no**, o por qué no hubo
  ninguna. El candidato previsto, B3, depende de P-27. Y el fallo de Lean **no vuelve a ningún
  rol como *feedback***: acaba en un `409` (P-28).
- ~~Ninguna traza vista en un Langfuse real.~~ Vistas desde el 2026-09-24 en la corrida real,
  tras adaptar el SDK v4 (§K bis).
- **Ninguna observación del navegador MCP.** `.claude/mcp.json` declara Playwright y la
  lectura web ya existe, pero **ningún agente la ha inspeccionado todavía**: no hay qué
  registrar.
