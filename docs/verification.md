# Verificación — StoryMaker

Cómo pensamos ganar confianza en el código y en el comportamiento del agente.
Dos preguntas, separadas porque fallan por separado:

1. **Nivel de artefacto** — ¿es correcto el código?
2. **Nivel de proceso** — ¿se comporta el agente de forma fiable?

Una suite de tests en verde no dice nada sobre si el agente ejecutará mañana una
acción destructiva. Un sandbox no dice nada sobre si el diff de hoy es correcto.

> **Estado de este documento:** el repositorio todavía no contiene código fuente, así
> que cada estado de más abajo es una *intención*, no una observación. Revísalos y
> corrígelos cuando aterrice el harness. Cada entrada enlaza a una explicación de la
> metodología, nunca a una herramienta que la implementa.

## Verificación a nivel de artefacto

| Metodología | Definición | Estado aquí | Explicación |
| --- | --- | --- | --- |
| Comprobación de tipos | Verificación automática de que los valores se usan de forma coherente con lo que las operaciones esperan de ellos | **Previsto** — línea base del orquestador | [Type system](https://en.wikipedia.org/wiki/Type_system) |
| Análisis estático / SAST | Escanear el código fuente sin ejecutarlo, contrastándolo con patrones conocidos como defectuosos | **Previsto** — barato, se ejecuta en CI | [Static program analysis](https://en.wikipedia.org/wiki/Static_program_analysis) |
| Ejecución simbólica | Ejecutar el código con entradas simbólicas para derivar las condiciones exactas de fallo mediante un solucionador SMT | **No aplicable** — el coste no se justifica en un harness de generación narrativa sin lógica numérica crítica | [Symbolic execution](https://en.wikipedia.org/wiki/Symbolic_execution) |
| Verificación formal / demostración de teoremas | Demostrar matemáticamente que el código satisface una especificación para todas las entradas posibles | **No aplicable** — mismo motivo; no existe aquí una especificación que merezca el esfuerzo de la demostración | [Formal verification](https://en.wikipedia.org/wiki/Formal_verification) |
| Tests unitarios / de integración | Comprobar el comportamiento frente a entradas concretas elegidas y salidas esperadas | **Previsto** — método principal a nivel de artefacto, dirigido al orquestador determinista | [Unit testing](https://en.wikipedia.org/wiki/Unit_testing) |
| Tests basados en propiedades | Especificar una propiedad general y generar muchas entradas para buscar una violación | **Previsto** — encaja mejor con las transiciones de estado del orquestador que los tests por ejemplo | [QuickCheck — Claessen y Hughes, 2000](https://www.cs.tufts.edu/~nr/cs257/archive/john-hughes/quick.pdf) |
| Tests de mutación | Introducir deliberadamente pequeños fallos para comprobar si la suite de tests los detecta | **Aplazado** — solo merece la pena cuando exista una suite en la que estemos tentados de confiar | [Mutation testing](https://en.wikipedia.org/wiki/Mutation_testing) |
| Tests de contrato | Verificar que la interfaz entre dos servicios se mantiene coherente, con independencia de sus interioridades | **Previsto** — la frontera orquestador ↔ agente es exactamente ese tipo de interfaz | [Contract Test — Martin Fowler](https://martinfowler.com/bliki/ContractTest.html) |

## Verificación a nivel de proceso

| Metodología | Definición | Estado aquí | Explicación |
| --- | --- | --- | --- |
| Observabilidad / trazas en ejecución | Instrumentar el agente para que su trayectoria sea visible y consultable a posteriori | **Previsto** — imprescindible para diagnosticar el bucle y vigilar el gasto de tokens | [Observability primer](https://opentelemetry.io/docs/concepts/observability-primer/) |
| Evals | Pruebas estructuradas del comportamiento del agente contra un conjunto de datos y un método de puntuación | **Previsto** — la única forma de saber si un cambio de prompt mejoró la salida o solo la desplazó | [HELM — Liang et al., 2022](https://arxiv.org/abs/2211.09110) |
| Ejecución en sandbox | Ejecutar el código del agente en un entorno aislado para que las acciones dañinas fallen sin consecuencias | **Parcialmente aplicado por diseño** — los agentes no reciben herramientas de fichero, lo que elimina el radio de impacto en lugar de contenerlo | [Sandbox (computer security)](https://en.wikipedia.org/wiki/Sandbox_%28computer_security%29) |
| Guardarraíles | Políticas y filtros que restringen qué acciones puede producir un agente | **Aplicado por diseño** — permisos mínimos por agente | [AI Risk Management Framework — NIST](https://www.nist.gov/itl/ai-risk-management-framework) |
| Revisión humana en el bucle | Una persona aprueba, rechaza o edita las acciones de alta consecuencia del agente | **Aplicado** — toda escritura en el repositorio pasa por una persona | [Human-in-the-loop](https://en.wikipedia.org/wiki/Human-in-the-loop) |
| Verificación multiagente | Patrones de crítico, debate, autoconsistencia, reflexión o ensamblado que revisan la salida del modelo | **En estudio** — una pasada de crítico cuesta una generación completa; justifícala contra el presupuesto de tokens antes de adoptarla | [AI Safety via Debate — Irving et al., 2018](https://arxiv.org/abs/1805.00899) |
| Integración en CI/CD | Hacer pasar los cambios generados por el agente por la misma tubería que los escritos por personas | **Previsto** — sin una vía aparte y más débil para los diffs del agente | [Continuous integration](https://en.wikipedia.org/wiki/Continuous_integration) |
| Despliegue progresivo | Enviar un cambio a un pequeño porcentaje del tráfico tras un flag antes de la publicación completa | **No aplicable todavía** — no hay tráfico desplegado que repartir | [Feature toggle](https://en.wikipedia.org/wiki/Feature_toggle) |
| Red teaming / pruebas adversarias | Sondear deliberadamente en busca de fallos bajo un modelo de amenaza adversario | **Previsto** — la inyección de prompts a través del contenido narrativo es la amenaza realista | [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/) |
| Comprobación de modelos | Explorar exhaustivamente los estados y transiciones alcanzables del agente para verificar invariantes | **No aplicable** — reservado para el caso en que la máquina de estados del orquestador crezca más allá de lo que cubren los tests | [Model checking](https://en.wikipedia.org/wiki/Model_checking) |

## Clasificación: T / A / I / D / U

Cada requisito recibe exactamente una letra, para que los que nadie puede comprobar
queden visibles en vez de darse por supuestos. Véase
[Verification and validation](https://en.wikipedia.org/wiki/Verification_and_validation).

| Letra | Significado | Cómo se ve aquí |
| --- | --- | --- |
| **T** — Test (prueba) | Se verifica ejecutando el sistema con entradas definidas | Transiciones de estado del orquestador, contratos de E/S de los agentes |
| **A** — Análisis | Se verifica razonando sobre el artefacto sin ejecutarlo | Tipos, análisis estático, ámbito de permisos por agente |
| **I** — Inspección | Se verifica con una persona leyéndolo | Prompts, política de guardarraíles, este documento |
| **D** — Demostración | Se verifica observando el sistema operar en una ejecución realista | Generación de un relato de principio a fin a partir de un brief de muestra |
| **U** — No verificable | Ningún método que estemos dispuestos a pagar lo establece | Véase más abajo |

### Qué es hoy U

Nombrarlos es el sentido del ejercicio: una U sin marcar es una afirmación que
hacemos sin pruebas.

- **Calidad narrativa.** «El relato es bueno» no tiene test. Las evals pueden medir
  aproximaciones (coherencia, adecuación al brief); no pueden medir si merece la pena
  leerlo. Esto sigue siendo U, y sigue siendo un juicio humano.
- **Ausencia de fallos semánticos sutiles introducidos por el modelo.** Los tests
  detectan aquello para lo que se escribieron. Los tests de mutación aumentan la
  confianza en la suite, no en el código.
- **Comportamiento del modelo subyacente entre cambios de versión.** No lo
  controlamos, y una suite de evals detecta regresiones a posteriori en lugar de
  prevenirlas.
- **Gasto de tokens de un bucle sin límite.** Acotado por los guardarraíles, no
  verificado: el coste de una ejecución patológica lo limita una política, no lo
  demuestra un análisis.

## Advertencias

- Los tests basados en propiedades y las evals no tienen una referencia fundacional
  neutra única como sí la tiene la verificación formal. Los enlaces de arriba apuntan
  al artículo que introdujo o formalizó cada método (QuickCheck; HELM): una elección
  defendible, no la única.
- Aparecer en estas tablas no es una recomendación de adopción. La ejecución
  simbólica y la comprobación de modelos figuran aquí para que la decisión de
  descartarlas quede por escrito.
