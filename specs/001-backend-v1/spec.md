---
id: 001-backend-v1
titulo: Backend, versión 1 — de la entrevista a la novela publicada
estado: en-revision       # borrador | en-revision | aprobada | implementada
aprobada_por:             # necesita firma nueva: ver Cierre
fecha: 2026-09-23
---

# 001-backend-v1 — Backend, versión 1

Qué tiene que hacer el backend para que una persona encargue una novela personalizada y otra la reciba, y cómo se sabrá que lo hace. **Aquí no se decide cómo se implementa:** eso es el plan, y no se escribe hasta que esta spec esté `aprobada`.

> **Esta spec reemplaza a la aprobada el 2026-09-22, y por eso vuelve a `borrador`.**
>
> Aquella cubría *el ciclo completo de una escena* para una novela larga de 80.000–120.000 palabras. El producto es otro: diez capítulos personalizados para una persona concreta, con entrevista, guardarraíles, observabilidad, verificación formal y publicación. Casi nada de su alcance sobrevive intacto.
>
> **Mantenerla en `aprobada` con este contenido sería afirmar que alguien firmó algo que no leyó.** La firma anterior valía para aquel alcance; este necesita otra.

Es una spec única y grande a propósito: cubre **el backend entero**. Las piezas no se pueden entregar por separado —un ensamblador sin orquestador no se prueba, un orquestador sin memoria no cierra el bucle, y una publicación sin validadores no es una publicación— y trocearlas habría multiplicado las puertas de `CLAUDE.md` §3 sin añadir información.

---

## Problema

**Una novela personalizada se rompe por dos sitios a la vez, y ninguno de los dos se ve mirando un capítulo suelto.**

**Por la coherencia.** La novela terminada no cabe en una llamada, y meterla entera empeora el resultado (`domain-knowledge.md` §1 y §10). Se escribe por partes, y cada parte por separado parece correcta: el capítulo siete no sabe que el cuatro dijo otra cosa. A diez capítulos esto **no se afloja, se aprieta**: el lector se la lee de una sentada y compara sin esfuerzo.

**Por la personalización.** El destinatario existe, conoce de primera mano la mitad de los hechos y **detecta errores que ningún editor podría detectar**. Si el perro se llama Luna en el capítulo siete, no lo lee como un descuido: lo lee como que el regalo no era para él.

Lo sufren tres personas distintas: el **comprador**, que encarga y no sabe si lo que pidió llegó al texto; el **destinatario**, que recibe; y el **Autor**, que no puede responder por qué una novela salió como salió.

Y hoy no hay nada que lo evite: `src/backend/` está vacío. Cinco documentos de contexto, un encargo, y ni una línea de código contra ellos.

---

## Alcance

**El backend entero.** Todo lo que no sea la interfaz de lectura.

| Capacidad | Encargo | Motivo |
| --- | --- | --- |
| Entrevista: datos del destinatario, vetos, texto libre no confiable, brief validado | §1 | Es la mitad del producto y hoy no existe |
| Detección de datos que faltan y de al menos un tipo de contradicción | §1 | Una contradicción del brief no se arregla escribiendo mejor |
| Ciclo de capítulo: planificar, ensamblar, escribir, validar, reparar, integrar | §3 | Es el motor |
| Presupuesto por capa, **los dos techos de 100.000 tokens** y límite de llamadas en vuelo | §7 | Restricción no negociable, y el techo **concurrente** es literal del encargo (`CLAUDE.md` §4.1) |
| Orquestador con estado persistido y **checkpoint por capítulo** | §4 | Sin él, una caída pierde la novela |
| *Story bible* en SQLite: canon con **uso por capítulos**, ledger, cronología, resúmenes | §4 | Cierra el bucle entre capítulos, y es la entrada de Lean |
| Guardarraíles: vetos en tres ámbitos con normalización, y registro de auditoría | §7 | Se aplican en código, antes de aceptar el capítulo |
| Validadores programáticos, con nombre y punto de ejecución | §5a | Son los que se cuentan |
| Juez con rúbrica, **revisión del Autor** con la misma rúbrica y **aceptación del comprador** | §5b | Sin la revisión con rúbrica, el juez emite números que nadie contrastó; sin la aceptación, nadie decide si se entrega |
| Verificación formal: **Lean** sobre la cronología, **TLA+** sobre el harness | §5c, §5d | Dos sujetos distintos (`architecture.md` §9.3) |
| Observabilidad en Langfuse: sesión por novela, spans, *scores*, plantillas versionadas | §6 | Sin ella no hay *tuning* documentable |
| Publicación: `VersionPublicada` inmutable, conservando la anterior | §2 | La interfaz es de la 002; el concepto es de aquí |
| Petición de cambio del lector y regeneración acotada | §2 | Ídem: el flujo es backend |
| API que la 002 consume | §2 | Es su contrato |

---

## Fuera de alcance

| Excluido | Motivo | Dónde |
| --- | --- | --- |
| La interfaz de lectura: portada, índice, ficha, petición desde la página | Es otra feature y otra capa | `specs/002-frontend/` |
| Servidor MCP de consulta | Opcional del encargo; requiere la API cerrada antes | Después |
| Login y multiusuario | Opcional, y las cuentas están fuera del encargo | — |
| *Linters* de prosa más allá de los obligatorios | Opcional | — |
| Edición manual del texto con *linter* en vivo | Opcional, y exige la lectura web | — |
| Despliegue en producción, pagos, ilustraciones, audio | Fuera del encargo por escrito | — |
| El **filtro estructural** de la recuperación híbrida | **No está excluido: se implementa aquí** (RF-CTX-04). Se nombra porque en la versión anterior de esta spec quedó como deuda declarada con un requisito que decía estar probado, y no debe repetirse | — |

---

## Restricciones de diseño

**El stack es fijo y no lo decide esta spec.** Se escribe aquí porque un requisito que lo contradiga es un requisito mal escrito, no una alternativa a considerar.

| Restricción | Origen | Dónde se detalla |
| --- | --- | --- |
| **FastAPI** (Python 3.12+), Pydantic v2 | **Nuestro**, presupuesto por el encargo, que lo nombra una vez en una sección opcional | `CLAUDE.md` §4 |
| **SQLite**, un fichero por obra, sin segunda base de datos | **Encargo §4, literal:** «story bible en SQLite (obligatorio)» | `CLAUDE.md` §4.2 · RD-01 |
| **React 19 + TypeScript + Vite** en el frontend | **Nuestro.** El encargo §2 dice «web o PDF» y no nombra tecnología | `CLAUDE.md` §5.2 · es de la 002 |
| **Techo de 100.000 tokens por llamada** | **Nuestro**, derivado del presupuesto por capas | `CLAUDE.md` §4.1 · RF-CTX-02, RF-CTX-03 |
| **Techo de 100.000 tokens concurrentes** —el **presupuesto concurrente**: la suma de lo que está en vuelo— | **Encargo §7, literal** | `architecture.md` §2.2 · RF-ORQ-10 |
| **Anthropic** por consumo de cuenta, **sin clave de API**. Haiku 4.5 escribe; **Opus 5 juzga** | **Nuestro** (P-02) | `CLAUDE.md` §4 · RF-OBS-03 |

**Los dos techos no son el mismo, y hasta hoy los docs los confundían.** Decían que el de 100.000 era «por llamada» y «el único techo de tokens». El encargo §7 dice «concurrentes», que es una **suma**. Mientras la concurrencia fue 1 los dos números coincidían y el sistema cumplía **por consecuencia, no por regla**. Con el paralelismo admitido (P-06), dejan de coincidir: **RF-ORQ-10 es desde el primer día el único requisito que comprueba lo que el encargo pide.**

