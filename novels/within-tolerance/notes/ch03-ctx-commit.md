---
context: storymaker/node-context@1
novel: within-tolerance
node: commit
chapter: 3
assembledAt: 2026-09-18T17:59:54.098Z
---

# Contexto ensamblado — commit · capítulo 3

Lo ensambla el orquestador en el nodo LOAD. Es **todo** tu contexto de biblia y notas:
no abras los ficheros originales, ya están aquí y recortados a lo que tu nodo necesita.
Los capítulos anteriores no se leen nunca — para eso están los resúmenes.
## Cronología

### catorce-meses-antes
Se deniega la ayuda del expediente a nombre de Teodora Nin, aplicando el criterio
sobrante que Adela encuentra en el capítulo 1. Hecho pasado, fuera de escena.

### dia-1-capitulo-1
Febrero. Adela saca el muestreo mensual y encuentra el criterio mal aplicado repetido en
varias tandas. Lo comprueba tres veces el mismo día. Marcial está presente y lo reconoce
sin sorpresa.

### dia-1-a-dia-3
Adela eleva el hallazgo por el cauce correspondiente.

### dia-3-capitulo-2
Llega la respuesta: el desvío está medido, consta en el informe trimestral y cae dentro
de la tolerancia aceptada. Nuria confirma la validez de la tanda en el pasillo, el mismo
día. Adela identifica la cifra del informe como propia: es la tasa de desvío que ella y
Marcial calculan cada mes en el muestreo.

## Hilos abiertos

### criterio-mal-aplicado
Abierto en capítulo 1: Adela encuentra un requisito de denegación que la norma no exige,
repetido en varias tandas. En capítulo 2 la respuesta oficial lo confirma como válido por
estar dentro de tolerancia, sin repararlo. Sigue abierto.

### naturalidad-de-marcial
Abierto en capítulo 1: Marcial reconoce el hallazgo sin sorpresa. Cerrado en capítulo 2:
es la tercera vez ese trimestre que la cuenta sale dentro de tolerancia; no es cinismo,
es aritmética de un patrón que ya ha visto repetirse.

### autoria-de-la-cifra
Abierto en capítulo 2: Adela reconoce que la cifra de tolerancia que valida el criterio
cuestionado es la misma tasa de desvío que ella y Marcial producen cada mes en el
muestreo. Abierto.

## Reporte de incidencias

{
  "report": "storymaker/issue-report@1",
  "novel": "within-tolerance",
  "chapter": 3,
  "attempt": 1,
  "issues": [
    {
      "id": "ck-01",
      "severity": "note",
      "kind": "thread-dropped",
      "where": "ch03 (capítulo completo)",
      "claim": "El hilo criterio-mal-aplicado sigue abierto al cierre de la novela: Adela busca cauce de reapertura, no lo encuentra y no repara el criterio.",
      "canon": "bible/threads.md#criterio-mal-aplicado",
      "fix": "Ninguna acción necesaria: coincide con el arco declarado de Adela (bible/characters.md#adela-roig), cuyo cierre es la decisión privada, no una resolución del conflicto. Se deja como nota informativa para la compuerta."
    }
  ],
  "counts": { "blocker": 0, "warning": 0, "note": 1 }
}

## Resúmenes previos (ventana 2)

### Resumen del capítulo 1

Adela, en el muestreo mensual de febrero, encuentra un criterio de denegación que la
norma no exige, repetido en varias tandas anteriores. Lo comprueba tres veces. Marcial
reconoce el patrón sin sorpresa: va la tercera vez ese trimestre, el desvío está medido
y publicado, dentro de tolerancia. Adela recopila las referencias y eleva el hallazgo
por el cauce correspondiente; Nuria lo recibirá al día siguiente.

Hilos abiertos: criterio-mal-aplicado (el requisito sobrante y su repetición en varias
tandas) y naturalidad-de-marcial (por qué lo acepta sin sorpresa). Ninguno se cierra en
este capítulo.

### Resumen del capítulo 2

Nuria confirma en el pasillo que la tanda es válida: el desvío está medido y cae dentro de la tolerancia aceptada. Establece la distinción de que el criterio sobrante sigue vigente porque la tanda es válida, no porque el criterio sea correcto. Marcial explica su falta de sorpresa: ya había hecho la cuenta, es la tercera vez ese trimestre y las tres cayeron dentro de tolerancia — cierra el hilo naturalidad-de-marcial como cálculo, no cinismo. Adela reconoce que la cifra de tolerancia que la contradice es la misma que ella y Marcial producen cada mes en su propio muestreo. Abre el hilo autoria-de-la-cifra: qué hará con esa autoría queda sin resolver. Pide el detalle desagregado del desvío.
