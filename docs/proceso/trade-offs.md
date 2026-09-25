# Trade-offs — cada decisión relevante, como decisión

**Qué es este documento.** Las decisiones de diseño del proyecto escritas con la forma que
pide el encargo: **opciones, criterio y elección**, más lo que cada una cuesta. No es un
catálogo de aciertos: varias invierten una decisión anterior que estaba razonada —P-07, P-02,
los invariantes de Lean, la apariencia de la lectura—, y en esos casos se escribe por qué dejó
de valer el motivo original (`CLAUDE.md` §3.3).

**De dónde sale cada una.** P-01 a P-09 son de `specs/001-backend-v1/spec.md`; D-01 a D-07
son de `specs/002-frontend/spec.md`; P-A a P-C son de `specs/001-backend-v1/plan-2-capitulo.md`;
D-1 a D-5 del plan 8 son de `specs/001-backend-v1/plan-8-corrida-real.md`; las «decisiones 1 y
2» de la apariencia son de `specs/002-frontend/plan-4-apariencia-de-lectura.md`; las numeradas
1 a 20 son la tabla de `docs/architecture.md` §12. Se citan con su identificador para que
cualquiera pueda ir a leer el original.

**Puesto al día el 2026-09-24 por la tarde.** La primera versión (`63363e8`) se escribió antes
de las Fases 4 a 8 del backend y del frontend, y daba por ausentes Lean, TLA+, el Crítico, el
hook de policy y `src/frontend/`, que hoy existen. Las decisiones T-26 a T-33 son posteriores.

**Cómo se lee la columna de estado:** una decisión puede estar **firmada y no implementada**.
Eso no la hace menos decisión; lo contrario —dar por hecho que lo firmado existe— es
exactamente el error que este proyecto ha encontrado varias veces.

---

## Las cinco que el encargo nombra

### T-1 · Un agente o varios: **varios roles separados, orquestados por código**

| | |
| --- | --- |
| **Opciones** | (a) Un agente que escribe y se corrige a sí mismo. (b) Varios agentes que se llaman entre sí. (c) **Diez roles separados y un orquestador determinista en estrella** |
| **Criterio** | Que un defecto sea **atribuible**, y que un fallo se pueda reproducir |
| **Elección** | (c). Decisiones 6 y 10 de `architecture.md` §12 |
| **Coste** | La puerta de escena gasta hasta dos validaciones además de la escritura, y hay diez prompts que mantener |

**Por qué.** Un agente que se corrige a sí mismo **no ve sus propias contradicciones**: el
mismo modelo que decidió que el perro se llama Luna considera coherente que se llame Luna. Y
una cadena de agentes que se invocan entre sí hace imposible saber quién introdujo el
defecto. La topología en estrella —el orquestador invoca a uno, recibe su salida, la
persiste y decide el siguiente— convierte la traza en una tabla en vez de una conversación.

**Lo que esta decisión NO compra, y está declarado:** los validadores siguen
**correlacionados**. Comparten proveedor, comparten la redacción de las restricciones duras
y, sobre todo, **comparten la entrada**: lo que faltó en el paquete le falta al Escritor y al
Continuista a la vez. `verification.md` §6.1 fija la regla de lectura — dos validadores
correlacionados cuentan como uno.

**Y lo que la reforzaba ya no está:** la P-02 original separaba los modelos —Haiku 4.5
escribía, Opus 5 juzgaba— y eso rompía la correlación por modelo. **Desde el 2026-09-24 todos
los roles corren en Haiku** (T-16), así que escritor y jueces comparten también modelo.

---

### T-2 · Formato de la *story bible*: **SQLite única, ledger *append-only* y vistas derivadas**

| | |
| --- | --- |
| **Opciones** | (a) Postgres más una base vectorial. (b) SQLite con **un fichero por obra**. (c) **Una sola base SQLite, un solo motor** |
| **Criterio** | El encargo §4 obliga a SQLite, y el esquema tiene dos conceptos que **cruzan obras** |
| **Elección** | (c), decisión 4 de §12 corregida por **P-07** el 2026-09-24 |
| **Coste** | Ninguna obra es un fichero portable que se pueda mover suelto |

**Por qué se invirtió (b), que estaba escrito y razonado.** Lo destapó escribir el plan de la
Fase 1: **la entrevista existe antes que la obra**. `POST /entrevistas` precede a `cerrar`,
que es lo que crea la `Obra`, así que con un fichero por obra la entrevista no tiene dónde
vivir. Y tirando del hilo aparecieron dos cosas más: **el encargo nunca lo pidió** —«un
fichero por obra» era glosa nuestra, no una cita— y **contradecía dos requisitos propios**:
`serie` comparte canon **entre** obras desde el primer día (RD-04) y un `comprador` encarga
varias.

*El motivo original —que la base de una obra fuera portable y aislada— sigue siendo bueno; lo
que no era cierto es que se pudiera tener a la vez que `serie`, que `comprador` y que una
entrevista anterior a la obra.*

**Y dentro del esquema, tres decisiones de forma que valen tanto como la elección del motor:**

- **El ledger es *append-only* y el estado en T es una vista derivada** (decisión 3). Una
  tabla de estado editable se desincroniza del texto, y entonces hay dos relatos de lo que
  pasó. Lo sostienen tres disparadores de SQLite, no la buena voluntad de quien escribe.
- **Corregir un hecho no lo edita:** se escribe uno nuevo que **cita al anterior** en
  `sustituye_a`. Así se puede encontrar la escena que se apoyó en el hecho viejo.
- **`version_publicada` fija los `version_texto_id`** (decisión 19). Resolver por «la versión
  vigente de cada escena» al leer contestaría «el manuscrito ahora» y no «el que se
  entregó», y haría irrecuperable la versión anterior — que es justo lo que el encargo
  prohíbe.

---

### T-3 · Modelo de lectura: **web, con revelado progresivo y petición desde la ficha**

El encargo §2 dice «web o PDF» y **no nombra tecnología**. Elegir web, y elegir React, fue
decisión de `maujimenez4`. Dentro de esa elección hay siete decisiones de producto, todas
con su alternativa descartada:

