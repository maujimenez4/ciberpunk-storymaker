---
context: storymaker/node-context@1
novel: night-haul
node: commit
chapter: 1
assembledAt: 2026-09-18T20:04:40.614Z
---

# Contexto ensamblado — commit · capítulo 1

Lo ensambla el orquestador en el nodo LOAD. Es **todo** tu contexto de biblia y notas:
no abras los ficheros originales, ya están aquí y recortados a lo que tu nodo necesita.
Los capítulos anteriores no se leen nunca — para eso están los resúmenes.
## Escaleta — entrada del capítulo 1

### Capítulo 1 — La hoja corta
Ferrán entrega a Bruna una hoja de ruta sin el punto de control intermedio y un sobre por
no preguntar. Ella lo coge sin engaño de por medio: sabe lo que es. Se establecen los dos
hechos exactos del contenedor siete y las 23:40 (`world.md#el-contenedor-siete`,
`world.md#el-turno-de-bruna`). En escena: Bruna, Ferrán. Abre los hilos *ruta sin control
intermedio*, *deuda con plazo* y *contenedor siete*.

## Cronología

No hay fechas de calendario explícitas; la secuencia es de noches relativas.

### Antes del capítulo 1
Bruna lleva tres semanas conduciendo el turno de noche antes de que Ferrán le ofrezca la
ruta corta. Este dato es contexto de biblia: no se cuenta como cifra en el texto de
ningún capítulo.

### Capítulo 1
Noche en que Ferrán ofrece por primera vez la hoja sin control intermedio. Turno de
23:40. Aparece por primera vez el contenedor siete con sus dos rasgos exactos.

### Capítulo 2
Noche posterior, no necesariamente consecutiva: suficiente tiempo para que Nel note un
patrón de ausencia de Bruna en la garita ("esta semana").

### Capítulo 3
Noche posterior al capítulo 2, cuando Bruna intenta salirse por primera vez.

### Capítulo 4
La noche siguiente, en la que Bruna conduce la ruta corta con el contenedor siete por
última vez.

### Capítulo 5
Inmediatamente después del capítulo 4: la primera noche en tres semanas en que las 23:40
no significan nada para Bruna.

## Hilos abiertos

### Ruta sin control intermedio
Abierto en el capítulo 1. Cerrado en el capítulo 5: nadie vuelve a firmarla.

### Deuda con plazo
Abierto en el capítulo 1. Cerrado en el capítulo 5 como coste ya contado, no como
promesa pendiente: el plazo no se mueve un día.

### Contenedor siete
Abierto en el capítulo 1 con sus dos rasgos exactos (`world.md#el-contenedor-siete`).
Cerrado en el capítulo 4, cuando Nel los verifica y anota.

### Nel como testigo involuntario
Abierto en el capítulo 2. Cerrado en el capítulo 4, cuando deja de ser involuntario al
anotar por petición de Bruna.

### El nombre de Bruna en las hojas
Abierto en el capítulo 3. Tensado en el capítulo 4. Cerrado en el capítulo 5.

### Motivo de Ferrán
Abierto en el capítulo 3. Cerrado en el capítulo 5: queda dicho, no resuelto a su favor.
Ningún capítulo debe inventarle una causa concreta sin editar primero `characters.md`.

### Antagonismo ambiguo
Implícito desde el capítulo 1 (Ferrán tiene intención propia desde la primera página).
Cerrado en el capítulo 3: desde ahí la presión tiene rostro y método declarados.

## Reporte de incidencias

{
  "report": "storymaker/issue-report@1",
  "novel": "night-haul",
  "chapter": 1,
  "attempt": 1,
  "issues": [
    {
      "id": "ck-01",
      "severity": "warning",
      "kind": "character-drift",
      "where": "ch01 ¶2-16 (diálogo de Ferrán)",
      "claim": "Ferrán habla casi siempre en fragmentos de una o dos palabras («Esta.», «Al final. Como siempre.», «Por no preguntar.», «En el papel sí.»).",
      "canon": "characters.md#ferrán-oleta",
      "fix": "Tensiona, sin romperlo, el rasgo de voz «frases completas, tono razonable»; si se revisa, dar a alguna de sus réplicas estructura de oración completa sin perder la sequedad ni subir el tono."
    }
  ],
  "counts": { "blocker": 0, "warning": 1, "note": 0 }
}