React es del frontend y esta spec no lo implementa; se lista porque **fija el contrato**: el OpenAPI de RI-13 es lo que la 002 consume, y se genera para un cliente TypeScript.

---

## Requisitos

| Prefijo | Tipo | | Marca | Significado |
| --- | --- | --- | --- | --- |
| `CU-` | Caso de uso | | `M` | Imprescindible: si falta, no se cumple un criterio |
| `RI-` | Interfaz externa | | `S` | Necesario pero degradable |
| `RF-` | Funcional | | **T/A/I/D/U** | Prueba / Análisis / Inspección / Demostración / No verificable (`verification.md` §4) |
| `RD-` | Datos | | | |
| `RNF-` | No funcional | | | |

**125 requisitos en total:** 14 interfaces, 99 funcionales, 6 de datos y 6 no funcionales. Se desglosa porque «123» a secas obliga a contar a mano para saber si incluye las interfaces, y un número que hay que recontar caduca en silencio.

**Todo requisito cita su origen.** Uno sin origen es una invención y se rechaza en revisión. **Una letra por requisito:** la del método que lo **establece**; un segundo método que lo refuerza va entre paréntesis.

### Casos de uso

**CU-01 · Encargar una novela.** *Precondición:* ninguna. *Flujo:* el comprador responde la entrevista y puede pegar texto libre → el Entrevistador extrae hechos, detecta lo que falta y lo que se contradice → cuando no falta nada y nada se contradice, se valida el brief con esquema y se crea la obra. *Postcondición:* existe una `Obra` con su `Destinatario`, sus vetos y sus elementos obligatorios. *Excepción:* falta un dato o hay contradicción → **se vuelve a preguntar; no se escribe nada**. → RI-01, RI-02, RI-03, RF-ENT-01 a RF-ENT-08.

**CU-02 · Planificar la obra.** *Precondición:* brief válido. *Flujo:* se produce biblia y outline de diez capítulos, y cada beat obligatorio de género se asigna a exactamente un capítulo. *Postcondición:* cada capítulo tiene POV, lugar, objetivo, obstáculo y giro previsto. → RI-04, RF-PLA-01, RF-PLA-02, RF-PLA-03, RF-PLA-04.

**CU-03 · Escribir un capítulo** *(caso central)*. *Precondición:* el capítulo existe en el outline y el anterior está integrado.

*Flujo principal:* `PLANIFICANDO` → `ENSAMBLANDO` (paquete presupuestado y recortado) → `ESCRIBIENDO` → `VALIDANDO` (mecánicos, guardarraíles y juez) → `EXTRAYENDO` (canon, ledger, resumen, hilos y **uso por capítulo**, en una transacción) → `INTEGRADA`, con **checkpoint**.

*Flujos alternativos:*
- Defecto bloqueante → `REPARANDO` con el defecto y su cita → vuelve a `ESCRIBIENDO`. **Máximo dos veces**; después `ESCALADA`.
- Palabra vetada → vuelve al escritor con el término concreto, con el mismo límite. Agotado, **la generación se detiene y se informa**.
- El paquete no cabe tras recortar → `FALLIDA` con `ContextBudgetExceeded`, **sin llamar al modelo**.
- Sin turno antes del *timeout* → `FALLIDA` con `TiempoAgotado`, sin coste. **Se espera turno igual si la llamada cabe pero la suma en vuelo no**: el techo concurrente se cumple esperando, nunca recortando.

*Postcondición de éxito:* el capítulo está en el manuscrito y la memoria lo incluye. *Postcondición de fracaso:* **la memoria de largo plazo no ha cambiado.** → RF-ORQ-01 a RF-ORQ-09, RF-CTX-01 a RF-CTX-09, RF-ESC-01, RF-ESC-02, RF-ESC-03, RF-VAL-01 a RF-VAL-08, RF-GUA-01 a RF-GUA-07, RF-MEM-01 a RF-MEM-08.

**CU-04 · Reanudar tras una caída.** *Precondición:* el proceso se detiene con capítulos pendientes. *Flujo:* al arrancar se lee el último capítulo completado y se sigue desde ahí. *Postcondición:* **ni se duplica ni se pierde ningún capítulo.** → RF-ORQ-05, RF-ORQ-06, RF-ORQ-07.

**CU-05 · Publicar.** *Precondición:* los diez capítulos integrados. *Flujo:* se verifica la cronología con Lean → se comprueba que ningún capítulo quedó fuera de su puerta → se fijan los textos, se deriva la ficha y se guarda el cuadro de defectos. *Postcondición:* existe una `VersionPublicada` inmutable. *Excepción:* Lean falla o un capítulo no pasó su puerta → **no se publica**, y el fallo vuelve al editor. → RI-08, RF-PUB-01 a RF-PUB-08, RF-FOR-01, RF-FOR-02, RF-FOR-03.

**CU-06 · Atender una petición del lector.** *Precondición:* existe una versión publicada. *Flujo:* se registra la petición sobre un hecho → se determinan los capítulos que lo usan → se corrige el canon **sin editarlo** → se regeneran esos capítulos → se revalida sobre los posteriores al origen del hecho sustituido → se compara con el cuadro guardado → si no hay defecto **introducido**, se publica una versión nueva. *Postcondición de fracaso:* la vigente no cambia y **la petición se conserva con su resultado**. → RI-09, RI-10, RF-PET-01 a RF-PET-08.

**CU-07 · Auditar qué se envió al modelo.** *Precondición:* una fila de `ejecucion`. *Flujo:* se leen los identificadores de lo que entró en el paquete. *Postcondición:* se sabe **qué hechos de canon** se enviaron, no solo qué memoria se recuperó. → RI-07, RF-CTX-08, RF-CTX-09, RF-OBS-06.

**CU-08 · Evaluar el sistema.** *Precondición:* el ciclo completo funciona. *Flujo:* se corren cinco briefs de prueba —uno adversarial, uno con trampa temporal— y se recoge por brief qué validadores pasaron y cuáles fallaron. *Postcondición:* existe la tabla y una iteración de *tuning* con resultados antes y después. → RF-EVA-01, RF-EVA-02, RF-EVA-03, RF-EVA-04.

### Interfaces externas

| ID | Interfaz | Pr. | Verif. |
| --- | --- | --- | --- |
| RI-01 | `POST /entrevistas` — abre una entrevista | M | Test |
| RI-02 | `POST /entrevistas/{id}/respuestas` — aporta datos o texto libre; devuelve **faltantes y contradicciones** | M | Test |
| RI-03 | `POST /entrevistas/{id}/cerrar` — valida el brief con esquema y crea la obra | M | Test |
| RI-04 | `POST /obras/{id}/outline` — biblia y outline de diez capítulos | M | Test |
| RI-05 | `POST /capitulos/{id}/escribir` — lanza el ciclo | M | Test |
| RI-06 | `GET /trabajos/{id}` — estado del trabajo, **legible por capítulo** | M | Test |
| RI-07 | `GET /capitulos/{id}/contexto` — paquete y desglose de tokens (depuración) | S | Test |
| RI-08 | `POST /obras/{id}/publicar` | M | Test |
| RI-09 | `POST /obras/{id}/peticiones` — petición de cambio del lector | M | Test |
| RI-10 | `POST /obras/{id}/versiones/{v}/revertir` | M | Test |
| RI-11 | `GET /obras/{id}/versiones`, `…/{v}`, `…/{v}/ficha`, `…/{v}/pdf` — lo que consume la 002 | M | Test |
| RI-12 | `GET /obras/{id}/canon` — consulta del grafo | S | Test |
| RI-13 | Todo aparece en el **OpenAPI** con sus modelos: es el contrato del que la 002 genera su cliente | M | Análisis (+Test) |
| RI-14 | El cliente de modelo, el contador de tokens y el reloj se **inyectan**: ninguna prueba llama al proveedor | M | Análisis (+Test) |

