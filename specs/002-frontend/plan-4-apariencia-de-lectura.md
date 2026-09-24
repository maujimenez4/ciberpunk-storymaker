---
id: 002-frontend / plan-4-apariencia-de-lectura
titulo: "Fase 4 — Que parezca un lector de libros, no un formulario"
estado: completado        # borrador | en-revision | aprobado | completado — revisión visual (U) de maujimenez4, 2026-09-24: «ya la revise y la apruebo»
aprobado_por: maujimenez4 # firmado el 2026-09-24 («esta aprobado ese plan, implementalo»)
fecha: 2026-09-24
spec: specs/002-frontend/spec.md      # D-06 («Leer… tipo Kindle»), D-07, RF-ACC-*
---

# Fase 4 — Que parezca un lector de libros, no un formulario

> **Enmienda 1 · 2026-09-24 · la dirección visual pasa a ser «Cuaderno de viaje».** Implementada la primera dirección (papel frío, ciruela, Atkinson), `maujimenez4` la revisó y dijo que no le terminaba de gustar; pidió algo «más vintage». Se exploraron cuatro direcciones en un lienzo de diseño (Imprenta, Fichero, Tela y oro, Cuaderno de viaje) y eligió la última: *«Me gusto la D, asi que esa usaremos. Ahora si, implementala»*.
>
> **Qué cambia:** la sección *Dirección visual* de abajo queda **sustituida** en color, tipografía y ornamento por la de la enmienda (al final de este fichero). **Qué no cambia:** las tareas T1–T6, sus tests, la navegación en píldora, «Creación», el panel «Aa», el pie de lectura, los tres temas y todo lo que dice *Lo que esta fase no hace*. La decisión 1 (tipografía de interfaz aparte) **se revierte**: en D la interfaz también es serif (Spectral), porque una sans rompía el cuaderno.

**Objetivo:** que la página se sienta como un lector electrónico —la interfaz se retira y queda el libro— sin tocar el proceso, que está bien: primero la entrevista, luego historia, capítulos y publicación.

**Enfoque:** la casa se queda (tokens, primitivos, `Pagina`, fronteras de ESLint). Cambia **la piel**: tipografía de interfaz, controles redondeados, navegación en píldora, temas de lectura y una vista de progreso que sobrevive a la recarga **con su sitio en la navegación**.

**Spec:** [`spec.md`](spec.md). D-06 ya pedía «Leer, la novela entera y continua, **tipo Kindle**»; esta fase lo cumple en lo visual. Ningún requisito de la 002 decae.

---

## Por qué, en una línea por problema

| Lo que ve hoy el comprador | Lo que falla |
| --- | --- |
| Pestañas subrayadas y botones rectangulares | Parece un formulario administrativo, no un regalo que se lee |
| Una sola familia (Literata) para prosa **y** para botones, etiquetas y avisos | La interfaz y el libro hablan con la misma voz, y el libro pierde protagonismo |
| Al recargar a mitad de novela, el progreso aparece **dentro** de la pestaña «La entrevista» | La pestaña se llama como algo que ya terminó; «Leer» y «Quién es quién» salen apagadas sin decir por qué ni cuándo se abren |
| Un solo tema claro, tamaño fijo | Un lector de libros deja elegir tamaño y fondo; de noche, en un móvil, el blanco deslumbra |

---

## Dirección visual

**Una frase:** *la pantalla de un lector electrónico al que le han cosido una cinta ciruela.* La interfaz es gris, pequeña y redondeada; el libro es grande, serif y sin marco; el ciruela solo aparece donde se puede tocar o donde algo avanza.

### Color (se mantienen los tres tokens actuales y se añaden temas)

| Token | Papel (por defecto) | Sepia | Noche |
| --- | --- | --- | --- |
| `--papel` fondo | `#f2f3ee` (el actual, frío) | `#efe6d4` | `#1c2024` |
| `--tinta` texto | `#1b2a3a` (el actual) | `#3b2f22` | `#d9d6ce` |
| `--tinta-suave` metadatos | `#4a5b68` | `#6a5a47` | `#9aa3ab` |
| `--guarda` bloques no-prosa | `#e4e7de` | `#e3d8c3` | `#262b30` |
| `--acento` lo que se toca | `#6b3a52` (ciruela actual) | `#6b3a52` | `#c9a0b6` |

