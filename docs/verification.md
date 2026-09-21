# Verificación — StoryMaker

**Versión:** 2.0 · **Fecha:** 2026-09-21

Cómo pensamos ganar confianza en el código y en el comportamiento de los agentes.
Dos preguntas, separadas porque fallan por separado:

1. **Nivel de artefacto** — ¿es correcto el código?
2. **Nivel de proceso** — ¿se comportan los agentes de forma fiable?

Una suite de tests en verde no dice nada sobre si un agente ejecutará mañana una
acción destructiva. Un sandbox no dice nada sobre si el diff de hoy es correcto.
Confundir las dos preguntas es el modo de fallo habitual de un plan de verificación.

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
| Análisis estático / SAST | Escanear el código fuente sin ejecutarlo, contrastándolo con patrones conocidos como defectuosos | **Previsto** — es lo que hace verificables las fronteras. `ruff` y ESLint son la línea base; lo que aporta de verdad es `import-linter` (§5.2) e `import/no-restricted-paths` (§6.2): las reglas de dependencia entre features son afirmaciones sobre el código fuente, se comprueban sin ejecutarlo y fallan la build | [Static program analysis](https://en.wikipedia.org/wiki/Static_program_analysis) |
| Ejecución simbólica | Ejecutar el código con entradas simbólicas para derivar las condiciones exactas de fallo mediante un solucionador SMT | **No aplicable** — la única lógica numérica con condiciones de fallo interesantes es la aritmética de presupuesto del ensamblador, y ahí un test basado en propiedades da la misma respuesta por mucho menos | [Symbolic execution](https://en.wikipedia.org/wiki/Symbolic_execution) |
| Verificación formal / demostración de teoremas | Demostrar matemáticamente que el código satisface una especificación para todas las entradas posibles | **No aplicable** — las invariantes que merecerían demostración (el estado en T deriva del ledger; ningún paquete supera los 100.000 tokens) se garantizan **por construcción**: ledger *append-only*, vista derivada y `ContextBudgetExceeded`. Construirlas sale más barato que demostrarlas | [Formal verification](https://en.wikipedia.org/wiki/Formal_verification) |
| Tests unitarios / de integración | Comprobar el comportamiento frente a entradas concretas elegidas y salidas esperadas | **Previsto** — método principal a nivel de artefacto. `pytest` con `pytest-asyncio`; test colocado junto al componente en el frontend. Dos reglas del proyecto lo sostienen: toda regla de dominio de `CLAUDE.md` §8 tiene su test, y el cliente de modelo se inyecta, de modo que ninguna prueba llama al proveedor | [Unit testing](https://en.wikipedia.org/wiki/Unit_testing) |
| Tests basados en propiedades | Especificar una propiedad general y generar muchas entradas para buscar una violación | **Previsto** — dirigido al **ensamblador de contexto**, que es donde los ejemplos elegidos se quedan cortos. Propiedades: el desglose por capa suma el total contado; recortar una capa no altera las demás; las capas constitucional e instrucción nunca encogen; o el paquete cabe en 100.000 tokens o se lanza `ContextBudgetExceeded`, nunca un truncado silencioso | [QuickCheck — Claessen y Hughes, 2000](https://www.cs.tufts.edu/~nr/cs257/archive/john-hughes/quick.pdf) |
| Tests de mutación | Introducir deliberadamente pequeños fallos para comprobar si la suite de tests los detecta | **Aplazado** — tendrá sentido cuando exista la suite del ensamblador, porque es precisamente la suite en cuya luz verde estaremos tentados de confiar para afirmar que el contexto nunca se recorta a escondidas. Hoy no hay suite que mutar | [Mutation testing](https://en.wikipedia.org/wiki/Mutation_testing) |
| Tests de contrato | Verificar que la interfaz entre dos servicios se mantiene coherente, con independencia de sus interioridades | **Previsto, y en parte por construcción** — hay tres fronteras de este tipo: el OpenAPI entre backend y frontend (el cliente se genera, no se escribe a mano); el `__init__.py` de cada feature como única superficie importable; y la E/S de cada agente narrativo, que es un contrato real —el Continuista devuelve **códigos de defecto con cita**, nunca prosa corregida— y por tanto se valida con esquema y se prueba | [Contract Test — Martin Fowler](https://martinfowler.com/bliki/ContractTest.html) |

## 3. Verificación a nivel de proceso

| Metodología | Definición | Estado aquí | Explicación |
| --- | --- | --- | --- |
| Observabilidad / trazas en ejecución | Instrumentar el agente para que su trayectoria sea visible y consultable a posteriori | **Aplicado por diseño (narrativos)** — cada llamada registra `run_id`, escena, versión de prompt y de biblia, IDs recuperados, modelo, parámetros, semilla, tokens por capa, coste y veredicto (§9). Matiz: el §11 prohíbe registrar por defecto los prompts de producción y los fragmentos de manuscrito, así que la traza es **estructural, no textual**: dice qué se envió y cuánto costó, no qué decía | [Observability primer](https://opentelemetry.io/docs/concepts/observability-primer/) |
| Evals | Pruebas estructuradas del comportamiento del agente contra un conjunto de datos y un método de puntuación | **Previsto (narrativos)** — fase 4 de la hoja de ruta. El criterio de éxito del Crítico es «correlación con el editor humano», y eso *es* una eval: un conjunto de escenas etiquetadas por una persona contra el que se puntúa al juez. Sin él no se distingue un cambio de prompt que mejora de uno que solo desplaza la salida, ni se detecta la descalibración al cambiar de modelo (riesgo abierto del §12) | [HELM — Liang et al., 2022](https://arxiv.org/abs/2211.09110) |
| Ejecución en sandbox | Ejecutar el código del agente en un entorno aislado para que las acciones dañinas fallen sin consecuencias | **Sustituido por supresión del alcance (ambos)** — los agentes narrativos no ejecutan código, y el Escritor no accede a la base de datos: solo ve el paquete recibido (§3.5). El agente de código corre sin herramientas de fichero; el orquestador lee y escribe por él. En los dos casos se **elimina** el radio de impacto en lugar de contenerlo: más fuerte que un sandbox, pero deja de ser cierto en cuanto un agente reciba una herramienta | [Sandbox (computer security)](https://en.wikipedia.org/wiki/Sandbox_%28computer_security%29) |
| Guardarraíles | Políticas y filtros que restringen qué acciones puede producir un agente | **Aplicado en código (ambos)** — edad mínima y nivel de calor se validan **en esquema**, no en el prompt (§11); el presupuesto de contexto falla explícitamente en vez de truncar; el reintento dirigido tiene tope de dos; cada agente recibe el mínimo de permisos que su nodo necesita. Regla que lo sostiene: ninguna regla de seguridad depende solo del prompt | [AI Risk Management Framework — NIST](https://www.nist.gov/itl/ai-risk-management-framework) |
| Revisión humana en el bucle | Una persona aprueba, rechaza o edita las acciones de alta consecuencia del agente | **Aplicado (ambos), con puntos definidos** — G1a escala a la persona tras dos reparaciones fallidas; G3 no cierra borrador sin revisión; el arco romántico figura en la tabla de dimensiones de calidad como «revisión humana». En el repositorio, toda escritura del agente de código pasa por una persona | [Human-in-the-loop](https://en.wikipedia.org/wiki/Human-in-the-loop) |
| Verificación multiagente | Patrones de crítico, debate, autoconsistencia, reflexión o ensamblado que revisan la salida del modelo | **Aplicado (narrativos): es el mecanismo central de calidad, no una opción en estudio** — Continuista y Crítico existen separados del Escritor exactamente por esto (decisión 6 del §12: quien escribe no ve sus contradicciones, y quien juzga no repara). Coste asumido: la puerta de escena gasta hasta dos validaciones además de la escritura. Límite conocido y ahora explícito en el diseño: el juez no está calibrado, así que **G1b no bloquea** hasta la fase 4 (§8.3); lo que hoy aporta es detección de contradicciones, no juicio de calidad | [AI Safety via Debate — Irving et al., 2018](https://arxiv.org/abs/1805.00899) |
| Integración en CI/CD | Hacer pasar los cambios generados por el agente por la misma tubería que los escritos por personas | **Previsto (agente de código)** — sin una vía aparte y más débil para los diffs del agente. La tubería es la lista de `CLAUDE.md` §15: `ruff`, `mypy`, `pytest`, `lint-imports`, `pnpm typecheck`, `pnpm lint` y migraciones de Alembic. Exigencia propia de este proyecto: la suite debe correr **en los dos modos de `VectorStore`**; si solo se ejecuta con `sqlite-vec` cargado, el modo degradado que promete el §2 no está verificado | [Continuous integration](https://en.wikipedia.org/wiki/Continuous_integration) |
| Despliegue progresivo | Enviar un cambio a un pequeño porcentaje del tráfico tras un flag antes de la publicación completa | **No aplicable** — el modo de referencia es local, con un fichero SQLite por obra (§10): no hay tráfico que repartir. Lo que sí cumple la función de comparar variantes sin desplegar son las versiones de texto inmutables y la comparación de estrategias de contexto de la fase 6 | [Feature toggle](https://en.wikipedia.org/wiki/Feature_toggle) |
| Red teaming / pruebas adversarias | Sondear deliberadamente en busca de fallos bajo un modelo de amenaza adversario | **Previsto (narrativos), con modelo de amenaza concreto** — la vía realista no es un atacante externo, es el propio bucle: el Extractor convierte prosa generada en canon, de modo que un texto con instrucciones incrustadas se realimenta al sistema por un canal legítimo. Segundo objetivo: empujar desde el brief contra los guardarraíles de edad y nivel de calor, para comprobar que lo que aguanta es el esquema y no el prompt | [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/) |
| Comprobación de modelos | Explorar exhaustivamente los estados y transiciones alcanzables del agente para verificar invariantes | **No aplicable, por ahora** — la máquina de estados del orquestador es explícita desde que existe el §3.3: diez estados y transiciones cerradas, más las cuatro puertas y los dos reintentos. Sigue siendo lo bastante pequeña para que la cubran los tests, y lo que la mantiene tratable es la restricción de **una escena en vuelo por obra** (§3.8). Se reconsidera si esa restricción se levanta o si aparece concurrencia real de escritura sobre una misma obra | [Model checking](https://en.wikipedia.org/wiki/Model_checking) |

## 4. Clasificación: T / A / I / D / U

Cada requisito recibe exactamente una letra, para que los que nadie puede comprobar
queden visibles en vez de darse por supuestos. Véase
[Verification and validation](https://en.wikipedia.org/wiki/Verification_and_validation).

| Letra | Significado | Cómo se ve aquí |
| --- | --- | --- |
| **T** — Test (prueba) | Se verifica ejecutando el sistema con entradas definidas | Presupuesto del ensamblador, validadores de canon y continuidad, esquemas de dominio |
| **A** — Análisis | Se verifica razonando sobre el artefacto sin ejecutarlo | Tipos, fronteras entre features, ámbito de permisos por agente |
| **I** — Inspección | Se verifica con una persona leyéndolo | Prompts versionados, rúbricas, política de guardarraíles, este documento |
| **D** — Demostración | Se verifica observando el sistema operar en una ejecución realista | La vertical mínima de la fase 1: un capítulo coherente de principio a fin |
| **U** — No verificable | Ningún método que estemos dispuestos a pagar lo establece | Véase más abajo |

### 4.1 Los requisitos del proyecto, clasificados

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
| Una escena tiene un POV y un giro de valor no nulo | CLAUDE §8.1 | **T** | Esquema Pydantic con su test |
| Ningún personaje usa información sin `sabe_desde` anterior | CLAUDE §8.2 | **T** | Validador de conocimiento (defecto CON-03) sobre casos conocidos |
| El estado en T se deriva del ledger y no se edita | CLAUDE §8.3 | **A + T** | No hay repositorio que escriba sobre la vista; un test reconstruye el estado desde el ledger |
| Todo hecho de canon cita la escena que lo estableció | CLAUDE §8.4 | **T** | El campo de origen es obligatorio en el esquema |
| Cada ejecución guarda prompt, biblia, IDs, modelo, semilla y coste | CLAUDE §8.7 | **T** | Test de la escritura en `ejecucion` |
| El sistema funciona con y sin extensión vectorial | arq. §2 | **T + D** | La suite corre en los dos modos; además, arranque real con la extensión ausente |
| Una ejecución se puede reproducir | CLAUDE §3.6 | **D**, no T | Se reproduce el **paquete de contexto**, que es determinista; la prosa no, porque el modelo no lo es. Es justo la razón de que el ensamblador sea código: lo reproducible es lo auditable |
| Ninguna escena excede el nivel de calor declarado | CLAUDE §8.5 | **T** parcial **+ I** | El esquema comprueba el nivel declarado; que la prosa se mantenga dentro lo juzga el Crítico (defecto SEG-01) y, en última instancia, una lectura humana |
| Ningún contenido romántico o sexual con personajes menores de 18 | CLAUDE §8.6 | **T + I** | La edad se valida en esquema y bloquea por construcción; que la prosa no lo insinúe se inspecciona |
| El coste por novela se mantiene acotado | arq. §12 | **A** hoy, **D** al ejecutar | El presupuesto por llamada lo acota una política; el total con nueve agentes no existe hasta la primera corrida completa |
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
  como defecto, no antes.
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
  reabrirlas **antes** de conceder el permiso, no después.
- Al actualizar este documento, mantén separados los dos sujetos. Verificar al agente
  de código no dice nada sobre el comportamiento de los agentes narrativos en
  producción, ni al revés.