### Funcionales — entrevista y configuración (§1)

**Nada se escribe hasta que el brief está completo y no se contradice.** Estos ocho requisitos son esa puerta.

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-ENT-01 | La entrevista recoge del destinatario nombre, edad, rasgos y recuerdos; y de la obra género, tono y extensión | M | Test |
| RF-ENT-02 | Recoge **las palabras y temas que el comprador no quiere que aparezcan**, que pasan al ámbito `brief` de los vetos | M | Test |
| RF-ENT-03 | Detecta **qué datos obligatorios faltan** y los devuelve nombrados, no como un error genérico | M | Test |
| RF-ENT-04 | Detecta **al menos un tipo de contradicción** —por ejemplo edad contra tono, o contra género— y la devuelve explicada. **El esquema no la ve**: un brief puede ser válido y contradictorio a la vez | M | Test |
| RF-ENT-05 | El texto libre se guarda como `TextoAportado` y **se trata como contenido no confiable**: entra marcado como dato y **nunca se concatena a un prompt sin esa marca** | M | Análisis (+Test) |
| RF-ENT-06 | De ese texto se extraen hechos, que entran al canon con `origen: brief` y **sin escena de origen** | M | Test |
| RF-ENT-07 | El brief **se valida con esquema** antes de persistirse. Un brief que no valida no crea obra | M | Test |
| RF-ENT-08 | El brief declara sus **elementos obligatorios**: los datos que deben aparecer en el texto | M | Test |

### Funcionales — planificación

**Los diez capítulos existen antes de escribir el primero, y cada beat de género tiene dueño.**

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-PLA-01 | Se produce una biblia versionada a partir del brief | M | Test |
| RF-PLA-02 | El outline tiene **diez capítulos**, cada uno con una escena (`definitions.md` §10) | M | Test |
| RF-PLA-03 | Cada beat obligatorio de género se asigna a **exactamente un** capítulo. Uno sin asignar o duplicado es error de dominio | M | Test |
| RF-PLA-04 | Cada capítulo lleva POV, lugar, objetivo, obstáculo y giro de valor previsto | M | Test |

### Funcionales — contexto (§7 del encargo, §4.1 de `CLAUDE.md`)

**Nunca se llama al modelo sin haber contado, y lo que no cabe falla en vez de truncarse en silencio.**

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-CTX-01 | El paquete se ensambla por **código determinista**, nunca por un modelo | M | Análisis |
| RF-CTX-02 | **Nunca se llama al modelo sin haber contado los tokens.** El contador es inyectado, no una estimación por caracteres | M | Test |
| RF-CTX-03 | Cada capa respeta su tope; si una se pasa se recorta **esa**, no las demás. Si tras recortar no cabe, `ContextBudgetExceeded` **sin llamar** | M | Test |
| RF-CTX-04 | Recuperación híbrida **en este orden**: filtro estructural —presentes, lugar, hilos abiertos, rango de capítulos— → orden semántico sobre lo ya filtrado → fusión con recencia. **El filtro estructural existe y filtra**, no solo pone un tope | M | Test |
| RF-CTX-05 | El ensamblador devuelve el desglose por capa junto al paquete, y se persiste | M | Test |
| RF-CTX-06 | Una capa vacía cuando debería tener contenido **falla antes de llamar**: es un fallo del almacén, no del escritor | M | Test |
| RF-CTX-07 | Las capas constitucional e instrucción **nunca se recortan** | M | Análisis (+Test) |
| RF-CTX-08 | La capa de canon etiqueta cada pieza por **`hc_id`**, no por posición: la posición cambia con el recorte y el identificador no | M | Test |
| RF-CTX-09 | `ejecucion` persiste los identificadores de **todas** las capas que los tienen, con su capa, y **solo de las piezas que sobrevivieron al recorte** | M | Test |

### Funcionales — escritura y orquestación (§3)

**Quien decide el siguiente paso es código; quien escribe solo ve el paquete.** De ahí sale que un defecto sea atribuible.

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-ESC-01 | El Escritor **solo ve el paquete**. Nunca accede a la base de datos | M | Análisis |
| RF-ESC-02 | Cada versión de texto es **inmutable**: editar crea una nueva y marca la vigente | M | Test |
| RF-ESC-03 | El reintento lleva **el defecto concreto con su cita** en el prompt. Nunca un reintento genérico | M | Test |
| RF-ORQ-01 | El orquestador es una **máquina de estados en código**. Ningún agente decide el siguiente paso | M | Análisis |
| RF-ORQ-02 | El estado vive en SQLite, no en memoria del proceso | M | Test |
| RF-ORQ-03 | Idempotencia por `run_id`: repetir un paso no duplica escrituras | M | Test |
| RF-ORQ-04 | **Máximo dos reparaciones dirigidas** por capítulo; después `ESCALADA`. El contador **solo crece dentro del capítulo** y **avanzar al siguiente no lo consume** | M | Test |
| RF-ORQ-05 | Al integrar un capítulo se persiste **checkpoint** | M | Test |
| RF-ORQ-06 | Tras una caída se reanuda **desde el último capítulo completado** | M | Test |
| RF-ORQ-07 | La reanudación **no duplica ni pierde capítulos** | M | Test |
| RF-ORQ-08 | **Una escena en vuelo por obra.** Las llamadas de obras distintas, y las del Continuista y el Crítico sobre el mismo capítulo, **pueden solaparse**. Si no hay turno, la llamada **espera**: nunca se recorta el paquete para hacerla caber | M | Test |
| RF-ORQ-09 | La E/S de cada agente se **valida con esquema**. Un agente que devuelve algo fuera de su esquema es un fallo, no una respuesta | M | Test |
| RF-ORQ-10 | **La suma de tokens de las llamadas en vuelo no pasa de 100.000** (encargo §7). El turno se da **contando tokens, no llamadas**. Si admitir una llamada la haría pasar, esa llamada **espera**: no se recorta el paquete ni se lanza igualmente | M | Test |

### Funcionales — memoria (§4)

**Lo que un capítulo aprende llega al siguiente; lo que se rechaza no deja rastro.**

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-MEM-01 | *Story bible* en **SQLite**: canon, ledger, manuscrito, hilos | M | Test |
| RF-MEM-02 | **Cada hecho registra en qué capítulos se usa.** Lo escribe quien integra el capítulo | M | Test |
| RF-MEM-03 | Tabla de **cronología** —eventos con momento, lugar y presentes— **derivada del ledger**, no escrita a mano | M | Test |
| RF-MEM-04 | **Resumen por capítulo**, derivado del texto aprobado, que alimenta el contexto de los siguientes | M | Test |
| RF-MEM-05 | El ledger es *append-only* y `estado_en_t` es vista derivada. **Nunca se editan** | M | Análisis (+Test) |
| RF-MEM-06 | Solo el Extractor escribe memoria de largo plazo, y solo desde el paso de extracción | M | Análisis |
| RF-MEM-07 | Un capítulo rechazado **no deja rastro** en canon, ledger ni índice | M | Test |
| RF-MEM-08 | Corregir un hecho **no lo edita**: crea uno nuevo que lo sustituye y cita al anterior, e invalida los *snapshots* posteriores a su origen | M | Test |

