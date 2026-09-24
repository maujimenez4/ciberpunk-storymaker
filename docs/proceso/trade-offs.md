# Trade-offs — cada decisión relevante, como decisión

**Qué es este documento.** Las decisiones de diseño del proyecto escritas con la forma que
pide el encargo: **opciones, criterio y elección**, más lo que cada una cuesta. No es un
catálogo de aciertos: tres de ellas invierten una decisión anterior que estaba razonada, y en
esos casos se escribe por qué dejó de valer el motivo original (`CLAUDE.md` §3.3).

**De dónde sale cada una.** P-01 a P-08 son de `specs/001-backend-v1/spec.md`; D-01 a D-05 y
las tres «decisiones de la 002» son de `specs/002-frontend/spec.md`; P-A a P-C son de
`specs/001-backend-v1/plan-2-capitulo.md`; las numeradas 1 a 20 son la tabla de
`docs/architecture.md` §12. Se citan con su identificador para que cualquiera pueda ir a
leer el original.

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

**Y una cosa que la refuerza de verdad:** P-02 separa los modelos —Haiku 4.5 escribe, Opus 5
juzga—, lo que rompe la correlación por modelo. No por proveedor.

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
decisión de `maujimenez4`. Dentro de esa elección hay cuatro decisiones de producto, todas
con su alternativa descartada:

| | Decisión | Se descartó | Criterio |
| --- | --- | --- | --- |
| **D-01** | **Un solo enlace: quien lee puede pedir el cambio** | Dos enlaces con capacidades distintas | El encargo §2 dice literalmente que «**el lector** puede seleccionar un fragmento o un hecho y pedir un cambio desde la propia página». Restringirlo al Comprador era una desviación del texto, no una lectura de él |
| **D-02** | **La petición se hace desde la ficha**, no seleccionando prosa | Selección de texto libre | Cada entrada de la ficha **ya es un hecho de canon con su identificador**. Mapear prosa a canon con búsqueda difusa significa que, si acierta el hecho equivocado, **se regeneran los capítulos equivocados** y quien lee no tiene forma de saberlo |
| **D-03** | **Distintivo en el índice y página de novedades** | Resaltar las diferencias dentro del capítulo | Un capítulo regenerado **se reescribe entero**: el resaltado sería casi todo el texto. Ruido, no información |
| **D-04** | **La ficha se revela al avanzar** | Enseñar el canon entero, que es lo que el encargo pide literalmente | En una novela de diez capítulos que se lee de una sentada, la ficha completa **es un índice de spoilers**. Se cumple el requisito —la ficha existe y enlaza al capítulo— sin cumplirlo de la forma que estropea el producto |
| **D-05** | **Mientras se regenera, la lectura se detiene y se muestra el progreso** | Seguir leyendo la vigente con un aviso | Que nadie lea un capítulo que está a punto de cambiar |

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
| **Estado** | **No existe ningún `.tla`.** Es la Fase 7 |

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
   descrita en `architecture.md` §3.9 **y el `.tla` se escribirá contra ella**.
2. La máquina del **capítulo** ya está en código y cerrada: `features/escritura/maquina.py`,
   con tabla de transiciones explícita y 64 tests. Quien escriba el `.tla` no parte de una
   pizarra.
3. `RF-FOR-07` exige que el README empareje **cada acción de la especificación con el estado
   o transición del código** que la implementa.

**El riesgo que esta decisión abre, y está declarado sin suavizar:** que la especificación
deje de corresponder al código. Es una **inspección** que nadie repite cuando el orquestador
cambia, y `verification.md` §7 la marca **Descubierta**. Una especificación verde sobre un
código que ya no implementa esa máquina **no es cobertura ausente, es cobertura falsa**:
afirma la seguridad de otro sistema.

---

### T-5 · Invariantes de Lean priorizados: **las dos que el encargo nombra primero**

El encargo §5c ofrece cuatro candidatas y pide «al menos dos». La elección:

| Invariante | Prioridad | Por qué |
| --- | --- | --- |
| Los eventos respetan el **orden temporal declarado** | **Entra** | Es la propiedad del conjunto por excelencia: no es comprobable sobre un capítulo, hay que mirar **todos** los pares de eventos |
| La **edad** de un personaje concuerda con su **fecha de nacimiento** | **Entra** | `RF-FOR-02` la nombra, es la regla de dominio 13, y el dato ya está en el esquema |
| Nadie está en **dos lugares** en el mismo momento | **Entra como caso de prueba**, vía `CA-21` | Es la cronología imposible con la que se demuestra que la puerta bloquea de verdad |
| Nadie aparece **después de un evento que lo excluye** | Aplazada | Exige modelar la exclusión —muerte, partida definitiva— y hoy el ledger no la tipifica |