Sepia existe porque es lo que un lector de libros ofrece, **no es el tema por defecto** (el crema con acento terroso es la estética que más se repite en páginas generadas). Noche no usa negro puro ni gris neutro: es azul pizarra, de la misma familia que la tinta. **Cada pareja texto/fondo pasa AA con `axe`** (RF-ACC-04) en los tres temas; si una no pasa, se corrige el valor, no se relaja el test.

### Tipografía

| Rol | Familia | Por qué |
| --- | --- | --- |
| **El libro**: prosa, títulos de capítulo, dedicatoria | **Literata** (se queda) | Es una serif hecha para leer en pantalla largo rato; es lo que ya pide la spec |
| **La interfaz**: pestañas, botones, etiquetas, avisos, progreso | **Atkinson Hyperlegible Next** | Diseñada para legibilidad, con formas claras en tamaños pequeños. Separa la voz de la interfaz de la del libro sin competir con ella |

Escala: la actual (razón 1.25) para el libro; la interfaz baja un escalón (`0.875–0.9375rem`), en caja normal, **sin mayúsculas sostenidas en etiquetas**.

### Forma

- **Botones en píldora** (`border-radius: 999px`), tres pesos: **principal** (relleno ciruela), **secundario** (contorno), **discreto** (solo texto, para «Empezar otra novela»).
- **Campos** con radio de 12 px, borde de 1 px en tinta aguada, foco con anillo ciruela de 3 px (RF-ACC-01).
- **Avisos y bloques** con radio de 16 px y fondo `--guarda`, **sin sombras**. El radio sigue la jerarquía: el botón es el más redondo, el bloque el que menos.
- **Nada de tarjetas** alrededor de la prosa. El libro no tiene marco.

### Navegación

```
 ┌──────────────────────────────────────────────┐
 │  Tu novela                              Aa    │   ← barra mínima; Aa solo al leer
 │  ( Creación ) (  Leer  ) ( Quién es quién )   │   ← control segmentado en píldora
 └──────────────────────────────────────────────┘
```

- La primera pestaña pasa de «La entrevista» a **«Creación»**, y dentro enseña **lo que toque según la fase**: el formulario, o el progreso si ya hay una novela en marcha.
- **Si al cargar hay una novela en curso** (el `obra_id` que ya se guarda en el navegador desde la fase anterior), la página abre en «Creación» con el progreso, y «Leer» y «Quién es quién» siguen apagadas **pero dicen por qué**: «Se abre cuando termine la novela · capítulo 3 de 10». Es lo que pediste: saber dónde mirar tras recargar sin volver a mandar nada.
- **No se habilita «Leer» antes de publicar**: la lectura sirve versiones publicadas, y publicar exige los diez capítulos con su puerta (regla de dominio 14). Enseñar capítulos sueltos a medio escribir sería una decisión de producto nueva, no de apariencia.

### La creación

```
  Entrevista ✓ ── Historia ✓ ── Capítulos ── Publicación
  ────────────────────────────────────────────────────
  Se está escribiendo tu novela
  Capítulo 3 de 10

  ▰▰▰▱▱▱▱▱▱▱                                (diez tramos)
  Empezó hace 24 min · Faltan unos 56 min (estimación)
```

Los pasos pasan a ser una **línea con nodos** (hecho, actual, pendiente) en lugar de palabras subrayadas; la barra de diez tramos se queda (ya es la metáfora de los pliegos cosidos) con los extremos redondeados. **La entrevista se parte en tres bloques con título**: *Quién es*, *Cómo quieres la historia*, *Lo que no debe aparecer*; mismos campos y mismo contrato con el backend.

### La lectura