| | Decisión | Se descartó | Criterio |
| --- | --- | --- | --- |
| **D-01** | **Un solo enlace: quien lee puede pedir el cambio** | Dos enlaces con capacidades distintas | El encargo §2 dice literalmente que «**el lector** puede seleccionar un fragmento o un hecho y pedir un cambio desde la propia página». Restringirlo al Comprador era una desviación del texto, no una lectura de él |
| **D-02** | **La petición se hace desde la ficha**, no seleccionando prosa | Selección de texto libre | Cada entrada de la ficha **ya es un hecho de canon con su identificador**. Mapear prosa a canon con búsqueda difusa significa que, si acierta el hecho equivocado, **se regeneran los capítulos equivocados** y quien lee no tiene forma de saberlo |
| **D-03** | **Distintivo en el índice y página de novedades** | Resaltar las diferencias dentro del capítulo | Un capítulo regenerado **se reescribe entero**: el resaltado sería casi todo el texto. Ruido, no información |
| **D-04** | **La ficha se revela al avanzar** | Enseñar el canon entero, que es lo que el encargo pide literalmente | En una novela de diez capítulos que se lee de una sentada, la ficha completa **es un índice de spoilers**. Se cumple el requisito —la ficha existe y enlaza al capítulo— sin cumplirlo de la forma que estropea el producto |
| **D-05** | **Mientras se regenera, la lectura se detiene y se muestra el progreso** | Seguir leyendo la vigente con un aviso | Que nadie lea un capítulo que está a punto de cambiar |
| **D-06** | **La lectura deja de tener cinco rutas**: la novela entera y continua, «tipo Kindle», y la entrevista fuera del token | Cinco direcciones (portada, índice, capítulo, ficha, novedades) | El enlace del regalo se reenvía y se pega; cada URL de más es una forma de recibir la página tres sin saber que hay una uno. Y la entrevista bajo el token es imposible cuando se usa y llevaría al Destinatario a lo que el Comprador escribió sobre él |
| **D-07** | **Una sola dirección y tres pestañas**; la de leer se activa sola al publicar | Las dos entradas de D-06 | Nadie navega. El token pasa de ruta a parámetro y sigue siendo lo único que protege la lectura. **Coste declarado:** `RF-VAL-08` ya no puede llegar navegando a cuatro rutas que no existen |

**El argumento que sostenía D-01 al revés sigue siendo bueno y por eso queda escrito:**
enseñarle al Destinatario un botón de «pedir un cambio» le revela que la novela la escribió
una máquina y que se puede reescribir, que es lo que un regalo no debería mostrar. Pesó más
la letra del encargo.

**Y D-05 tiene una víctima que no la pidió:** Comprador y Destinatario pueden estar leyendo
la misma novela a la vez. Si uno pide una corrección, **el otro se queda sin su regalo
durante minutos** sin haber pedido nada. Es el coste conocido y se acepta.

---

### T-4 · Integración de TLA+ con el flujo real: **TLC en desarrollo, contra la máquina que ya existe**

| | |
| --- | --- |
| **Opciones** | (a) TLA+ en cada generación, como Lean. (b) **TLC solo en desarrollo**. (c) No modelar el harness: los tests cubren la máquina |
| **Criterio** | Qué gana un *model checker* sobre los tests, y cuándo |
| **Elección** | (b), decisión 18 de §12. Y (c) **era la decisión anterior y caducó** |
| **Estado** | **Existe.** `formal/tla/Harness.tla` con `harness.cfg`, TLC en verde (65.601 estados distintos) y la correspondencia con el código comprobada por test (`test_correspondencia_tla.py`, `e76ab85`). **Ningún contraejemplo real**, y `formal/tla/README.md` lo dice |

**Por qué (c) dejó de valer, que es la parte interesante.** `verification.md` v3.1 descartó
la comprobación de modelos con un argumento correcto —la máquina es pequeña y la cubren los
tests— **y dejó escrita su condición de caducidad**: se reconsidera si aparece concurrencia
real. No apareció concurrencia. Aparecieron **tres ejes que no estaban**: publicación de
versiones, checkpoint por capítulo y regeneración parcial por petición del lector. Los tres
se multiplican entre sí, y ese producto es justo el espacio donde los tests eligen caminos y
un *model checker* los recorre todos.

*La lección no es que la decisión fuera mala: es que **caducó por donde no se esperaba**. La
condición que se escribe es la que uno imagina.*

**Por qué TLC no corre en cada generación:** Lean mira **una cronología concreta** y es
barato; TLC explora un espacio de estados y **no depende de los datos de una novela**.
Ejecutarlo por generación sería pagar lo mismo mil veces por la misma respuesta. El propio
encargo §6 lo dice: «TLC se ejecuta en desarrollo, no en cada generación».

**Cómo se integra con el flujo real, que es lo que el encargo pregunta:**

1. La máquina de la novela —`CONFIGURANDO → PLANIFICADA → ESCRIBIENDO_CAPITULO →
   VALIDANDO_CAPITULO → VERIFICANDO → PUBLICADA`, con `REGENERANDO` y `DETENIDA`— está
   descrita en `architecture.md` §3.9, y `Harness.tla` se escribió contra ella.
2. La máquina del **capítulo** estaba en código antes que la especificación
   (`features/escritura/maquina.py`, con tabla de transiciones explícita), así que el `.tla`
   no partió de una pizarra.
3. `RF-FOR-07` exige que el README empareje **cada acción de la especificación con el estado
   o transición del código** que la implementa: está en `formal/tla/README.md`.

**El riesgo que esta decisión abre:** que la especificación deje de corresponder al código.
Una especificación verde sobre un código que ya no implementa esa máquina **no es cobertura
ausente, es cobertura falsa**: afirma la seguridad de otro sistema. Se diseñó como inspección,
y **se mecanizó con un test, que además tuvo que corregirse**: el primero leía la tabla
`_TRANSICIONES` —11 transiciones— en vez de llamar a `transitar`, que produce 31, y siguió en
verde cuando se añadió `PROCESO_INTERRUMPIDO` (`e76ab85`). Hoy mide el código. Lo que sigue
siendo inspección es que el `.tla` modele **lo que importa** de la máquina, no solo lo que el
test compara.

---

### T-5 · Invariantes de Lean priorizados: **los dos que el esquema permite probar de verdad**

El encargo §5c ofrece cuatro candidatas y pide «al menos dos». **La priorización se escribió
dos veces**, y la segunda invierte la primera:

| Invariante | Primera prioridad (antes del código) | Lo que entró | Por qué cambió |
| --- | --- | --- | --- |
| Los eventos respetan el **orden temporal declarado** | Entra | **No entra** | `evento.tiempo_historia` es texto libre —«el verano del 98»— y **no hay en el esquema ninguna magnitud ordenable de tiempo de historia**. Lo único ordenable es el orden de discurso, que avanza aunque la historia retroceda: el invariante sería verde por construcción (`b6b1463`) |
| La **edad** concuerda con la **fecha de nacimiento** | Entra | **No entra** | La regla 13 es condicional —«cuando ambas existen»—, y hoy solo el Destinatario tiene fecha y no es un `Personaje`. Sería un verde permanente que parecería una garantía (`plantilla.lean`, cabecera) |
| Nadie está en **dos lugares** en el mismo momento | Caso de prueba | **Invariante 1, `sinUbicuidad`** | Es literalmente lo que `CA-21` exige probar, y solo necesita igualdad de momento, que cualquier índice respeta |
| Nadie aparece **después de un evento que lo excluye** | Aplazada | **Invariante 2, `sinReaparecidos`** | `evento.excluye[]` existía desde la Fase 2 y no lo miraba nadie. Estricto (`<`, no `≤`): quien muere está en la escena de su muerte (`4c6ff5c`) |

**El criterio no cambió; cambió lo que se sabía.** Se decía «entran primero las invariantes
cuya entrada ya existe», y resultó que la entrada de las dos primeras **no existía como se
creía**: el tiempo es texto y la fecha de nacimiento no la tiene ningún personaje. Mantenerlas
habría dado dos invariantes que no pueden fallar, y esa es la cobertura falsa de T-4.

