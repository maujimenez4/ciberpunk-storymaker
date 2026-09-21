---
id: NNN-slug
spec: ./spec.md
estado: borrador          # borrador | en-revision | aprobado | completado
aprobado_por:             # lo rellena una persona, nunca un agente
fecha:                    # AAAA-MM-DD
---

# Plan de implementación — NNN-slug

> **No se rellena este fichero si `spec.md` no está en `estado: aprobada`** (`CLAUDE.md` §3.3).

## Enfoque

Dos o tres frases: cómo se implementa y qué alternativa se descartó, con el motivo.

## Pasos

Cada paso: un test que falla primero, un cambio mínimo, un commit verificable por separado.

### Paso 1 — <nombre>

- **Cubre:** CA-1
- **Test (rojo):** `ruta/al/test.py::nombre_del_test` — qué comprueba exactamente.
- **Cambio mínimo:** qué se escribe para ponerlo en verde.
- **Ficheros:** por feature.
- **Verificación:** comando que lo demuestra.

### Paso 2 — <nombre>

- **Cubre:**
- **Test (rojo):**
- **Cambio mínimo:**
- **Ficheros:**
- **Verificación:**

## Fronteras

Features implicadas y por qué ningún paso cruza una frontera de §5. Si alguno la cruzara, el plan no está listo.

## Esquema y migraciones

Migración de Alembic si la hay, y cómo se comprueba en los **dos** modos de `VectorStore` (§4.2).

## Presupuesto de contexto

Desglose por capa si se toca el ensamblado (§4.1), y qué capa absorbe el crecimiento.

## Riesgos

Qué puede salir mal y qué señal lo delataría.

## Qué queda fuera

Lo que este plan no hace aunque la spec lo mencione, y por qué.

## Desviaciones

Se anota **antes de seguir** cualquier desvío respecto a lo aprobado (§3.4).

| Fecha | Paso | Qué cambió y por qué |
| --- | --- | --- |
|  |  |  |
