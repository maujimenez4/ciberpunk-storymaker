# AGENTS.md

Este fichero no contiene especificaciones. **Todo el manual operativo del repositorio vive en [`CLAUDE.md`](CLAUDE.md)**: léelo entero antes de escribir o modificar código.

| Buscas… | Sección de `CLAUDE.md` |
| --- | --- |
| Vocabulario del dominio y qué documento manda | §2 |
| Cómo trabajar en este repositorio: principios y **proceso** (`docs/` → spec → plan → código con TDD) | §3 |
| Stack, límite de 100.000 tokens, SQLite con y sin vectores | §4 |
| Arquitectura y reglas de frontera (backend y frontend) | §5 |
| Convenciones de backend y de frontend | §6, §7 |
| Reglas de dominio que el código debe respetar | §8 |
| Agentes narrativos: roles, reglas transversales, flujo, dónde vive cada uno | §9 |
| Prompts: versionado, contenido obligatorio, seguridad | §10 |
| Qué puede afirmar un agente como hecho | §11 |
| Skills del proyecto | §12 |
| Comandos | §13 |
| Qué no hacer | §14 |
| Checklist antes de dar una tarea por terminada | §15 |

Los documentos de dominio siguen donde estaban: `docs/definitions.md` (fuente de verdad del vocabulario), `docs/domain-knowledge.md`, `docs/architecture.md` (incluye los diagramas y los árboles de ficheros) y `docs/verification.md`.

Las funcionalidades en curso viven en `specs/`, con su spec y, una vez aprobada, su plan: ver §3 de `CLAUDE.md`.