### Funcionales — validadores (§5a)

**Cada comprobación tiene nombre y punto de ejecución declarados, y las que corren dentro de una generación emiten *score*.** Lo que no se puede nombrar no se puede contar.

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-VAL-01 | Cada validador tiene **nombre** y corre en un **punto declarado** del harness. Todo validador **que corre dentro de una generación** emite su resultado a Langfuse como *score*. **La excepción es TLC**, que corre en desarrollo y no en cada generación, como el propio encargo §6 establece. El catálogo vive en `verification.md` §8 y esta spec lo cita, no lo duplica | M | Test |
| RF-VAL-02 | El brief y la salida de cada rol **cumplen su esquema** | M | Test |
| RF-VAL-03 | El nombre del destinatario y los de los personajes aparecen **tal y como el canon los declara**: su forma canónica o una de sus **variantes declaradas** —apodos, hipocorísticos, diminutivos—. Una grafía que no es ninguna de las dos es defecto `PER-02` | M | Test |
| RF-VAL-04 | La longitud de cada capítulo está **dentro del rango declarado** | M | Test |
| RF-VAL-05 | **Cada elemento obligatorio del brief aparece en al menos un capítulo**, comprobado contra la tabla de hechos | M | Test |
| RF-VAL-06 | Los validadores de canon, continuidad y conocimiento contrastan **contra el grafo**, no a ojo | M | Test |
| RF-VAL-07 | Antes de llegar a la puerta se comprueba la **forma** de cada defecto: código de la taxonomía, cita que es subcadena en su desplazamiento, y `hecho_canon_id` existente si es `CAN-01`. Un defecto mal formado **no bloquea, no gasta reintento y se cuenta aparte** | M | Test |
| RF-VAL-08 | La validación visual abre la lectura en un navegador y comprueba que índice, ficha y portada **renderizan**; un fallo se registra como `REN-01`. **Es código conduciendo un navegador, no un agente** (`architecture.md` §3.5.1) | M | Demostración |

### Funcionales — juicio semántico (§5b)

**El juez emite números, y esos números no valen nada hasta que se miden contra una persona.** Son dos personas distintas y dos actos distintos: el **equipo** puntúa la rúbrica para calibrar, y el **comprador** acepta o rechaza el regalo.

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-JUZ-01 | Existe una `Rubrica` versionada con criterios y **anclajes descritos**: qué es un 1 y qué un máximo | M | Inspección |
| RF-JUZ-02 | Cubre continuidad, tono, calidad narrativa —arco, coherencia de personajes, ritmo— **y naturalidad de la personalización** | M | Inspección |
| RF-JUZ-03 | El juez devuelve **puntuación por criterio y justificación**. Una puntuación de juicio sin justificación **no se acepta** | M | Test |
| RF-JUZ-04 | Existe una **revisión humana de al menos una novela completa con la misma rúbrica**, criterio a criterio. La hace **el Autor**, como parte de la evaluación de §5, **no el comprador**: el encargo §5b la exige con rúbrica, y una aceptación comercial no la sustituye | M | Inspección |
| RF-JUZ-05 | Se registra la **distancia** entre el juicio automático y el humano. Es la única medida de cuánto vale el juez | M | Test |
| RF-JUZ-06 | **El juez no bloquea** mientras esa correlación no se haya medido sobre un conjunto y firmado (`architecture.md` §8.3) | M | Análisis |
| RF-JUZ-07 | **El comprador aprueba o rechaza la entrega**, y su veredicto se registra con la versión publicada. Es un booleano, es la aceptación del producto, y **no alimenta la distancia de RF-JUZ-05**: de un sí o un no no sale una distancia | M | Test |

### Funcionales — verificación formal (§5c, §5d)

**Dos herramientas sobre dos sujetos distintos:** Lean sobre la cronología de la historia, TLC sobre el harness (`architecture.md` §9.3). Solo la primera bloquea una publicación.

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-FOR-01 | De la cronología en SQLite se **genera un fichero Lean** con eventos, momento, presentes, lugar y fechas de nacimiento | M | Test |
| RF-FOR-02 | Se definen **al menos dos invariantes** en Lean, entre ellas el orden temporal y la edad contra la fecha de nacimiento | M | Test |
| RF-FOR-03 | Se ejecuta con `lake build`, **es una puerta**, y si falla **la versión no se publica**: el fallo vuelve al editor | M | Test |
| RF-FOR-04 | Se documenta **un caso real** en que Lean detecta una incoherencia que los demás no vieron, **o se justifica por qué no se encontró ninguno** | M | Demostración |
| RF-FOR-05 | Existe una especificación **TLA+ o PlusCal** de la máquina de la novela (`architecture.md` §3.9), con **tres invariantes de seguridad** y **una de liveness** | M | Análisis |
| RF-FOR-06 | Se comprueba con **TLC** sobre un modelo pequeño —cinco capítulos, dos reintentos—, con la configuración en el repositorio | M | Demostración |
| RF-FOR-07 | El README empareja **cada acción de la especificación con el estado o transición del código** que la implementa | M | Inspección |
| RF-FOR-08 | Si TLC encuentra un contraejemplo, se documenta **junto al cambio que provocó** | M | Inspección |

### Funcionales — guardarraíles (§7)

**Los vetos se aplican en código, antes de aceptar el capítulo, y cada decisión queda registrada.**

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-GUA-01 | Las listas de vetos viven en SQLite en **tres ámbitos**: global, obra y brief | M | Test |
| RF-GUA-02 | La comparación es sobre **texto normalizado**: mayúsculas, acentos, plurales y variantes simples | M | Test |
| RF-GUA-03 | Una coincidencia devuelve el capítulo al escritor **con el término concreto**, con límite de intentos. Agotado, **la generación se detiene y se informa** | M | Test |
| RF-GUA-04 | Cada coincidencia queda en el **registro de auditoría** y en Langfuse | M | Test |
| RF-GUA-05 | El registro de auditoría es *append-only* y dice **qué se permitió, qué se bloqueó y por qué** | M | Test |
| RF-GUA-06 | Edad mínima y nivel de calor se validan **en esquema**, no en el prompt | M | Test |
| RF-GUA-07 | **Dos hooks**: uno de validación de capítulo y otro de policy, fuera del bucle del modelo | M | Análisis (+Test) |

### Funcionales — observabilidad (§6)

**Una novela es una sesión, y todo lo que costó y todo lo que se juzgó cuelga de ella.**

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-OBS-01 | Cada novela es **una sesión** en Langfuse, que abarca la entrevista, la generación y **todas las regeneraciones posteriores** | M | Test |
| RF-OBS-02 | Cada uno de los **diez roles** y cada llamada a tool es un **span** con nombre identificable | M | Test |
| RF-OBS-03 | Tokens, coste y latencia visibles **por llamada, por capítulo y por novela**. El coste se **deriva de los tokens y de la tarifa declarada del modelo**, no se lee de una factura: con consumo de cuenta (P-02) no existe cargo por llamada. Es una cifra imputada, y sirve igual para comparar y para el *tuning* | M | Test |
| RF-OBS-04 | El resultado de **todos** los validadores llega como *score* asociado a su traza. **TLC no**: corre en desarrollo | M | Test |
| RF-OBS-05 | Las **plantillas** de prompt se versionan en Langfuse, de forma que el *tuning* pueda decir qué versión produjo qué resultado | M | Test |
| RF-OBS-06 | Cada ejecución guarda en `ejecucion`: plantilla con su hash, versión de biblia, IDs recuperados, modelo, semilla, tokens por capa, coste y veredicto | M | Test |
| RF-OBS-07 | Ninguna clave de proveedor se lee del repositorio ni de la base de datos: solo del entorno | M | Análisis |

