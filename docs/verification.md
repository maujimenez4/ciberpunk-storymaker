# Verificación — StoryMaker

**Versión:** 4.1 · **Fecha:** 2026-09-23

Cómo pensamos ganar confianza en el código y en el comportamiento de los agentes.
Dos preguntas, separadas porque fallan por separado:

1. **Nivel de artefacto** — ¿es correcto el código?
2. **Nivel de proceso** — ¿se comportan los agentes de forma fiable?

Una suite de tests en verde no dice nada sobre si un agente ejecutará mañana una
acción destructiva. Un sandbox no dice nada sobre si el diff de hoy es correcto.
Confundir las dos preguntas es el modo de fallo habitual de un plan de verificación.

Y una tercera advertencia, que gobierna la lectura de todo lo que sigue: **ningún método
garantiza por sí solo que el resultado sea correcto.** Cada uno tiene una fortaleza y un
punto ciego, y los puntos ciegos no se anulan por acumulación. Lo que este documento
permite afirmar del sistema no es la suma de sus filas, sino lo que queda cubierto al
superponerlas. Por eso las tablas de §2 y §3 se leen junto a §2.1 y §3.1 —qué **no**
detecta cada método—, y se cierran en §6 con las reglas del conjunto y en §7 con la
matriz de riesgos, que es donde se ve lo que hoy no cubre nadie.

Este documento se apoya en [`architecture.md`](architecture.md) para el **qué** hay que
verificar, y en `CLAUDE.md` §8 para las reglas de dominio que el código debe respetar.
Si este documento y `architecture.md` discrepan, gana `architecture.md`.

## 1. Dos sujetos, no uno

En este repositorio la palabra «agente» designa dos cosas distintas, y la verificación
de una no vale para la otra:

| Sujeto | Qué es | Dónde está descrito |
| --- | --- | --- |
| **Agentes narrativos** | Los diez roles del producto —Entrevistador, Arquitecto, Escritor, Continuista, Crítico, Extractor…— que se ejecutan en producción para generar una novela | `architecture.md` §7 |
| **Agente de código** | El asistente de programación que escribe este repositorio | `CLAUDE.md` §3 |

El nivel de artefacto es común a ambos: el código es el mismo, venga de quien venga.
El nivel de proceso se bifurca, y cada entrada de la segunda tabla dice a qué sujeto se
refiere.

> **Estado de este documento:** `src/backend/` y `src/frontend/` están todavía vacíos,
> así que cada «Previsto» de más abajo es una *intención*, no una observación. Los
> «Aplicado por diseño» sí son comprobables hoy, pero se comprueban leyendo
> `architecture.md`, no ejecutando nada. Revísalos cuando aterrice el código. Cada
> entrada enlaza a una explicación de la metodología, nunca a una herramienta que la
> implementa.

## 2. Verificación a nivel de artefacto