**El criterio de priorización, dicho en una frase:** entran primero las invariantes cuya
**entrada ya existe**. La vista `cronologia` se deriva del ledger desde la Fase 2 con
eventos, momento, lugar y presentes, que es exactamente lo que §5c pide como entrada del
fichero Lean. Una invariante que necesita una columna nueva se paga dos veces.

**Y lo que Lean no ve, que conviene no olvidar al leer un `lake build` en verde:** demuestra
sobre el **fichero generado desde la biblia**, no sobre la prosa. Si el capítulo dice algo
que nunca llegó a la biblia, Lean no lo ve. Verifica el modelo de la historia, no la
historia.

**Estado: no existe.** Lean 4 está aprobado en bloque por P-01 y **sin instalar**. `CA-21`
—uno de los cinco criterios que deciden si el sistema existe— sigue abierto.

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

**Lo que se descubrió después de firmarla, y hoy son problemas abiertos:**

1. El SDK **no habla HTTP: lanza el binario `claude`**, que `pyproject.toml` no declara y
   ninguna puerta comprueba. Sin él la corrida real falla **y la suite sigue verde**.
2. «Ya autenticado» **no está definido fuera de la máquina del autor**.
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
son **obras distintas**, el **Continuista con el Crítico** sobre el mismo capítulo y los
cinco briefs de evaluación. Sobre una novela sola, el paralelismo **le quita una espera de
validación por capítulo** — diez en total. Quien espere que una novela salga en la mitad de
tiempo se va a llevar una sorpresa.

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

**Estado honesto:** existe `HOOK_DE_CAPITULO` y existe `PUERTA_G4`; **el hook de policy no**.
El registro de auditoría está; las decisiones del motor de policy, no.

---

## Las decisiones sobre la calidad y quién la juzga

### T-16 · P-02 · Anthropic por consumo de cuenta, **Haiku escribe y Opus juzga**

| | |
| --- | --- |
| **Opciones** | (a) Un solo modelo para todo. (b) **Modelo barato para el volumen, modelo caro para el juicio** |
| **Criterio** | Un juez que comparte modelo con quien escribió **tiende a aprobar su propio estilo** |
| **Elección** | (b). Cuesta poco: el juez corre una o dos veces por capítulo y el escritor muchas más |

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

## Resumen: qué está firmado y qué está construido

| Decisión | Firmada | Implementada |
| --- | --- | --- |
| T-1 roles separados y orquestador en código | Sí | **Sí**, seis de los diez roles |
| T-2 SQLite única, ledger *append-only* | Sí | **Sí**: 21 tablas, 2 vistas, 3 disparadores |
| T-3 lectura web con revelado progresivo | Sí | **No.** `src/frontend/` no existe |
| T-4 TLA+ / TLC en desarrollo | Sí | **No.** No hay `.tla` |
| T-5 dos invariantes de Lean | Sí | **No.** Lean sin instalar |
| T-6 Claude Agent SDK sin clave | Sí | Sí, con tres deudas abiertas |
| T-7 dos contadores de tokens | Sí | Sí |
| T-8 paralelismo dentro del techo sumado | Sí | Sí, y **contando tokens, no llamadas** |
| T-9 presupuesto por capa con fallo explícito | Sí | Sí |
| T-10 Ensamblador determinista | Sí | Sí, con la salvedad de la capa de instrucción |
| T-11 recuperación híbrida | Sí | Sí, con vectorizador léxico |
| T-12 extensión vectorial opcional | Sí | Sí, con la suite en dos modos |
| T-13 ningún agente con herramientas | Sí | Sí, por ausencia |
| T-14 vetos normalizados por palabra | Sí | Sí |
| T-15 dos hooks | Sí | **A medias:** falta el de policy |
| T-16 Haiku escribe, Opus juzga | Sí | La capacidad está; **el Crítico no existe** |
| T-17 Comprador acepta, Autor calibra | Sí | **No** |
| T-18 G1b no bloquea | Sí | Trivialmente: el juez no existe |
| T-19 cobertura bloqueante, naturalidad umbral | Sí | La cobertura sí; la naturalidad no |
| T-20 puerta mecánica sin juez | Sí | Sí |
| T-21 comprobación de forma del defecto | Sí | Sí |
| T-22 features + commons / feature-first | Sí | Backend sí; frontend no |
| T-23 capítulo fuera, escena dentro | Sí | Sí |
| T-24 varios planes por spec | Sí | Sí: tres planes de backend **completados** |
| T-25 prompts como ficheros con hash | Sí | Sí |