### Funcionales — publicación y petición del lector (§2)

**Publicar fija, y regenerar no destruye.** El lector no paga una deuda anterior a su petición.

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-PUB-01 | Publicar **fija** los `version_texto_id` de cada capítulo; no se recalcula por vigencia al leer | M | Test |
| RF-PUB-02 | Publicar una versión **no altera** ninguna anterior | M | Test |
| RF-PUB-03 | **No se publica ningún capítulo que no haya pasado su puerta.** Un intento con un capítulo escalado falla con error de dominio | M | Test |
| RF-PUB-04 | Al publicar se guarda el **cuadro de defectos** de esa versión | M | Test |
| RF-PUB-05 | Al publicar se deriva y guarda la `FichaDeLectura`, que es **reproducible** desde el ledger. Cada entrada lleva **los capítulos en que aparece**, tomados del uso registrado del hecho (RF-MEM-02) | M | Test |
| RF-PUB-06 | Cada versión apunta a la que sucede, y los capítulos cambiados se calculan por **diferencia de texto** | M | Test |
| RF-PUB-07 | El identificador de una obra publicada **no es adivinable** | M | Test |
| RF-PUB-08 | Publicar es **atómico**: o queda la versión entera con su ficha y su cuadro, o no queda nada | M | Test |
| RF-PET-01 | La petición se registra con el hecho afectado, la versión de origen y el texto pedido | M | Test |
| RF-PET-02 | La petición **no edita** el hecho: la corrección es un hecho nuevo que sustituye | M | Test |
| RF-PET-03 | Los capítulos afectados se determinan por el **uso registrado** del hecho | M | Test |
| RF-PET-04 | Se revalida sobre los capítulos posteriores **al origen del hecho sustituido**, no a los regenerados | M | Test |
| RF-PET-05 | Cada defecto de la revalidación se clasifica en **preexistente** o **introducido**, contra el cuadro guardado | M | Test |
| RF-PET-06 | **Solo un defecto introducido impide publicar.** El lector no paga una deuda anterior a su petición | M | Test |
| RF-PET-07 | Si no se publica, la vigente no cambia, no queda rastro de la prosa descartada, y **la petición se conserva con su resultado** | M | Test |
| RF-PET-08 | Revertir devuelve la anterior a vigente y **no borra** la revertida | M | Test |

### Funcionales — evaluación (§5)

**Cinco briefs, una tabla y una iteración documentada.** Es lo que demuestra que el sistema se probó, no solo que funcionó una vez.

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-EVA-01 | Existen **cinco briefs de prueba**, uno **adversarial** —instrucciones incrustadas en el texto libre— y uno construido para **provocar una incoherencia temporal** | M | Test |
| RF-EVA-02 | Existe una **tabla** que dice, por brief, qué validadores pasaron y cuáles fallaron | M | Demostración |
| RF-EVA-03 | Se documenta **una iteración de *tuning***, con resultados antes y después y **qué versión de plantilla** produjo cada uno | M | Demostración |
| RF-EVA-04 | El brief adversarial **no altera ningún prompt**: sus instrucciones llegan como dato | M | Test |

### Datos

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RD-01 | **SQLite, un fichero por obra**, con WAL, `foreign_keys=ON` y `busy_timeout`. Sin segunda base de datos | M | Test |
| RD-02 | Migraciones con **Alembic desde el primer commit** | M | Test |
| RD-03 | Esquema para: canon con **uso por capítulos**, ledger, cronología, resúmenes, manuscrito versionado, vetos, auditoría, ejecuciones, defectos, personalización y entrega | M | Test |
| RD-04 | `Serie` contemplada **desde la migración inicial**: si existe, el canon se comparte desde el primer día (`definitions.md` §4.1) | M | Test |
| RD-05 | La `Dedicatoria` **no es una versión de texto**: no entra en el ensamblado, ni en el PDF como capítulo, ni en la lista negra de n-gramas | M | Test |
| RD-06 | Toda la prosa generada queda **fuera del repositorio** | M | Análisis |

### No funcionales

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RNF-SEG-01 | Ninguna regla de seguridad depende solo del prompt | M | Análisis |
| RNF-SEG-02 | Un brief que empuja contra la edad mínima o el nivel de calor **se rechaza en el esquema** | M | Test |
| RNF-SEG-03 | Prosa con instrucciones incrustadas **no altera el paquete del capítulo siguiente** al pasar por el Extractor | M | Test |
| RNF-FIA-01 | La suite pasa **sin red y sin credenciales**: el proveedor se sustituye por un doble determinista | M | Test |
| RNF-FIA-02 | La suite corre en **los dos modos de `VectorStore`**, con y sin la extensión | M | Test |
| RNF-REN-01 | El peor caso de revalidación —diez llamadas en serie— no se da por perdido ni por terminado | M | Test |

---

## Criterios de aceptación

**Treinta y siete criterios, y cinco deciden si el sistema existe:** CA-1 (sale una novela entera), CA-5 (sobrevive a una caída), CA-7 (el presupuesto falla antes de llamar), CA-21 (Lean detiene una publicación) y CA-25 (una petición no rompe lo que ya estaba). Los otros treinta protegen partes; estos cinco son el producto.