**Lo que cuesta, y está abierto:** §5c pide que el fichero Lean incluya **fechas de
nacimiento**, y no las incluye (P-27). Y el brief de evaluación diseñado para la trampa
temporal contaba con el invariante de edad, así que tal como está no fallaría donde el plan 6
dice. Cerrarlo pide una de dos: rediseñar ese brief contra los invariantes que existen, o dar
fecha a los personajes y añadir el invariante. Las dos son decisión de `maujimenez4`.

**Y lo que Lean no ve, que conviene no olvidar al leer un verde:** demuestra sobre el
**fichero generado desde la biblia**, no sobre la prosa. Si el capítulo dice algo que nunca
llegó a la biblia, Lean no lo ve. Verifica el modelo de la historia, no la historia.

**Estado:** `CronologiaIncoherente` detiene `publicar` y se ha visto detenerla: quitando la
llamada caen cuatro de los cinco tests de la puerta (`4c6ff5c`, `CA-21` cerrado). En la
publicación se llama a `lean` sobre un fichero autocontenido y no a `lake build`: medido,
2,4 s con cuarenta eventos frente a 13,1 s de `lake` en frío. **Lo que falta:** que el fallo
vuelva a un rol como *feedback* (P-28) —hoy termina en un `409`— y un caso real, no provocado.

---

## Las decisiones del harness

### T-6 · P-08 · El cliente de modelo invoca el **Claude Agent SDK**, no la API con clave

| | |
| --- | --- |
| **Opciones** | (a) API de Anthropic con clave. (b) **Claude Agent SDK / Claude Code, ya autenticado** |
| **Criterio** | Coherencia con P-02, que fija consumo de cuenta **sin clave de API** |
| **Elección** | (b), `maujimenez4`, 2026-09-24 |
| **Coste** | Tres cosas que la decisión daba por hechas y no lo eran |

**Lo destapó la Fase 1 de la peor manera posible:** sus tres endpoints existían, estaban en
el OpenAPI y **respondían 500 contra la aplicación levantada**, porque la única
implementación de `ClienteModelo` al terminar era el doble determinista. Ninguna tarea tenía
asignado el cliente real.

**Lo que se descubrió después de firmarla:**

1. El SDK **no habla HTTP: lanza el binario `claude`**. Se creyó que había que instalarlo
   aparte; **no hace falta**, porque `claude_agent_sdk` trae el suyo y `uv sync` lo instala
   (P-15, reformulado). `README.md` y `.env.example` todavía piden instalarlo.
2. «Ya autenticado» **no lo comprueba ninguna puerta al arrancar**: sin cuenta autenticada,
   el fallo aparece a mitad de una corrida y la suite sigue verde. Y la cuenta **importa más
   de lo que parecía**: la de trabajo anonimiza los nombres de persona (T-26).
3. **La semilla no la admite el proveedor.** Se registra en `Consumo` por `RF-OBS-06` y **no
   hace reproducible la llamada**: lo reproducible es el paquete, no la prosa.

**Y deja abierta una pregunta que no cierra**, planteada como P-A: `RF-CTX-02` exige contar
tokens antes de llamar y prohíbe la estimación por caracteres, pero contar **exactamente** los
de Anthropic requiere su endpoint `count_tokens`, que necesita clave.

---

### T-7 · P-A · Dos contadores de tokens, porque son dos momentos distintos

**La pregunta original era falsa en su premisa.** Se preguntaba cómo contar tokens sin clave,
dando por hecho que había **un** contador. Hay dos:

| Momento | Requisito | Quién lo da |
| --- | --- | --- |
| **Antes** de llamar | `RF-CTX-02` — contar para decidir si el paquete cabe, y **fallar sin gastar** | Un tokenizador **local** inyectado (`tiktoken`) |
| **Después** de llamar | `RF-OBS-03` — tokens, coste y latencia | El recuento **real** del proveedor, persistido en `ejecucion` |

**Langfuse mide el segundo, no el primero**, y esa es la parte que la pregunta no veía: para
cuando el *tracing* ve una llamada, la llamada ya se hizo.

**Lo que cuesta, declarado como riesgo y no como comodidad:** un tokenizador local
**aproxima** al de Anthropic. Lo acotan la capa de reserva de 10.000 tokens y que `ejecucion`
guarda **los dos números**, previsto y real — con lo que la deriva deja de ser un riesgo y
pasa a ser una cifra medible. Y un agujero que apareció después: **`tiktoken` descarga su
vocabulario la primera vez**, así que el contador de producción en una máquina sin red y sin
caché falla al primer `contar()`.

---

### T-8 · P-06 · Se permite el paralelismo **dentro** del techo sumado

| | |
| --- | --- |
| **Opciones** | (a) Una llamada en vuelo, que es lo que había. (b) **Varias a la vez mientras sus paquetes sumen 100.000 o menos** |
| **Criterio** | El encargo §7 dice «100.000 tokens **concurrentes**»: es una suma, no el tope de una llamada |
| **Elección** | (b), y el turno se da **contando tokens, no llamadas** |
| **Coste** | Dejan de ser gratis la atribución de un fallo y la reproducción de una corrida |

**Lo grave no era el número: era por qué no se notaba.** Con la concurrencia en 1, las dos
lecturas dan el mismo resultado, así que el sistema cumplía **por consecuencia y no por
regla**. Subir la concurrencia a dos habría incumplido el encargo **sin que fallara ningún
test**. Por eso `RF-ORQ-10` se aplica y se comprueba aunque hoy sea trivial: para que el día
que la concurrencia suba, el que falle sea el sistema y no la entrega.

**Y hay que decir qué NO acelera, porque la pregunta se planteó sugiriendo lo contrario.** Los
diez capítulos siguen siendo **estrictamente secuenciales**, y no por el límite de
concurrencia sino por `CU-03`: cada capítulo necesita integrado el anterior. Lo que se solapa
son **obras distintas**, el **Continuista con el Crítico** sobre el mismo capítulo —hecho
desde `92d2da7`, T-27— y las novelas de evaluación. Sobre una novela sola, el paralelismo
**le quita una espera de validación por intento**. Quien espere que una novela salga en la
mitad de tiempo se va a llevar una sorpresa.

**El techo concurrente se hace cumplir esperando, nunca recortando:** si admitir una llamada
pasaría del techo, esa llamada **espera**. Recortar obedece al presupuesto de contexto, no a
la carga del sistema.

---

### T-9 · Presupuesto por capa con **fallo explícito**, no truncado por ventana

| | |
| --- | --- |
| **Opciones** | (a) Ventana deslizante que trunca por el final. (b) **Ocho capas con tope propio y `ContextBudgetExceeded`** |
| **Criterio** | Un truncado silencioso produce defectos invisibles |
| **Elección** | (b), decisión 7 de §12 |

**Y tres consecuencias que no estaban en la decisión y salieron al implementarla:**

