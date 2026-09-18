---
context: storymaker/node-context@1
novel: dead-floor
node: commit
chapter: 1
assembledAt: 2026-09-18T01:02:40.528Z
---

# Contexto ensamblado — commit · capítulo 1

Lo ensambla el orquestador en el nodo LOAD. Es **todo** tu contexto de biblia y notas:
no abras los ficheros originales, ya están aquí y recortados a lo que tu nodo necesita.
Los capítulos anteriores no se leen nunca — para eso están los resúmenes.
## Cronología

Tres capítulos, tres jornadas consecutivas dentro del mismo ciclo de cierre del
certificado anual. Sin fechas ni plazos concretos: el orden es lo que importa, no la
cifra de días.

## Orden de los hechos

### jornada-1-cierre-de-certificado
Capítulo 1. El técnico, cerrando el certificado del edificio, cruza el registro de
tránsito con el plano de paradas y encuentra la parada que sobra. No sube. Repite el
cruce por si el error es suyo.

### jornada-2-la-planta-que-no-consta
Capítulo 2. El técnico sube a comprobar. Encuentra oficinas en uso en una planta que el
catastro no recoge. La conserje lo ve salir de la cabina. En el rellano, la inquilina le
pregunta si va a pasar algo. Ocurre después de `jornada-1-cierre-de-certificado` y antes
de que el certificado quede cerrado.

### jornada-3-la-firma
Capítulo 3. El compañero de turno le ofrece cerrar el certificado sin mirar. El técnico
redacta la discrepancia y firma. Es la última jornada del acto: el certificado queda
resuelto con la firma, no con la corrección del expediente, que queda para después de la
novela.

## Restricción de orden

Ningún capítulo puede repetir ni adelantar un hecho de otro: la parada que sobra se
descubre en la jornada 1, se sube a comprobarla en la jornada 2, y solo en la jornada 3
existe una versión escrita y firmada de la discrepancia.

## Hilos abiertos

## Abiertos

### coste-humano-de-corregirlo
Abierto en el capítulo 2: corregir la numeración deja fuera de uso el metraje que ocupa
la inquilina y quienes trabajan con ella, mientras se rehace el expediente. Sigue abierto
al cierre del acto.

### expediente-abierto
Abierto en el capítulo 3: la discrepancia queda por escrito y firmada, y eso pone en
marcha un expediente cuyo trámite y consecuencia no se cuentan en esta novela. Abierto a
propósito al cierre del acto.

## Cerrados

### discrepancia-registro-plano
Abierto en el capítulo 1: la cabina se detiene en una parada que el plano no recoge.
Cerrado en el capítulo 2: deja de ser un enigma —el técnico confirma qué hay arriba— y
pasa a ser un hecho administrativo pendiente de firma.

### dilema-de-la-firma
Abierto en el capítulo 1, como herida del técnico (ver
`characters.md#el-tecnico`): si firma lo que sabe o lo que le conviene. Cerrado en el
capítulo 3 con la firma de la discrepancia, sin testigos.

## Reporte de incidencias

{
  "report": "storymaker/issue-report@1",
  "novel": "dead-floor",
  "chapter": 1,
  "attempt": 1,
  "issues": [
    {
      "id": "tv-01",
      "severity": "warning",
      "kind": "unsourced-technical-detail",
      "where": "ch01 ¶1, ¶13",
      "claim": "El texto da por hecho una cadencia anual para el certificado de mantenimiento de ascensores (\"Llevo once años cerrando el certificado\"; \"el año pasado salió. Y el otro.\"), justo el concepto que las notas dejan como HUECO sin fuente (certificado periódico firmado por técnico).",
      "canon": null,
      "fix": "Si el capítulo pasa la compuerta, dejar constancia de que la periodicidad anual es una suposición sin respaldo para que una revisión posterior no la trate como dato verificado."
    }
  ],
  "counts": { "blocker": 0, "warning": 1, "note": 0 }
}