- [ ] **CA-1** — Se genera **una novela completa de diez capítulos** de principio a fin, desde el brief de ejemplo, con todos los capítulos integrados. *(Demostración)* → CU-01 a CU-05.
- [ ] **CA-2** — Cuando el brief tiene una contradicción o le falta un dato obligatorio, entonces **no se crea la obra** y se devuelve qué falta o qué se contradice, nombrado. *(Test)* → RF-ENT-03, RF-ENT-04, RF-ENT-07.
- [ ] **CA-3** — Cuando el texto libre contiene «ignora tus instrucciones», entonces se extraen sus hechos y **ningún prompt cambia**. *(Test)* → RF-ENT-05, RF-ENT-06, RF-EVA-04, RNF-SEG-03.
- [ ] **CA-4** — La suite pasa **sin red y sin credenciales**. *(Test)* → RNF-FIA-01, RI-14.
- [ ] **CA-5** — Se mata el proceso en cualquier estado no terminal y el trabajo **se reanuda desde el último capítulo completado, sin duplicar ni perder ninguno**. *(Test)* → RF-ORQ-02, RF-ORQ-03, RF-ORQ-05, RF-ORQ-06, RF-ORQ-07.
- [ ] **CA-6** — Toda regla de dominio de `CLAUDE.md` §8 tiene test, y **el test falla si se quita la validación**. *(Test)* → RF-GUA-06, RF-MEM-05, RF-VAL-06.
- [ ] **CA-7** — El desglose por capa **suma lo que dice** y respeta los topes; y si no cabe tras recortar, se lanza `ContextBudgetExceeded` **sin haber llamado al modelo**. Y una capa vacía cuando debería tener contenido **falla igualmente antes de llamar**. *(Test)* → RF-CTX-02, RF-CTX-03, RF-CTX-05, RF-CTX-06, RF-CTX-07.
- [ ] **CA-8** — La recuperación **filtra antes de ordenar**: con un corpus donde lo parecido y lo pertinente difieren, devuelve lo pertinente. *(Test)* → RF-CTX-04.
- [ ] **CA-9** — Un capítulo con defecto bloqueante se repara dirigidamente y **a la tercera acaba en `ESCALADA`**, no en bucle. Y **avanzar de capítulo no consume reintentos**. *(Test)* → RF-ESC-03, RF-ORQ-04.
- [ ] **CA-10** — Un capítulo rechazado **no ha dejado rastro** en canon, ledger ni índice. *(Test)* → RF-MEM-06, RF-MEM-07.
- [ ] **CA-11** — Dos capítulos de **la misma obra** nunca están en vuelo a la vez; dos de **obras distintas** sí, y el Continuista y el Crítico del mismo capítulo también. *(Test)* → RF-ORQ-08.
- [ ] **CA-12** — Desde una fila de `ejecucion`, **y con el estado de almacenes de ese capítulo**, se reconstruye el mismo paquete con el mismo desglose, y se sabe **qué hechos de canon** entraron. *(Demostración)* → RF-CTX-01, RF-CTX-08, RF-CTX-09, RF-OBS-06.
- [ ] **CA-13** — Una palabra vetada escrita **con acento distinto o en plural** se detecta igual, en los tres ámbitos. *(Test)* → RF-GUA-01, RF-GUA-02.
- [ ] **CA-14** — Agotado el límite de reescrituras por veto, **la generación se detiene y se informa**, y la coincidencia está en el registro de auditoría y en Langfuse. *(Test)* → RF-GUA-03, RF-GUA-04, RF-GUA-05, RF-GUA-07.
- [ ] **CA-15** — **Cada elemento obligatorio del brief aparece en al menos un capítulo**, comprobado contra la tabla de hechos; si falta uno, se señala cuál. *(Test)* → RF-ENT-08, RF-VAL-05, RF-MEM-02.
- [ ] **CA-16** — Una grafía que no está en el canon —«Maria» por «María»— se detecta como defecto; una **variante declarada** —«Mari» por «María», si el canon la declara— **no**. *(Test)* → RF-VAL-03.
- [ ] **CA-17** — Un defecto con **cita inventada** no bloquea, no gasta intento y **se cuenta aparte** como mal formado. *(Test)* → RF-VAL-07, RF-ORQ-09.
- [ ] **CA-18** — Cada validador emite su *score* a Langfuse, y la traza agrupa **por novela**: la entrevista, la generación y una regeneración posterior caen en la misma sesión. *(Test)* → RF-VAL-01, RF-OBS-01, RF-OBS-02, RF-OBS-03, RF-OBS-04.
- [ ] **CA-19** — Dos versiones de plantilla producen dos entradas distinguibles en Langfuse, y el *tuning* puede decir **cuál produjo qué**. *(Test)* → RF-OBS-05, RF-EVA-03.
- [ ] **CA-20** — Una puntuación del juez **sin justificación se rechaza**, y la rúbrica que usa es la misma que la de la revisión humana. *(Test)* → RF-JUZ-01, RF-JUZ-02, RF-JUZ-03, RF-JUZ-04, RF-JUZ-05, RF-JUZ-06.
- [ ] **CA-21** — `lake build` pasa sobre la cronología generada; y con una cronología **imposible a propósito** —alguien en dos sitios a la vez— **falla y la versión no se publica**. *(Test)* → RF-MEM-03, RF-FOR-01, RF-FOR-02, RF-FOR-03.
- [ ] **CA-22** — TLC pasa sobre el modelo pequeño con los tres invariantes de seguridad y el de liveness, y el README empareja cada acción con su transición. *(Demostración)* → RF-FOR-05, RF-FOR-06, RF-FOR-07, RF-FOR-08.
- [ ] **CA-23** — Cuando se intenta publicar con un capítulo escalado, **no se crea ninguna versión**. *(Test)* → RF-PUB-03, RF-PUB-08.
- [ ] **CA-24** — Publicar y después regenerar: pedir la versión antigua devuelve **el mismo texto**, y la ficha reconstruida desde el ledger **coincide con la guardada**. *(Test)* → RF-PUB-01, RF-PUB-02, RF-PUB-04, RF-PUB-05, RF-PUB-06, RF-PUB-07.
- [ ] **CA-25** — Un defecto **preexistente** no impide publicar; uno **introducido** sí, y entonces la vigente no cambia y la petición se conserva. *(Test)* → RF-PET-01, RF-PET-02, RF-PET-03, RF-PET-04, RF-PET-05, RF-PET-06, RF-PET-07, RF-PET-08, RNF-REN-01.
- [ ] **CA-26** — Los cinco briefs corren y producen la tabla de qué validador pasó y cuál falló; el de trampa temporal **lo caza Lean**. *(Demostración)* → RF-EVA-01, RF-EVA-02, RF-FOR-04.
- [ ] **CA-27** — La validación visual abre la lectura en un navegador y **registra un fallo** cuando índice, ficha o portada no renderizan. *(Demostración)* → RF-VAL-08.
- [ ] **CA-28** — `ruff`, `mypy`, `pytest`, `lint-imports` y las migraciones pasan en limpio, **en los dos modos de `VectorStore`**. *(Test)* → RD-01, RD-02, RD-03, RD-04, RNF-FIA-02, RNF-SEG-01.
- [ ] **CA-29** — Ninguna clave, prosa generada ni fragmento de manuscrito queda en el repositorio. *(Análisis)* → RD-06, RF-OBS-07.
- [ ] **CA-30** — La dedicatoria **no aparece** en el manuscrito ensamblado, ni en el PDF como capítulo, ni en `ngrama_vetado`. *(Test)* → RD-05.
- [ ] **CA-31** — Un brief que empuja contra la edad mínima o el nivel de calor **se rechaza al construirlo**, no en el prompt. *(Test)* → RNF-SEG-02.
- [ ] **CA-32** — El outline asigna cada beat obligatorio a **exactamente un** capítulo; uno duplicado o sin asignar falla. *(Test)* → RF-PLA-01, RF-PLA-02, RF-PLA-03, RF-PLA-04.
- [ ] **CA-33** — Los catorce endpoints aparecen en el OpenAPI con sus modelos, y el estado de un trabajo se lee **por capítulo**. *(Test)* → RI-01, RI-02, RI-03, RI-04, RI-05, RI-06, RI-07, RI-08, RI-09, RI-10, RI-11, RI-12, RI-13, RF-ESC-01, RF-ESC-02, RF-MEM-01, RF-MEM-04, RF-MEM-08, RF-ORQ-01.

- [ ] **CA-34** — Cuando la entrevista se completa sin faltantes ni contradicciones, entonces el brief resultante contiene **el destinatario con sus datos, los vetos del comprador y sus elementos obligatorios**, y valida contra su esquema; y la salida de cada rol valida contra el suyo. *(Test)* → RF-ENT-01, RF-ENT-02, RF-VAL-02.
- [ ] **CA-35** — Un capítulo por debajo o por encima del rango declarado **se detecta y vuelve al escritor**; uno dentro del rango pasa. *(Test)* → RF-VAL-04.
- [ ] **CA-37** — La revisión humana de una novela completa produce **puntuación por criterio**, y de ahí se **registra y se consulta la distancia** frente al juicio del modelo. Y el veredicto del comprador —aprobar o rechazar— queda asociado a su versión **sin entrar en ese cálculo**. *(Test)* → RF-JUZ-04, RF-JUZ-05, RF-JUZ-07.
- [ ] **CA-36** — Dos paquetes que suman más de 100.000 tokens **no corren a la vez**: el segundo espera, y arranca en cuanto el primero libera. Dos que suman menos **sí se solapan**. El contador de tokens en vuelo es **observable**, no implícito. *(Test)* → RF-ORQ-10.