1. **Los ocho topes suman exactamente 100.000.** Respetar el tope de cada capa **es**
   respetar el techo por llamada, así que un `if total > TECHO` sería una rama que ningún
   test puede poner en rojo. No se escribió; lo que hay es un test **de la identidad
   aritmética**, que cae si alguien sube un tope. Y esa identidad **no estaba declarada como
   intencionada en ningún documento**: hoy solo la guarda ese test.
2. **El recorte quita piezas enteras y nunca la última.** Vaciar una capa que tenía contenido
   no es recortarla, es perderla, y dejaría al Ensamblador sin poder distinguirla de una que
   nunca se surtió. La alternativa cómoda —trocear la pieza— es justo el «truncar por el
   final» que el requisito prohíbe.
3. **Una capa vacía cuando debería tener contenido falla antes de llamar.** Para que eso sea
   comprobable, quien surte declara **cuánto tenía** además de qué entrega: sin ese segundo
   número, «capa vacía» y «avería del almacén» son indistinguibles.

---

### T-10 · El **Ensamblador es código**, y el Escritor solo ve el paquete

| | |
| --- | --- |
| **Opciones** | (a) Un agente que decide qué recuperar. (b) **Código determinista** |
| **Criterio** | Reproducibilidad y auditoría: si quien decide es un modelo, un fallo no se puede reproducir |
| **Elección** | (b), decisión 2 de §12 |

**Lo que compra de verdad:** que un defecto sea **atribuible**. El Escritor nunca accede a la
base de datos, así que si le falta un dato **es un fallo del ensamblado, no del escritor**.

**Y lo que hoy no se cumple al pie de la letra, dicho porque se descubrió implementando:** las
tres restricciones duras que `CLAUDE.md` §10 obliga a repetir —persona, tiempo verbal, nivel
de calor— **no están en el paquete en forma legible por código**: la capa constitucional las
vuelca como prosa de biblia. Construirlas desde el paquete obligaría a **parsear prosa para
recuperar una restricción dura**, así que viajan con la ficha. La regla se sostiene en lo que
protege —el Escritor sigue sin recibir sesión— y para cerrarla del todo hay que cambiar **la
capa de instrucción**, no al Escritor.

---

### T-11 · Recuperación **híbrida y en este orden**, y la palabra que se corrigió

| | |
| --- | --- |
| **Opciones** | (a) Similitud vectorial sobre todo el corpus. (b) **Filtro estructural → orden por afinidad → fusión con recencia** |
| **Criterio** | La búsqueda puramente vectorial trae escenas **parecidas**, no **pertinentes** |
| **Elección** | (b) |

**Y una corrección de vocabulario que vale como decisión.** El vectorizador que hay es
**léxico, local y determinista** —bolsa de palabras normalizadas repartidas con `blake2b`—, y
eso **no es semántica**: dos fragmentos que dicen lo mismo con otras palabras no se
reconocen. Se decidió **corregir la palabra, no el código**: Anthropic no publica extremo de
*embeddings* y P-02 fija consumo de cuenta sin clave, así que meter un proveedor
contradiría una decisión firmada. `CLAUDE.md` §4.2 y `architecture.md` §2 pasaron a decir
«**afinidad de vectores**», con lo que **no** hace escrito al lado.

---

### T-12 · La extensión vectorial es **opcional**, y es decisión nuestra

El encargo obliga a SQLite y **no menciona vectores en ninguna parte**. Mantener `VectorStore`
con dos implementaciones cuesta una interfaz y una suite que corre en dos modos; a cambio, el
sistema arranca en una máquina sin la extensión. **Si ese coste deja de pagarse, se retira y
no se incumple nada** (decisión 20).

**Cómo se hace ejecutable el modo degradado:** una variable de entorno,
`STORYMAKER_SIN_SQLITE_VEC`, en vez de desinstalar la rueda. Sin ella, «la suite corre en los
dos modos» solo sería comprobable en dos máquinas distintas, y en la práctica no se
comprobaría nunca.

---

### T-13 · **Ningún agente recibe una herramienta** — y el validador visual no es la excepción

El encargo §3 pide «tools con schema validado». La decisión es **no dárselas a los agentes
narrativos**: ni fichero, ni red, ni proceso. Eso permite decir que el radio de impacto está
**eliminado** y no contenido — no hay *sandbox* porque no hay nada que aislar.

**El encargo §5a pide además un validador que abra la novela en un navegador, y eso parece
conceder una herramienta.** No lo hace: es **código conduciendo un navegador**, como el
Ensamblador es código que ensambla. No recibe prompt, no llama al modelo y no decide. La
distinción se escribió como **reapertura explícita** de la fila de `verification.md`, porque
esa fila ya caducó una vez en silencio — afirmó durante semanas que el agente de código
corría sin herramientas de fichero después de dejar de ser cierto.

---

### T-14 · Guardarraíles en código, y **por palabra, no por subcadena**

| | |
| --- | --- |
| **Opciones** | (a) Instrucción en el prompt. (b) Comparación literal en código. (c) **Comparación sobre texto normalizado, por palabra** |
| **Criterio** | Un veto que solo caza la forma exacta no es un veto: basta con escribir el plural |
| **Elección** | (c), en los tres ámbitos —global, obra y brief— |

**Y el trade-off fino, que apareció implementando:** el tokenizador `\w+` parte los apellidos
con guion, así que un veto «Ortiz» saltaría dentro de «García-Ortiz» — que puede ser el
nombre del Destinatario. Se evaluó **ensanchar el tokenizador** y se descartó: aflojarlo
compra un falso positivo a cambio de **falsos negativos**, y un veto que deja de saltar es
peor que uno que salta de más. La garantía que hacía falta no la puede dar el tokenizador, y
se cerró donde sí se puede: **al construir el brief**, comprobando que ningún veto choca con
el nombre del Destinatario.

**Lo que este guardarraíl no caza, escrito y no disimulado:** la **alusión**. Quien pidió no
leer sobre su expareja no la nombra, y el tema entra sin que ningún término de la lista
aparezca. Y el plural en `-es` de las palabras terminadas en consonante —«ratones» frente a
«ratón»— necesita un diccionario, no una regla.

---

### T-15 · Dos hooks, **fuera** del bucle del modelo

Un guardarraíl que vive dentro del código que vigila se puede saltar cambiando ese código sin
que nada lo note. **Un hook es un punto de enganche declarado, y su ausencia se ve.** Son dos:
validación de capítulo y policy.

**Estado:** existen los dos. `HOOK_DE_CAPITULO` y el **hook de policy declarado**, que sacó el
veto de un `if` dentro del ciclo (`168461a`); `registro_auditoria` recibe cada decisión suya,
permitida o bloqueada.

**Lo que no está razonado todavía (P-31):** el encargo §3 nombra los hooks junto a
`CLAUDE.md` y la skill, que son artefactos de Claude Code, y cabe leer que pide hooks **de
Claude Code** en `.claude/settings.json`. El proyecto los implementa como puntos de enganche
del sistema. Es defendible —vigilan la novela, no al agente que programa—, pero la otra lectura
no se ha descartado por escrito y no hay `.claude/settings.json` con hooks.