```
            Capítulo 3
       El verano que no llovió

   Lorem ipsum… (Literata, medida 34rem,
   sangría de libro, sin marco)

  ─────────────────────────────── 34 %
  Quedan 6 min en este capítulo
```

- **Panel «Aa»** (se abre con un botón, se cierra con Escape, foco atrapado mientras está abierto): **tamaño** (4 pasos), **interlineado** (3) y **tema** (Papel, Sepia, Noche). Se guarda en el navegador; es comodidad de quien lee, no dato del dominio (RD-01, RD-03).
- **Pie de lectura fijo y fino**: porcentaje de la novela leído y **minutos que quedan del capítulo**, calculados con las palabras del capítulo a 230 palabras por minuto. Es el gesto más reconocible de un lector electrónico.
- El título del capítulo centrado, el número en tinta aguada encima. La dedicatoria se queda como está (cursiva, grande): es lo único que no existe en ninguna otra novela.

### Movimiento

Uno solo, el que ya existe: el tramo en curso late. Abrir y cerrar el panel «Aa» se anima porque responde a un gesto. Todo lo demás, quieto; con `prefers-reduced-motion`, nada.

---

## Tareas

Cada tarea es un commit con sus tests. **Lo que se puede comprobar se comprueba en rojo primero**; lo puramente visual (que un radio o una tipografía «queden bien») no lo juzga ningún test, y la spec ya lo clasifica como **U**: se revisa mirándolo, con capturas en el informe.

| # | Tarea | Qué se comprueba con test |
| --- | --- | --- |
| **T1** | **Tokens y temas.** Variables por tema en `estilos.css` bajo `[data-tema]`, la tipografía de interfaz, y el tema aplicado en `<html>` | Contraste AA con `axe` en **los tres temas** (hoy solo se mira uno) |
| **T2** | **Primitivos redondeados.** `Boton` con `principal` / `secundario` / `discreto`; campos, selector y área de texto; `Aviso` | Las variantes existen y el foco es visible (RF-ACC-01); los tests de primitivos actuales siguen en verde |
| **T3** | **Navegación en píldora y la pestaña «Creación».** Control segmentado; con novela en curso guardada, abre en Creación, y Leer y Quién es quién dicen por qué están apagadas y cuándo se abren | Recarga con `obra_id` guardado ⇒ Creación activa y las otras dos `disabled` con su motivo en `aria-describedby`; sin novela ⇒ formulario; con token ⇒ Leer. Teclado: flechas entre pestañas (RF-ACC-02) |
| **T4** | **La creación.** Pasos como línea con nodos, barra con extremos redondeados, entrevista en tres bloques | El contrato del formulario no cambia: el cuerpo de `/respuestas` es idéntico (el test que ya existe lo guarda); los pasos siguen marcando `aria-current="step"` |
| **T5** | **Panel «Aa».** Tamaño, interlineado y tema, guardados en el navegador con `try/catch` | Cambiar el tema pone `data-tema` en `<html>`; se recuerda al recargar; sin `localStorage` funciona con los valores por defecto; Escape cierra y devuelve el foco al botón |
| **T6** | **Pie de lectura.** Porcentaje leído y minutos que quedan del capítulo | Con un capítulo inventado de 1.150 palabras a mitad, «quedan 3 min»; al final, 100 %. **Manuscrito inventado** en los tests (RD-04) |

**Orden:** T1 → T2 → T3 → T4, que es lo que ves hoy, y luego T5 → T6, que es la lectura. T3 es la que responde a «dónde veo el progreso si recargo».

**Puertas de cada tarea:** `vitest` completo, `tsc`, `eslint` (incluye las fronteras), y una captura por tema de la vista tocada.

---

## Lo que esta fase no hace

- **No cambia el proceso** ni ningún contrato con el backend.
- **No abre «Leer» antes de publicar** (regla 14). Si se quiere leer por capítulos mientras se escribe, es una decisión de producto aparte.
- **No convierte la entrevista en una pregunta por pantalla.** Sería más conversacional, pero es un rediseño del flujo, no de la piel; queda como propuesta.
- **No añade dependencias.** Las fuentes vienen de Google Fonts, como Literata hoy.