**Sobre CA-6.** No basta con que el test pase: si se desactiva la validación y el test sigue verde, el test no comprobaba nada. Es la salvaguarda más barata contra una suite que da confianza sin darla, y sustituye a mano a los tests de mutación mientras estén aplazados (`verification.md` §2).

**Sobre CA-8.** Es el criterio que la versión anterior de esta spec **no tuvo**, y por eso el filtro estructural quedó sin implementar con un requisito que decía estar probado. Un criterio que solo comprueba el tope se cumple sin filtrar.

**Sobre CA-37, y por qué RF-JUZ-05 necesitaba criterio propio.** Su único criterio era CA-20, que comprueba que una puntuación sin justificación se rechaza y que la rúbrica es la misma — **nunca que la distancia se registre**. La palabra «distancia» aparecía en el requisito, en Decisiones y en «lo que no se verifica», y en ningún criterio. El cruce mecánico daba cero huérfanos, porque RF-JUZ-05 **sí** estaba citado por CA-20: citado no es lo mismo que comprobado, y esa diferencia no la ve ningún script. Lo encontró Nubia leyendo.

**Sobre CA-36, y sus dos mitades.** El criterio comprueba que el techo **frena** y que **deja pasar**. Solo la primera mitad es la obvia, y una implementación que no diera turno nunca la pasaría igual: un sistema que serializa todo cumple el techo y no cumple la decisión. Por eso la segunda mitad —dos paquetes pequeños **sí se solapan**— es la que de verdad distingue.

**Sobre CA-16, y por qué RF-VAL-03 no dice «exactamente».** La primera redacción exigía que los nombres aparecieran *exactamente* como en la *story bible*, y eso **prohibía por escrito que a María la llamaran Mari** — que en una novela de regalo es justo lo que uno espera encontrar. Un validador de comparación literal no distingue un error de un apodo; la diferencia tiene que estar **en el canon**, declarada, no en la astucia del validador.

---

## Reglas de dominio afectadas

Las quince de `CLAUDE.md` §8, todas. Las que esta spec **establece por primera vez**:

| Regla | Dónde se cumple |
| --- | --- |
| 4 — el hecho de `origen: brief` no tiene escena | RF-ENT-06 |
| 7 — la ejecución guarda los IDs recuperados, **de memoria y de canon** | RF-CTX-09, RF-OBS-06 |
| 11 — todo elemento obligatorio aparece en un capítulo | RF-VAL-05, CA-15 |
| 12 — ninguna palabra prohibida, comparando normalizado | RF-GUA-02, CA-13 |
| 13 — la edad concuerda con la fecha de nacimiento | RF-FOR-02, CA-21 |
| 14 — no se publica un capítulo que no pasó su puerta | RF-PUB-03, CA-23 |
| 15 — la dedicatoria no es prosa del manuscrito | RD-05, CA-30 |

---

## Impacto técnico

**Lo que cambia los plazos, antes que la tabla:** cuatro comprobaciones —cobertura de personalización, dedicatoria, inspección visual y Lean— **bloquean en G4, con la novela ya escrita**. Es su sitio correcto, porque ninguna es comprobable sobre un capítulo suelto, y es el más caro: **un fallo en G4 no cuesta un capítulo, cuesta lo que haya que rehacer.**

| Aspecto | Impacto |
| --- | --- |
| Esquema | **Toda la base de datos.** Es la migración inicial, y contempla `Serie` desde el principio |
| Presupuesto de contexto | Es el núcleo: ocho capas con tope propio y fallo explícito |
| Fronteras | Nueve features de backend (`CLAUDE.md` §5.1). **Ninguna nueva** |
| Dependencias nuevas | FastAPI, Pydantic v2, SQLAlchemy, aiosqlite, Alembic, tiktoken, NumPy, `sqlite-vec` opcional, **Langfuse**, **Lean 4**, **TLA+/TLC**, Playwright. Requieren aprobación (`CLAUDE.md` §3, punto 7) |
| **Concentración en G4** | Cobertura de personalización, dedicatoria, inspección visual y Lean **bloquean al final, con la novela ya escrita**. Es el sitio correcto —ninguno es comprobable sobre un capítulo suelto— y es el más caro: **un fallo en G4 no cuesta un capítulo, cuesta lo que haya que rehacer.** Va escrito aquí y no en el plan, porque cambia cómo se calculan los plazos |
| Coste | **El total de una novela no lo acota nada.** El techo es por llamada y la concurrencia por proceso; la suma de diez capítulos con reintentos y regeneraciones es un riesgo abierto declarado |
| `docs/` al cerrar | `verification.md` §4.1 gana las letras de todo lo que aquí se verifica; `architecture.md` §13 avanza de fase |

---

## Actores

Los tres del sistema, con el nombre que tienen en `docs/definitions.md` y **solo ese**:

| Actor | Qué hace en esta spec |
| --- | --- |
| **Comprador** | Responde la entrevista, aporta el `TextoAportado` y los vetos, y **acepta o rechaza la entrega** (RF-JUZ-07) |
| **Destinatario** | Recibe la obra. **No interviene en el backend**: sus datos entran por el Comprador, y la lectura es de la 002 |
| **Autor** | Resuelve escalados y **puntúa la rúbrica** de la revisión humana (RF-JUZ-04) |

*No se escribe ~~cliente~~ ni ~~usuario~~ por «comprador», ni ~~operador~~ o ~~el equipo~~ por «autor». `cliente` solo designa software: cliente de modelo, cliente OpenAPI.*

---

## Vocabulario

Todos los términos existen en `docs/definitions.md` v2.1. Los que esta spec usa y entraron con esa versión: `Destinatario`, `Comprador`, `Dedicatoria`, `TextoAportado`, `PalabraProhibida`, `RegistroDeAuditoria`, `VersionPublicada`, `PeticionDeCambio`, `FichaDeLectura`, `Cronologia`, `Rubrica`, `Puntuacion`, `RevisionHumana`, `ResumenDeCapitulo`.

**Dos términos entran con esta spec**, aprobados por `maujimenez4` el 2026-09-23 y escritos en `definitions.md` antes de cerrarla:

- **cuadro de defectos** — el conjunto de defectos vigentes de una `VersionPublicada`. Es contra lo que RF-PET-05 clasifica **preexistente** frente a **introducido** (P-04).
- **presupuesto concurrente** — la suma de los tokens de las llamadas en vuelo de un proceso, en un instante. **No es** el presupuesto de contexto, que es el techo de *una* llamada: aquel se comprueba al ensamblar el paquete, este al conceder el turno. Que las dos cifras sean 100.000 es **casualidad de números, no el mismo límite** — confundirlos es exactamente lo que hizo que el encargo §7 quedara sin cumplir durante meses (P-06).

---

## Decisiones

**P-05 · Quién aprueba la novela y quién calibra al juez son dos personas distintas.** Decidido por `maujimenez4`, 2026-09-23.

**El comprador aprueba o rechaza la entrega.** Eso, y no más: un veredicto, no una rúbrica puntuada. Es la respuesta correcta para un producto de regalo —quien decide si el regalo sirve es quien lo paga, no un crítico literario— y es lo único que se le puede pedir de verdad a un comprador.

