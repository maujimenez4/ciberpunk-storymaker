---
context: storymaker/node-context@1
novel: dead-floor
node: commit
chapter: 3
assembledAt: 2026-09-18T15:35:56.657Z
---

# Contexto ensamblado — commit · capítulo 3

Lo ensambla el orquestador en el nodo LOAD. Es **todo** tu contexto de biblia y notas:
no abras los ficheros originales, ya están aquí y recortados a lo que tu nodo necesita.
Los capítulos anteriores no se leen nunca — para eso están los resúmenes.
## Cronología

Tres jornadas consecutivas dentro del mismo ciclo de cierre del certificado anual. Sin
fechas ni plazos concretos: el orden es lo que importa, no la cifra de días.

### jornada-1-cierre-de-certificado
Capítulo 1. El técnico, cerrando el certificado del edificio, cruza el registro de
tránsito con el plano de paradas y encuentra la parada que sobra. No sube. Repite el
cruce por si el error es suyo.

### jornada-2-la-planta-que-no-consta
Capítulo 2. El técnico sube a comprobar la parada que sobra. Encuentra oficinas en uso —
mesas ocupadas, gente trabajando— en una planta que el plano no recoge. La conserje lo ve
salir de la cabina y no pregunta. En el rellano, una de las inquilinas le pregunta si va a
pasar algo; el técnico no le contesta lo que ella espera. Ocurre después de
`jornada-1-cierre-de-certificado` y antes de que el certificado quede cerrado.

## Restricción de orden

Ningún capítulo repite ni adelanta un hecho de otro: la parada que sobra se descubre
antes de subir a comprobarla, y comprobarla es distinto de dejar constancia escrita de la
discrepancia.

## Hilos abiertos

## Abiertos

### dilema-de-la-firma
Abierto en el capítulo 1, como herida del técnico (ver `characters.md#el-tecnico`): si
firma lo que sabe o lo que le conviene.

### coste-humano-de-corregirlo
Abierto en el capítulo 2: corregir la numeración deja fuera de uso el metraje que ocupa
la inquilina y quienes trabajan con ella, mientras se rehace el expediente.

## Cerrados

### discrepancia-registro-plano
Abierto en el capítulo 1: la cabina se detiene en una parada que el plano no recoge.
Cerrado en el capítulo 2: deja de ser un enigma —el técnico confirma qué hay arriba— y
pasa a ser un hecho administrativo pendiente de firma.

## Reporte de incidencias

{
  "report": "storymaker/issue-report@1",
  "novel": "dead-floor",
  "chapter": 3,
  "attempt": 2,
  "issues": [
    {
      "id": "tv-01",
      "severity": "warning",
      "kind": "unsupported-claim",
      "where": "ch03 ¶5",
      "claim": "La casilla de observaciones del certificado \"es pequeña, tres renglones, hecha para escribir «sin novedad»\".",
      "canon": null,
      "fix": "El dossier no trae ninguna fuente sobre el formato del certificado de mantenimiento de ascensores (HUECO declarado). El detalle es de relleno, no sostiene ninguna consecuencia de la trama; si se quiere mantener, dejarlo como impresión del narrador en vez de dato de diseño del formulario, o quitarlo."
    },
    {
      "id": "tv-02",
      "severity": "warning",
      "kind": "unsupported-claim",
      "where": "ch03 ¶7",
      "claim": "\"Subí a pie, por no dejar el trayecto anotado\" — implica que el uso del ascensor queda registrado/trazado.",
      "canon": null,
      "fix": "El dossier declara como hueco el vocabulario y las prácticas reales de trazabilidad de tránsito vertical (sin fuente). La frase asume una capacidad de registro sin respaldo; mantenerla en términos igual de vagos está bien para no afirmar un mecanismo concreto, pero si en revisiones futuras se detalla cómo funciona ese registro, necesitará fuente."
    }
  ],
  "counts": { "blocker": 0, "warning": 2, "note": 0 }
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

### Resumen del capítulo 2

El técnico sube a comprobar la parada que el plano no recoge y encuentra una planta en
uso: mesas ocupadas, gente trabajando, sin que conste en el catastro ni en el expediente.
La conserje lo ve salir de la cabina y no pregunta. Una inquilina le pregunta en el
rellano si va a pasar algo; él no le da respuesta.

Canon nuevo: la parada deja de ser un enigma de registro y pasa a ser un hecho
administrativo pendiente de firma (`threads.md#discrepancia-registro-plano`, cerrado).
Se abre `threads.md#coste-humano-de-corregirlo`: corregir la numeración deja fuera de uso
el metraje mientras se rehace el expediente.

Hilo abierto: `dilema-de-la-firma`, sin resolver.
