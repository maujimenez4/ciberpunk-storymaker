# Registro de iteraciones — causa y efecto

**Qué es este documento.** Lo que el encargo pide con estas palabras: «qué cambió tras cada
eval o contraejemplo de TLC o Lean, y por qué. **No un diario, sino un log de decisiones con
causa y efecto.**»

**Y lo primero que hay que decir es lo que falta, porque si no este documento engaña.**

> **No hay una sola fila originada en una eval, en un contraejemplo de TLC o en un fallo de
> Lean.** Los tres no existen: las cinco evals son la Fase 6, TLA+ es la Fase 7 y Lean la
> Fase 4. Lo que sí hay son **más de ciento cincuenta iteraciones registradas con causa y
> efecto**, disparadas por otras seis cosas. Cuando las evals y los dos verificadores
> formales existan, sus filas entran aquí y este aviso se retira.

**De dónde sale.** De las tablas de **Desviaciones** de los tres planes de
`specs/001-backend-v1/` —54, 109 y 104 filas—, que se escriben **antes de seguir, no
después** (`CLAUDE.md` §3.4). Allí está el detalle; aquí está la extracción con la forma que
el encargo pide: **qué lo destapó → qué cambió → por qué**.

**Qué se ha dejado fuera.** Las filas de coordinación pura —un *worktree* que arranca en el
commit equivocado, veinte veces— y las que solo anotan dónde vive un fichero. Están en los
planes. Aquí queda lo que **cambió una decisión, un requisito, un documento o una regla del
proceso**.

---

## Las seis causas, y cuántas veces disparó cada una

| Causa | Qué es | Veces | Lo más caro que encontró |
| --- | --- | --- | --- |
| **A · Mutación deliberada** (`CA-6`) | Se quita la validación y se comprueba que cae **su** test y solo el suyo | ~20 | **Nueve restricciones sobre las que ningún test podía caer** y **ocho tests verdes por el motivo equivocado** |
| **B · Las puertas de la build** | `ruff`, `mypy`, `lint-imports`, Alembic, sobre código que la suite daba por bueno | 12 | Un renombrado a medias con la **suite entera en verde** |
| **C · Ejecutar contra el servidor de verdad** | Levantar la aplicación y llamarla, en vez de fiarse de la suite | 6 | Un endpoint que **respondía y no dejaba una fila en disco** |
| **D · Cruce contra el encargo y entre documentos** | Leer el texto del encargo al lado del nuestro | 9 | Un techo del encargo **que nadie contaba** |
| **E · Junturas del reparto** | Trabajo que vive entre dos tareas y no es de ninguna | 7 olas | Una regla del proceso que **no dice qué hacer** cuando la juntura está en fichero ajeno |
| **F · Un agente corrige una cita o un supuesto** | El subagente va a comprobar en vez de creerse el encargo | 5 | Una regla de dominio que, **al pie de la letra, prohibía guardar el nombre del Destinatario** |

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

**Y una que no se cambió y volverá a firma:** la Fase 3 añadió `POST /obras/{obra_id}/novela`
porque «de principio a fin» y la corrida real necesitan **una** entrada. **La spec dice catorce
endpoints y hay quince.** El agente lo añadió y **pidió que lo firme alguien**, que es lo
correcto: modificar un requisito de una spec aprobada es lo que hizo P-07, y aquello volvió a
firma.

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
| «El SDK habla con el proveedor» | **Lanza el binario `claude`**, que `pyproject.toml` no declara y ninguna puerta comprueba | Queda declarado: sin el binario, la corrida real falla **y la suite sigue verde** |
| «El contador local es local» | `tiktoken` **descarga su vocabulario** la primera vez | Declarado: el contador de producción en una máquina sin red y sin caché falla al primer `contar()` |
| «La semilla hace reproducible la llamada» | El proveedor **no la admite** | Se registra por requisito y **no se promete reproducibilidad de la prosa**: lo reproducible es el paquete |
| «Aprobada es instalada» | NumPy estaba aprobada en bloque y **no en `pyproject.toml`** | Se instala, y queda el aviso: en las fases siguientes esa distancia se llama **Langfuse, Lean y Playwright** |
| «Los topes por capa no agotan el techo» | Los ocho suman **exactamente 100.000** | No se escribe la comprobación redundante —sería una rama que ningún test puede poner en rojo— y entra **un test de la identidad aritmética** |

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

---

## Lo que este registro todavía no puede tener

Y conviene que esté escrito, porque es exactamente lo que el encargo pedía y hoy no está:

- **Ninguna iteración disparada por una eval.** Las cinco evals y la iteración de *tuning* con
  resultados antes y después son la Fase 6. Hasta entonces no hay ningún cambio de prompt del
  que se pueda decir **con qué versión de plantilla mejoró**.
- **Ningún contraejemplo de TLC.** No hay `.tla`.
- **Ningún fallo de Lean.** Y con él falta la fila que el encargo §5c pide explícitamente: **un
  caso real en que el validador formal detecte una incoherencia que los otros no vieron**, o la
  justificación de por qué no se encontró ninguno.
- **Ninguna observación del navegador MCP.** El encargo pide documentar qué inspeccionó el
  agente, qué detectó y qué cambió a consecuencia. No hay lectura web que abrir.