**Y por eso la revisión humana del encargo §5b no la hace él.** El §5b pide, literalmente, «una revisión humana de al menos una novela completa, **con la misma rúbrica**, para comparar el juicio humano con el del LLM». De un sí o un no no sale ninguna comparación por criterio, así que si el comprador fuera el único revisor, **el encargo quedaría incumplido**. La revisión con rúbrica la hace **el Autor**, en desarrollo, junto a los cinco briefs de evaluación de §5.

| Acto | Quién | Qué produce | Para qué |
| --- | --- | --- | --- |
| Aceptación de la entrega | **Comprador** | Un booleano, asociado a su versión | Es el producto: decide si se entrega |
| Revisión con rúbrica | **Autor** | Puntuación por criterio | Es la calibración: mide la distancia con el juez |

**Qué sigue sin cerrarse:** una novela es una novela. La distancia medida sobre un solo manuscrito dice muy poco, así que RF-JUZ-06 sigue en pie — **el juez no bloquea** hasta que haya un número firmado sobre un conjunto (`architecture.md` §8.3). El encargo pide *al menos* una; nosotros no fingimos que una baste.

*Esta decisión corrige un supuesto que esta spec declaró y que resultó falso: se había asumido que el comprador puntuaría la rúbrica criterio a criterio. Se declaró como supuesto en vez de darlo por hecho, y por eso se pudo preguntar y corregir en el mismo día.*

**P-02 · Claude, por consumo de cuenta, y Haiku para generar.** Decidido por `maujimenez4`, 2026-09-23.

Proveedor **Anthropic**, y **sin clave de API**: el consumo va contra la cuenta. **Haiku 4.5** escribe y edita, que es el volumen; **Opus 5 juzga** —Crítico y Continuista—.

**Que el juez no comparta modelo con el escritor es lo que más gana aquí.** Esta spec ya declaraba como punto ciego que «la naturalidad la juzga un juez que comparte modelo con quien escribió»: un modelo tiende a aprobar su propio estilo. Separarlos lo rompe antes de que RF-JUZ-05 mida nada, y cuesta poco, porque el juez corre una o dos veces por capítulo y el escritor muchas más.

Dos consecuencias que se escriben aquí porque cambian requisitos:

- **No hay coste por llamada que leer.** El encargo §6 pide coste visible por llamada, capítulo y novela, así que RF-OBS-03 lo **deriva de los tokens y la tarifa declarada**. Es una cifra imputada, no dinero gastado; vale para comparar plantillas y para el *tuning*, que es para lo que el encargo la pide.
- **RF-OBS-07 no se relaja.** Sigue diciendo que ninguna clave se lee del repositorio ni de la base de datos. Que hoy no haya clave que leer no es motivo para retirar la regla: es motivo para que siga siendo barata.

**P-03 · La entrevista se implementa antes que el ciclo de capítulo.** Decidido por `maujimenez4`, 2026-09-23. Demuestra primero que el sistema **personaliza**, que es la mitad del producto que hoy no existe.

**P-04 · El «cuadro de defectos» entra en `definitions.md` con ese nombre.** Decidido por `maujimenez4`, 2026-09-23. Es el conjunto de defectos vigentes de una `VersionPublicada`, y es contra lo que RF-PET-05 clasifica **preexistente** frente a **introducido**.

**P-01 · Las catorce dependencias se aprueban en bloque al firmar la spec.** Decidido por `maujimenez4`, 2026-09-23. Ninguna es opcional —cada una la exige un requisito del encargo—, así que discutirlas una a una en el plan habría repetido catorce veces una conversación cuya respuesta ya estaba determinada. La firma de esta spec **es** la aprobación de `CLAUDE.md` §3, punto 7.

**P-06 · Se permite el paralelismo dentro del techo sumado.** Decidido por `maujimenez4`, 2026-09-23. Varias llamadas a la vez mientras sus paquetes sumen 100.000 o menos; el turno se da contando tokens, no llamadas.

**Y hay que decir qué no acelera, porque la pregunta se planteó de forma que sugería lo contrario.** Los diez capítulos de una novela siguen siendo **estrictamente secuenciales**, y no por el límite de concurrencia sino por CU-03: cada capítulo necesita integrado el anterior. Lo que se solapa son **obras distintas**, el **Continuista con el Crítico** sobre el mismo capítulo, y los **cinco briefs** de RF-EVA-01. Sobre una novela sola el efecto no es nulo pero sí pequeño: **le quita una espera de validación por capítulo**, diez en total, sin tocar la cadena de diez pasos (`architecture.md` §2.3).

---

## Lo que esta spec no verifica

| Qué no se verifica | Por qué | Qué lo cubriría |
| --- | --- | --- |
| Que la novela **se lea bien** | Ningún test juzga prosa. Las evals miden aproximaciones | Lectura humana. Es **U** y sigue siéndolo |
| Que el **destinatario se reconozca** | La cobertura comprueba que el dato **está**, no que haga algo; la naturalidad la juzga un juez que comparte modelo con quien escribió | Solo lo sabe él |
| Que un hecho nuevo **deba** entrar en el canon | El grafo solo sabe si algo **choca**. Un hecho que no contradice nada no tiene contra qué contrastarse | Nada hoy. Riesgo declarado en `verification.md` §7 |
| Que el juez **acierte** | La revisión humana mide la **distancia entre dos jueces**, no que el automático tenga razón | Un conjunto etiquetado suficiente. Por eso G1b no bloquea |
| El **coste total** de una novela | El techo es por llamada; nada acota la suma | Nada. Es **U** |
| Que **«bien formado» signifique «cierto»** | La comprobación de forma verifica la transcripción, no el juicio | Nada dentro de esta spec |
| Que la especificación **TLA+ siga correspondiendo al código** | Es una inspección que nadie repite cuando el orquestador cambia | El checklist de `CLAUDE.md` §16. Sigue siendo **I** |
| Que «fuera de Langfuse no sale nada» **se cumpla** | Es una promesa que ningún método vigila | Nada hoy |

---

## Cierre

**Vuelve a `en-revision` el 2026-09-24, y necesita firma nueva.** Estuvo `aprobada` por `maujimenez4` el 2026-09-23; desde entonces **cambió un requisito**, así que la firma anterior ya no cubre lo que dice.

**Qué cambió, y es todo:** `RF-PUB-05` pasa a exigir que **cada entrada de la `FichaDeLectura` lleve los capítulos en que aparece**. Lo pide el encargo §2 —«ficha de personajes y lugares… **con enlaces al capítulo donde aparece cada uno**»— y lo destapó escribir la spec 002, que es la primera que miró este contrato de verdad. El dato ya existía en el canon (RF-MEM-02); lo que faltaba era prometerlo en la ficha.

Es **aditivo**: no retira ni contradice nada de lo firmado, y ningún otro requisito ni criterio cambia. Pero `CLAUDE.md` §3.4 dice que una spec corregida **se vuelve a aprobar**, y una firma que cubre un texto distinto del que se firmó no es una firma.

**Lo que se mantiene de la aprobación del 2026-09-23**, y no se vuelve a preguntar: las seis decisiones P-01 a P-06 y las catorce dependencias en bloque.

Es **firma nueva y no heredada**: reemplaza a la spec aprobada el 2026-09-22, cuyo alcance era otro. Y aprueba además, **en bloque**, las catorce dependencias de Impacto técnico (P-01).

**Lo que esta firma abre:** el plan (`§3.2`), y con él la pregunta que se apartó a propósito de esta spec porque era de plan y no de alcance — **qué se puede comprobar antes de G4 aunque sea parcialmente**. Cuatro validadores bloquean con la novela ya escrita, y ahí un fallo no cuesta un capítulo: cuesta lo que haya que rehacer.
