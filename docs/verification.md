# Verificación — StoryMaker

**Versión:** 3.1 · **Fecha:** 2026-09-22

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
| **Agentes narrativos** | Los nueve roles del producto —Arquitecto, Escritor, Continuista, Crítico, Extractor…— que se ejecutan en producción para generar una novela | `architecture.md` §7 |
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
| Comprobación de tipos | Verificación automática de que los valores se usan de forma coherente con lo que las operaciones esperan de ellos | **Previsto** — línea base de las dos aplicaciones: `mypy` estricto sobre `commons/domain/` y los `service.py`, TypeScript estricto sin `any`. El cliente del frontend se **genera** del OpenAPI, así que una ruptura de contrato es error de compilación y no un 422 en ejecución. Pydantic v2 añade la comprobación equivalente en ejecución, en la frontera | [Type system](https://en.wikipedia.org/wiki/Type_system) |
| Análisis estático / SAST | Escanear el código fuente sin ejecutarlo, contrastándolo con patrones conocidos como defectuosos | **Previsto** — es lo que hace verificables las fronteras. `ruff` y ESLint son la línea base; lo que aporta de verdad es `import-linter` (arq. §5.2) e `import/no-restricted-paths` (arq. §6.2): las reglas de dependencia entre features son afirmaciones sobre el código fuente, se comprueban sin ejecutarlo y fallan la build | [Static program analysis](https://en.wikipedia.org/wiki/Static_program_analysis) |
| Ejecución simbólica | Ejecutar el código con entradas simbólicas para derivar las condiciones exactas de fallo mediante un solucionador SMT | **No aplicable** — la única lógica numérica con condiciones de fallo interesantes es la aritmética de presupuesto del ensamblador, y ahí un test basado en propiedades da la misma respuesta por mucho menos | [Symbolic execution](https://en.wikipedia.org/wiki/Symbolic_execution) |
| Verificación formal / demostración de teoremas | Demostrar matemáticamente que el código satisface una especificación para todas las entradas posibles | **No aplicable** — las invariantes que merecerían demostración (el estado en T deriva del ledger; ningún paquete supera los 100.000 tokens) se garantizan **por construcción**: ledger *append-only*, vista derivada y `ContextBudgetExceeded`. Construirlas sale más barato que demostrarlas | [Formal verification](https://en.wikipedia.org/wiki/Formal_verification) |
| Tests unitarios / de integración | Comprobar el comportamiento frente a entradas concretas elegidas y salidas esperadas | **Previsto** — método principal a nivel de artefacto. `pytest` con `pytest-asyncio`; test colocado junto al componente en el frontend. Dos reglas del proyecto lo sostienen: toda regla de dominio de `CLAUDE.md` §8 tiene su test, y el cliente de modelo se inyecta, de modo que ninguna prueba llama al proveedor | [Unit testing](https://en.wikipedia.org/wiki/Unit_testing) |
| Tests basados en propiedades | Especificar una propiedad general y generar muchas entradas para buscar una violación | **Previsto** — dirigido al **ensamblador de contexto**, que es donde los ejemplos elegidos se quedan cortos. Propiedades: el desglose por capa suma el total contado; recortar una capa no altera las demás; las capas constitucional e instrucción nunca encogen; o el paquete cabe en 100.000 tokens o se lanza `ContextBudgetExceeded`, nunca un truncado silencioso | [QuickCheck — Claessen y Hughes, 2000](https://www.cs.tufts.edu/~nr/cs257/archive/john-hughes/quick.pdf) |
| Tests de mutación | Introducir deliberadamente pequeños fallos para comprobar si la suite de tests los detecta | **Aplazado** — tendrá sentido cuando exista la suite del ensamblador, porque es precisamente la suite en cuya luz verde estaremos tentados de confiar para afirmar que el contexto nunca se recorta a escondidas. Hoy no hay suite que mutar | [Mutation testing](https://en.wikipedia.org/wiki/Mutation_testing) |
| Tests de contrato | Verificar que la interfaz entre dos servicios se mantiene coherente, con independencia de sus interioridades | **Previsto, y en parte por construcción** — hay tres fronteras de este tipo: el OpenAPI entre backend y frontend (el cliente se genera, no se escribe a mano); el `__init__.py` de cada feature como única superficie importable; y la E/S de cada agente narrativo, que es un contrato real —el Continuista devuelve **códigos de defecto con cita**, nunca prosa corregida— y por tanto se valida con esquema y se prueba | [Contract Test — Martin Fowler](https://martinfowler.com/bliki/ContractTest.html) |

### 2.1 Lo que no detecta cada método

Una fila de la tabla anterior sin su punto ciego es una promesa. Aquí está el reverso de
cada una, incluidas las descartadas: saber qué se escapa de un método que **no** se usa
es lo que impide volver a proponerlo como solución de algo que tampoco resolvería.

| Metodología | Qué no detecta |
| --- | --- |
| Comprobación de tipos | Habla de forma, no de significado. Un programa bien tipado puede hacer exactamente lo contrario de lo que debe: que `escena_de_origen` sea una cadena no dice que apunte a una escena que exista, ni que sea la escena correcta |
| Análisis estático / SAST | Solo encuentra lo que alguien supo describir como patrón. Las fronteras que comprueba son las **declaradas como import**: un acoplamiento real por inyección, por configuración o por nombre de tabla no es un import y no aparece |
| Ejecución simbólica | Descartada, y aunque se adoptara resolvería la aritmética del paquete, no su contenido. Un paquete cuyos números cuadran puede ser el paquete equivocado |
| Verificación formal | Demuestra que el código cumple **la especificación escrita**; si la especificación es la equivocada, la demostración es correcta y el sistema está mal. Aquí, además, está descartada, así que lo que sostiene las invariantes «por construcción» es una lectura del repositorio, no una comprobación |
| Tests unitarios / de integración | Comprueban los casos que a alguien se le ocurrieron. No dicen nada del caso que no se escribió, y su luz verde crece con el número de tests, no con su calidad |
| Tests basados en propiedades | Buscan violaciones de la propiedad **enunciada**. La propiedad que nadie enunció no se busca: que el paquete quepa y respete los topes no dice que contenga lo que la escena necesitaba |
| Tests de mutación | Miden la suite, no el código: un mutante muerto prueba que algún test reacciona a ese cambio, no que el comportamiento sea correcto. Y están aplazados, de modo que hoy nada mide la suite |
| Tests de contrato | Verifican la **forma** del intercambio, y desde arq. §8.3 la forma de un defecto incluye que su cita sea subcadena real del texto que señala: la categoría del **defecto bien formado con la cita inventada ha desaparecido**. Queda lo que ninguna comprobación de forma alcanza: el defecto cuya cita es real pero cuyo **diagnóstico** es equivocado, y el que el Continuista no llegó a emitir |

## 3. Verificación a nivel de proceso

| Metodología | Definición | Estado aquí | Explicación |
| --- | --- | --- | --- |
| Observabilidad / trazas en ejecución | Instrumentar el agente para que su trayectoria sea visible y consultable a posteriori | **Aplicado por diseño (narrativos)** — cada llamada registra `run_id`, escena, versión de prompt y de biblia, IDs recuperados, modelo, parámetros, semilla, tokens por capa, coste y veredicto (arq. §9). Matiz: arq. §11 prohíbe registrar por defecto los prompts de producción y los fragmentos de manuscrito, así que la traza es **estructural, no textual**: dice qué se envió y cuánto costó, no qué decía | [Observability primer](https://opentelemetry.io/docs/concepts/observability-primer/) |
| Evals | Pruebas estructuradas del comportamiento del agente contra un conjunto de datos y un método de puntuación | **Previsto (narrativos)** — fase 4 de la hoja de ruta. El criterio de éxito del Crítico es «correlación con el editor humano», y eso *es* una eval: un conjunto de escenas etiquetadas por una persona contra el que se puntúa al juez. Sin él no se distingue un cambio de prompt que mejora de uno que solo desplaza la salida, ni se detecta la descalibración al cambiar de modelo (riesgo abierto de arq. §12) | [HELM — Liang et al., 2022](https://arxiv.org/abs/2211.09110) |
| Ejecución en sandbox *(narrativos)* | Ejecutar el código del agente en un entorno aislado para que las acciones dañinas fallen sin consecuencias | **Sustituido por supresión del alcance** — los agentes narrativos no ejecutan código, y el Escritor no accede a la base de datos: solo ve el paquete recibido (arq. §3.5). Se **elimina** el radio de impacto en lugar de contenerlo: más fuerte que un sandbox, y cierto mientras ningún agente reciba una herramienta | [Sandbox (computer security)](https://en.wikipedia.org/wiki/Sandbox_%28computer_security%29) |
| Ejecución en sandbox *(agente de código)* | Lo mismo, aplicado al asistente que escribe este repositorio | **No aplicado** — el agente de código lee y escribe ficheros y ejecuta órdenes directamente: no hay entorno aislado ni intermediario que lo haga por él. Lo que acota el daño es otra cosa, y está dos filas más abajo: toda escritura pasa por una persona, y por la tubería de `CLAUDE.md` §15. Hasta el 2026-09-22 esta fila afirmaba lo contrario —que corría sin herramientas de fichero— y siguió afirmándolo después de dejar de ser cierto | [Sandbox (computer security)](https://en.wikipedia.org/wiki/Sandbox_%28computer_security%29) |
| Guardarraíles *(narrativos)* | Políticas y filtros que restringen qué acciones puede producir un agente | **Aplicado en código** — edad mínima y nivel de calor se validan **en esquema**, no en el prompt (arq. §11); el presupuesto de contexto falla explícitamente en vez de truncar; el reintento dirigido tiene tope de dos; cada agente recibe el mínimo de permisos que su nodo necesita (arq. §3.5); y un defecto mal formado no llega a la puerta (arq. §8.3). Regla que lo sostiene: ninguna regla de seguridad depende solo del prompt | [AI Risk Management Framework — NIST](https://www.nist.gov/itl/ai-risk-management-framework) |
| Guardarraíles *(agente de código)* | Lo mismo, aplicado al asistente que escribe este repositorio | **Aplicado, pero a posteriori** — no hay filtro sobre lo que el agente puede producir: hay una tubería que lo rechaza después. Las fronteras entre features fallan la build, `mypy` es estricto sobre `commons/domain/` y los `service.py`, y el proceso de `CLAUDE.md` §3 no deja entrar código sin spec y plan aprobados. La diferencia con la fila de arriba importa: allí el guardarraíl impide, aquí detecta | [AI Risk Management Framework — NIST](https://www.nist.gov/itl/ai-risk-management-framework) |
| Revisión humana en el bucle | Una persona aprueba, rechaza o edita las acciones de alta consecuencia del agente | **Aplicado (ambos), con puntos definidos** — G1a escala a la persona tras dos reparaciones fallidas; G3 no cierra borrador sin revisión; el arco romántico figura en la tabla de dimensiones de calidad como «revisión humana». En el repositorio, toda escritura del agente de código pasa por una persona | [Human-in-the-loop](https://en.wikipedia.org/wiki/Human-in-the-loop) |
| Verificación multiagente | Patrones de crítico, debate, autoconsistencia, reflexión o ensamblado que revisan la salida del modelo | **Aplicado (narrativos): es el mecanismo central de calidad, no una opción en estudio** — Continuista y Crítico existen separados del Escritor exactamente por esto (decisión 6 de arq. §12: quien escribe no ve sus contradicciones, y quien juzga no repara). Coste asumido: la puerta de escena gasta hasta dos validaciones además de la escritura. Límite conocido y ahora explícito en el diseño: el juez no está calibrado, así que **G1b no bloquea** hasta la fase 4 (arq. §8.3); lo que hoy aporta es detección de contradicciones, no juicio de calidad | [AI Safety via Debate — Irving et al., 2018](https://arxiv.org/abs/1805.00899) |
| Integración en CI/CD | Hacer pasar los cambios generados por el agente por la misma tubería que los escritos por personas | **Previsto (agente de código)** — sin una vía aparte y más débil para los diffs del agente. La tubería es la lista de `CLAUDE.md` §15: `ruff`, `mypy`, `pytest`, `lint-imports`, `pnpm typecheck`, `pnpm lint` y migraciones de Alembic. Exigencia propia de este proyecto: la suite debe correr **en los dos modos de `VectorStore`**; si solo se ejecuta con `sqlite-vec` cargado, el modo degradado que promete arq. §2 no está verificado | [Continuous integration](https://en.wikipedia.org/wiki/Continuous_integration) |
| Despliegue progresivo | Enviar un cambio a un pequeño porcentaje del tráfico tras un flag antes de la publicación completa | **No aplicable** — el modo de referencia es local, con un fichero SQLite por obra (arq. §10): no hay tráfico que repartir. Lo que sí cumple la función de comparar variantes sin desplegar son las versiones de texto inmutables y la comparación de estrategias de contexto de la fase 6 | [Feature toggle](https://en.wikipedia.org/wiki/Feature_toggle) |
| Red teaming / pruebas adversarias | Sondear deliberadamente en busca de fallos bajo un modelo de amenaza adversario | **Previsto (narrativos), con modelo de amenaza concreto** — la vía realista no es un atacante externo, es el propio bucle: el Extractor convierte prosa generada en canon, de modo que un texto con instrucciones incrustadas se realimenta al sistema por un canal legítimo. Segundo objetivo: empujar desde el brief contra los guardarraíles de edad y nivel de calor, para comprobar que lo que aguanta es el esquema y no el prompt | [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/) |
| Comprobación de modelos | Explorar exhaustivamente los estados y transiciones alcanzables del agente para verificar invariantes | **No aplicable, por ahora** — la máquina de estados del orquestador es explícita desde que existe arq. §3.3: diez estados y transiciones cerradas, más las cuatro puertas y los dos reintentos. Sigue siendo lo bastante pequeña para que la cubran los tests, y lo que la mantiene tratable es la restricción de **una escena en vuelo por obra** (arq. §3.8). Se reconsidera si esa restricción se levanta o si aparece concurrencia real de escritura sobre una misma obra | [Model checking](https://en.wikipedia.org/wiki/Model_checking) |

### 3.1 Lo que no detecta cada método

Una entrada por **método**, no por fila: dos de ellos —sandbox y guardarraíles— aparecen
en §3 partidos por sujeto, y el punto ciego que sigue es el del método, común a los dos.

| Metodología | Qué no detecta |
| --- | --- |
| Observabilidad / trazas | Registra lo que se decidió registrar, y aquí, a propósito, no el texto. La traza dice qué se envió y cuánto costó, **no si lo enviado era lo que la escena necesitaba**: un fallo de pertinencia del ensamblado es invisible en ella |
| Evals | Puntúan contra un conjunto y un criterio, y miden lo que ese conjunto representa. Sin conjunto etiquetado —hoy— no miden nada; con él seguirán sin ver lo que no esté representado |
| Sandbox / supresión del alcance | Acota el daño, no la corrección: un agente sin herramientas produce texto equivocado con la misma facilidad que uno con ellas. Y la propiedad depende de una configuración de permisos que nada vigila de forma continua |
| Guardarraíles | Bloquean lo que está **tipificado** como prohibido. Lo que no está tipificado —el caso del §7, un hecho nuevo que no contradice nada— atraviesa el guardarraíl sin activarlo |
| Revisión humana en el bucle | Su calidad decae con el volumen: un escalado frecuente produce aprobación en masa, y «revisado» deja de distinguirse de «aprobado sin leer». Hoy ninguna señal separa esos dos estados |
| Verificación multiagente | Supone que los validadores fallan de forma independiente. Aquí comparten modelo, redacción de las restricciones y **la misma entrada** (§6.1): lo que faltó en el paquete le falta al Escritor y al Continuista a la vez |
| Integración en CI/CD | Dice que la tubería terminó, no que haya comprobado algo. Una prueba omitida por falta de extensión, un modo no ejercitado o una fixture ausente se ven igual que el verde |
| Despliegue progresivo | Descartado por ausencia de tráfico. Con él se descarta la única forma de observar una variante con uso real antes de adoptarla, que en modo local no existe de todos modos |
| Red teaming / pruebas adversarias | Encuentra lo que el modelo de amenaza contempla. Queda fuera por definición el vector no previsto y, sobre todo, el fallo **accidental** que se comporta como un ataque: una escena legítima en la que un personaje dicta instrucciones |
| Comprobación de modelos | Descartada. Explora estados y transiciones, no **contenido**: una máquina de estados perfecta puede pasear una escena equivocada por los diez estados correctos |

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
| Todo hecho de canon cita la escena que lo estableció | CLAUDE §8, regla 4 | **T** | El campo de origen es obligatorio en el esquema |
| Cada ejecución guarda prompt, biblia, IDs, modelo, semilla y coste | CLAUDE §8, regla 7 | **T** | Test de la escritura en `ejecucion` |
| La cita de un `Defecto` es subcadena exacta del texto que señala | def. §11, axioma 11 | **T** | Comprobación de forma en código antes de G1a (arq. §8.3): se contrasta la subcadena y su desplazamiento sobre la `VersionDeTexto`, sin volver a llamar al modelo |
| Todo `CAN-01` declara un `hecho_canon_id` que existe en el grafo | def. §11, axioma 12 | **T** | Misma comprobación, contra el grafo de canon |
| Un defecto mal formado no bloquea ni consume reintento | arq. §8.3 | **T** | Emitir un defecto con cita inventada y comprobar que no llega al prompt de reparación, que no gasta intento y que se cuenta aparte (arq. §9) |
| El sistema funciona con y sin extensión vectorial | arq. §2 | **T + D** | La suite corre en los dos modos; además, arranque real con la extensión ausente |
| Una ejecución se puede reproducir | CLAUDE §3, principio 6 | **D**, no T | Se reproduce el **paquete de contexto**, que es determinista; la prosa no, porque el modelo no lo es. Es justo la razón de que el ensamblador sea código: lo reproducible es lo auditable. **Con fecha de caducidad:** el paquete se reproduce mientras el estado de almacenes sea el de entonces, y el canon crece en cada escena, así que reconstruir una escena antigua desde los almacenes de hoy da otro paquete |
| Ninguna escena excede el nivel de calor declarado | CLAUDE §8, regla 5 | **T** parcial **+ I** | El esquema comprueba el nivel declarado; que la prosa se mantenga dentro lo juzga el Crítico (defecto SEG-01) y, en última instancia, una lectura humana |
| Ningún contenido romántico o sexual con personajes menores de 18 | CLAUDE §8, regla 6 | **T + I** | La edad se valida en esquema y bloquea por construcción; que la prosa no lo insinúe se inspecciona |
| El coste **por llamada** se mantiene acotado | arq. §2.1 y §2.2 | **T** | El contador inyectado y los topes por capa lo acotan antes de llamar, y el límite de concurrencia acota el proceso. **El total de una novela no lo acota nada**: por eso figura como U en §4.2 y como descubierto en §7, y no como un requisito verificado aquí |
| El juez correlaciona con el editor humano | arq. §7 | **U** hoy → **T** | Pasa a T el día que exista el conjunto de escenas etiquetadas |
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
  es verificable; el total de nueve agentes, con G1 gastando dos validaciones por
  escena, lo limita una política y no lo demuestra ningún análisis.

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
  trabajo, no una condición de aceptación.
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

- **Comparten modelo.** Son el mismo proveedor y, salvo configuración explícita, el mismo
  modelo. Un sesgo del modelo lo tienen los cuatro a la vez, y ninguno está en posición de
  notarlo.
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
- Hay **una** señal, y es nueva: la **tasa de defectos mal formados** (arq. §8.3 y §9) mide
  cuántas veces el Continuista afirma algo que no está en el texto, porque la comprobación
  de forma lo detecta sin volver a llamar al modelo. Es una medida del validador, no del
  código, y por eso vale: es la primera.
- Lo que esa señal **no** mide es la mitad que importa para la puerta: la **tasa de falsos
  negativos** del Continuista y del Extractor sigue sin medirse, porque no existe un
  conjunto de defectos conocidos contra el que puntuarlos. Un validador que calla no
  produce ningún registro que contar.
- El **Crítico** no está calibrado. Es el único de los tres cuya falta de validación tiene
  consecuencia declarada en el diseño: por eso G1b no bloquea (`architecture.md` §8.3).

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
| Hay más llamadas en vuelo de las permitidas | Prueba de concurrencia sobre el turno único | **Cubierto** |
| Un trabajo interrumpido duplica escrituras | Tests de reanudación estado por estado, idempotencia por `run_id` | **Parcial** — la exhaustividad sobre los diez estados la sostiene quien escribe los tests, no un método |
| Una contradicción de canon pasa desapercibida | Continuista (extracción, probabilística) más contraste contra el grafo (determinista), más la comprobación de forma que exige `hecho_canon_id` en `CAN-01` (arq. §8.3) | **Parcial** — §6.2: lo que no se extrae no se contrasta, y esa tasa sigue sin medirse |
| **Un hecho nuevo, inventado, entra en el canon** | Nada. El Continuista contrasta contra lo ya sabido y un hecho que no contradice no colisiona; el Extractor lo consolida citando su escena de origen, que es trazabilidad, no veracidad. **La comprobación de forma de arq. §8.3 no alcanza aquí**: ata lo que afirma el Continuista sobre el texto, no lo que el Extractor escribe en el canon | **Descubierto** |
| Al paquete le falta un dato que la escena necesitaba | Nada antes del hecho; se observa después, como defecto de continuidad | **Descubierto** en prevención |
| La prosa excede el nivel de calor declarado | Esquema sobre el valor declarado (determinista) más lectura humana | **Parcial** — el juicio sobre la prosa no bloquea mientras G1b no bloquee |
| Contenido prohibido con menores | Validación en esquema, que bloquea por construcción, más inspección | **Cubierto** en lo tipificado |
| Prosa con instrucciones incrustadas realimentada como canon | Red teaming, **previsto** y no ejecutado | **Descubierto** hoy |
| Un defecto inventado bloquea una escena o consume un reintento | Comprobación de forma en código antes de G1a: axiomas 11 y 12 de `definitions.md` §11 (arq. §8.3) | **Cubierto** |
| El modo sin extensión vectorial no es el que se prueba | Suite declarada en los dos modos | **Parcial** — §3.1: una prueba omitida se ve igual que el verde |
| El ledger deja de ser *append-only*, o el estado en T se edita | Lectura del repositorio (**A**) | **Parcial** — un solo validador, y humano |
| Un agente recibe una herramienta y las filas «Aplicado por diseño» caducan | La advertencia del §5 | **Descubierto** — nada lo detecta el día que ocurre, y de hecho ya ocurrió con el agente de código sin que nada lo señalara (§3) |
| La revisión humana se degrada por volumen | Métrica de escalados por cada cien escenas (`architecture.md` §9), sin umbral declarado | **Parcial** |
| El coste total de la novela se dispara | Techo por llamada y límite de concurrencia | **Descubierto** en el total: acotan la llamada y el proceso, no la suma. §4.1 solo afirma el techo por llamada; el total es U (§4.2) |
| Un cambio de modelo descalibra a los validadores | Evals, previstas para la fase 4 | **Descubierto** hoy |
| Este documento deja de describir el repositorio | Revisión manual al aterrizar el código | **Descubierto** |

Siete riesgos están **descubiertos**, y conviene distinguir dos clases. Dos esperan a un
método ya decidido y fechado: la prosa con instrucciones incrustadas, al red teaming del
§3, y la descalibración al cambiar de modelo, a las evals de la fase 4. Los otros cinco
—el hecho nuevo que entra en el canon, el dato que le faltó al paquete, el agente que
recibe una herramienta, el coste total y la deriva de este documento— **no tienen método
asignado en ninguna fase**. Enumerarlos es el sentido de la matriz, igual que enumerar las
U lo es del §4.2: un riesgo sin casilla es un riesgo que se está corriendo sin decirlo.

## 8. Registro de cambios

| Versión | Qué cambió |
| --- | --- |
| 1.0 | Catálogo de metodologías con veredicto por método, y clasificación T/A/I/D/U de los requisitos del proyecto |
| 2.0 | Se separan los dos sujetos del §1, se detalla el estado de cada método en este repositorio y se nombra lo que es U |
| 3.0 | El documento pasa de catálogo a conjunto: §2.1 y §3.1 añaden el punto ciego de cada método; §6, las reglas del conjunto —independencia correlacionada, determinista frente a probabilístico, quién mide a los validadores—; §7, la matriz de riesgo × validadores con los descubiertos. §4 fija la letra principal con refuerzo; §4.1 anota que la reproducción del paquete caduca con el estado de almacenes y que el techo por llamada no acota el total; §4.2 separa pertinencia de presencia y añade el hecho nuevo que no contradice nada |
| 3.1 | Se clasifican los axiomas 11 y 12 y la comprobación de forma previa a G1a (§4.1), y la matriz gana la casilla que cubren (§7). El punto ciego de los tests de contrato (§2.1) se corrige: la comprobación de forma elimina el defecto bien formado con la cita inventada. §6.3 deja de decir que nada mide a los validadores: la tasa de defectos mal formados es la primera señal, y se nombra lo que no alcanza. Guardarraíles deja de mezclar los dos sujetos (§3) |

*La v3.0 se commiteó en `aa47bd0`, que arrastró también la v1.2 de `definitions.md` y la v1.3 de `architecture.md`; el mensaje de ese commit describe solo esta. Queda dicho aquí en vez de reescribir la historia: el trabajo que se mezcló no era de quien escribió el commit, y el registro de cada documento es donde se busca una versión.*
