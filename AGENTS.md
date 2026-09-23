# AGENTS.md

Este fichero no contiene especificaciones. **Todo el manual operativo del repositorio vive en [`CLAUDE.md`](CLAUDE.md)**: léelo entero antes de escribir o modificar código.

Esto es un índice. Si una fila te parece que necesita explicación, lo que falta está en `CLAUDE.md`, no aquí: dos ficheros que explican lo mismo divergen a la primera.

| Buscas… | Sección de `CLAUDE.md` | Se titula |
| --- | --- | --- |
| Qué es el producto: novela personalizada de regalo, diez capítulos, un capítulo por escena | §1 | Qué es este proyecto |
| Vocabulario del dominio y qué documento manda | §2 | El vocabulario no se improvisa |
| Cómo se trabaja, y **qué lleva spec y qué no** | §3 | Cómo se trabaja |
| Stack y límites: el techo de 100.000 tokens, SQLite, Langfuse, Lean y TLA+ | §4 | Requisitos técnicos |
| Arquitectura y reglas de frontera (backend y frontend) | §5 | Arquitectura del código |
| Convenciones de backend y de frontend | §6, §7 | Convenciones |
| Reglas de dominio que el código debe respetar | §8 | Reglas de dominio |
| Agentes narrativos: roles, reglas transversales, flujo, dónde vive cada uno | §9 | Agentes narrativos del sistema |
| Prompts: versionado, contenido obligatorio, seguridad | §10 | Prompts |
| Guardarraíles: palabras vetadas, registro de auditoría, texto no confiable | §11 | Guardarraíles |
| Qué puede afirmar un agente como hecho | §12 | Definición de «hecho» para un agente |
| Skills del proyecto | §13 | Skills del proyecto |
| Comandos | §14 | Comandos |
| Qué no hacer | §15 | Qué no hacer |
| Checklist antes de dar una tarea por terminada | §16 | Antes de dar una tarea por terminada |

**La tercera columna existe para que este índice se pueda desmentir.** Un índice que solo lleva números caduca en silencio: alguien inserta una sección, todo se desplaza uno y las filas siguen pareciendo correctas. Con el título delante, una fila que ya no corresponde se ve al leerla.

> **Los números cambiaron el 2026-09-23 y conviene saber por dónde.** Al entrar §11 Guardarraíles, todo lo que iba del 11 al 15 se corrió uno: «Definición de hecho» pasó de §11 a **§12**, skills de §12 a **§13**, comandos de §13 a **§14**, «Qué no hacer» de §14 a **§15** y el checklist de §15 a **§16**. Si vienes de un enlace viejo, son esas cinco. Es exactamente el desplazamiento silencioso que la columna de títulos existe para hacer visible.

Los documentos de dominio siguen donde estaban:

| Documento | Qué contiene |
| --- | --- |
| [`docs/definitions.md`](docs/definitions.md) | Fuente de verdad del vocabulario |
| [`docs/domain-knowledge.md`](docs/domain-knowledge.md) | Cómo funciona una novela, y la personalización como problema narrativo |
| [`docs/architecture.md`](docs/architecture.md) | Cómo se construye el sistema; incluye diagramas y árboles de ficheros |
| [`docs/verification.md`](docs/verification.md) | Cómo se gana confianza, qué no detecta cada método y qué queda descubierto |
| [`docs/entregable/examen-final.md`](docs/entregable/examen-final.md) | El encargo externo contra el que se comprueba si el proyecto cumple. **No se edita para que encaje con lo construido** |

## Sobre `specs/`

Hoy hay **una sola spec**: `specs/001-backend-v1/`, en `estado: aprobada` y **sin `plan.md`**.

El resto del entregable **no lleva spec**. Es una decisión explícita de `maujimenez4`, no un descuido ni un atajo tomado sobre la marcha: las cuatro puertas de `CLAUDE.md` §3 para cada área del encargo no caben en el plazo, así que ese trabajo va documentado en `docs/` y en los registros de cambios de cada documento.

Conviene saber qué se paga por eso, porque el proceso de §3 existía por algo: **sin spec no hay criterios de aceptación escritos antes de construir**, así que lo que se entregue se juzga contra el encargo directamente y no contra una lista propia. Quien trabaje aquí no debe deducir de esto que §3 ya no rige: rige, y la excepción es esta entrega y su motivo.