---

## Decisiones que te pido al firmar

Van con recomendación; si no dices nada, se aplica la recomendada.

**Resueltas al firmar:** el plan se aprobó sin cambios, así que rigen las cuatro recomendadas — tipografía de interfaz aparte, tema por defecto según el sistema (Papel como claro), Sepia disponible pero nunca por defecto, y la primera pestaña se llama «Creación».

1. **Tipografía de interfaz aparte (Atkinson Hyperlegible Next)** o todo en Literata como hoy. *Recomendado: aparte.*
2. **Tema por defecto:** Papel (el actual) o seguir la preferencia del sistema (claro u oscuro). *Recomendado: seguir el sistema, con Papel como claro.*
3. **Sepia sí o no** entre los temas. *Recomendado: sí, pero nunca por defecto.*
4. **El nombre de la primera pestaña:** «Creación», «Tu novela» o «Encargo». *Recomendado: «Creación».*

---

## Enmienda 1 · Dirección visual «Cuaderno de viaje»

**Una frase:** *la novela como un viaje anotado en un diario de los años veinte*: tinta azul de estilográfica, sellos postales en rojo desvaído y el margen rojo de un cuaderno. La maqueta aprobada son las cuatro pantallas de la fila D del lienzo de diseño (Leer, Quién es quién, Creación: entrevista, Creación: progreso).

### Color (tema Papel; Sepia y Noche se derivan con las mismas reglas de contraste AA)

| Token | Papel | Para qué |
| --- | --- | --- |
| `--papel` | `#e6e0d2` | Fondo |
| `--tinta` | `#2a2a2e` | Texto |
| `--tinta-suave` | `#5f5a50` | Metadatos, ayudas |
| `--acento` | `#243a5e` | **Tinta de estilográfica**: títulos, pestaña activa, botón principal |
| `--sello` *(nuevo)* | `#9b3b32` | Sellos, leyendas de bloque, lo recorrido en el mapa. Nunca texto de párrafo |
| `--margen` *(nuevo)* | `#d3a8a0` | La línea roja del margen del cuaderno. Decorativa |
| `--guarda` | `#f1ece0` | Hoja del cuaderno: formularios, etiquetas |

### Tipografía

| Rol | Familia |
| --- | --- |
| Títulos (novela, capítulo, pantalla), sellos | **Sorts Mill Goudy** (`--fuente-titulo`, nuevo) |
| Prosa **e interfaz** | **Spectral** (`--fuente-libro` y `--fuente-interfaz` apuntan a ella) |

### Ornamento, pantalla por pantalla

- **Pasos:** el paso actual es un **sello** circular punteado e inclinado («paso 1 de 4»).
- **Progreso:** un **mapa de ruta**: diez paradas sobre una línea de puntos, lo recorrido en `--sello`, la parada actual sellada, bandera en la meta. Copia: «Tu novela va de camino».
- **Entrevista:** hoja de cuaderno rayada con margen rojo, campos en píldora, leyendas de bloque en cursiva `--sello`.
- **Leer:** el número de capítulo como sello en el margen izquierdo, la línea roja de margen junto a la prosa, pie con la posición como un punto sobre una línea de puntos.
- **Quién es quién:** «Quién viaja contigo»; cada entrada es una **etiqueta de equipaje** con su agujero; las no reveladas, un sello «+N».

**Se mantienen:** botones en píldora, el control segmentado, «Aa», los tres temas, el foco visible y el contraste AA en los tres, que es test y gana a la estética.

**Se revierte la decisión 2** (tema según el sistema), el mismo día, tras ver la D en un sistema en modo oscuro: *«solo que usa el modo claro, no el modo oscuro»* (`maujimenez4`). Sin elegir nada, el tema es **siempre Papel**; Noche y Sepia solo se aplican si se eligen en «Aa», y la opción «Automático» desaparece.
