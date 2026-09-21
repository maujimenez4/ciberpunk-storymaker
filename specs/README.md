# specs/

Una carpeta por funcionalidad. Dentro, `spec.md` (qué debe ocurrir) y, **solo cuando la spec está aprobada**, `plan.md` (cómo se implementa).

El proceso completo —las cuatro puertas, qué cierra cada una y quién la abre— está en [`CLAUDE.md`](../CLAUDE.md) §3. Este fichero es solo la convención de la carpeta.

```
specs/
  _plantilla-spec.md
  _plantilla-plan.md
  001-slug/
    spec.md            estado: aprobada
    plan.md            estado: aprobado   <- no existe antes de aprobar la spec
  002-otro-slug/
    spec.md            estado: borrador
```

## Convención de nombres

- `NNN` correlativo de tres dígitos, en orden de creación. No se reutiliza un número, aunque se abandone la spec.
- `slug` en minúsculas y con guiones, usando el vocabulario de `docs/definitions.md`.

## Estados

| Documento | Estados | Quién cambia a «aprobada/aprobado» |
| --- | --- | --- |
| `spec.md` | `borrador` → `en-revision` → `aprobada` → `implementada` | una persona, en un commit que no contenga nada más |
| `plan.md` | `borrador` → `en-revision` → `aprobado` → `completado` | una persona, en un commit que no contenga nada más |

Un agente no se aprueba a sí mismo una spec ni un plan. La aprobación tiene que ser localizable en el historial de git, no solo en una conversación.

## Qué no va aquí

`specs/` es lo que **queremos** que sea verdad. Lo que **ya** es verdad —vocabulario, dominio, arquitectura, verificación— vive en `docs/` y se actualiza al cerrar la spec (§3.1).

## Índice

| Id | Título | Estado | Plan |
| --- | --- | --- | --- |
| _(todavía no hay ninguna spec)_ | | | |