---

## Las decisiones sobre la calidad y quién la juzga

### T-16 · P-02 · Anthropic por consumo de cuenta, **Haiku 4.5 en todos los roles**

| | |
| --- | --- |
| **Opciones** | (a) **Un solo modelo para todo.** (b) Modelo barato para el volumen, modelo caro para el juicio |
| **Criterio** | Primero, que un juez que comparte modelo con quien escribió **tiende a aprobar su propio estilo**. Después, el coste medido |
| **Elección** | (b) el 2026-09-23 —Haiku escribía, Opus 5 juzgaba—, **invertida a (a) el 2026-09-24** (`b80e911`) |
| **Coste** | La distancia de `RF-JUZ-05` se medirá con un juez que comparte modelo, familia y entrenamiento con el autor: **saldrá mejor de lo que el sistema merece** |

**Por qué se invirtió, con la cifra delante.** Diez capítulos todo en Haiku salen a **~1,5 USD**;
con Opus juzgando, **~8,8 USD**, y con reintentos 12–15 USD. La diferencia es entera del cambio de
modelo —el juez cuesta cinco veces la entrada y la salida—, y pesa porque la novela de ejemplo
depende de una corrida real que no se puede repetir muchas veces.

*El argumento original no dejó de ser cierto: se decidió pagarlo.* Por eso el punto ciego vuelve
a estar abierto en `verification.md` §6.1, y la constante `MODELO_JUEZ` **se mantiene separada**:
una línea vuelve a separarlos sin tocar ningún rol.

**Dos consecuencias que cambian requisitos y por eso se escriben aquí:** no hay **coste por
llamada** que leer, así que `RF-OBS-03` lo **deriva** de los tokens y la tarifa declarada —es
una cifra imputada, y sirve igual para comparar plantillas—; y `RF-OBS-07` **no se relaja**:
que hoy no haya clave que leer no es motivo para retirar la regla, es motivo para que siga
siendo barata.

---

### T-17 · P-05 · El Comprador **acepta**; el Autor **calibra**

| Acto | Quién | Qué produce | Para qué |
| --- | --- | --- | --- |
| Aceptación de la entrega | **Comprador** | Un booleano, asociado a su versión | Decide si se entrega |
| Revisión con rúbrica | **Autor** | Puntuación por criterio | Mide la distancia con el juez |

**Por qué no puede ser el mismo.** El encargo §5b pide «una revisión humana de al menos una
novela completa, **con la misma rúbrica**, para comparar el juicio humano con el del LLM». De
un sí o un no **no sale ninguna comparación por criterio**, así que si el Comprador fuera el
único revisor el encargo quedaría incumplido. Y pedirle una rúbrica puntuada a quien compra un
regalo no es realista.

**Lo que sigue sin cerrarse:** una novela es una novela. La distancia medida sobre un solo
manuscrito dice muy poco. El encargo pide *al menos* una; nosotros no fingimos que una baste.

---

### T-18 · **G1b no bloquea**, y la condición de reapertura lleva firma

El juez con rúbrica es el validador más caro y **hoy es telemetría**. La redacción anterior
decía que bloquearía «hasta que exista la calibración» — y eso **se habría disparado solo**,
porque la revisión humana de una novela es obligatoria y va a existir.

La condición se reescribió para que **no se dispare sola**: G1b pasará a bloquear cuando la
correlación entre el Crítico y la revisión humana se haya medido sobre un conjunto etiquetado
y **alguien decida, con ese número delante, que basta**. No es una fecha ni un hito: es un
dato y una firma.

*Se escribe así porque la redacción anterior es el modo de fallo que este proyecto ha
encontrado varias veces: una invariante sostenida por una ausencia, con una condición de
reapertura que caduca sin que nadie mire.*

---

### T-19 · Decisión 16 · Cobertura **bloqueante**, naturalidad **umbral**

| | |
| --- | --- |
| **Opciones** | Una sola métrica de personalización, o dos con tratamiento distinto |
| **Criterio** | **Fallan en direcciones opuestas** |
| **Elección** | La cobertura de elementos obligatorios bloquea; la naturalidad es umbral |

Medir solo la cobertura **premia el relleno**: se meten los datos quince veces y pasa. Medir
solo la naturalidad **deja pasar una novela impersonal** que está muy bien escrita. Un
elemento obligatorio que no aparece no es una omisión: **es el producto sin entregar**.

---

### T-20 · P-B · La puerta de la Fase 2 es **mecánica**, y el juez no entra

**Recomendación aplicada, y el motivo no es solo de alcance.** `RF-JUZ-06` dice que el juez no
bloquea mientras su correlación no esté medida y firmada. Construirlo en esa fase habría sido
**construir un componente que, por regla del propio proyecto, no puede parar nada**.

**Pero sin ninguna puerta, «un capítulo rechazado no deja rastro» no se puede probar:** si
nada rechaza nunca, el test es teatro. Por eso entraron los validadores que **sí** funcionan
sobre un capítulo solo y **sin llamar a ningún modelo**: extensión, persona y tiempo verbal,
nombres contra el canon, y la forma del defecto.

---

### T-21 · La comprobación de **forma** del defecto, antes de la puerta

El Continuista es un modelo, así que lo que afirma es una señal con varianza: **lo que hace
mecánica a G1a es el contraste, no la extracción**. Antes de que un defecto llegue a la
puerta se comprueba, en código y sin volver a llamar al modelo, que su código pertenece a la
taxonomía, que la cita **es subcadena exacta en el desplazamiento declarado** y que un
`CAN-01` trae un `hecho_canon_id` que existe.

Un defecto mal formado **no bloquea, no gasta reintento y se cuenta aparte**.

**Lo que compra, sin ampliarlo al leerlo:** desaparece la categoría del defecto bien formado
con la **cita inventada**. **Lo que no dice nada sobre:** el defecto que el Continuista **no
vio**. El falso negativo sigue sin medirse, y ninguna comprobación de forma lo alcanza.

---

## Las decisiones de estructura del código y del proceso

### T-22 · Backend por **features + commons**; frontend **feature-first** con tres reglas

| | Elección | Descartado | Criterio |
| --- | --- | --- | --- |
| Backend | Features + `commons/`, con `import-linter` que **falla la build** | Capas, hexagonal, clean, monolito modular | Cohesión por caso de uso; migra a modular sin reescribir |
| Frontend | Bulletproof React **+ tres reglas de frontera** tomadas de FSD | FSD completo, Nx+DDD, Atomic Design, carpetas por tipo | Coste de adopción bajo, y las tres reglas cierran justo la debilidad conocida de Bulletproof: no define las dependencias entre feature y zona global |

**Y una regla de las cuatro que se ha incumplido y está dicho:** «se duplica primero, sube a
`commons/` al **tercer** uso real». `SalidaMalFormada` va por **cinco copias**. La deuda
estaba vencida antes de la Fase 3 y nadie la paga porque `commons/llm/` siempre pertenece a
otra tarea.

---

