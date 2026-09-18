---
context: storymaker/node-context@1
novel: dead-floor
node: commit
chapter: 2
assembledAt: 2026-09-18T01:30:58.164Z
---

# Contexto ensamblado — commit · capítulo 2

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
  "chapter": 2,
  "attempt": 2,
  "issues": [
    {
      "id": "tv-01",
      "severity": "warning",
      "kind": "unsourced-claim",
      "where": "ch02 ¶2",
      "claim": "\"El registro anotó el trayecto con mi credencial, como siempre.\" — se afirma como rutina establecida que el ascensor registra cada trayecto asociado a la credencial del técnico.",
      "canon": null,
      "fix": "El dossier no trae fuente para vocabulario o prácticas de registro de tránsito vertical (bitácoras, monitorización de accesos): es un hueco declarado, no una nota con fuente. El detalle es breve y no incluye cifras ni procedimiento verificable, así que no llega a blocker, pero conviene que quede constancia de que el mecanismo se afirma sin respaldo externo."
    }
  ],
  "counts": { "blocker": 0, "warning": 1, "note": 0 }
}

## Resúmenes previos (ventana 2)

### Resumen del capítulo 1

Cerrando el certificado anual, el técnico cruza el registro de tránsito con el plano de
paradas y encuentra una parada que el plano no recoge, repetida y con gente subiendo y
bajando en horas de oficina. Repite el cruce a mano por si el error es suyo: el registro
cuadra entero, el plano no. No sube a comprobarlo esa tarde. El compañero de turno le
ofrece firmar sin mirar, apoyándose en que salió bien los años anteriores; el técnico lo
aplaza.

Canon nuevo: ninguno más allá de lo ya recogido en `timeline.md#jornada-1-cierre-de-certificado`
y `threads.md#discrepancia-registro-plano` / `threads.md#dilema-de-la-firma`, que este
capítulo confirma sin desviarse.

Hilo abierto: `dilema-de-la-firma` — si firmará lo que sabe o lo que le conviene.
