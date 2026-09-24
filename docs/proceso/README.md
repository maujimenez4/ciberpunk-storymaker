# Documentación de proceso

**Qué es esta carpeta.** Los seis documentos que `docs/entregable/examen-final.md` exige en
su sección «`/docs` en storyMaker con la documentación de proceso», bajo una frase que
decide cómo se leen todos: **«No se corrige el resultado, se corrige el razonamiento que
llevó a él.»**

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
| [`trade-offs.md`](trade-offs.md) | Cada decisión relevante **como decisión**: opciones, criterio y elección | P-01 a P-08 de la 001, D-01 a D-05 de la 002, `architecture.md` §12, P-A a P-C de los planes |
| [`explainers.md`](explainers.md) | Un explainer breve por concepto del curso aplicado, **con su estado real** | `architecture.md`, `verification.md`, `definitions.md` |
| [`diagramas.md`](diagramas.md) | Arquitectura del harness, máquinas de estados, esquema SQLite y tabla de validadores | Los diagramas de `docs/`, las migraciones y `verification.md` §8 |
| [`registro-de-iteraciones.md`](registro-de-iteraciones.md) | Qué cambió tras cada hallazgo **y por qué**: causa y efecto, no diario | Las tablas de **Desviaciones** de los tres planes de `specs/001-backend-v1/` |
| [`red-team-log.md`](red-team-log.md) | Casos adversariales probados, qué los detectó **o no**, y cómo se resolvió | Tests de inyección, `RF-ENT-05`, `RNF-SEG-03`, `verification.md` §7 |

**Fecha de extracción: 2026-09-24.** Los seis se escribieron de una vez, a partir de
material que ya existía. Ninguno describe algo que no esté construido sin decirlo con esas
palabras: lo que falta se nombra como falta, porque un documento de proceso que solo cuenta
lo que salió bien no demuestra que se entienda el proceso.

Dónde mirar el estado del sistema, que **no** se duplica aquí:
[`specs/estado-del-entregable.md`](../../specs/estado-del-entregable.md) —el cruce contra el
encargo, sección a sección— y
[`specs/problemas-abiertos.md`](../../specs/problemas-abiertos.md) —las dieciséis cosas que
hoy están rotas o a medias—.
