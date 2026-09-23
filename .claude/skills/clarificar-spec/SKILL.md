---
name: clarificar-spec
description: Cierra la ambigüedad de una spec de `specs/NNN-slug/spec.md` antes de que pueda aprobarse. Barre el borrador por una taxonomía de once categorías, marca cada una como Clara/Parcial/Ausente, hace como mucho cinco preguntas por ronda, puntúa la ambigüedad que queda y no deja pasar la puerta hasta bajar del umbral. Comprueba además que ningún requisito se queda sin criterio de aceptación observable y que todo término usado existe en `docs/definitions.md`. Usar al escribir una spec nueva, antes de pasarla a `en-revision`, cuando una spec en revisión parezca incompleta, o cuando al implementar aparezca una pregunta que la spec debería haber respondido. Escribe las respuestas en la spec; nunca cambia su `estado` ni la aprueba.
---

# Clarificar una spec

Conviertes un borrador en una spec que **no deja preguntas abiertas**, que es lo único
que le permite pasar a `aprobada` (`CLAUDE.md` §3.2). No la apruebas tú: eso lo hace
una persona, en un commit suyo (§3.2 y §14).

## Lo que lees antes de abrir la boca

En este orden, siempre:

1. **`docs/definitions.md`** — la fuente de verdad del vocabulario (§2). Todo término
   que aparezca en la spec tiene que estar ahí.
2. **`CLAUDE.md` §3.2** — qué cierra una spec antes de salir de borrador.
3. **`CLAUDE.md` §8** — las reglas de dominio; y §4.1, el presupuesto de contexto.
4. **`specs/001-backend-v1/spec.md`** — la spec vigente, que es la estructura de
   referencia y el ejemplo de nomenclatura (`RF-<FEAT>-NN`, `RI-NN`, `RD-NN`,
   `RNF-<AREA>-NN`, `CA-N`, `D-NN`; columnas `Pr.` MoSCoW y `Verif.` con T/A/I/D/U).
5. El borrador que te ocupa.

No preguntas nada que esté contestado en esos cinco sitios. Preguntar lo que ya está
escrito quema el turno y enseña a la otra persona a no leerte.

## Paso 1 — Barrido por taxonomía

Recorres el borrador categoría por categoría y marcas cada una **Clara**, **Parcial**
o **Ausente**. El mapa es interno: no lo publicas salvo que no vayas a preguntar nada.

| # | Categoría | Está clara cuando… |
| --- | --- | --- |
| 1 | Problema y actor | Se sabe qué no se puede hacer hoy y para quién |
| 2 | Alcance | Lo que entra está enumerado, no insinuado |
| 3 | Fuera de alcance | Está escrito lo que **no** se hace y por qué. Vacío es *Ausente*, no *Clara* |
| 4 | Ontología y vocabulario | Todo término existe en `docs/definitions.md`; ninguno es sinónimo inventado |
| 5 | Requisitos comprobables | Cada `RF-*` dice qué pasa, con qué objeto y con qué resultado observable |
| 6 | Reglas de dominio (§8) | Están nombradas las que toca y dicho cómo se respetan |
| 7 | Presupuesto de contexto (§4.1) | Se sabe qué capa crece, cuánto y qué se recorta primero |
| 8 | Persistencia y esquema | Se sabe si hay migración de Alembic y si el ledger cambia |
| 9 | Agentes y prompts | Si toca un agente de §9: qué ve, qué devuelve, qué versión de prompt |
| 10 | Fallo, reintento y escalado | Qué pasa cuando falla, cuántas veces se reintenta y cuándo va a una persona |
| 11 | Verificación | Cada criterio dice cómo se comprueba (T/A/I/D/U de `docs/verification.md`) |

Dos categorías no admiten *Parcial* y valen por sí solas para bloquear la puerta: la
**5** y la **6**. Una spec con requisitos que no se pueden comprobar no es una spec;
es una intención larga.

## Paso 2 — Preguntar: cinco como mucho, por ronda

- **Máximo cinco preguntas por ronda, y como mucho seis rondas.** Si a la sexta sigue
  sin cerrarse, paras y lo dices: eso ya no es ambigüedad, es que no hay decisión
  tomada, y no la tomas tú.
- Preguntas primero lo que **más mueve el resto**: una respuesta sobre alcance
  reescribe requisitos; una sobre el nombre de un campo, no.
- Cada pregunta trae **opciones concretas** y, cuando hay una razonable, tu
  recomendación con el porqué. Usa `AskUserQuestion`.