### T-23 · P-C · Hacia fuera **capítulo**, hacia dentro **escena**

Las dos cosas a la vez. El endpoint es `POST /capitulos/{id}/escribir`, el trabajo es de un
capítulo y lo que se entrega es un capítulo, porque **el encargo cuenta capítulos**. Pero la
unidad atómica de generación es la **escena**, y hoy coinciden 1:1.

**Las dos tablas existen y no se colapsan.** El capítulo es unidad de **lectura** y la escena
de **generación**; si la extensión crece, la cardinalidad vuelve a `1..*` sin tocar nada más.
Colapsarlas ahora ahorra una tabla y cuesta una migración de datos después.

---

### T-24 · Una spec puede tener **varios planes**, escritos cuando les toca

| | |
| --- | --- |
| **Opciones** | (a) Un `plan.md` por spec. (b) **`plan-N-<slug>.md`, uno por fase** |
| **Criterio** | Un plan a la granularidad que exige la skill —pasos de dos a cinco minutos, con su test escrito— habría pasado de **tres mil líneas** |
| **Elección** | (b), `maujimenez4`, 2026-09-23 |

Dos problemas tenía el plan único, y el segundo es el que decide: **no se lee** —se aprueba de
una firma un documento que nadie recorre entero— y **se escribe demasiado pronto** — detallar
hoy, paso a paso, la fase que se implementará dentro de semanas produce sobre todo
desviaciones. El criterio del corte no es el número de requisitos: **cada plan entrega
software que funciona y se puede probar solo**.

---

### T-25 · Prompts como **ficheros del repositorio**, con su hash en `ejecucion`

Descartado: una tabla de prompts versionada en la base de datos. Criterio: se revisan como
código, cambiarlos no exige migración, y **el hash basta para reproducir una ejecución**
(decisión 14). No se editan en sitio: versión nueva y se cambia la referencia.

---

## Las decisiones de la primera corrida real y del cierre

Salen del 2026-09-24: de intentar la primera novela contra el modelo real, del plan 8
—firmado con D-1 a D-5 como recomendadas— y de la revisión visual de la lectura.

### T-26 · El nombre del Destinatario: **cuenta sin anonimizado**, no marcador

| | |
| --- | --- |
| **Opciones** | (a) **Marcador**: los agentes escriben con un nombre inventado y el código pone el real al servir (plan 8 T2–T3). (b) **Generar con una cuenta cuya organización no obligue a anonimizar** —una cuenta personal— |
| **Criterio** | Que el nombre llegue a la página. Y D-1: **medir antes de construir** |
| **Elección** | (b). T2 y T3 **no se ejecutan** |
| **Coste** | Una restricción de entorno: *el sistema no puede escribir nombres propios con una cuenta cuya organización obliga a anonimizarlos* |

**Lo destapó la primera corrida:** el outline salía personalizado —el perro, el verano— y el
protagonista como `[NOMBRE_ANONIMIZADO]`. La solución acordada era el marcador, y D-1 pidió
sondear primero. La sonda (`src/backend/scripts/sonda_nombre.py`, `38924c3`), una llamada real
al Arquitecto con el brief de ejemplo y la cuenta de trabajo:

| Nombre que recibe el modelo | Apariciones en la salida | Marcas `ANONIMIZADO` |
| --- | --- | --- |
| El real del brief de ejemplo | 0 | sí |
| Uno inventado, el que el marcador habría usado | 0 | 13 |

**La cuenta anonimiza cualquier nombre de persona, también uno inventado.** No es el modelo ni
el código: son instrucciones de la organización de esa cuenta, que se aplican a toda llamada.
El marcador habría costado un campo nuevo en el brief (`trato`), una migración, un prompt v3 del
Entrevistador, un campo en el formulario y dos términos de vocabulario, **para salir anonimizado
igual**.

**Lo que queda escrito y sin hacer, para no confundirlo con hecho:** T2–T3 siguen en el plan por
si una cuenta futura anonimizara solo nombres reales. **La enmienda de spec `trato` y los
términos *marcador del destinatario* y *trato* están firmados con el plan 8 y no han entrado**:
ni la spec, ni el esquema, ni `docs/definitions.md` los tienen. Y P-19 **sigue abierto** hasta
repetir la sonda con la cuenta de la corrida y ver salir el nombre.

---

### T-27 · Continuista ‖ Crítico: **en paralelo dentro del techo, y en serie si no cabe**

| | |
| --- | --- |
| **Opciones** | (a) En serie, como estaba. (b) En paralelo, reservando turno por la sobrecarga de **33.000–49.000 tokens** por llamada que citaba el relevo. (c) **Medir la sobrecarga primero**, y en paralelo con retirada a serie |
| **Criterio** | El techo concurrente del encargo §7 se cuenta en tokens (T-8); **qué cuenta una llamada** tiene que ser una cifra medida, no heredada |
| **Elección** | (c): `092e319` mide, `92d2da7` paraleliza |
| **Coste** | Una novela más rápida a cambio de que el orden de los *spans* deje de ser secuencial |

**La medida decidió.** Había dos cifras que diferían en un orden de magnitud: ~1.800 y
33.000–49.000. Con la segunda, dos jueces en vuelo rozan el techo y había que cambiar
`CLAUDE.md` §4.1 para decir que el techo pasaba a ser la restricción real. Medido con
`src/backend/scripts/medir_sobrecarga.py` —tres tamaños, dos rondas—: **~1.200 tokens fijos**
(1.200, 1.152, 1.002), con y sin caché. Los 33.000–49.000 **no se reproducen**; la hipótesis
más probable, no comprobada, es que se midieron cuando el CLI cargaba el `CLAUDE.md` del
repositorio en cada prompt (P-1). `SOBRECARGA_POR_LLAMADA = 2_000`, por encima del máximo y de
la medida anterior, y §4.1 no cambió.

**Cómo es seguro:** el Crítico **no usa** la salida del Continuista y **no decide** nada
(`RF-JUZ-06`); la puerta G1a sigue esperando al Continuista. El turno se pide con
`espera_maxima=0`: si no cabe, o hay alguien antes en la cola, `TiempoAgotado` significa **«en
serie, como hasta hoy»**. Así nadie espera turno reteniendo el suyo, y no hay interbloqueo con
dos obras a la vez. Un `SalidaMalFormada` del Crítico ya no tumba el intento **ni en paralelo ni
en serie**: si dependiera del camino, que el capítulo cayera dependería del hueco que tuviera el
techo en ese instante.

**Lo que sigue abierto:** la sobrecarga se midió con la **cuenta de trabajo**, que inyecta
instrucciones de organización en cada llamada; hay que remedirla con la de la corrida
(`5a6baa3`). Y el ahorro —estimado en 10–15 minutos sobre ~80–90 por novela— **no está medido**.

---

### T-28 · La evidencia de una escalada: **tabla aparte**, no dejar de borrar

