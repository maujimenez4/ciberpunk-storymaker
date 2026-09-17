---
name: bible-schema
description: Estructura de la biblia narrativa, qué va en cada fichero y cómo se cita una entrada de canon.
---

La biblia es la **fuente única de verdad**. Si algo no está aquí, no es canon. Vive en
`novels/<slug>/bible/` y la escribe un solo rol: `continuity-keeper`.

## Los ficheros

| Fichero | Qué contiene |
|---|---|
| `canon.md` | Qué es esta novela, sus reglas inviolables y el índice del resto. Corto. |
| `world.md` | Reglas del mundo: cómo funciona, qué se da por supuesto, qué es imposible. |
| `characters.md` | Una ficha por personaje: deseo, herida, voz, límite moral, arco. |
| `outline.md` | Actos y escaleta capítulo a capítulo, con la promesa narrativa de cada uno. |
| `timeline.md` | Qué ocurre y cuándo. Lo que impide que el martes pase dos veces. |
| `threads.md` | Hilos abiertos y cerrados, con el capítulo donde se abrió cada uno. |
| `summaries/ch<NN>.md` | Resumen del capítulo aprobado. Máximo 120 palabras. |

## Cómo se cita una entrada de canon

`bible/<fichero>#<ancla-en-kebab-case>`, por ejemplo
`bible/characters.md#credenciales-revocadas`. Para que una cita así funcione, cada
entrada lleva su propio encabezado `###`.

## Cómo se escribe

- Afirmaciones, no narración. «Le revocaron la credencial en el capítulo 2», no «la
  escena en que le revocan la credencial es tensa».
- Una entrada por hecho, con encabezado propio.
- Nada de conjeturas ni de «quizá más adelante». La biblia recoge lo que ya es cierto.
- Lo que deja de ser cierto se corrige en su sitio, no se añade debajo contradiciéndolo.

## Por qué importa el tamaño

La biblia entra en el contexto de **todos** los capítulos siguientes. Cada párrafo de
más se envía decenas de veces a lo largo de una novela. Escribir corto aquí no es
elegancia: es lo que hace que el coste no crezca sin control.