| Metodología | Definición | Estado aquí | Explicación |
| --- | --- | --- | --- |
| Comprobación de tipos | Verificación automática de que los valores se usan de forma coherente con lo que las operaciones esperan de ellos | **Previsto** — línea base de las dos aplicaciones. Backend: `mypy` estricto sobre `commons/domain/` y los `service.py`. Frontend: `tsc` en modo estricto por `pnpm typecheck`, **sin `any` en código de producción** (`RNF-CAL-02` de la 002). Que la prohibición del `any` valga algo depende de que nadie use `as unknown as T`, que la desactiva sin que el compilador diga nada — es el equivalente frontend de un `# type: ignore` sin justificar. El cliente del frontend se **genera** del OpenAPI, así que una ruptura de contrato es error de compilación y no un 422 en ejecución. Pydantic v2 añade la comprobación equivalente en ejecución, en la frontera | [Type system](https://en.wikipedia.org/wiki/Type_system) |
| Análisis estático / SAST | Escanear el código fuente sin ejecutarlo, contrastándolo con patrones conocidos como defectuosos | **Previsto** — es lo que hace verificables las fronteras. `ruff` y ESLint son la línea base; lo que aporta de verdad es `import-linter` (arq. §5.2) e `import/no-restricted-paths` (arq. §6.2): las reglas de dependencia entre features son afirmaciones sobre el código fuente, se comprueban sin ejecutarlo y fallan la build | [Static program analysis](https://en.wikipedia.org/wiki/Static_program_analysis) |
| Ejecución simbólica | Ejecutar el código con entradas simbólicas para derivar las condiciones exactas de fallo mediante un solucionador SMT | **No aplicable** — la única lógica numérica con condiciones de fallo interesantes es la aritmética de presupuesto del ensamblador, y ahí un test basado en propiedades da la misma respuesta por mucho menos | [Symbolic execution](https://en.wikipedia.org/wiki/Symbolic_execution) |
| Verificación formal / demostración de teoremas | Demostrar matemáticamente que el código satisface una especificación para todas las entradas posibles | **Obligatorio (Lean 4)** — no sobre el código, sobre la **cronología de la historia**. De la biblia se genera un fichero Lean con eventos, momento, presentes, lugar y fechas de nacimiento, y se demuestran al menos dos invariantes: el orden temporal declarado se respeta, y la edad de un personaje en cada evento concuerda con su fecha de nacimiento. Se ejecuta con `lake build` y **es una puerta**: si falla, la versión no se publica y el fallo vuelve al editor. Hasta la v3.1 esta fila decía «No aplicable» y el argumento era bueno para otro producto — véase §10 | [Formal verification](https://en.wikipedia.org/wiki/Formal_verification) |
| Tests unitarios / de integración | Comprobar el comportamiento frente a entradas concretas elegidas y salidas esperadas | **Previsto** — método principal a nivel de artefacto. `pytest` con `pytest-asyncio`; test colocado junto al componente en el frontend. Dos reglas del proyecto lo sostienen: toda regla de dominio de `CLAUDE.md` §8 tiene su test, y el cliente de modelo se inyecta, de modo que ninguna prueba llama al proveedor | [Unit testing](https://en.wikipedia.org/wiki/Unit_testing) |
| Tests basados en propiedades | Especificar una propiedad general y generar muchas entradas para buscar una violación | **Previsto** — dirigido al **ensamblador de contexto**, que es donde los ejemplos elegidos se quedan cortos. Propiedades: el desglose por capa suma el total contado; recortar una capa no altera las demás; las capas constitucional e instrucción nunca encogen; o el paquete cabe en 100.000 tokens o se lanza `ContextBudgetExceeded`, nunca un truncado silencioso | [QuickCheck — Claessen y Hughes, 2000](https://www.cs.tufts.edu/~nr/cs257/archive/john-hughes/quick.pdf) |
| Tests de mutación | Introducir deliberadamente pequeños fallos para comprobar si la suite de tests los detecta | **Aplazado** — tendrá sentido cuando exista la suite del ensamblador, porque es precisamente la suite en cuya luz verde estaremos tentados de confiar para afirmar que el contexto nunca se recorta a escondidas. Hoy no hay suite que mutar | [Mutation testing](https://en.wikipedia.org/wiki/Mutation_testing) |
| Tests de contrato | Verificar que la interfaz entre dos servicios se mantiene coherente, con independencia de sus interioridades | **Previsto, y en parte por construcción** — hay tres fronteras de este tipo: el OpenAPI entre backend y frontend —el cliente **se genera**, no se escribe a mano (`RF-EST-03` de la 002)—. **Y hoy nada comprueba que siga siendo así:** si alguien escribe un tipo de respuesta a mano, `pnpm typecheck` pasa igual y la comprobación de contrato **desaparece sin que falle nada**. Es el caso puro de un validador que se puede desactivar en silencio, y no tiene fila en §8 porque verifica el código y no la novela (§8.5); el `__init__.py` de cada feature como única superficie importable; y la E/S de cada agente narrativo, que es un contrato real —el Continuista devuelve **códigos de defecto con cita**, nunca prosa corregida— y por tanto se valida con esquema y se prueba | [Contract Test — Martin Fowler](https://martinfowler.com/bliki/ContractTest.html) |

### 2.1 Lo que no detecta cada método

Una fila de la tabla anterior sin su punto ciego es una promesa. Aquí está el reverso de
cada una, incluidas las descartadas: saber qué se escapa de un método que **no** se usa
es lo que impide volver a proponerlo como solución de algo que tampoco resolvería.

| Metodología | Qué no detecta |
| --- | --- |
| Comprobación de tipos | Habla de forma, no de significado. Un programa bien tipado puede hacer exactamente lo contrario de lo que debe: que `escena_de_origen` sea una cadena no dice que apunte a una escena que exista, ni que sea la escena correcta |
| Análisis estático / SAST | Solo encuentra lo que alguien supo describir como patrón. Las fronteras que comprueba son las **declaradas como import**: un acoplamiento real por inyección, por configuración o por nombre de tabla no es un import y no aparece |
| Ejecución simbólica | Descartada, y aunque se adoptara resolvería la aritmética del paquete, no su contenido. Un paquete cuyos números cuadran puede ser el paquete equivocado |
| Verificación formal (Lean) | Demuestra que la cronología cumple **las invariantes escritas**; si la invariante es la equivocada, la demostración es correcta y la historia está mal. Y tiene un punto ciego propio de este uso, que conviene no perder de vista: **Lean demuestra sobre el fichero generado desde la biblia, no sobre la prosa**. Si el capítulo dice algo que nunca llegó a la biblia, Lean no lo ve — verifica el modelo de la historia, no la historia |
| Tests unitarios / de integración | Comprueban los casos que a alguien se le ocurrieron. No dicen nada del caso que no se escribió, y su luz verde crece con el número de tests, no con su calidad |
| Tests basados en propiedades | Buscan violaciones de la propiedad **enunciada**. La propiedad que nadie enunció no se busca: que el paquete quepa y respete los topes no dice que contenga lo que la escena necesitaba |
| Tests de mutación | Miden la suite, no el código: un mutante muerto prueba que algún test reacciona a ese cambio, no que el comportamiento sea correcto. Y están aplazados, de modo que hoy nada mide la suite |
| Tests de contrato | Verifican la **forma** del intercambio, y desde arq. §8.3 la forma de un defecto incluye que su cita sea subcadena real del texto que señala: la categoría del **defecto bien formado con la cita inventada ha desaparecido**. Queda lo que ninguna comprobación de forma alcanza: el defecto cuya cita es real pero cuyo **diagnóstico** es equivocado, y el que el Continuista no llegó a emitir |

## 3. Verificación a nivel de proceso

| Metodología | Definición | Estado aquí | Explicación |
| --- | --- | --- | --- |
| Observabilidad / trazas en ejecución | Instrumentar el agente para que su trayectoria sea visible y consultable a posteriori | **Aplicado por diseño (narrativos)** — cada llamada registra `run_id`, escena, versión de prompt y de biblia, IDs recuperados, modelo, parámetros, semilla, tokens por capa, coste y veredicto (arq. §9). **Cambio del 2026-09-23:** hasta hoy esta fila decía que la traza era «estructural, no textual». `maujimenez4` ha autorizado que **el prompt renderizado y el tracing** lleguen a Langfuse, y que **la prosa generada no**. Lo que desbloquea es real —comparar dos versiones de prompt deja de ser comparar dos números sin contexto— y lo que cuesta también: los **datos personales del destinatario** viajan a un servicio externo dentro del prompt. Es una decisión sobre datos de terceros, no un matiz técnico, y por eso se fecha y se atribuye. **Y con el prompt sube el manuscrito**, porque cinco de los diez roles reciben la prosa *como* entrada: su prompt renderizado **es** el capítulo. `CLAUDE.md` §4.3 lo dice con esas palabras en vez de prometer lo contrario, que es la única forma honesta de escribirlo | [Observability primer](https://opentelemetry.io/docs/concepts/observability-primer/) |
| Evals | Pruebas estructuradas del comportamiento del agente contra un conjunto de datos y un método de puntuación | **Obligatorio (narrativos)** — deja de ser trabajo de una fase futura: **cinco briefs de prueba**, uno **adversarial** (instrucciones incrustadas en el texto libre) y uno construido para **provocar una incoherencia temporal**, una tabla que diga por brief qué validadores pasaron y cuáles fallaron, y **una iteración de tuning documentada** con resultados antes y después. Sigue valiendo lo que ya decía esta fila: sin conjunto etiquetado no se distingue un cambio de prompt que mejora de uno que solo desplaza la salida | [HELM — Liang et al., 2022](https://arxiv.org/abs/2211.09110) |
| Juicio por modelo con rúbrica | Un modelo puntúa la salida de otro contra criterios escritos, con una puntuación y una justificación por criterio | **Obligatorio (narrativos)** — el Crítico deja de puntuar a ojo: la rúbrica es un artefacto con nombre (`Rubrica` en `definitions.md` §9) y cubre continuidad, tono, calidad narrativa —arco, coherencia de personajes, ritmo— y **naturalidad de la personalización**. Cada criterio devuelve puntuación **y** justificación: una nota sin motivo no se puede contrastar ni discutir | [LLM-as-a-judge — Zheng et al., 2023](https://arxiv.org/abs/2306.05685) |
| Revisión humana con la misma rúbrica | El **Autor** puntúa con los mismos criterios que el modelo, para medir la distancia entre los dos juicios | **Obligatorio (narrativos)** — al menos **una novela completa** leída por una persona con la **misma** rúbrica. Que sea la misma es lo que hace comparables las dos columnas: con rúbricas distintas se obtienen dos opiniones y ninguna medida. Es lo que convierte la calibración del Crítico de intención en dato, y es la única fila de este documento que produce el patrón contra el que se mide todo juicio semántico | [Inter-rater reliability](https://en.wikipedia.org/wiki/Inter-rater_reliability) |
| Ejecución en sandbox *(narrativos)* | Ejecutar el código del agente en un entorno aislado para que las acciones dañinas fallen sin consecuencias | **Sustituido por supresión del alcance** — los agentes narrativos no ejecutan código, y el Escritor no accede a la base de datos: solo ve el paquete recibido (arq. §3.5). Se **elimina** el radio de impacto en lugar de contenerlo: más fuerte que un sandbox. **La condición exacta es que los diez agentes narrativos no reciben ninguna herramienta** —ni fichero, ni red, ni proceso— y así está declarado en arq. §3.5. La formulación «ningún agente recibe una herramienta» **sobrevive intacta**, y estuvo a punto de debilitarse sin motivo: el validador visual conduce un navegador pero **no es un agente** —no recibe prompt, no llama al modelo, no decide— igual que el Ensamblador es código que ensambla (arq. §3.5.1). Lo que sí tiene navegador es el **agente de código**, y eso está dos filas más abajo | [Sandbox (computer security)](https://en.wikipedia.org/wiki/Sandbox_%28computer_security%29) |
| Ejecución en sandbox *(agente de código)* | Lo mismo, aplicado al asistente que escribe este repositorio | **No aplicado** — el agente de código lee y escribe ficheros y ejecuta órdenes directamente: no hay entorno aislado ni intermediario que lo haga por él. Lo que acota el daño es otra cosa, y está dos filas más abajo: toda escritura pasa por una persona, y por la tubería de `CLAUDE.md` §15. Hasta el 2026-09-22 esta fila afirmaba lo contrario —que corría sin herramientas de fichero— y siguió afirmándolo después de dejar de ser cierto | [Sandbox (computer security)](https://en.wikipedia.org/wiki/Sandbox_%28computer_security%29) |
| Guardarraíles *(narrativos)* | Políticas y filtros que restringen qué acciones puede producir un agente | **Aplicado en código** — edad mínima y nivel de calor se validan **en esquema**, no en el prompt (arq. §11); el presupuesto de contexto falla explícitamente en vez de truncar; el reintento dirigido tiene tope de dos; cada agente recibe el mínimo de permisos que su nodo necesita (arq. §3.5); y un defecto mal formado no llega a la puerta (arq. §8.3). Regla que lo sostiene: ninguna regla de seguridad depende solo del prompt | [AI Risk Management Framework — NIST](https://www.nist.gov/itl/ai-risk-management-framework) |
| Guardarraíles *(agente de código)* | Lo mismo, aplicado al asistente que escribe este repositorio | **Aplicado, pero a posteriori** — no hay filtro sobre lo que el agente puede producir: hay una tubería que lo rechaza después. Las fronteras entre features fallan la build, `mypy` es estricto sobre `commons/domain/` y los `service.py`, y el proceso de `CLAUDE.md` §3 no deja entrar código sin spec y plan aprobados. La diferencia con la fila de arriba importa: allí el guardarraíl impide, aquí detecta | [AI Risk Management Framework — NIST](https://www.nist.gov/itl/ai-risk-management-framework) |
| Revisión humana en el bucle | Una persona aprueba, rechaza o edita las acciones de alta consecuencia del agente | **Aplicado (ambos), con puntos definidos** — G1a escala a la persona tras dos reparaciones fallidas; G3 no cierra borrador sin revisión; el arco romántico figura en la tabla de dimensiones de calidad como «revisión humana». En el repositorio, toda escritura del agente de código pasa por una persona | [Human-in-the-loop](https://en.wikipedia.org/wiki/Human-in-the-loop) |
| Verificación multiagente | Patrones de crítico, debate, autoconsistencia, reflexión o ensamblado que revisan la salida del modelo | **Aplicado (narrativos): es el mecanismo central de calidad, no una opción en estudio** — Continuista y Crítico existen separados del Escritor exactamente por esto (decisión 6 de arq. §12: quien escribe no ve sus contradicciones, y quien juzga no repara). Coste asumido: la puerta de escena gasta hasta dos validaciones además de la escritura. Límite conocido y ahora explícito en el diseño: el juez no está calibrado, así que **G1b no bloquea** hasta la fase 4 (arq. §8.3); lo que hoy aporta es detección de contradicciones, no juicio de calidad | [AI Safety via Debate — Irving et al., 2018](https://arxiv.org/abs/1805.00899) |
| Integración en CI/CD | Hacer pasar los cambios generados por el agente por la misma tubería que los escritos por personas | **Previsto (agente de código)** — sin una vía aparte y más débil para los diffs del agente. La tubería es la lista de `CLAUDE.md` §15: `ruff`, `mypy`, `pytest`, `lint-imports`, `pnpm typecheck`, `pnpm lint` y migraciones de Alembic. Exigencia propia de este proyecto: la suite debe correr **en los dos modos de `VectorStore`**; si solo se ejecuta con `sqlite-vec` cargado, el modo degradado que promete arq. §2 no está verificado | [Continuous integration](https://en.wikipedia.org/wiki/Continuous_integration) |
| Despliegue progresivo | Enviar un cambio a un pequeño porcentaje del tráfico tras un flag antes de la publicación completa | **No aplicable** — el modo de referencia es local, con **una sola base SQLite** (arq. §10): no hay tráfico que repartir. Lo que sí cumple la función de comparar variantes sin desplegar son las versiones de texto inmutables y la comparación de estrategias de contexto de la fase 6 | [Feature toggle](https://en.wikipedia.org/wiki/Feature_toggle) |
| Red teaming / pruebas adversarias | Sondear deliberadamente en busca de fallos bajo un modelo de amenaza adversario | **Previsto (narrativos), con modelo de amenaza concreto** — la vía realista no es un atacante externo, es el propio bucle: el Extractor convierte prosa generada en canon, de modo que un texto con instrucciones incrustadas se realimenta al sistema por un canal legítimo. Segundo objetivo: empujar desde el brief contra los guardarraíles de edad y nivel de calor, para comprobar que lo que aguanta es el esquema y no el prompt | [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/) |
| Inspección visual automatizada *(browser MCP)* | Abrir el artefacto en un navegador real y comprobar sobre el renderizado lo que el código fuente no dice | **Obligatorio, y el encargo lo pide en dos sitios que no son el mismo** — (a) el **validador visual** de la puerta G4, que es **código conduciendo un navegador y no un agente** (arq. §3.5.1), así que no añade sujeto ninguno a §1; y (b) el **agente de código**, que sí es un sujeto de este documento y a quien el encargo obliga a conectar un navegador por `.claude/mcp.json`, documentando su uso real: qué inspeccionó, qué detectó y qué cambió. Solo el segundo recibe una herramienta. El código abre la lectura web, navega los capítulos y verifica que el **índice**, la **ficha de personajes y lugares** y la **portada con dedicatoria** se ven; si algo no renderiza, es un fallo que vuelve al rol que lo produjo. Es el único método de este documento que mira **el producto tal y como lo recibe el destinatario**, y caza la clase de defecto que ningún test de unidad ve: el enlace que apunta a un capítulo que no existe, la ficha vacía, la dedicatoria que se sale. Su **uso real se documenta**: qué se inspeccionó, qué se detectó y qué cambió a consecuencia | [Browser automation](https://en.wikipedia.org/wiki/Browser_automation) |
| Comprobación de modelos | Explorar exhaustivamente los estados y transiciones alcanzables del agente para verificar invariantes | **Obligatorio (TLA+ / PlusCal, con TLC)** — sobre el **harness**, no sobre la historia: configuración → planificación → escritura → validación → publicación, con reintentos, reanudación desde checkpoint y regeneración por petición del lector. Al menos tres invariantes de seguridad —no se publica una versión con un capítulo que no pasó todos los validadores; la reanudación no duplica ni pierde capítulos; la versión anterior se conserva— y una de liveness: toda generación termina publicando o parando con error. Se comprueba con TLC sobre un modelo pequeño, con la configuración en el repositorio. **El argumento con el que se descartó en la v3.1 —«la máquina es pequeña y la cubren los tests»— ha dejado de valer**: publicación de versiones, checkpoint por capítulo y regeneración parcial son tres ejes nuevos que se multiplican entre sí, y ahí es donde un model checker gana a los tests | [Model checking](https://en.wikipedia.org/wiki/Model_checking) |

### 3.1 Lo que no detecta cada método

Una entrada por **método**, no por fila: dos de ellos —sandbox y guardarraíles— aparecen
en §3 partidos por sujeto, y el punto ciego que sigue es el del método, común a los dos.

| Metodología | Qué no detecta |
| --- | --- |
| Observabilidad / trazas | Registra lo que se decidió registrar, y aquí, a propósito, no el texto. La traza dice qué se envió y cuánto costó, **no si lo enviado era lo que la escena necesitaba**: un fallo de pertinencia del ensamblado es invisible en ella |
| Evals | Puntúan contra un conjunto y un criterio, y miden lo que ese conjunto representa. **Cinco briefs son cinco puntos**: cubren los modos de fallo que alguien imaginó al escribirlos, y el sexto brief —el que un **Comprador** real traerá— no está representado. Una tabla con cinco filas en verde mide la cobertura del conjunto, no la del sistema |
| Juicio por modelo con rúbrica | Puntúa contra los criterios **enunciados en la rúbrica**, así que la calidad que nadie supo enunciar no se puntúa. Y comparte **proveedor** con lo que juzga, aunque desde P-02 ya no el modelo (§6.1): un texto que le suena bien por las mismas razones por las que se escribió obtiene buena nota sin que nadie pueda notarlo desde dentro |
| Revisión humana con la misma rúbrica | Mide **la distancia entre dos jueces**, no si alguno acierta. Si los dos comparten el sesgo —y una rúbrica común empuja a eso—, una correlación alta confirma que se entienden entre ellos, no que la novela sea buena. Y es una sola novela: dice lo que pasó con esa |
| Sandbox / supresión del alcance | Acota el daño, no la corrección: un agente sin herramientas produce texto equivocado con la misma facilidad que uno con ellas. Y la propiedad depende de una configuración de permisos que nada vigila de forma continua |
| Guardarraíles | Bloquean lo que está **tipificado** como prohibido. Lo que no está tipificado —el caso del §7, un hecho nuevo que no contradice nada— atraviesa el guardarraíl sin activarlo |
| Revisión humana en el bucle | Su calidad decae con el volumen: un escalado frecuente produce aprobación en masa, y «revisado» deja de distinguirse de «aprobado sin leer». Hoy ninguna señal separa esos dos estados |
| Verificación multiagente | Supone que los validadores fallan de forma independiente. Aquí comparten modelo, redacción de las restricciones y **la misma entrada** (§6.1): lo que faltó en el paquete le falta al Escritor y al Continuista a la vez |
| Integración en CI/CD | Dice que la tubería terminó, no que haya comprobado algo. Una prueba omitida por falta de extensión, un modo no ejercitado o una fixture ausente se ven igual que el verde |
| Despliegue progresivo | Descartado por ausencia de tráfico. Con él se descarta la única forma de observar una variante con uso real antes de adoptarla, que en modo local no existe de todos modos |
| Red teaming / pruebas adversarias | Encuentra lo que el modelo de amenaza contempla. Queda fuera por definición el vector no previsto y, sobre todo, el fallo **accidental** que se comporta como un ataque: una escena legítima en la que un personaje dicta instrucciones |
| Inspección visual automatizada | Comprueba que **algo** se ve, no que sea **lo correcto**: un índice que renderiza once entradas para diez capítulos renderiza perfectamente. Y mira la página, no la novela — que la ficha de personajes aparezca no dice que sus datos coincidan con la biblia |
| Comprobación de modelos (TLA+) | Explora estados y transiciones, no **contenido**: una máquina de estados perfecta puede pasear una escena equivocada por los diez estados correctos. Y verifica **la especificación, no el código**: que TLC no encuentre contraejemplo no dice que el orquestador implemente esa máquina. Esa correspondencia es una lectura humana —el README dice qué transición del código implementa cada acción—, o sea una **I**, y es el eslabón más débil de la cadena |

## 4. Clasificación: T / A / I / D / U

Cada requisito recibe **una letra principal**: la del método que lo *establece*. Es la
letra que decide si el requisito está verificado, y existe para que los que nadie puede
comprobar queden visibles en vez de darse por supuestos. Cuando un segundo método lo
**refuerza** sin establecerlo se anota junto a la principal —así aparecen en §4.1 las
filas con dos letras—, y no la sustituye. Un refuerzo no convierte en verificado lo que
la letra principal deja pendiente. Véase
[Verification and validation](https://en.wikipedia.org/wiki/Verification_and_validation).

| Letra | Significado | Cómo se ve aquí |
| --- | --- | --- |
| **T** — Test (prueba) | Se verifica ejecutando el sistema con entradas definidas | Presupuesto del ensamblador, validadores de canon y continuidad, esquemas de dominio |
| **A** — Análisis | Se verifica razonando sobre el artefacto sin ejecutarlo | Tipos, fronteras entre features, ámbito de permisos por agente |
| **I** — Inspección | Se verifica con una persona leyéndolo | Prompts versionados, rúbricas, política de guardarraíles, este documento |
| **D** — Demostración | Se verifica observando el sistema operar en una ejecución realista | La vertical mínima de la fase 1: un capítulo coherente de principio a fin |
| **U** — No verificable | Ningún método que estemos dispuestos a pagar lo establece | Véase más abajo |

### 4.1 Los requisitos del proyecto, clasificados

`CLAUDE.md` §3 y §8 no tienen subsecciones numeradas: sus puntos son listas. Por eso la
columna de origen cita «§8, regla 2» y «§3, principio 6», y no «§8.2» ni «§3.6», que en §3
chocarían con subsecciones reales —§3.5 es «Cierre», no el quinto principio—.

| Requisito | Origen | Letra | Con qué |
| --- | --- | --- | --- |
| Ninguna llamada al modelo supera los 100.000 tokens | arq. §2.1 | **T** | Propiedades y unitarios sobre el ensamblador; `ContextBudgetExceeded` en vez de truncar |
| El recorte es por capa y no toca las capas vecinas | arq. §2.1 | **T** | Propiedad sobre el desglose devuelto junto al paquete |
| Las capas constitucional e instrucción nunca se recortan | arq. §2.1 | **A** | No existe ruta de código que las recorte: se lee, no se ejecuta. Un test lo refuerza |
| Nunca hay más llamadas al modelo en vuelo de las permitidas | arq. §2.2 | **T** | Prueba de concurrencia: se lanza más carga que turnos y se comprueba que la sobrante **espera**, no que se recorta el paquete |
| Un trabajo interrumpido se reanuda sin duplicar escrituras | arq. §3.7 | **T** | Matar el proceso en cada estado no terminal y comprobar la idempotencia por `run_id` |
| Solo el Extractor escribe memoria de largo plazo | arq. §4.3 | **A** | Ninguna otra ruta de código escribe en canon, ledger ni índice; se lee en el repositorio, no se ejecuta |
| Una escena rechazada no deja rastro en canon | arq. §4.4 | **T** | Provocar un defecto bloqueante y comprobar que canon, ledger e índice quedan intactos |
| Las fronteras entre features no se cruzan | arq. §5.2 y §6.2 | **A** | `import-linter` e `import/no-restricted-paths`; falla la build |
| Una escena tiene un POV y un giro de valor no nulo | CLAUDE §8, regla 1 | **T** | Esquema Pydantic con su test |
| Ningún personaje usa información sin `sabe_desde` anterior | CLAUDE §8, regla 2 | **T** | Validador de conocimiento (defecto CON-03) sobre casos conocidos |
| El estado en T se deriva del ledger y no se edita | CLAUDE §8, regla 3 | **A + T** | No hay repositorio que escriba sobre la vista; un test reconstruye el estado desde el ledger |
| Todo hecho de canon **con `origen: escena`** cita la escena; los de `origen: brief` **no la tienen y no la inventan** | CLAUDE §8, regla 4 | **T** | `CheckConstraint` en la tabla `hecho_canon`, no solo en el servicio: es lo que la sostiene cuando se escriba por otra ruta. Probado por los dos lados —esquema y repositorio— y con el método de §2: quitando la restricción caen sus tests y solo los suyos |
| Cada ejecución guarda prompt, biblia, IDs, modelo, semilla y coste | CLAUDE §8, regla 7 | **T** | Test de la escritura en `ejecucion` |
| La prosa usa la `persona` y el `tiempo_verbal` declarados en la obra | CLAUDE §8, regla 10 · def. §11, axioma 13 | **T** | Validador de discurso (defecto `VOZ-03`) sobre la narración, excluido el diálogo: un personaje puede hablar en primera dentro de una narración en tercera. **Llevaba sin clasificar desde la v1.3**, y era la única regla con código de defecto propio y sin letra |
| La dedicatoria no es prosa del manuscrito | CLAUDE §8, regla 15 | **T** | No entra en el ensamblado, ni en el PDF como capítulo, ni en la lista negra de n-gramas. Es un test barato y la regla es de las que se incumplen sin que nadie lo note: la dedicatoria sería un fragmento más |
| La cita de un `Defecto` es subcadena exacta del texto que señala | def. §11, axioma 11 | **T** | Comprobación de forma en código antes de G1a (arq. §8.3): se contrasta la subcadena y su desplazamiento sobre la `VersionDeTexto`, sin volver a llamar al modelo |
| Todo `CAN-01` declara un `hecho_canon_id` que existe en el grafo | def. §11, axioma 12 | **T** | Misma comprobación, contra el grafo de canon |
| Un defecto mal formado no bloquea ni consume reintento | arq. §8.3 | **T** | Emitir un defecto con cita inventada y comprobar que no llega al prompt de reparación, que no gasta intento y que se cuenta aparte (arq. §9) |
| El sistema funciona con y sin extensión vectorial | arq. §2 | **T + D** | La suite corre en los dos modos; además, arranque real con la extensión ausente. **Es un requisito propio, no del examen:** el examen §4 exige SQLite por su nombre y no menciona `sqlite-vec`, así que lo obligatorio es la base y opcional la extensión. Que el modo degradado se pruebe lo decidimos nosotros, y por eso se puede retirar sin incumplir nada |
| Una ejecución se puede reproducir | CLAUDE §3, principio 6 | **D**, no T | Se reproduce el **paquete de contexto**, que es determinista; la prosa no, porque el modelo no lo es. Es justo la razón de que el ensamblador sea código: lo reproducible es lo auditable. **Con fecha de caducidad:** el paquete se reproduce mientras el estado de almacenes sea el de entonces, y el canon crece en cada escena, así que reconstruir una escena antigua desde los almacenes de hoy da otro paquete |
| Ninguna escena excede el nivel de calor declarado | CLAUDE §8, regla 5 | **T** parcial **+ I** | El esquema comprueba el nivel declarado; que la prosa se mantenga dentro lo juzga el Crítico (defecto SEG-01) y, en última instancia, una lectura humana |
| Ningún contenido romántico o sexual con personajes menores de 18 | CLAUDE §8, regla 6 | **T + I** | La edad se valida en esquema y bloquea por construcción; que la prosa no lo insinúe se inspecciona |
| El coste **por llamada** se mantiene acotado | arq. §2.1 y §2.2 | **T** | El contador inyectado y los topes por capa lo acotan antes de llamar, y el límite de concurrencia acota el proceso. **El total de una novela no lo acota nada**: por eso figura como U en §4.2 y como descubierto en §7, y no como un requisito verificado aquí |
| El juez correlaciona con el editor humano | arq. §7 | **U** hoy → **T** | Pasa a T con la revisión humana de una novela completa **con la misma rúbrica** (§3). Es el requisito que más cambia de estado en esta versión: deja de esperar a una fase y tiene método asignado |
| Los eventos respetan el orden temporal declarado | examen §5c | **T** | Invariante demostrada en Lean sobre la cronología generada desde la biblia, ejecutada con `lake build`. **Bloquea la publicación** |
| La edad de un personaje concuerda con su fecha de nacimiento en cada evento | CLAUDE §8, regla 13 · examen §5c | **T** | Segunda invariante de Lean, misma puerta. **Y antes de llegar ahí:** un `model_validator` sobre el brief rechaza la contradicción en la entrevista, que es donde cuesta una respuesta y no una novela entera |
| No se publica una versión con un capítulo que no pasó todos los validadores | CLAUDE §8, regla 14 · examen §5d | **T + A** | Invariante de seguridad comprobada por TLC sobre el modelo; que el código implemente ese modelo es **I** y no está cubierto (§7) |
| La reanudación desde checkpoint no duplica ni pierde capítulos | examen §5d | **T** | Invariante de TLC, y la prueba de reanudación que ya existía en esta tabla. Dos métodos no correlacionados sobre el mismo requisito |
| La versión anterior de la novela se conserva tras una regeneración | examen §5d | **T** | Invariante de TLC más versiones de texto inmutables por construcción |
| Toda generación termina publicando o parando con error | examen §5d | **T, bajo una hipótesis** | Propiedad de liveness en TLC, la única de la lista que **no** es de seguridad: las demás dicen qué no debe pasar, esta dice que algo tiene que pasar. **Y se cumple gracias a `SF_vars(Aprobar)`, no gracias a la cota de reintentos** *(medido el 2026-09-24)*: con el contador de reintentos reiniciándose en cada reanudación la propiedad **sigue en verde**, y solo cae al bajar a `WF_vars`. El contador sostiene `TypeOK`; quien cierra el bucle es la equidad fuerte. Eso convierte la fila en condicional: TLC demuestra que **si** un capítulo acaba aprobándose, la generación termina — y que eso ocurra en el sistema real es supuesto, no comprobado. **El escenario que queda fuera es real**: un capítulo que el escritor nunca logra dejar aceptable. El código lo acota con los dos reintentos de `CLAUDE.md` §9.1 y el escalado a revisión humana, que es un mecanismo del código y no del modelo |
| Ninguna palabra vetada llega al capítulo aceptado | CLAUDE §8, regla 12 · examen §7 | **T** | Comparación léxica normalizada en código, **por palabra y no por subcadena** —un veto que salta dentro de otra palabra se acaba desactivando, y entonces no protege de nada—, con tests de cada nivel de lista y de variante con acento o plural. **Caza la palabra, no la alusión** (§7) |
| Cada elemento personalizado obligatorio aparece en al menos un capítulo | CLAUDE §8, regla 11 · examen §5a | **T** | Contraste contra los hechos y su `usado_en[]`. Comprueba **presencia**, no integración |
| La personalización está integrada y no incrustada | examen §5b | **I + U parcial** | Juez con rúbrica y revisión humana. La prueba de oficio —quitar el dato y ver si la escena cambia (`domain-knowledge.md` §14.1)— es enunciable pero no mecanizable |
| El destinatario se reconoce en la novela | examen, Contexto | **U** | Solo lo sabe él. Ninguna de las dos dimensiones del §1.1 de `domain-knowledge.md` tiene juez definitivo distinto de la persona a la que se regala |
| El relato merece la pena leerse | — | **U** | — |

### 4.2 Qué es hoy U

Nombrarlos es el sentido del ejercicio: una U sin marcar es una afirmación que
hacemos sin pruebas.

- **Calidad narrativa.** «El relato es bueno» no tiene test. Las evals pueden medir
  aproximaciones —coherencia, cobertura de beats, adecuación al brief—; no pueden
  medir si merece la pena leerlo. Esto sigue siendo U, y sigue siendo un juicio humano.
- **Calibración del Crítico.** Mientras no exista el conjunto etiquetado, sus
  puntuaciones son una opinión no contrastada. Las puertas que dependen de umbrales
  —voz, prosa, diálogo— heredan esa incertidumbre; las bloqueantes por contradicción de
  canon no, porque se contrastan contra el grafo.
- **Pertinencia de la memoria recuperada.** La recuperación híbrida está diseñada para
  traer lo pertinente y no solo lo parecido, pero *pertinente* no tiene métrica: el
  único síntoma observable es que al Escritor le faltó un dato, y eso aparece después,
  como defecto, no antes. Conviene no arrastrar con ella a su vecina: la **presencia**
  de un dato concreto en el paquete sí es comprobable, y que hoy no se compruebe es un
  hueco de cobertura (§7), no una U.
- **Que un hecho nuevo deba entrar en el canon.** El grafo solo sabe decir si algo
  **choca** con lo que ya contiene. Un hecho que no contradice nada no tiene contra qué
  contrastarse: ni el canon ni ningún validador pueden decir si es cierto, ni si conviene
  fijarlo. La consecuencia —la memoria se consolida con lo que nadie desmintió— está en
  §7 como riesgo descubierto.
- **Ausencia de fallos semánticos sutiles introducidos por el modelo.** Los tests
  detectan aquello para lo que se escribieron. Los tests de mutación aumentan la
  confianza en la suite, no en el código.
- **Comportamiento del modelo subyacente entre cambios de versión.** No lo
  controlamos, y una suite de evals detecta regresiones a posteriori en lugar de
  prevenirlas.
- **Coste total de una novela completa.** El presupuesto *por llamada* está acotado y
  es verificable; el total de diez agentes, con G1 gastando dos validaciones por
  escena, lo limita una política y no lo demuestra ningún análisis.
- **Que el destinatario se reconozca.** Es la mitad del producto (`domain-knowledge.md`
  §1.1) y no tiene juez distinto de la persona a la que se regala. Se puede comprobar que
  cada dato obligatorio **aparece** —eso es T, contra la tabla de hechos— y se puede
  puntuar si suena integrado o incrustado —eso es I, con rúbrica—. Ninguna de las dos
  responde la pregunta, que es si al abrirlo pensó «esto es mío». Conviene no confundir la
  cobertura, que es medible, con el reconocimiento, que no lo es.

## 5. Advertencias

- Los tests basados en propiedades y las evals no tienen una referencia fundacional
  neutra única como sí la tiene la verificación formal. Los enlaces de arriba apuntan
  al artículo que introdujo o formalizó cada método (QuickCheck; HELM): una elección
  defendible, no la única.
- Aparecer en estas tablas no es una recomendación de adopción. La ejecución simbólica
  y la comprobación de modelos figuran aquí para que la decisión de descartarlas quede
  por escrito.
- Varios «Aplicado por diseño» son fuertes precisamente porque la capacidad no existe:
  no hay sandbox porque no hay herramienta que aislar. Si algún día un agente recibe
  acceso de fichero o de red, esas filas dejan de ser ciertas el mismo día, y hay que
  reabrirlas **antes** de conceder el permiso, no después. **Ya ocurrió una vez:** la
  fila de sandbox afirmaba que el agente de código corría sin herramientas de fichero, y
  lo siguió afirmando mucho después de dejar de ser verdad. De ahí que §3 separe ahora
  los dos sujetos en filas distintas: una fila que los mezcla puede caducar por la mitad
  sin que se note.
- Ninguna fila de §2 y §3 declara criterio de paso: cuántas propiedades, qué proporción
  de casos adversarios, qué cobertura. Un «Previsto» sin umbral no se puede incumplir, y
  lo que no se puede incumplir no verifica. Los umbrales son requisitos y viven en una
  spec, no aquí; mientras no existan, el estado de una fila describe intención de
  trabajo, no una condición de aceptación. **Las dos filas formales de la v4.0 son la
  excepción, y por eso valen más de lo que parece:** «`lake build` pasa» y «TLC no
  encuentra contraejemplo» son criterios binarios que alguien puede incumplir, y las
  únicas de este documento que bloquean por sí solas.
- Un método marcado «Aplicado» puede dejar de estarlo sin que nada cambie en su fila: la
  revisión humana se degrada por volumen, la supresión del alcance por una configuración
  de permisos, la suite en dos modos por una prueba que se omite en silencio. El estado
  de una fila es una afirmación sobre hoy, no una propiedad estable.
- Al actualizar este documento, mantén separados los dos sujetos. Verificar al agente
  de código no dice nada sobre el comportamiento de los agentes narrativos en
  producción, ni al revés.
- Al actualizar §2 o §3, actualiza su punto ciego en §2.1 o §3.1 y revisa si alguna fila
  del §7 cambia de estado. Un método nuevo que no mueve ninguna casilla de la matriz no
  está aportando cobertura: está aportando trabajo.

### 5.1 Cómo se destapa un verde falso

**El fallo más caro de este repositorio no ha sido un test en rojo: ha sido un test en
verde que no comprobaba nada.** Apareció tantas veces el 2026-09-24, en sesiones y
ficheros sin relación, que conviene escribir el método y no los casos — los casos los
rehace cualquiera; el método es lo que se reutiliza.

La forma es siempre la misma: **un resultado con la pinta correcta, producido por algo que
no llegó a ejecutarse, o que se ejecutó sobre otra cosa.** Y lo peligroso es que un verde
no invita a mirar.

Cuatro comprobaciones, cada una con el caso que la justificó.

**1 · Que el control cuente, no que mire.** Cuatro ablaciones de la especificación TLA+ se
aplicaron con `sed` sobre operadores que llevan barras invertidas. Ninguna de las cuatro
sustituciones casó, y las cuatro corridas dijeron `Model checking completed. No error has
been found.` — el resultado que se esperaba de un invariante sólido. Lo destapó un
`grep -c` de control que devolvió `0`: **la mutación no estaba en el fichero**. Desde
entonces cada ablación lleva un aserto que convierte el no-match en un fallo ruidoso.
Una modificación que puede no aplicarse necesita que alguien cuente si se aplicó.

**2 · Medir sobre el artefacto, no a través de una capa.** El error simétrico del anterior:
una comprobación de una expresión regular dio «no casa» y estuvo a punto de reportarse como
un defecto del plan. El defecto estaba en los escapes del *heredoc* de `bash` que
transportaba el patrón, no en el patrón. Se resolvió poniendo la comprobación en un fichero
y quitando el intérprete de en medio. **El shell entre quien mide y lo medido es una fuente
de error en los dos sentidos:** puede fabricar un verde y puede fabricar un rojo.

**3 · Ejecutar, no leer una representación.** Un test afirmaba que «cada transición del
código está reclamada o declarada», y lo comprobaba contra la tabla `_TRANSICIONES`. Pero
la función que decide el siguiente estado tiene dos caminos que **no consultan esa tabla**:
las averías se resuelven antes, y el destino de una reparación lo decide un contador.
Medido: **31 transiciones reales, 11 en la tabla, 20 invisibles.** Añadir una señal de
avería no ponía nada en rojo. El arreglo fue dejar de leer la estructura y **llamar a la
función** sobre todo el alfabeto. Una prueba sobre una representación del código solo vale
lo que valga la representación, y nada avisa cuando deja de ser fiel.

**4 · Quitar la pieza y mirar qué cae.** Un invariante que nunca se ha visto fallar no
distingue un sistema correcto de una comprobación vacía, y en especificación formal el
riesgo es mayor que en un test, porque es fácil escribir algo verdadero por vacuidad. Cada
invariante de `formal/tla/` tiene su ablación registrada con el resultado; el hook de
policy se desconectó para comprobar que **su ausencia tumba tres tests**; y al invariante
que **no** cayó al ablarlo se le buscó el porqué en vez de darlo por sólido — resultó ser
redundante y no vacuo, que son cosas distintas y solo una es un problema.

**Y un quinto que salió de aplicar los otros cuatro.** El mismo test de correspondencia
declara funciones aún no escritas en un campo `codigo_previsto`, y falla si alguna empieza
a existir. El mecanismo tenía un agujero: **solo avisa si la función nace con el nombre que
alguien adivinó.** La puerta de Lean aterrizó con otro nombre, el test siguió en verde y la
correspondencia quedó afirmando que estaba pendiente. Se cerró por el lado comprobable: si
el **módulo** donde se espera la función ya existe pero la función no, la zona aterrizó y
el nombre es sospechoso. No prueba que haya aterrizado, pero convierte el caso más probable
en rojo. **Un marcador de futuro que nadie puede incumplir no vigila nada**, que es la
advertencia de los umbrales de §5 aplicada a un test.

**Lo que las cinco tienen en común** es que ninguna comprueba el sistema: comprueban **la
comprobación**. Salen gratis cuando se piensan al escribir el test y son carísimas cuando
se descubren por un tropiezo, porque hasta entonces todo lo que ese test afirmaba estaba
sin sostener — y se había citado como evidencia.

## 6. El conjunto de validadores

Las tablas de §2 y §3 están ordenadas por método, y leídas así inducen a contar: ocho
métodos a nivel de artefacto, diez a nivel de proceso. La cuenta no significa nada. Lo
que se puede afirmar del sistema es lo que queda cubierto cuando se superponen los
puntos ciegos de §2.1 y §3.1, y eso no crece con el número de filas. Cuatro reglas para
leer este documento como un conjunto y no como un inventario.

### 6.1 Dos validadores que fallan por la misma causa cuentan como uno

La verificación multiagente del §3 descansa sobre una hipótesis que hasta ahora no
estaba escrita: que Escritor, Continuista, Crítico y Extractor fallan de forma
**independiente**. La separación por rol (`architecture.md` §12, decisión 6) compra parte
de esa independencia —quien escribe no se juzga a sí mismo— y no compra el resto:

- **Comparten proveedor, y desde el 2026-09-23 ya no el modelo.** P-02 fija **Haiku 4.5
  para escribir y Opus 5 para juzgar**, así que el Escritor y el Crítico dejan de tener el
  mismo sesgo por la vía más directa. **Es la primera mitigación real de este apartado** y
  conviene medir lo que compra y lo que no: rompe la correlación por *modelo*, no por
  *proveedor* —siguen siendo el mismo entrenamiento y la misma familia—, y no toca las tres
  causas de abajo. Un sesgo del proveedor lo siguen teniendo los cuatro a la vez.
- **Comparten la redacción de las restricciones.** Las restricciones duras se enuncian con
  las mismas palabras en todos los prompts (`CLAUDE.md` §10). Un malentendido en cómo está
  enunciada una restricción se propaga a todos los roles que la reciben.
- **Comparten la entrada.** Es la correlación más fuerte y la menos visible. El Continuista
  juzga la prosa contra el canon, pero lo que el Escritor no supo lo ignoraba porque no
  estaba en el paquete. Un fallo de ensamblado produce a la vez una prosa incompleta y un
  validador sin material para detectarlo.

**Regla de lectura:** al valorar la cobertura de un riesgo en §7, dos validadores
correlacionados cuentan como uno.

### 6.2 Determinista y probabilístico no dan la misma clase de confianza

| Clase | Cuáles son aquí | Qué permite afirmar |
| --- | --- | --- |
| **Determinista** | Contador de tokens y aritmética del presupuesto, esquemas de dominio, contraste contra el grafo de canon, máquina de estados del orquestador, `import-linter`, comprobación de tipos | Una garantía: con el mismo código y la misma entrada, el resultado se repite. Se puede construir encima |
| **Probabilístico** | Los agentes narrativos que llaman al modelo, **incluidos los que validan**: Continuista, Crítico y Extractor | Una señal con varianza. Una detección no repetida no prueba que el defecto exista; una no-detección no prueba que no lo haya |

De aquí sale una precisión que el diseño da por sabida y conviene dejar escrita: **la
puerta G1a es mecánica en el contraste, no en la extracción.** Quien decide qué afirma la
prosa es el Continuista, que es un modelo; quien decide si esa afirmación choca con el
canon es código. El criterio de éxito «cero falsos negativos en CAN y CON»
(`CLAUDE.md` §9) recae por tanto sobre un paso probabilístico: una afirmación que el
Continuista no extraiga no llega nunca al contraste determinista que la habría rechazado.

### 6.3 Lo que hoy mide a los validadores, y lo que no

- Los **tests de mutación** están aplazados (§2), así que lo único que mediría la suite
  está apagado.
- Hay **una** señal: la **tasa de defectos mal formados** (arq. §8.3 y §9). Es una medida
  del validador, no del código, y por eso vale. Pero **mide menos de lo que la v3.1
  afirmaba, y conviene decirlo con precisión: no mide al Continuista, mide su capacidad de
  copiar.** `comprobar_forma` comprueba dos cosas —que la cita esté literalmente donde dice
  que está, y que un `CAN-01` traiga un `hecho_canon_id` que exista—. Las dos son
  propiedades de la **transcripción**. Un modelo que copie el pasaje con exactitud y se
  invente entera la contradicción que ese pasaje supuestamente contiene saca el **100 %** en
  esta tasa. Sigue siendo la primera señal que existe, y sigue siendo barata; simplemente
  no es la que mide el juicio.
- Lo que esa señal **no** mide es la mitad que importa para la puerta: la **tasa de falsos
  negativos** del Continuista y del Extractor sigue sin medirse, porque no existe un
  conjunto de defectos conocidos contra el que puntuarlos. Un validador que calla no
  produce ningún registro que contar.
- El **Crítico** no tiene su correlación medida. Es el único de los tres cuya falta de
  validación tiene consecuencia declarada en el diseño: por eso G1b no bloquea
  (`architecture.md` §8.3). **Y el motivo ya no es «hasta que exista la calibración»**, que
  era una condición que se habría disparado sola en cuanto llegara la revisión humana de una
  novela: pasará a bloquear cuando la correlación esté medida sobre un conjunto etiquetado y
  **alguien lo firme con ese número delante**. Una novela mide la distancia entre dos jueces,
  no que el automático acierte.

Los tres son la misma carencia vista desde tres sitios, y explican por qué varias casillas
del §7 son «parcial» aunque exista un validador dedicado.

### 6.4 Qué se hace con esto

Este apartado no prescribe validadores nuevos: describe cómo se lee el conjunto que hay.
Cualquier validador añadido es un **requisito**, y los requisitos viven en una spec
(`CLAUDE.md` §3.2), no en `docs/`. Lo que sí pertenece aquí es la consecuencia de
añadirlo: qué casilla del §7 cambia de estado, y qué punto ciego de §2.1 o §3.1 deja de
estar descubierto.

## 7. Matriz de riesgo × validadores

Ordenada por **riesgo**, que es como se lee un conjunto: no «qué métodos tenemos», sino
«qué queda sin cubrir». Los riesgos son los de `architecture.md` §12 y los que se derivan
de los puntos ciegos de §2.1 y §3.1. Tres estados:

- **Cubierto** — más de un validador no correlacionado, y al menos uno determinista.
- **Parcial** — un solo validador, validadores correlacionados (§6.1), o cobertura de una
  parte del riesgo pero no de todo.
- **Descubierto** — hoy ningún validador lo detecta antes de que ocurra.

| Riesgo | Qué lo toca hoy | Estado |
| --- | --- | --- |
| El paquete se trunca en silencio | Propiedades sobre el ensamblador, `ContextBudgetExceeded`, desglose por capa persistido en `ejecucion` | **Cubierto** |
| Una llamada supera el techo de 100.000 tokens | Contador inyectado antes de llamar, propiedades, unitarios | **Cubierto** |
| Hay más llamadas en vuelo de las permitidas | Prueba de concurrencia sobre el limitador de llamadas en vuelo | **Cubierto** |
| Un trabajo interrumpido duplica escrituras | Tests de reanudación estado por estado, idempotencia por `run_id` | **Parcial** — la exhaustividad sobre los diez estados la sostiene quien escribe los tests, no un método |
| Una contradicción de canon pasa desapercibida | Continuista (extracción, probabilística) más contraste contra el grafo (determinista), más la comprobación de forma que exige `hecho_canon_id` en `CAN-01` (arq. §8.3) | **Parcial** — §6.2: lo que no se extrae no se contrasta, y esa tasa sigue sin medirse |
| **Un hecho nuevo, inventado, entra en el canon** | Nada. El Continuista contrasta contra lo ya sabido y un hecho que no contradice no colisiona; el Extractor lo consolida citando su escena de origen, que es trazabilidad, no veracidad. **La comprobación de forma de arq. §8.3 no alcanza aquí**: ata lo que afirma el Continuista sobre el texto, no lo que el Extractor escribe en el canon | **Descubierto** |
| Al paquete le falta un dato que la escena necesitaba | Nada antes del hecho; se observa después, como defecto de continuidad | **Descubierto** en prevención |
| La prosa excede el nivel de calor declarado | Esquema sobre el valor declarado (determinista) más lectura humana | **Parcial** — el juicio sobre la prosa no bloquea mientras G1b no bloquee |
| Contenido prohibido con menores | Validación en esquema, que bloquea por construcción, más inspección | **Cubierto** en lo tipificado |
| Prosa con instrucciones incrustadas realimentada como canon | El brief **adversarial** de las cinco evals, que ahora es obligatorio, más el red teaming del §3 | **Parcial** — el brief adversarial ataca por la puerta de entrada, el texto libre del **Comprador**. El vector que este documento describe es otro y sigue sin cubrirse: la instrucción que entra en la **prosa generada** y el Extractor consolida como canon |
| Un defecto inventado bloquea una escena o consume un reintento | Comprobación de forma en código antes de G1a: axiomas 11 y 12 de `definitions.md` §11 (arq. §8.3) | **Cubierto** |
| El modo sin extensión vectorial no es el que se prueba | Suite declarada en los dos modos | **Parcial** — §3.1: una prueba omitida se ve igual que el verde |
| El ledger deja de ser *append-only*, o el estado en T se edita | Lectura del repositorio (**A**) | **Parcial** — un solo validador, y humano |
| Un agente recibe una herramienta y las filas «Aplicado por diseño» caducan | La advertencia del §5, y **por primera vez se ha cumplido**: al conceder navegador al inspector visual, la fila se reabrió antes y el permiso quedó acotado en arq. §3.5.1 | **Parcial** — el aviso funcionó esta vez porque alguien lo leyó, no porque nada lo comprobara. Sigue sin haber método: la vez anterior, con el agente de código, la fila siguió afirmando lo contrario durante semanas |
| La revisión humana se degrada por volumen | Métrica de escalados por cada cien escenas (`architecture.md` §9), sin umbral declarado | **Parcial** |
| El coste total de la novela se dispara | Techo por llamada y límite de concurrencia | **Descubierto** en el total: acotan la llamada y el proceso, no la suma. §4.1 solo afirma el techo por llamada; el total es U (§4.2) |
| Un cambio de modelo descalibra a los validadores | Evals, ahora obligatorias, con cinco briefs y una iteración de tuning | **Parcial** — las evals detectan la descalibración **después** del cambio; nada la previene |
| **Una incoherencia temporal llega al lector** | Lean sobre la cronología (determinista, y **bloquea la publicación**) más el Continuista (probabilístico) | **Cubierto** — dos validadores no correlacionados y uno determinista. Es la casilla que justifica sola el coste de Lean |
| **Una palabra vetada por el Comprador llega al texto** | Guardarraíl léxico en código sobre cada capítulo, con normalización de mayúsculas, acentos y variantes, y tope de reintentos | **Parcial** — es comparación léxica: caza la palabra, no la alusión. Quien pidió no ver a su expareja no la nombra, y el tema puede entrar sin que ningún término de la lista aparezca |
| **El destinatario no se reconoce en la novela** | Cobertura de la personalización, contra la tabla de hechos (determinista) más el juez con rúbrica y la revisión humana | **Parcial** — la cobertura comprueba que el dato **está**, no que haga nada; que esté **integrado y no incrustado** solo lo juzga un juicio, y el juez comparte modelo con quien escribió |
| **El manuscrito del Destinatario sale a un servicio externo** | La decisión de `maujimenez4` del 2026-09-23, declarada en `CLAUDE.md` §4.3: sube el prompt renderizado, y con él la prosa, porque **cinco de los diez roles reciben el texto como entrada** —Continuista, Crítico, Editor de línea, Extractor y Auditor de manuscrito (arq. §7)—. Fuera de Langfuse no sale nada | **Aceptado, no cubierto** — es el único riesgo de esta tabla que no espera un validador: **está decidido a sabiendas**. Se registra porque una decisión sobre datos de un tercero que no está escrita se convierte en un descuido en cuanto cambia quien la tomó. Lo que sí queda sin método es comprobar que la última línea se cumple: nada vigila que un fragmento no acabe en otro log |
| **La especificación TLA+ deja de corresponder al código** | `formal/tla/correspondencia.toml` y el test que ejercita `maquina.transitar` junto a la máquina | **Parcial** *(2026-09-24)* — Un test recorre `transitar` **por ejecución** sobre todo el alfabeto y los dos lados del contador, y falla si una transición no está reclamada ni declarada, si una acción del modelo no aparece en la tabla, si un símbolo emparejado no existe, o si uno declarado *previsto* empieza a existir. **Mide el comportamiento y no la tabla, y esa diferencia no es teórica:** mientras comparaba contra `_TRANSICIONES` había **20 transiciones invisibles** de 31 —las tres averías de §3.6, que `transitar` resuelve antes de consultar la tabla, y las dos ramas del contador de `REPARANDO`—, y añadir una señal de avería no ponía nada en rojo. **Lo que sigue siendo I es que la acción haga lo que su nombre dice**: nada comprueba que `Publicar` publique. Tampoco cubre lo que el modelo no reclama —la cancelación del Autor y la avería técnica—, **declarado** con su motivo y no verificado, ni las tres acciones cuyo código aún no existe —la petición del lector y sus dos ramas, de la Fase 5— |
| Este documento deja de describir el repositorio | Revisión manual al aterrizar el código | **Descubierto** |

**Seis riesgos siguen descubiertos, y ninguno tiene ya la excusa de esperar a una fase
futura**, porque las dos que la tenían —red teaming y evals— han dejado de ser previsiones
y son obligatorias. Los seis son: el hecho nuevo que entra en el canon, el dato que le
faltó al paquete, el agente que recibe una herramienta, el coste total de la novela, la
correspondencia entre la especificación TLA+ y el código, y la deriva de este documento.

Conviene ver qué clase de cosa son, porque no es la misma. Cuatro son **huecos de método**:
nadie ha decidido cómo se comprobarían. Los otros dos —la correspondencia de TLA+ y la
deriva de este documento— son de una clase peor: **son afirmaciones que se hacen y que
nada vuelve a comprobar**. Una especificación formal verde sobre un código que ya no
implementa esa máquina no es cobertura ausente, es cobertura **falsa**, y afirma seguridad
sobre un sistema que no es el que se ejecuta.

Enumerarlos es el sentido de la matriz, igual que enumerar las U lo es del §4.2: un riesgo
sin casilla es un riesgo que se está corriendo sin decirlo.

## 8. Los validadores, uno a uno: dónde corren, qué bloquean y qué se les escapa

Las tablas anteriores ordenan por **método** (§2, §3) y por **riesgo** (§7). Este es el eje
operativo, el que hace falta para construir el sistema y el único que permite comprobar que
la afirmación «cada validador corre en un punto concreto» es cierta y no un deseo.

Cuatro columnas, y la última es la que da valor a las otras tres. **Dónde corre** decide qué
información tiene disponible: uno que corre en el *hook* del capítulo no puede mirar la
novela entera. **Qué bloquea** separa verificación de telemetría — uno que se ejecuta y no
detiene nada informa, no verifica. Y **qué no detecta** es lo que impide leer esta tabla
como una lista de defensas: un catálogo sin puntos ciegos se cuenta, y contar no es cubrir.

**Todos emiten *score* a Langfuse salvo `spec_tla`**, que corre en desarrollo y no dentro de
una generación. Un validador que no emite score no es comprobable a posteriori: no se puede
decir si mejoró o empeoró entre dos versiones de prompt.

**Esa frase es la regla, no el estado.** Lo que **hoy emite en producción**, en el span del
validador que lo produce (`architecture.md` §9.2.1): `palabras_vetadas`, los validadores de la
puerta G1a que corren —`extension_de_capitulo`, `nombres_literales`, `discurso` y
`continuidad_y_canon`— y `juez_con_rubrica`, uno por criterio. Son los del ciclo del capítulo, y
quitar cualquiera de las tres llamadas que los emiten —policy, G1a, juez— pone rojo un test
(comprobado quitándolas una a una). Los demás de esta sección
todavía no emiten: o no corren en una generación o corren sin span.

### 8.1 Programáticos — deterministas

**En la configuración, puerta G0.**

| Nombre | Dónde corre | Qué bloquea | Qué no detecta |
| --- | --- | --- | --- |
| `esquema_de_brief` | Al cerrar la entrevista | No se planifica con un brief inválido | Que el brief diga lo que el comprador quería decir. Un brief válido puede describir a otra persona |
| `contradiccion_en_brief` | Al cerrar la entrevista | `CFG-01`: se resuelve **en la entrevista**, no escribiendo | Solo ve las contradicciones **tipificadas** —edad contra tono, contra género—. Dos recuerdos aportados que no encajan entre sí pasan enteros |
| `texto_aportado_marcado` | Al entrar el `TextoAportado` | Que el texto del comprador llegue a un prompt sin su marca de dato | Que el contenido marcado sea inofensivo. Marca el origen; no juzga el texto |

**Por capítulo, en el *hook* de validación.**

| Nombre | Dónde corre | Qué bloquea | Qué no detecta |
| --- | --- | --- | --- |
| `esquema_de_salida_de_rol` | Tras cada llamada a un rol | Salida mal formada: es fallo del paso, no resultado vacío | Nada del contenido. Un JSON perfecto puede afirmar una barbaridad |
| `extension_de_capitulo` | *Hook* | `EST-02`: fuera del rango declarado | Si lo que sobra o falta es lo correcto. Un capítulo en rango puede ser todo relleno |
| `nombres_literales` | *Hook* | `PER-02`: un nombre escrito distinto que en el canon | El nombre **inventado y coherente**: si el personaje no está en el canon, no hay contra qué comparar |
| `giro_de_valor` | *Hook*, sobre la ficha | `EST-01`: valor de entrada y de salida iguales o nulos | Que la prosa **entregue** el giro que la ficha declara. Eso es juicio y vive en G1b |
| `nivel_de_calor` | *Hook* | `SEG-01`: término por encima del nivel declarado | Lo que excede sin vocabulario explícito. Es léxico: cierra el camino fácil, no entiende la escena |
| `edad_minima` | Esquema, al crear personaje | Contenido romántico con menores; **bloquea por construcción** | La insinuación sobre un personaje **sin edad declarada**. Lo que protege es el campo, y un campo vacío no dispara nada |
| `discurso` | *Hook* | `VOZ-03`: persona o tiempo verbal distintos de los declarados | La deriva de voz: que el capítulo 8 no suene como el 2 respetando los dos. Y excluye el diálogo a propósito |
| `palabras_vetadas` | *Hook* de *policy*, antes de aceptar | `SEG-02`, con tope de intentos; agotado, **se detiene la generación** | La alusión. Quien pidió no leer sobre su expareja no la nombra: el tema entra sin que ningún término de la lista aparezca |
| `continuidad_y_canon` | Puerta G1a | `CAN-01`, `CON-01` y `CON-03` contra el grafo | **Lo que el Continuista no extrae no se contrasta** (§6.2). El contraste es determinista; la extracción de la que depende, no |
| `presupuesto_de_contexto` | Antes de **cada** llamada al modelo | `ContextBudgetExceeded`: nunca un truncado silencioso | Que el paquete que cabe sea el **pertinente**. Los números cuadran igual con el contexto equivocado |
| `techo_concurrente` | Antes de conceder turno de modelo, en el orquestador | Que la **suma de tokens de las llamadas en vuelo** supere 100.000 (encargo §7, línea 264: «máximo de 100.000 tokens **concurrentes**») | Que el reparto sea el bueno: dos llamadas de 50.000 pasan igual que una de 100.000, y una de ellas puede ser la equivocada. **Esta fila nació el 2026-09-23 declarando que no podía dispararse, porque la concurrencia era uno — y la decisión de P-06 la activó el mismo día.** Desde entonces es el **único** validador que comprueba lo que pide el encargo §7: `presupuesto_de_contexto` acota cada llamada por separado y **nadie más suma** |
| `limite_de_reintentos` | Orquestador, en cada reparación | Superar el tope: la única salida pasa a ser `DETENIDA` | Si los intentos gastados sirvieron de algo. Cuenta reintentos, no progreso |

**En la memoria.**

| Nombre | Dónde corre | Qué bloquea | Qué no detecta |
| --- | --- | --- | --- |
| `hecho_usado_en` | Al integrar un capítulo | Un hecho sin registro de en qué capítulos se usa: sin eso no se puede regenerar tras una corrección | Si el hecho se usó **bien**. Registra dónde apareció, no si hacía algo allí |
| `checkpoint_reanudacion` | Al reanudar tras una caída | Duplicar o perder un capítulo | Los estados que nadie probó. La exhaustividad la sostiene quien escribe los casos — por eso `spec_tla` cubre el mismo requisito por otra vía |

**En la publicación, puerta G4.**

| Nombre | Dónde corre | Qué bloquea | Qué no detecta |
| --- | --- | --- | --- |
| `cobertura_de_personalizacion` | G4 | `PER-01`: un elemento obligatorio que no aparece en ningún capítulo | Si está **integrado o incrustado** (`domain-knowledge.md` §14.1). Comprueba presencia, y la presencia es lo barato |
| `dedicatoria_fuera` | G4 | Que la dedicatoria entre como fragmento del manuscrito, al PDF como capítulo o a la lista de n-gramas | Si la dedicatoria es buena, ni si va dirigida a quien debe |
| `inspeccion_visual` | G4, sobre la lectura publicada | Índice, ficha de personajes o portada que no renderizan | Que lo que se ve sea **correcto**: un índice con once entradas para diez capítulos renderiza perfectamente |

**En la lectura publicada.** Los cuatro que siguen comprueban **lo que el `Destinatario` recibe**, no el código que lo produce —esa distinción y por qué importa, en §8.5—. Corren donde corre `inspeccion_visual` y emiten *score* como cualquier otro.

| Nombre | Dónde corre | Qué bloquea | Qué no detecta |
| --- | --- | --- | --- |
| `no_revelado_no_se_envia` | G4, sobre la respuesta de la ficha | Que un personaje aún no revelado **llegue al navegador**, aunque no se pinte (`RF-FIC-04` de la 002) | Lo que se revela **de más por otra vía**: un resumen, un título de capítulo o la propia dedicatoria pueden nombrar a quien la ficha esconde |
| `prosa_como_texto` | G4, sobre cada capítulo renderizado | Que el manuscrito se interprete en vez de mostrarse: un capítulo con `<script>` se lee, no se ejecuta (`RF-EST-04`) | Que el texto **diga** algo dañino. Comprueba que no se ejecuta, no que sea inofensivo — y el manuscrito lo escribió un modelo sobre texto que aportó un `Comprador` |
| `accesibilidad` | G4, sobre las rutas publicadas | Violaciones mecánicas: contraste, etiquetas de formulario, foco, orden de encabezados | **Casi todo lo que importa.** Las reglas automáticas cazan una fracción de lo que encuentra una persona con un lector de pantalla: una página puede pasarlas enteras y ser inservible. `CLAUDE.md` §7 ya lo dice — renderizar no es ser accesible, y pasar `axe-core` tampoco |
| `rutas_estables` | G4, antes de `inspeccion_visual` | Que portada, índice, capítulo y ficha cambien de URL (`RNF-REN-01`) | Nada del contenido. **Existe para proteger a otro validador:** si una ruta cambia, `inspeccion_visual` abre una página que no es y sigue dando verde. Es el único de los veintiocho cuyo objeto es que otro no mienta |

### 8.2 Semánticos

| Nombre | Dónde corre | Qué bloquea | Qué no detecta |
| --- | --- | --- | --- |
| `juez_con_rubrica` | Puerta G1b, por capítulo | **Hoy no bloquea** — sin correlación medida ni firmada (§6.3) | La calidad que nadie supo enunciar en la rúbrica. Ya **no** comparte modelo con quien escribe —Opus 5 juzga, Haiku 4.5 escribe (P-02)—, pero sí proveedor y familia: la correlación baja, no desaparece (§6.1) |
| `revision_humana` | El **Autor**, fuera del bucle, sobre una novela completa | No bloquea: **produce el patrón** contra el que se mide el juez | Si alguno de los dos jueces acierta. Mide la distancia entre ellos, y una rúbrica común empuja a que compartan sesgo |

### 8.3 Formales

| Nombre | Dónde corre | Qué bloquea | Qué no detecta |
| --- | --- | --- | --- |
| `cronologia_lean` | G4, en cada publicación | **No se publica.** El fallo vuelve al editor | Lo que nunca llegó a la biblia. Demuestra sobre el fichero generado desde la cronología, no sobre la prosa |
| `spec_tla` | **En desarrollo**, no en generación | Nada en ejecución: su resultado cambia el código o la especificación | Que la acción haga lo que su nombre dice. Que las dos listas de transiciones coincidan **sí lo comprueba un test** (§7) |

### 8.4 Qué deja ver este eje y los otros dos no

**De los veintiocho, tres no bloquean nada y uno de esos tres no corre siquiera en producción.** El juez con
rúbrica es el más caro de los dos semánticos y hoy es telemetría. No es un defecto de la
tabla: es el estado real, y verlo en una columna evita contar veintiocho validadores como veintiocho
defensas.

**La concentración en G4.** Cobertura de personalización, dedicatoria, inspección visual y
Lean bloquean al final, con la novela ya escrita. Es el sitio correcto —ninguno es
comprobable sobre un capítulo suelto— y a la vez el más caro: un fallo en G4 no cuesta un
capítulo, cuesta lo que haya que rehacer. Conviene saberlo antes de calcular plazos.

**Y el patrón que recorre la última columna.** Casi todos los puntos ciegos son la misma
misma frase dicha de veinte maneras: **el validador comprueba la forma y no el fondo**. El
esquema no juzga el contenido, la extensión no juzga el relleno, la cobertura no juzga la
integración, el renderizado no juzga la corrección. Es una propiedad de lo determinista, no
un defecto de diseño — pero explica por qué los dos semánticos, que son los únicos que miran
el fondo, son también los únicos que hoy no detienen nada.

### 8.5 Por qué las comprobaciones de la *build* del frontend no entran en esta tabla

Al añadir los cuatro de la lectura publicada se planteó si el resto de lo que pide la 002
—las tres reglas de frontera de `CLAUDE.md` §5.2 por ESLint, que no haya `any`, que el
cliente de API sea el **generado** del OpenAPI y no escrito a mano— debía entrar aquí
también. **No entra, y el motivo separa dos cosas que es fácil confundir.**

El corte no es *cuándo* corre —en una generación o en la *build*—, que es donde uno mira
primero. Es **qué verifica**, y es el corte de §1 de este documento:

| | Verifica | Dónde vive |
| --- | --- | --- |
| Los veintiocho de §8 | **La novela**: lo que se le entrega a alguien | Este catálogo |

> **El número veintiocho está escrito a mano y nada lo comprueba.** Aparece en **cuatro sitios de este documento** —la fila `rutas_estables` de §8, dos veces en §8.4 y la fila de arriba—, así que un validador nuevo obliga a tocar los cuatro. Se deja dicho en vez de inventar un mecanismo: contar las filas de la tabla de §8 que empiezan por el nombre del validador da el número, y el 2026-09-24 dio **28**, que es el que está escrito. *(Quien añada uno: contó con `grep` y comprobó los cuatro sitios, no solo el que tenía delante.)*
| ESLint, `tsc`, cliente generado | **El código** que la fabrica | §2, nivel de artefacto |

`fronteras_frontend` es el gemelo exacto de `import-linter`, que nunca estuvo en esta tabla
y sí en §2; `sin_any` es comprobación de tipos; el cliente generado es un test de contrato.
Los tres ya tienen sitio, y están en la tubería de `CLAUDE.md` §15 que la fila de CI/CD de
§3 describe. Meterlos aquí no añadiría cobertura: **duplicaría el mismo control en dos
inventarios**, que es como se llega a dos listas que divergen.

**La consecuencia práctica importa más que la taxonomía, y es la razón de escribir esto:**
así **`RF-VAL-01` de la 001 no necesita una excepción nueva**. Aquel requisito dice que todo
validador que corre dentro de una generación emite su *score*, con TLC como única excepción.
Los cuatro de la lectura publicada corren en G4 y emiten; los de la *build* nunca fueron
validadores en el sentido de aquel requisito. **La 001 está firmada y no hay que tocarla.**

§2 y §3 ya las nombran con esa concreción: `tsc` estricto y el `as unknown as T` que lo
burla en la fila de tipos, `import/no-restricted-paths` en la de análisis estático —gemela
de `import-linter`—, y el cliente generado en la de contrato, **con la advertencia de que
hoy nada comprueba que nadie escriba un tipo a mano**. Esa es la única de las tres que no
tiene mecanismo, y por eso está dicha y no dada por hecha.

## 9. Registro de cambios

| Versión | Qué cambió |
| --- | --- |
| 1.0 | Catálogo de metodologías con veredicto por método, y clasificación T/A/I/D/U de los requisitos del proyecto |
| 2.0 | Se separan los dos sujetos del §1, se detalla el estado de cada método en este repositorio y se nombra lo que es U |
| 3.0 | El documento pasa de catálogo a conjunto: §2.1 y §3.1 añaden el punto ciego de cada método; §6, las reglas del conjunto —independencia correlacionada, determinista frente a probabilístico, quién mide a los validadores—; §7, la matriz de riesgo × validadores con los descubiertos. §4 fija la letra principal con refuerzo; §4.1 anota que la reproducción del paquete caduca con el estado de almacenes y que el techo por llamada no acota el total; §4.2 separa pertinencia de presencia y añade el hecho nuevo que no contradice nada |
| **4.1** | **Pasada de coherencia cruzada con `architecture.md`, hecha por dos sesiones por separado y fundida en un plan.** La fila de supresión del alcance se cruzó con la del navegador: **la primera resultó no estar caducada**, porque el validador visual es código conduciendo un navegador y no un agente (arq. §3.5.1), y quien sí recibe la herramienta es el **agente de código**. Se afila igualmente a «los diez agentes narrativos» y se deja escrito que la formulación original sobrevive, para que nadie la debilite otra vez por el mismo camino. G1b deja de no bloquear «hasta que exista la calibración» —condición que se habría disparado sola— y pasa a exigir correlación medida **y firmada**. Entran en §4.1 las dos reglas de `CLAUDE.md` §8 que no tenían letra: la **10** (`VOZ-03`), sin clasificar desde la v1.3 y única regla con código de defecto propio y sin ella, y la **15**. Y las reglas 11 a 14 pasan a citarse también por su número, no solo por su origen en el encargo |
| **4.0** | **Al cruzar el documento contra `docs/entregable/examen-final.md`, dos veredictos se invierten y uno se corrige.** Verificación formal deja de ser «No aplicable»: entra **Lean 4** sobre la cronología, con dos invariantes y **puerta de publicación** (§2). Comprobación de modelos deja de ser «No aplicable, por ahora»: entra **TLA+ con TLC** sobre el harness, con tres invariantes de seguridad y una de liveness (§3). Las **evals** dejan de esperar a la fase 4 y son obligatorias, con cinco briefs —uno adversarial y uno de trampa temporal— y una iteración de tuning; entran además el **juicio por modelo con rúbrica** y la **revisión humana con la misma rúbrica**, que es lo que convierte la calibración del Crítico en dato. §4.1 clasifica los once requisitos nuevos, §8 es nueva —cada validador con su nombre, dónde corre y qué bloquea, que es el eje que faltaba—, entra la **inspección visual por browser MCP** (§3), que era el único método del encargo ausente, §7 gana cuatro riesgos —incoherencia temporal, palabra vetada, el destinatario que no se reconoce y la correspondencia TLA+/código— y el porqué de las dos inversiones está en el §10. **Corrección de hecho:** §6.3 decía que la tasa de defectos mal formados mide al Continuista; no lo mide a él, mide su capacidad de copiar |
| 3.1 | Se clasifican los axiomas 11 y 12 y la comprobación de forma previa a G1a (§4.1), y la matriz gana la casilla que cubren (§7). El punto ciego de los tests de contrato (§2.1) se corrige: la comprobación de forma elimina el defecto bien formado con la cita inventada. §6.3 deja de decir que nada mide a los validadores: la tasa de defectos mal formados es la primera señal, y se nombra lo que no alcanza. Guardarraíles deja de mezclar los dos sujetos (§3) |

*La v3.0 se commiteó en `aa47bd0`, que arrastró también la v1.2 de `definitions.md` y la v1.3 de `architecture.md`; el mensaje de ese commit describe solo esta. Queda dicho aquí en vez de reescribir la historia: el trabajo que se mezcló no era de quien escribió el commit, y el registro de cada documento es donde se busca una versión.*

## 10. Por qué la v4.0 da la vuelta a dos decisiones

Las versiones 2.0 a 3.1 añadían filas y matices. La v4.0 **invierte dos veredictos que
estaban razonados**, y conviene que quede escrito por qué, porque en los dos casos lo que
había no era un descuido: era la respuesta correcta a otra pregunta.

**1 · La verificación formal pasa de «No aplicable» a obligatoria.**

El argumento de la v3.1 era: las invariantes que merecerían demostración —el estado en T
deriva del ledger, ningún paquete supera los 100.000 tokens— se garantizan **por
construcción**, y construirlas sale más barato que demostrarlas. **Ese argumento sigue
siendo cierto, y no es el que se ha invertido.** Hablaba de demostrar cosas sobre el
**código**, y ahí la conclusión no cambia.

Lo que entra es otra cosa: demostrar sobre la **historia**. La cronología de una novela no
se garantiza por construcción —nada impide que un personaje esté en dos sitios a la vez
salvo que alguien lo compruebe— y no es el tipo de propiedad que un test cubre bien,
porque hay que comprobarla sobre **todos** los pares de eventos, no sobre los que a alguien
se le ocurrieron. La fila decía «No aplicable» porque la pregunta que se hacía era sobre el
código; el examen §5c hace la pregunta sobre la historia, y para esa la respuesta era otra
desde el principio.

**2 · La comprobación de modelos pasa de «No aplicable, por ahora» a obligatoria, y el
«por ahora» estaba bien puesto.**

Aquí la v3.1 dejó escrita su propia condición de caducidad: la máquina de estados es
pequeña, la cubren los tests, y **se reconsidera si aparece concurrencia real o se levanta
la restricción de una escena en vuelo**. No ha aparecido concurrencia, pero han aparecido
tres ejes que no estaban: **publicación de versiones**, **checkpoint por capítulo** y
**regeneración parcial por petición del lector**. Los tres se multiplican entre sí, y el
producto de los tres es exactamente el tipo de espacio donde los tests eligen caminos y un
model checker los recorre todos.

La lección que conviene retener no es que la decisión fuera mala: es que **caducó por donde
no se esperaba**. Se escribió una condición de reapertura —concurrencia— y la realidad
reabrió el asunto por otra puerta. Una fila con condición de caducidad sigue necesitando
que alguien la relea cuando el producto cambia, porque la condición que se escribe es la
que se imagina.

**Y lo que no se toca.** Los dos métodos entran como **puertas reales**: si Lean falla, no
se publica. Eso los pone en el mismo sitio que el presupuesto de contexto —fallar antes, no
avisar después— y es la línea que este documento no cruza: un validador que se ejecuta y
cuyo resultado no bloquea nada no es verificación, es telemetría.
