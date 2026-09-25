# Documentación de proceso

**Qué es esta carpeta.** Los seis documentos que `docs/entregable/examen-final.md` exige en
su sección «`/docs` en storyMaker con la documentación de proceso», bajo una frase que
decide cómo se leen todos: **«No se corrige el resultado, se corrige el razonamiento que
llevó a él.»** Es una de las dos condiciones eliminatorias del encargo: sin ella, el proyecto
no aprueba.

**Y qué no es.** No son documentos de contexto. Los cuatro de `docs/` —`definitions.md`,
`domain-knowledge.md`, `architecture.md`, `verification.md`— describen **lo que es verdad
hoy** en el sistema y mandan sobre el código (`CLAUDE.md` §3.3). Estos seis describen
**cómo se llegó hasta ahí**: qué se decidió, contra qué alternativa, qué lo destapó y qué
cambió después. Si uno de estos seis discrepa de un documento de contexto, **gana el de
contexto**; lo que aquí se escribe es historia, no norma.

Van en carpeta propia por el mismo motivo por el que `CLAUDE.md` §3.2 separa `docs/` de
`docs/entregable/`: son tres cosas distintas y mezclarlas hace que nadie sepa cuál de las
tres está leyendo.

| Documento | Qué contiene | De dónde sale |
| --- | --- | --- |
| [`spec-inicial.md`](spec-inicial.md) | Qué se decidió construir y por qué, **antes de escribir código** | `specs/001-backend-v1/spec.md` y `specs/002-frontend/spec.md` |
| [`trade-offs.md`](trade-offs.md) | Cada decisión relevante **como decisión**: opciones, criterio y elección | Las decisiones P- de la 001, las D- de la 002, `architecture.md` §12 y las desviaciones de los planes |
| [`explainers.md`](explainers.md) | Un explainer breve por concepto aplicado, **con su estado real**: por qué la escena es la unidad, los dos techos de 100.000 tokens, ledger y canon, Lean como puerta, la correspondencia de TLA+, los jueces solapados y por qué el problema del nombre es del entorno | `architecture.md`, `verification.md`, `definitions.md` y los commits que cita |
| [`diagramas.md`](diagramas.md) | Los cuatro que pide el encargo —arquitectura del harness, máquina de TLA+, esquema SQLite, validadores con su punto— y tres más: el recorrido de extremo a extremo, el ciclo del capítulo con los jueces en paralelo, y sesión, traza y span en Langfuse | Los diagramas de `docs/`, el código de `escritura`, `manuscrito`, `commons/observabilidad` y la pantalla de Creación |
| [`registro-de-iteraciones.md`](registro-de-iteraciones.md) | Qué cambió tras cada hallazgo **y por qué**: causa y efecto, no diario | Las tablas de **Desviaciones** de los planes y la primera corrida real |
| [`red-team-log.md`](red-team-log.md) | Casos adversariales probados, qué los detectó **o no**, y cómo se resolvió | Tests de inyección, `RF-ENT-05`, `RNF-SEG-03`, `verification.md` §7 |

**Fecha de corte: 2026-09-24, por la tarde.** La primera versión de los seis (`63363e8`) se
extrajo de material anterior a las Fases 4 a 7 y al frontend, y afirmaba como pendientes
cosas que ya existían: Langfuse, Lean, TLA+, el hook de *policy*, el juez, la versión
publicada y la lectura web. Se han reescrito contra el código y `git log`, citando el commit o
el fichero de cada afirmación. **Ninguno describe algo que no esté construido sin decirlo con
esas palabras**: lo que falta se nombra como falta, porque un documento de proceso que solo
cuenta lo que salió bien no demuestra que se entienda el proceso.

**Cómo leerlos, si hay poco tiempo.** [`diagramas.md`](diagramas.md) §2 da el recorrido entero
en una figura; [`explainers.md`](explainers.md) §0, §4, §16 bis y §25 responden a las cuatro
preguntas que un revisor se hace primero —por qué la escena, cuánto contexto, por qué dos
jueces a la vez y por qué salía el nombre borrado—; y
[`registro-de-iteraciones.md`](registro-de-iteraciones.md) enseña qué se cambió cuando algo
falló.

**Cómo se usó Claude Code** —skills, subagentes en olas y lo que falló al repartir, el
servidor MCP de navegador— está fuera de esta carpeta, en
[`../claude-code.md`](../claude-code.md), y la validación visual en
[`../validacion-visual.md`](../validacion-visual.md).

Dónde mirar el estado del sistema, que **no** se duplica aquí:
[`specs/estado-del-entregable.md`](../../specs/estado-del-entregable.md) —el cruce contra el
encargo, sección a sección— y
[`specs/problemas-abiertos.md`](../../specs/problemas-abiertos.md) —lo construido que hoy está
roto o a medias, con dueño y coste—.
