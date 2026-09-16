---
id: orchestrator
tools: []
skills: [handoff-envelope, issue-report]
writes: [run-state.json, run-log.jsonl, notes/ch{NN}-issues.json, attic/**]
---

# Orquestador

Este fichero **no se envía a ningún modelo**. El orquestador es el código de `tools/`:
no aparece como caja en el diagrama porque *es* el bucle. El fichero existe para que su
reparto de permisos esté declarado en el mismo sitio que el de los demás, y para que la
comprobación de arranque lo cuente como el décimo rol.

## Responsabilidad

Recorre el diagrama, ensambla el contexto de cada turno, cuenta los ciclos, aplica la
configuración, presenta la compuerta en la CLI y hace los commits de git.

## Qué lee

`config/**`, `novels/<slug>/**`, el historial de git.

## Qué escribe

`run-state.json`, `run-log.jsonl`, el reporte de incidencias fundido y el directorio
`attic/` del rollback.

## Qué tiene prohibido

Generar prosa. Decidir canon. Escribir bajo `bible/` — eso es de `continuity-keeper`, y
la comprobación de arranque se niega a correr si este fichero declarase esa ruta.
