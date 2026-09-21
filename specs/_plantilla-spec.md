---
id: NNN-slug
titulo:
estado: borrador          # borrador | en-revision | aprobada | implementada
aprobada_por:             # lo rellena una persona, nunca un agente
fecha:                    # AAAA-MM-DD
---

# NNN-slug — <título>

Qué debe ocurrir y cómo se sabrá que ocurrió. **Aquí no se decide cómo se implementa:** eso es el plan (`plan.md`), y no se escribe hasta que esta spec esté `aprobada`.

## Problema

Qué no se puede hacer hoy, y para quién. Sin solución todavía.

## Alcance

Lo que esta spec cubre.

## Fuera de alcance

Lo que explícitamente **no** cubre, para que nadie lo dé por incluido.

## Criterios de aceptación

Observables y comprobables: cada uno acabará siendo un test. Si no se puede comprobar, no es un criterio.

- [ ] **CA-1** —
- [ ] **CA-2** —

## Reglas de dominio afectadas

Las de `CLAUDE.md` §8 que se tocan, y cómo las respeta esta funcionalidad.

| Regla | Cómo se respeta |
| --- | --- |
|  |  |

## Impacto técnico

- **Presupuesto de contexto (§4.1):** qué capa crece y cuánto; qué se recorta antes si no cabe.
- **Esquema:** ¿hay migración de Alembic? ¿funciona con y sin `sqlite-vec`?
- **Fronteras (§5):** features implicadas. Si hace falta cruzar una, es una pregunta abierta, no una decisión de esta spec.
- **Agentes narrativos (§9):** cuáles intervienen y qué cambia en su contrato de entrada/salida.

## Vocabulario

Términos del dominio usados aquí. Todos deben existir en `docs/definitions.md`; si falta alguno, se propone y se espera confirmación (§2).

## Preguntas abiertas

Mientras quede una sin cerrar, **esta spec no se aprueba**.

- [ ]

## Cierre

Se rellena al implementar (§3.5).

- **Commits:**
- **Documentos actualizados en `docs/`:**