| | |
| --- | --- |
| **Opciones** | (a) Dejar de borrar la `version_texto` de los intentos rechazados. (b) **Guardarlos en otra tabla, `intento_descartado`** |
| **Criterio** | Tras escalar, poder distinguir «el modelo escribió mal tres veces» de «un validador rechaza siempre», **sin romper R-7** |
| **Elección** | (b): `d3b0d88`, `7e44901`, `cda23f1`, `c8ecb22` (P-20 cerrado) |
| **Coste** | Una tabla que ningún paquete lee, y la palabra «rastro» que hay que matizar |

**Por qué no (a), que era lo directo.** `_retirar_lo_descartado` borra por **R-7**: la prosa
descartada no puede contaminar el paquete del capítulo siguiente a través de `vigente = 1`. Tres
lectores dependen de esa semántica —`contexto/service.py`, `canon/resumenes.py`,
`manuscrito/repository.py`—, y dejar de borrar habría obligado a cambiar los tres, con el riesgo
de que uno se olvidara y un intento rechazado acabara en la memoria de la novela.

**Lo que entrega:** cada intento con su texto, el código y la cita de cada bloqueante y el
término vetado, escrito **antes** de retirar lo descartado, y también cuando se aprueba tras
reparar, porque el *tuning* necesita esa misma evidencia. Se lee en `GET
/trabajos/{id}/intentos`. El capítulo escalado conserva además el juicio del Crítico, y
`causa_fallo` pasó de `String(60)` a `String(200)` porque el motivo medía ~63 y la columna
mentía.

**El test viejo «un capítulo rechazado no deja rastro» sigue verde sin tocarlo**, y es correcto:
la evidencia no es un almacén de lectura. Su docstring dice ahora por qué.

---

### T-29 · Langfuse: **un observador por proceso, el criterio en el nombre, el Entrevistador fuera**

Cuatro decisiones pequeñas, las cuatro del plan 8 T7 y D-5, y el estado de lo que corre está en
`docs/architecture.md` §9.2.1:

| Decisión | Se descartó | Por qué | Evidencia |
| --- | --- | --- | --- |
| **Un observador por proceso** y `flush` al apagar, por el blindaje | Un cliente por petición, que es lo que había | El SDK manda por lotes y en segundo plano: sin un punto donde vaciar, lo último de una corrida se pierde. Con Langfuse caído al apagar, el proceso se para igual y el fallo se cuenta | `dced524` |
| **El criterio en el nombre del *score***: `juez_con_rubrica.<criterio>` | Un solo nombre, con el criterio en el comentario | Las seis puntuaciones del juez llegaban con el mismo nombre y se mezclaban en una serie; `RF-JUZ-05` compara **por criterio** | `057eea4` |
| **La plantilla por referencia**: `prompt_id`, `prompt_version` y `prompt_hash` en los metadatos del *span* de cada rol con modelo | El gestor de prompts de Langfuse | La plantilla vive versionada en el repositorio (`CLAUDE.md` §10, T-25); lo que sube es **con cuál** se hizo cada llamada, con el hash de la que de verdad se envió | `bfb5396` |
| **El Entrevistador no tiene traza** (D-5) | Abrirle una sesión propia | La sesión se deriva de `obra_id`, que no existe mientras dura la entrevista; y no aporta al *tuning* | plan 8, D-5 |

**Lo que cuesta, sin suavizar:** `CLAUDE.md` §4.3 dice que la sesión de una novela **abarca la
entrevista**, y hoy no la abarca: es un incumplimiento declarado, no un olvido. Y **nada de esto
se ha visto contra un Langfuse real**: los tres cierres están probados contra un cliente falso que
imita la forma del SDK v3. La primera corrida es la que lo confirma.

---

### T-30 · La apariencia de la lectura: **«Cuaderno de viaje», siempre en claro, interfaz en serif**

| | |
| --- | --- |
| **Opciones** | Cuatro direcciones exploradas en un lienzo de diseño —**Imprenta, Fichero, Tela y oro, Cuaderno de viaje**— después de implementar una primera (papel frío, ciruela, Atkinson) |
| **Criterio** | Revisión visual de `maujimenez4`, que es **U** y no la juzga ningún test. El contraste AA en los tres temas **sí es test**, y gana a la estética |
| **Elección** | La cuarta (`d5207bd`, enmienda 1 del plan 4; `dbf2bda` … `00cf126`). Plan 4 `completado` con la revisión visual (`1b1cb45`) |

**Dos decisiones del mismo plan se invirtieron el mismo día, y conviene decir qué se pierde:**

1. **La interfaz pasa a serif (Spectral)**, igual que la prosa. El plan 4 había separado la voz
   de la interfaz —Atkinson Hyperlegible Next— de la del libro, precisamente porque «la
   interfaz y el libro hablan con la misma voz, y el libro pierde protagonismo». En el cuaderno
   una sans rompía el conjunto. Lo que distingue ahora las dos voces es el tamaño, la cursiva de
   las leyendas y los títulos en Sorts Mill Goudy; **el problema que motivó la separación vuelve
   a estar ahí**, amortiguado.
2. **Siempre en claro** (`cd2f38c`). El plan 4 seguía la preferencia del sistema; vista la
   dirección en un sistema en modo oscuro, `maujimenez4` decidió *«solo que usa el modo claro»*.
   Sin elegir, el tema es Papel; Noche y Sepia solo si se eligen en «Aa», y «Automático»
   desaparece. **Lo que se pierde es el motivo por el que Noche existía:** de noche, en un móvil,
   el claro deslumbra, y ahora hay que saber que se puede cambiar.

*Por qué se escribe como decisión y no como gusto:* se descartaron tres direcciones y dos
decisiones razonadas, y quien retome el frontend necesita saber que la tipografía única y el tema
fijo **fueron a propósito**, no un descuido que arreglar.

---

### T-31 · Las evals: **dos o tres novelas completas**, no cinco briefs

| | |
| --- | --- |
| **Opciones** | (a) Los cinco briefs de plan 6 T10, con la iteración de *tuning* sobre todos: **diez novelas**, unas 15 horas de reloj en serie y diez veces la cuota. (b) **Dos o tres novelas completas** |
| **Criterio** | El plazo. Una novela son **~80–90 minutos medidos**, y la novela de ejemplo sale de la misma cuota |
| **Elección** | (b). Decisión de `maujimenez4`, 2026-09-24, por tiempo |
| **Coste** | **Queda por debajo de la letra de una condición eliminatoria** |

**El coste, dicho entero porque es el más caro de este documento:** el encargo §5 pide **cinco
briefs**, con al menos uno adversarial y uno que provoque una incoherencia temporal, una tabla por
brief y una iteración de *tuning* con antes y después. Con dos o tres novelas, la tabla tiene dos
o tres filas y el antes/después se mide sobre muy poco — lo mismo que T-17 ya dice de una sola
revisión humana. Lo que la entrega tiene que decir es **qué briefs se corrieron, cuáles no y por
qué**, no dejar que se descubra.

**Lo que esta decisión todavía no ha arrastrado:** `plan-6-medir.md` sigue diciendo cinco, y
qué briefs entran no está escrito. El brief temporal, además, necesita antes su rediseño (T-5,
P-27): tal como está no fallaría donde el plan dice.

---

