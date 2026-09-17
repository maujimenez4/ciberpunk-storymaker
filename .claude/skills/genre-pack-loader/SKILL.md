---
name: genre-pack-loader
description: Cómo se lee un pack de género y por qué su lista de términos prohibidos no es negociable.
---

Un pack de género vive en `genres/<id>/` y trae dos cosas: `pack.md`, con las
convenciones del género, y `banned-terms.txt`, con los términos que no pueden aparecer.
Ambos te llegan ya cargados, más abajo, en la sección «Pack de género».

## Convenciones, no préstamos

Un pack codifica **convenciones**: preguntas que el género se hace y formas que ha ido
encontrando para hacérselas. Identidad sintética, soberanía corporativa, la memoria como
evidencia. Eso es dominio público del género y se usa con libertad.

Lo que un pack **nunca** trae, y tú nunca debes producir, son nombres propios, términos
acuñados, tecnologías bautizadas, organizaciones, lugares ni personajes procedentes de
obras existentes. El worldbuilding es original: si un lector reconoce de dónde viene una
palabra, esa palabra sobra.

## La lista de prohibidos

La lista es corta a propósito: recoge los términos acuñados que más se cuelan por
inercia, no todo lo imaginable. Que un término no esté en la lista no lo autoriza; la
regla de arriba manda sobre la lista.

La comprobación es mecánica y no opina: un término de la lista en la prosa produce una
incidencia `blocker` de tipo `banned-term`, y el capítulo se reescribe. Es la comprobación
más barata de evitar y la más cara de ignorar.

## Cuando dudes

Inventa. Un nombre propio tuyo, aunque sea peor, vale más que uno prestado: el primero se
puede pulir y el segundo hay que quitarlo.