- Nada de preguntas de cortesía («¿quieres que siga?»). Una pregunta que no cambia lo
  que vas a escribir no se hace.
- Lo que **infieras** y no te confirmen se marca en la spec como suposición, no como
  hecho (`CLAUDE.md` §11).

## Paso 3 — Puntuar lo que queda

Tras cada ronda, puntúas cada categoría: **0** si Clara, **0,5** si Parcial, **1** si
Ausente. Cada categoría cae en una dimensión, y la ambigüedad es la media ponderada:

| Dimensión | Categorías | Peso | Máximo que se le tolera |
| --- | --- | --- | --- |
| Requisitos comprobables | 5, 11 | 0,30 | **0,00** |
| Alcance y actor | 1, 2, 3 | 0,25 | 0,34 |
| Reglas de dominio | 4, 6, 10 | 0,25 | **0,00** en la categoría 6 |
| Impacto técnico | 7, 8, 9 | 0,20 | 0,34 |

`ambigüedad = Σ (media de la dimensión × su peso)`

**La puerta.** Solo se escribe la versión limpia de la spec cuando se cumplen las tres
a la vez:

1. `ambigüedad ≤ 0,20`;
2. ninguna dimensión supera su máximo;
3. las categorías 5 y 6 están en 0.

Publicas el número y las categorías que aún no están en cero. Un umbral se discute; una
sensación, no. Si la puerta no se abre, vuelves al paso 2 con lo que siga en rojo.

## Paso 4 — Un requisito sin criterio no es un requisito

Antes de dar nada por cerrado, cruzas las dos tablas: **cada `RF-*` tiene al menos un
`CA-N` que lo comprueba, y cada `CA-N` cuelga de algún requisito.** Un requisito
huérfano es trabajo que nadie verificará; un criterio huérfano es trabajo que nadie
pidió. Los dos se reportan.

Un criterio de aceptación está bien escrito cuando dice **cuándo** ocurre algo y **qué**
se observa entonces, en términos que ya existen en `docs/definitions.md`:

> **CA-N** — Cuando `<situación observable>`, entonces `<resultado comprobable>`.
> *(Verif.: T)*

Señales de que un criterio no vale: adjetivos sin medida (rápido, robusto, fluido,
coherente), verbos sin objeto («mejora la calidad»), y todo lo que exija leer la prosa
generada para decidir si pasa. Si el criterio no se puede convertir en un test o en una
demostración reproducible, no es un criterio: es un deseo, y su sitio es el problema o
el fuera de alcance.

## Paso 5 — Escribirlo en la spec

Las respuestas **se escriben en la spec**, no se quedan en la conversación:

- Mientras quede algo sin decidir, vive en **Preguntas abiertas**, con quién debe
  responder.
- Al cerrarse, la sección pasa a llamarse **Decisiones** y cada fila conserva `ID`,
  la decisión y **dónde aterriza** (los `RF-*`, `RI-*` y `CA-*` que toca), más el
  porqué. Un valor sin motivo es un número que nadie se atreve a cambiar después.
- Si una respuesta invalida algo ya escrito, lo corriges en el mismo paso y lo dices.
  Una spec con dos respuestas incompatibles es peor que una con un hueco.
- Si aparece un término que no está en `docs/definitions.md`: **no lo introduces**.
  Propones la definición y esperas confirmación (§2).

## Dónde paras

- **No cambias `estado`** ni rellenas `aprobada_por`. Ni aunque la puerta se abra y
  todo esté cerrado: lo dices y esperas.
- **No escribes el plan.** Eso es §3.3, y no antes de `estado: aprobada`.
- **No escribes código**, ni «para probar si la spec se sostiene».
- Si descubres que la spec está equivocada y no solo incompleta, paras y lo dices:
  se corrige y se vuelve a aprobar (§3.4).

## Al terminar una ronda, informas de esto

1. La puntuación, y las categorías que no estén en cero.
2. Las preguntas de esta ronda, o que no hay ninguna.
3. Qué has escrito en la spec y en qué apartado.
4. Qué falta para que una persona pueda aprobarla.

## De dónde sale esto

Tres técnicas de sistemas que no se pudieron instalar, traducidas al proceso de §3 y al
vocabulario de `docs/definitions.md`. El porqué de cada descarte y qué se le tomó a cada
uno están en `MyFactory/catalogo-sdd.md`: el barrido por taxonomía con cinco preguntas
viene del `/clarify` de GitHub Spec Kit, el umbral de ambigüedad como puerta del
`spec-phase` de GSD, y el requisito-sin-criterio-no-es-requisito del formato de OpenSpec.