### T-32 · La petición de cambio (`CA-25`): **obligatoria, y la última**

| | |
| --- | --- |
| **Opciones** | (a) Recortarla si aprieta el plazo, que es lo que la hoja de ruta dejaba abierto. (b) Hacerla antes de la corrida real. (c) **Obligatoria, y programada al final** |
| **Criterio** | El encargo §2 la exige para la lectura web, y `CA-25` es uno de los cinco criterios que deciden si el sistema existe. Pero **sin una novela real no hay nada que regenerar**, y cada regeneración cuesta un capítulo por capítulo afectado |
| **Elección** | (c), 2026-09-24. Backend `plan-5-peticion.md` y frontend `plan-2-ficha.md` T4–T7, aprobados y sin empezar; no comparten fichero |
| **Coste** | Lo último es lo que se queda sin tiempo. Si pasa, la entrega **incumple §2**, y eso ya no se podrá presentar como un recorte decidido |

**Por qué no (a):** la petición es lo único que distingue la lectura web del PDF (spec 002,
Alcance). Recortarla deja una web que es un PDF con pestañas. **Por qué no (b):** se probaría
contra novelas de los dobles, y la primera corrida real ya enseñó que los dobles no ven lo que
ve el modelo (`26efa68`). El plan 5 paga además tres deudas que vencen al regenerar —P-6, P-7 y
P-8— y reabre `CA-33`.

---

### T-33 · El `.env` **no se carga solo**: se lanza con un script fuera del repositorio

| | |
| --- | --- |
| **Opciones** | (a) `python-dotenv`, para que el backend lea el `.env` al arrancar. (b) **No cargarlo**: las variables tienen que estar en el entorno del proceso que lanza `uvicorn` |
| **Criterio** | Una dependencia nueva **se pregunta** (`CLAUDE.md` §3, punto 7); las catorce de P-01 se aprobaron en bloque y esta no está entre ellas. El plan 8 la dejó fuera por eso, explícitamente |
| **Elección** | (b). Hoy se lanza con un script **fuera del repositorio** que exporta las variables del `.env`, entre ellas las claves de Langfuse, que no entran al repositorio (`CLAUDE.md` §16) |
| **Coste** | Un clon limpio con su `.env` relleno arranca **sin medir nada** y solo lo dice un aviso. Y el arranque real no es reproducible desde el repositorio |

**Lo que lo mitiga:** `.env.example` lo dice en su última línea —«el backend NO carga este
fichero por sí solo»— y, con alguna de las tres variables de Langfuse vacía, el sistema arranca,
avisa y sigue con el observador nulo. No es una defensa: es que el fallo **se ve**. Cambiarlo es
una pregunta de una línea a `maujimenez4`, no una tarea.

---

## Resumen: qué está firmado y qué está construido

| Decisión | Firmada | Implementada |
| --- | --- | --- |
| T-1 roles separados y orquestador en código | Sí | **Sí**, ocho de los diez roles: faltan el Editor de línea y el Auditor de manuscrito |
| T-2 SQLite única, ledger *append-only* | Sí | **Sí**, una sola base con sus migraciones de Alembic |
| T-3 lectura web con revelado progresivo | Sí | **A medias:** una dirección, tres pestañas y revelado; faltan la petición (T-32), el enlace de la ficha al capítulo (P-24) y el PDF (`501`) |
| T-4 TLA+ / TLC en desarrollo | Sí | **Sí**, con la correspondencia por test; ningún contraejemplo real |
| T-5 dos invariantes de Lean | Sí, **repriorizados** | **Sí**: `sinUbicuidad` y `sinReaparecidos` bloquean la publicación. Faltan fechas de nacimiento (P-27) y el *feedback* a un rol (P-28) |
| T-6 Claude Agent SDK sin clave | Sí | Sí; la autenticación de la cuenta no la comprueba nadie al arrancar |
| T-7 dos contadores de tokens | Sí | Sí |
| T-8 paralelismo dentro del techo sumado | Sí | Sí, y **contando tokens, no llamadas** |
| T-9 presupuesto por capa con fallo explícito | Sí | Sí |
| T-10 Ensamblador determinista | Sí | Sí, con la salvedad de la capa de instrucción |
| T-11 recuperación híbrida | Sí | Sí, con vectorizador léxico |
| T-12 extensión vectorial opcional | Sí | Sí, con la suite en dos modos |
| T-13 ningún agente con herramientas | Sí | Sí, por ausencia |
| T-14 vetos normalizados por palabra | Sí | Sí |
| T-15 dos hooks | Sí | **Sí**, los dos en código; la lectura «hooks de Claude Code» sin razonar (P-31) |
| T-16 Haiku 4.5 en todos los roles | Sí, **invertida** el 2026-09-24 | Sí (`b80e911`); `MODELO_JUEZ` sigue separado |
| T-17 Comprador acepta, Autor calibra | Sí | **No:** las tablas existen; el servicio y las rutas no (plan 6 T9) |
| T-18 G1b no bloquea | Sí | Sí: el Crítico puntúa en producción y no bloquea (`0d0f4df`, `4f35669`) |
| T-19 cobertura bloqueante, naturalidad umbral | Sí | La cobertura sí; la naturalidad la puntúa el Crítico como criterio, sin umbral que pare nada |
| T-20 puerta mecánica sin juez | Sí | Sí |
| T-21 comprobación de forma del defecto | Sí | Sí |
| T-22 features + commons / feature-first | Sí | Sí, en los dos lados, con `lint-imports` y ESLint; `SalidaMalFormada` sigue en cinco copias (P-10) |
| T-23 capítulo fuera, escena dentro | Sí | Sí |
| T-24 varios planes por spec | Sí | Sí: ocho planes de backend y cuatro de frontend; el 3 del frontend implementado **sin firma** (P-29) |
| T-25 prompts como ficheros con hash | Sí | Sí, y el hash sube al *span* (T-29) |
| T-26 cuenta sin anonimizado, no marcador | Sí (D-1) | Sonda hecha; **falta repetirla con la cuenta de la corrida**. T2–T3 y la enmienda `trato`, firmadas y sin ejecutar |
| T-27 Continuista ‖ Crítico dentro del techo | Sí | Sí (`92d2da7`); sobrecarga por remedir con la cuenta de la corrida |
| T-28 evidencia de la escalada en tabla aparte | Sí | Sí (`d3b0d88`, `7e44901`, `cda23f1`, `c8ecb22`) |
| T-29 Langfuse: observador único, criterio, plantilla | Sí | Sí contra un cliente falso; **nunca visto contra un Langfuse real**; el Entrevistador sin traza |
| T-30 «Cuaderno de viaje», claro, serif | Sí | Sí; plan 4 del frontend `completado` |
| T-31 evals con dos o tres novelas | Sí | **No:** no existe `evals/`, y `plan-6-medir.md` sigue diciendo cinco |
| T-32 petición de cambio, obligatoria y última | Sí | **No:** plan 5 y plan 2 T4–T7 sin empezar |
| T-33 `.env` sin cargar | Sí | Sí, por ausencia |
