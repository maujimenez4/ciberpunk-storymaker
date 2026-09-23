---
id: 002-frontend
titulo: Frontend, versión 1 — la lectura del regalo
estado: borrador          # borrador | en-revision | aprobada | implementada
aprobada_por:             # lo rellena una persona, nunca un agente
fecha: 2026-09-23
depende_de: specs/001-backend-v1/spec.md
---

# 002-frontend — La lectura del regalo

Qué tiene que hacer la interfaz para que el destinatario lea la novela que le han regalado y quien la abra pueda corregir lo que esté mal, y cómo se sabrá que lo hace. **Aquí no se decide cómo se implementa:** eso es el plan, y no se escribe hasta que esta spec esté `aprobada`.

**Depende de la 001 y no la duplica.** Todo lo que esta spec consume —versiones publicadas, ficha, PDF, peticiones de cambio— lo produce el backend. Donde esta spec necesita algo que la 001 **no promete**, se dice con todas las letras y va a Preguntas abiertas, no se da por hecho.

---

## Problema

**Un regalo deja de serlo cuando se le ve la máquina.**

El destinatario abre un enlace y lo que tiene delante es una novela sobre él. Si esa página parece un panel de administración —con versiones, estados, botones de regenerar— el regalo se convierte en una demostración de producto. Y si la ficha de personajes le enseña en la portada al personaje que aparece en el capítulo nueve, le ha destripado el regalo antes de empezarlo.

**Y hay una segunda persona con necesidades opuestas.** El comprador encargó la novela y es quien detecta que el perro se llama Luna y debería llamarse Nala. Necesita exactamente lo que el destinatario no debe ver: el hecho concreto, el botón de corregirlo y la respuesta de qué capítulos cambiaron.

Las dos personas llegan por un enlace, sin cuenta y sin contraseña —el login está fuera del encargo—, y **la misma novela tiene que presentarse de dos maneras**.

Hoy no existe nada: `src/frontend/` está vacío, y el backend que sirve estos datos está en la Fase 1 de su plan.

---

## Alcance

**La lectura y lo que cuelga de ella.** Todo lo que el backend no hace.

| Capacidad | Encargo | Motivo |
| --- | --- | --- |
| Portada con la dedicatoria personalizada | §2 | Es lo primero que ve el destinatario, y lo único escrito para él y no por el modelo |
| Índice de capítulos navegable | §2 | Requisito literal, en ambos formatos |
| Lectura de un capítulo | §2 | Es el producto |
| Ficha de personajes y lugares, **con enlace al capítulo donde aparece cada uno** | §2 | Requisito literal. El enlace es la mitad que se olvida |
| **Revelado progresivo** de la ficha | — | Decisión propia: sin él la ficha es un índice de spoilers |
| Petición de cambio **desde la ficha**, para quien abra el enlace | §2 | Es lo que distingue la lectura web del PDF |
| Marca de **qué capítulos cambiaron** y página de novedades | §2 | Requisito literal para PDF; en web cuesta lo mismo |
| Lectura de una **versión anterior** | §2 | «En ambas opciones se conserva la versión anterior» |
| Enlace de **descarga del PDF** | §2, §8 | El encargo exige el PDF exportado aunque la lectura sea web |
| Dos vistas de la misma novela: **lectura** y **lectura con corrección** | — | Decisión propia. Ver §Restricciones |
| Cliente de API **generado del OpenAPI** | `CLAUDE.md` §7 | No se escriben tipos de respuesta a mano |

---

## Fuera de alcance

| Excluido | Motivo | Dónde |
| --- | --- | --- |
| Todo el backend: publicación, regeneración, validadores, PDF | Es la 001 | `specs/001-backend-v1/` |
| **Generar** el PDF | Lo produce el backend (RI-11 de la 001). Aquí solo se enlaza | 001 |
| Login, cuentas, recuperación de contraseña | Opcional del encargo y fuera de él | — |
| Editor manual del texto con *linter* en vivo | Opcional del encargo, y exige resolver antes el mapeo de prosa a canon | Después |
| **Seleccionar un fragmento de prosa** para pedir el cambio | Decisión: la petición se hace desde la ficha. Ver §Restricciones | Después |
| Panel del **Autor**: trazas, coste, estado de los trabajos | No lo pide el encargo, y es de otro actor | — |
| Aplicación móvil nativa | No lo pide el encargo. La lectura es web y responsiva | — |
| Modo sin conexión | No lo pide el encargo | — |

---

## Restricciones de diseño

**El stack es fijo y no lo decide esta spec.**

| Restricción | Origen | Dónde se detalla |
| --- | --- | --- |
| **React 19 + TypeScript estricto + Vite**, SPA | **Nuestro.** El encargo §2 dice «web o PDF» y no nombra tecnología | `CLAUDE.md` §4 y §5.2 |
| **Tres reglas de frontera**, comprobadas por ESLint y no a mano | **Nuestro** | `CLAUDE.md` §5.2 |
| **Nada de `any`** en código de producción | **Nuestro** | `CLAUDE.md` §7 |
| El cliente de API se **genera** del OpenAPI; no se escriben tipos a mano | **Nuestro** | `CLAUDE.md` §7 · RI-13 de la 001 |
| Estado de servidor con **TanStack Query**; estado de UI con `useState`/`useReducer`. **No se mezclan** | **Nuestro** | `CLAUDE.md` §7 |
| La lectura trabaja sobre **versiones publicadas inmutables** | **Nuestro**, derivado de RF-PUB-01/02 de la 001 | `CLAUDE.md` §7 |

### Las cuatro decisiones de producto, y por qué

Tomadas por `maujimenez4` el 2026-09-23. Van aquí y no en Preguntas abiertas porque están cerradas, y cada una descarta una alternativa que parecía razonable.

**D-01 · Un solo enlace: quien lee puede pedir el cambio.** Comprador y Destinatario **son personas distintas** —el encargo §Contexto lo deja claro: «los datos del destinatario… los detalles que el comprador ha aportado»— pero **ante la lectura tienen las mismas capacidades**: quien la abre lee y puede corregir un hecho escribiendo qué debería decir.

*Se descartó* separar dos enlaces con capacidades distintas, que fue la primera redacción de esta spec. **Conviene dejar escrito el argumento que la sostenía, porque sigue siendo bueno:** enseñarle al Destinatario un botón de «pedir un cambio» le revela que la novela la escribió una máquina y que se puede reescribir, que es lo que un regalo no debería mostrar.

**Se descartó igualmente, y por un motivo que pesa más:** el encargo §2 dice literalmente que **«el lector puede seleccionar un fragmento o un hecho y pedir un cambio desde la propia página»**. Restringirlo al comprador era una desviación del texto, no una lectura de él. Decisión de `maujimenez4`, 2026-09-23.

**D-02 · La petición se hace desde la ficha, no seleccionando prosa.** Cada entrada de la ficha **ya es un hecho de canon con su identificador**, así que la petición llega al backend diciendo exactamente qué hecho cambia — que es lo que RF-PET-03 de la 001 necesita para decidir qué capítulos regenerar. *Se descartó* la selección de texto, que es más natural para el lector, porque obliga a mapear prosa a canon con búsqueda difusa: **si acierta el hecho equivocado, se regeneran los capítulos equivocados**, y el lector no tiene forma de saberlo.

**D-03 · Distintivo en el índice y página de novedades.** El encargo lo exige literalmente para el PDF y en web cuesta lo mismo; el backend ya calcula qué capítulos cambiaron por diferencia de texto (RF-PUB-06). *Se descartó* resaltar las diferencias dentro del capítulo: un capítulo regenerado **se reescribe entero**, así que el resaltado sería casi todo el texto — ruido, no información.

**D-04 · La ficha se revela al avanzar.** Una entrada aparece cuando quien lee ha pasado por el capítulo donde el hecho se usa. *Se descartó* enseñar el canon entero, que es lo que el encargo pide literalmente, porque en una novela de diez capítulos que se lee de una sentada la ficha completa **es un índice de spoilers**. Cumplimos el requisito —la ficha existe y enlaza al capítulo— y no lo cumplimos de la forma que estropea el producto.

**D-05 · Mientras se regenera, la lectura se detiene y se muestra el progreso.** Decidido por `maujimenez4` el 2026-09-23. *Se descartó* seguir leyendo la versión vigente con un aviso —que es lo que la 001 ya permite, porque regenerar no destruye— para evitar que alguien lea un capítulo que está a punto de cambiar.

**Y hay que decir a quién le cuesta la espera, porque no siempre es quien la provocó.** Comprador y Destinatario pueden estar leyendo la misma novela a la vez: si uno pide una corrección, **el otro se queda sin su regalo durante minutos** sin haber pedido nada. La regeneración no es un instante — se rehacen capítulos, se revalidan y pasa Lean en G4.

Es el coste conocido de esta decisión, y se acepta a cambio de que nadie lea un capítulo que está a punto de cambiar.

---

## Actores

Los tres de `docs/definitions.md`, con el nombre que tienen allí y **solo ese**:

| Actor | Qué hace en esta spec |
| --- | --- |
| **Destinatario** | Abre el enlace, lee, consulta la ficha a medida que avanza, **pide correcciones** y descarga el PDF |
| **Comprador** | Lo mismo. **Ante la lectura tienen las mismas capacidades** (D-01); se distinguen en la 001, no aquí |
| **Autor** | **No aparece.** Su panel está fuera de alcance |

*`lector` está prohibido **como nombre del `Destinatario`, no como palabra**: la prueba es que si la frase seguiría siendo cierta en una novela que nadie regaló, es el lector narratológico y se queda. ~~cliente~~ y ~~usuario~~ no se escriben por «comprador». En esta spec `cliente` designa software —cliente de API generado— y el runtime del navegador se llama **navegador**, que es lo que es.*

**Que los dos actores puedan lo mismo aquí no los convierte en el mismo actor.** El encargo §Contexto los separa —«los datos del destinatario… los detalles que el comprador ha aportado»— y la 001 los trata distinto: el Comprador responde la entrevista y acepta la entrega; el Destinatario no toca el backend. Es la **lectura** la que no necesita distinguirlos.

---

## Requisitos

| Prefijo | Tipo | | Marca | Significado |
| --- | --- | --- | --- | --- |
| `CU-` | Caso de uso | | `M` | Imprescindible |
| `RI-` | Interfaz: ruta de la SPA o endpoint consumido | | `S` | Necesario pero degradable |
| `RF-` | Funcional | | **T/A/I/D/U** | Prueba / Análisis / Inspección / Demostración / No verificable |
| `RD-` | Datos y estado del navegador | | | |
| `RNF-` | No funcional | | | |

**68 requisitos en total:** 10 interfaces, 49 funcionales, 4 de datos y 5 no funcionales. Se desglosa porque un número a secas obliga a recontar para saber qué incluye — y porque el primer borrador de esta spec decía 57, contados a mano y mal. **Un número que hay que recontar caduca en silencio**, incluso escrito por quien acababa de escribir esa frase.

**Todo requisito cita su origen.** Uno sin origen es una invención y se rechaza en revisión.

### Casos de uso

**CU-01 · El destinatario lee su novela.** *Precondición:* existe una `VersionPublicada` y el destinatario tiene su enlace. *Flujo:* abre la portada con su dedicatoria → entra por el índice → lee capítulo a capítulo → consulta la ficha, que solo muestra lo que ya ha leído → puede descargar el PDF. *Postcondición:* **no ha visto ni un control de corrección, ni una versión, ni un estado.** → RI-01, RI-02, RI-03, RI-04, RI-05, RF-POR-01, RF-POR-02, RF-POR-03, RF-IND-01, RF-IND-02, RF-IND-03, RF-IND-04, RF-LEC-01, RF-LEC-02, RF-LEC-03, RF-LEC-04, RF-LEC-05, RF-FIC-01, RF-FIC-02, RF-FIC-03, RF-FIC-04, RF-FIC-05, RF-FIC-06.

**CU-02 · Quien lee corrige un hecho.** *Precondición:* existe una versión publicada y quien la abre tiene el enlace. *Flujo:* abre la ficha → pincha «Luna, el perro» → escribe qué debería decir → se envía la petición con el `hc_id` → la página informa de que la regeneración está en curso → al terminar, el índice marca los capítulos cambiados y hay una página de novedades. *Excepción:* la regeneración introduce un defecto → **la versión vigente no cambia**, y se dice que la petición no pudo aplicarse y por qué. → RI-06, RF-PET-01, RF-PET-02, RF-PET-03, RF-PET-04, RF-PET-05, RF-PET-06, RF-NOV-01, RF-NOV-02, RF-NOV-03, RF-NOV-04.

**CU-03 · Volver a una versión anterior.** *Precondición:* hay más de una versión publicada. *Flujo:* desde la página de novedades se abre la versión anterior y se lee igual que la vigente. *Postcondición:* **el texto antiguo es el mismo de siempre**; nada se recalcula. → RI-07, RF-NOV-03, RF-LEC-05.

**CU-04 · Descargar el PDF.** *Precondición:* existe una versión publicada. *Flujo:* se pulsa el enlace de descarga y llega el PDF de **esa** versión. → RI-08, RF-PDF-01, RF-PDF-02.

**CU-05 · Esperar a que termine una regeneración.** *Precondición:* hay una petición en curso sobre esta obra. *Flujo:* quien abre la lectura encuentra la novela detenida y ve el avance por capítulo. *Postcondición de éxito:* al terminar, la lectura vuelve con la versión nueva y el índice marcado. *Excepción:* la regeneración **termina sin publicar** —defecto introducido, o la generación se detuvo— → la espera **acaba**, la lectura vuelve a la versión de siempre y se explica qué pasó. → RF-ESP-01, RF-ESP-02, RF-ESP-03, RF-ESP-04, RF-ESP-05, RI-10.

### Interfaces

| ID | Interfaz | Pr. | Verif. |
| --- | --- | --- | --- |
| RI-01 | Ruta `/l/{token}` — portada. **Es la única entrada, y es la misma para todos** | M | Test |
| RI-02 | Ruta `/l/{token}/indice` | M | Test |
| RI-03 | Ruta `/l/{token}/capitulo/{n}` | M | Test |
| RI-04 | Ruta `/l/{token}/ficha` | M | Test |
| RI-05 | Ruta `/l/{token}/novedades` | M | Test |
| RI-06 | Consume `POST /obras/{id}/peticiones` (RI-09 de la 001) | M | Test |
| RI-07 | Consume `GET /obras/{id}/versiones` y `…/{v}` (RI-11 de la 001) | M | Test |
| RI-08 | Consume `GET /obras/{id}/versiones/{v}/pdf` (RI-11 de la 001) | M | Test |
| RI-09 | Consume `GET /obras/{id}/versiones/{v}/ficha` (RI-11 de la 001) | M | Test |
| RI-10 | Consume `GET /trabajos/{id}` (RI-06 de la 001) — estado de la regeneración, **legible por capítulo** | M | Test |

**Ninguna ruta lleva el identificador de la obra en claro.** El `token` de RI-01 es el identificador no adivinable de RF-PUB-07 de la 001, y es **lo único que protege la lectura**: quien lo tiene, entra. Con D-01 revertida ya no distingue a nadie, así que la spec deja de necesitar dos identificadores — y con ello **P-01 se cierra sola**.

### Funcionales — portada (§2)

**Lo primero que se ve es la dedicatoria, y la dedicatoria no la escribió el modelo.**

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-POR-01 | La portada muestra el título de la obra y **la dedicatoria**, tal y como la escribió el comprador | M | Test |
| RF-POR-02 | La dedicatoria se muestra **como texto del comprador y no como prosa del manuscrito**: no es el capítulo cero ni entra en la numeración (regla de dominio 15) | M | Test |
| RF-POR-03 | Desde la portada se entra al índice, a la ficha y a la descarga del PDF | M | Test |

### Funcionales — índice (§2)

**Navegable, y es donde vive la marca de lo que cambió.**

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-IND-01 | El índice lista los **diez capítulos** con su título y enlaza a cada uno | M | Test |
| RF-IND-02 | Marca **qué capítulos cambiaron** respecto a la versión anterior, con el dato que da el backend (RF-PUB-06 de la 001). **No lo calcula el navegador** | M | Test |
| RF-IND-03 | En la **primera** versión publicada no hay ninguna marca, porque no hay anterior con la que comparar | M | Test |
| RF-IND-04 | El índice dice **por dónde se iba**, y volver a él lleva al capítulo donde lo dejó | S | Test |

### Funcionales — lectura (§2)

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-LEC-01 | El capítulo se muestra completo, con navegación a anterior y siguiente | M | Test |
| RF-LEC-02 | El primer capítulo no ofrece «anterior» y el décimo no ofrece «siguiente» | M | Test |
| RF-LEC-03 | Un número de capítulo que no existe da una página de error legible, **no una pantalla en blanco** | M | Test |
| RF-LEC-04 | Leer un capítulo **marca su lectura**, que es lo que alimenta el revelado de la ficha (D-04) | M | Test |
| RF-LEC-05 | La prosa que se muestra es **la de la versión que se está leyendo**, fijada al publicar. No se recalcula por vigencia (RF-PUB-01 de la 001) | M | Test |

### Funcionales — ficha de personajes y lugares (§2)

**Existe, enlaza al capítulo, y no destripa.** Las tres cosas son requisitos distintos y la tercera es nuestra.

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-FIC-01 | La ficha lista personajes y lugares con su descripción, derivada de la *story bible* | M | Test |
| RF-FIC-02 | Cada entrada **enlaza al capítulo donde aparece**. Es requisito literal del encargo §2 y la mitad que se olvida | M | Test |
| RF-FIC-03 | Una entrada **solo se muestra cuando quien lee ha leído** el capítulo más temprano en que aparece (D-04) | M | Test |
| RF-FIC-04 | Lo aún no revelado **no se envía al navegador escondido con CSS**: se filtra antes de pintar. Un `display:none` no es una ocultación, es un spoiler a un «inspeccionar elemento» de distancia | M | Test (+Análisis) |
| RF-FIC-05 | La ficha dice **cuántas entradas quedan por descubrir**, sin decir cuáles. Una ficha que parece vacía se lee como un fallo | S | Test |
| RF-FIC-06 | Al saltar al último capítulo directamente, la ficha se revela entera: **se revela por lo leído, no por el número de capítulo** | M | Test |

### Funcionales — petición de cambio (§2)

**Quien abre el enlace puede pedirla.** No hay modo, ni enlace, ni permiso que lo distinga (D-01).

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-PET-01 | Cada entrada de la ficha ofrece **corregir este hecho**, y la petición viaja con el **`hc_id`** de esa entrada, no con el texto que el usuario escribió (D-02) | M | Test |
| RF-PET-02 | El formulario pide **qué debería decir**, en texto libre | M | Test |
| RF-PET-03 | Antes de enviar se dice **a cuántos capítulos afecta**, con el dato que da el backend | S | Test |
| RF-PET-04 | Enviada la petición, la lectura **sigue siendo legible**: la regeneración no bloquea la página | M | Test |
| RF-PET-05 | El estado de la regeneración es **consultable por capítulo** (RI-06 de la 001), no una barra de progreso inventada | M | Test |
| RF-PET-06 | Si la regeneración **no se publica** —hubo un defecto introducido—, se dice que la petición no se aplicó **y por qué**, y la versión vigente **no cambia** (RF-PET-06 y RF-PET-07 de la 001) | M | Test |

### Funcionales — espera durante una regeneración

**La lectura se detiene, y quien esté leyendo ve el mismo avance** (D-05).

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-ESP-01 | Con una petición en curso, la lectura **no se sirve**: el enlace lleva a la pantalla de espera | M | Test |
| RF-ESP-02 | El avance se muestra **por capítulo**, con el estado que da el backend (RI-06 de la 001). **No hay barra de progreso inventada** | M | Test |
| RF-ESP-03 | La espera **termina sola** cuando la regeneración acaba, y la lectura vuelve con la versión que corresponda. No hace falta recargar a mano | M | Test |
| RF-ESP-04 | Si la regeneración acaba **sin publicar** —defecto introducido, o la generación se detuvo—, la espera **acaba igual** y la lectura vuelve a la versión de siempre. Una pantalla de espera sin salida es peor que un error | M | Test |
| RF-ESP-05 | Si el backend **no responde** al consultar el estado, se reintenta con espera creciente y, agotado el intento, se ofrece **volver a la lectura**. La versión vigente sigue ahí: nunca se dejó de poder leer, solo se decidió no hacerlo | M | Test |

### Funcionales — novedades y versiones (§2)

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-NOV-01 | La página de novedades lista **los capítulos que cambiaron** en la versión vigente respecto a la anterior, con enlace a cada uno | M | Test |
| RF-NOV-02 | Dice **qué petición** produjo el cambio, con el texto que pidió quien la hizo | M | Test |
| RF-NOV-03 | Desde ahí se puede **abrir la versión anterior** y leerla igual que la vigente | M | Test |
| RF-NOV-04 | Una obra con una sola versión publicada **no muestra novedades**, y no es un error: no ha cambiado nada | M | Test |

### Funcionales — PDF (§2, §8)

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-PDF-01 | El enlace de descarga trae el PDF **de la versión que se está leyendo**, no siempre el de la vigente | M | Test |
| RF-PDF-02 | El PDF **no lo genera el navegador**: se enlaza al del backend | M | Análisis |

### Funcionales — estado, datos y fronteras

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-EST-01 | El estado de servidor vive en **TanStack Query** y el de UI en `useState`/`useReducer`. **No hay store global que mezcle los dos** | M | Análisis |
| RF-EST-02 | **Ningún `fetch` dentro de un componente**: vive en `shared/api/` o en el `api/` de la feature, y se consume por *hook* | M | Análisis (+Test) |
| RF-EST-03 | El cliente de API se **genera** del OpenAPI de la 001. Un tipo de respuesta escrito a mano es un defecto | M | Análisis |
| RF-EST-04 | Las respuestas del backend se muestran **como datos**, nunca como HTML interpretado: el manuscrito lo escribió un modelo a partir de texto que aportó un comprador | M | Análisis (+Test) |
| RF-FRO-01 | `shared/` **nunca** importa de `features/` | M | Análisis |
| RF-FRO-02 | Las features **no se importan entre sí** | M | Análisis |
| RF-FRO-03 | Se entra a una feature **solo por su `index.ts`** | M | Análisis |
| RF-FRO-04 | Las tres reglas las comprueba **ESLint `import/no-restricted-paths`**, y fallan la build. No se revisan a mano | M | Test |

### Funcionales — accesibilidad y presentación

**Renderizar no es ser accesible, y se comprueban por separado** (`CLAUDE.md` §7).

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-ACC-01 | Foco visible en todo elemento interactivo | M | Test |
| RF-ACC-02 | Toda la lectura es recorrible **solo con el teclado**: portada, índice, capítulos, ficha y el formulario de corrección | M | Test |
| RF-ACC-03 | Los formularios llevan **etiqueta asociada**, no solo texto de marcador | M | Test |
| RF-ACC-04 | Contraste **AA** en texto y en controles | M | Test |
| RF-ACC-05 | La prosa usa una medida de línea legible y se lee **en un teléfono sin desplazamiento horizontal** | M | Test |
| RF-ACC-06 | El título de la página cambia con la ruta: quien vuelve a una pestaña sabe dónde está | S | Test |

### Datos y estado del navegador

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RD-01 | El progreso de lectura —qué capítulos se han leído— vive **en el navegador**, por token. No es un dato del dominio ni viaja al backend | M | Test |
| RD-02 | Perder ese progreso **degrada, no rompe**: la ficha se muestra vacía con su aviso y la novela se lee igual | M | Test |
| RD-03 | **Ningún dato personal del destinatario se guarda fuera de lo que el backend ya sirve.** El navegador no acumula nada que no venga de la API | M | Análisis |
| RD-04 | **Ningún fragmento de manuscrito queda en el repositorio**, ni como fixture ni como instantánea de prueba. Los tests usan un manuscrito inventado | M | Análisis |

### No funcionales

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RNF-CAL-01 | `pnpm typecheck` y `pnpm lint` pasan, **incluidas las reglas de frontera** | M | Test |
| RNF-CAL-02 | **Nada de `any`** en código de producción | M | Análisis (+Test) |
| RNF-FIA-01 | La suite pasa **sin backend levantado**: la API se sustituye por un doble | M | Test |
| RNF-SEG-01 | El token de lectura **no aparece** en el título de la página, ni en analíticas, ni en logs del navegador | M | Análisis |
| RNF-REN-01 | La validación visual de la 001 (RF-VAL-08) abre **estas** páginas: portada, índice, capítulo y ficha. Esta spec las deja en rutas estables para que aquello pueda comprobarlas | M | Demostración |

---

## Criterios de aceptación

**Veintiocho criterios, y cuatro deciden si esto se lee o solo se renderiza:** CA-1 (se puede corregir desde la ficha), CA-4 (la ficha no destripa), CA-7 (una petición no rompe lo que ya estaba) y CA-12 (se lee con teclado). Los demás protegen partes.

- [ ] **CA-1** — Desde la ficha se puede **pedir una corrección**, y la petición sale con el `hc_id` de esa entrada. Quien lee, corrige: no hay modo ni enlace que lo impida. *(Test)* → RF-PET-01, RF-POR-03, RI-01.
- [ ] **CA-2** — La portada muestra la dedicatoria del comprador, y esa dedicatoria **no aparece en el índice ni cuenta como capítulo**. *(Test)* → RF-POR-01, RF-POR-02.
- [ ] **CA-3** — El índice lista diez capítulos, enlaza a cada uno, y **marca los que cambiaron** con el dato del backend; en la primera versión no marca ninguno. *(Test)* → RF-IND-01, RF-IND-02, RF-IND-03.
- [ ] **CA-4** — Un personaje que aparece por primera vez en el capítulo nueve **no está en la ficha** —ni en la respuesta que llega al navegador— hasta que el lector ha leído ese capítulo. *(Test)* → RF-FIC-03, RF-FIC-04.
- [ ] **CA-5** — Cada entrada de la ficha **enlaza al capítulo donde aparece**, y el enlace lleva allí. *(Test)* → RF-FIC-01, RF-FIC-02.
- [ ] **CA-6** — Saltando directamente al capítulo diez sin leer los anteriores, la ficha revela **lo de ese capítulo y no lo de los que no se han leído**. *(Test)* → RF-FIC-06, RF-LEC-04.
- [ ] **CA-7** — Cuando la regeneración no se publica por un defecto introducido, entonces la lectura **sigue mostrando el texto de siempre** y se dice que la petición no se aplicó y por qué. *(Test)* → RF-PET-06, RF-LEC-05.
- [ ] **CA-8** — La petición viaja con el **`hc_id`** de la entrada de la ficha; **cambiar el texto del formulario no cambia qué hecho se corrige**. *(Test)* → RF-PET-01, RF-PET-02.
- [ ] **CA-9** — Enviada una petición, la página **sigue siendo navegable** y el estado se lee por capítulo. *(Test)* → RF-PET-04, RF-PET-05.
- [ ] **CA-10** — La página de novedades lista los capítulos cambiados con enlace, dice qué petición los causó, y deja abrir la versión anterior, **que devuelve el mismo texto que antes**. *(Test)* → RF-NOV-01, RF-NOV-02, RF-NOV-03, RI-07.
- [ ] **CA-11** — Una obra con una sola versión **no muestra novedades y no da error**. *(Test)* → RF-NOV-04.
- [ ] **CA-12** — Portada, índice, capítulo, ficha y formulario de corrección se recorren **solo con el teclado**, con foco visible en cada parada. *(Test)* → RF-ACC-01, RF-ACC-02, RF-ACC-03.
- [ ] **CA-13** — El contraste es **AA** y la lectura no produce desplazamiento horizontal a 360 px de ancho. *(Test)* → RF-ACC-04, RF-ACC-05.
- [ ] **CA-14** — `pnpm typecheck` y `pnpm lint` pasan, y **un import entre features o desde `shared` hacia una feature falla la build**. *(Test)* → RF-FRO-01, RF-FRO-02, RF-FRO-03, RF-FRO-04, RNF-CAL-01, RNF-CAL-02.
- [ ] **CA-15** — La suite pasa **sin el backend levantado**. *(Test)* → RNF-FIA-01, RF-EST-02.
- [ ] **CA-16** — Un capítulo cuyo texto contiene `<script>` o HTML **se muestra como texto** y no se interpreta. *(Test)* → RF-EST-04.
- [ ] **CA-17** — El enlace de descarga trae el PDF **de la versión que se está leyendo**, no el de la vigente, cuando se está leyendo una anterior. *(Test)* → RF-PDF-01, RF-PDF-02, RI-08.
- [ ] **CA-18** — Borrado el progreso de lectura del navegador, la novela **se sigue leyendo** y la ficha aparece vacía con su aviso, no rota. *(Test)* → RD-01, RD-02, RF-FIC-05.
- [ ] **CA-19** — Un número de capítulo inexistente da una **página de error legible**, no una pantalla en blanco. *(Test)* → RF-LEC-03.
- [ ] **CA-20** — El **token no aparece** en el título de la página ni en ninguna traza del navegador, y ningún fragmento de manuscrito real está en el repositorio. *(Análisis)* → RNF-SEG-01, RD-03, RD-04.

- [ ] **CA-26** — Con una petición en curso, la lectura **se detiene** y se muestra el avance **por capítulo con el dato del backend**, no una barra inventada. *(Test)* → RF-ESP-01, RF-ESP-02, RI-10.
- [ ] **CA-27** — Cuando la regeneración termina **sin publicar**, la espera acaba, la lectura vuelve **al mismo texto de antes** y se explica qué pasó. *(Test)* → RF-ESP-03, RF-ESP-04, RF-PET-06.
- [ ] **CA-28** — Si el backend deja de responder durante la espera, **se puede volver a la lectura**; no queda una pantalla sin salida. *(Test)* → RF-ESP-05.
- [ ] **CA-21** — Las cinco rutas responden y pintan: portada, índice, capítulo, ficha y novedades. En el capítulo, **«anterior» no aparece en el primero ni «siguiente» en el décimo**. *(Test)* → RI-02, RI-03, RI-04, RI-05, RF-LEC-01, RF-LEC-02.
- [ ] **CA-22** — **Ningún componente hace `fetch`**, los tipos de respuesta son los generados del OpenAPI —uno escrito a mano falla la comprobación— y no hay store global que mezcle estado de servidor con estado de UI. *(Análisis + Test)* → RF-EST-01, RF-EST-03, RI-06, RI-09.
- [ ] **CA-23** — Volver al índice lleva **al capítulo donde se dejó**, y el título de la pestaña cambia con la ruta. *(Test)* → RF-IND-04, RF-ACC-06.
- [ ] **CA-24** — Antes de enviar la petición se dice **a cuántos capítulos afecta**, con el dato del backend y no con una cuenta hecha en el navegador. *(Test)* → RI-06, RF-PET-03.
- [ ] **CA-25** — Las cuatro páginas que abre la validación visual de la 001 —portada, índice, capítulo y ficha— responden en **URLs estables** y se abren sin paso previo. Si una ruta cambia, RF-VAL-08 de la 001 deja de comprobar lo que cree. *(Demostración)* → RNF-REN-01.

**Sobre CA-4, y por qué dice «ni en la respuesta que llega al navegador».** Un criterio que solo comprobara que la entrada no se *pinta* se cumple escondiéndola con CSS, y entonces el spoiler está a un «inspeccionar elemento» de distancia. La diferencia entre ocultar y no enviar no la ve el usuario: la ve quien mira. Por eso RF-FIC-04 es un requisito aparte.

**Sobre CA-21 a CA-25, y de dónde salieron.** Los cinco se añadieron en la auto-revisión, al cruzar mecánicamente los requisitos contra los criterios: **quince requisitos no estaban citados por ninguno**. Todos eran de la misma clase —rutas, fronteras de estado, detalles de navegación—, lo que se da por supuesto porque «se ve al abrir la página». Es justo lo que nadie escribe como criterio y por tanto nadie prueba.

**Sobre CA-8.** Es el criterio que protege D-02. Si la petición viajara con el texto que el comprador escribió en vez de con el `hc_id`, el backend tendría que adivinar qué hecho es — y entonces habríamos reintroducido por la puerta de atrás la búsqueda difusa que D-02 descartó por la de delante.

---

## Reglas de dominio afectadas

De las quince de `CLAUDE.md` §8, esta spec toca **una** directamente:

| Regla | Dónde se cumple |
| --- | --- |
| 15 — la dedicatoria no es prosa del manuscrito | RF-POR-02, CA-2 |

Las otras catorce las hace cumplir el backend. **Esta spec no puede violarlas porque no escribe nada en el dominio**: solo lee versiones publicadas y envía peticiones. Es una consecuencia del corte, y conviene que esté escrita — si alguna vez el frontend necesita escribir, el corte ha cambiado.

---

## Impacto técnico

**Lo que cambia los plazos, antes que la tabla:** esta spec **no se puede implementar entera hasta que exista la Fase 3 de la 001**, que es la que publica versiones y atiende peticiones. La portada, el índice, la lectura y la ficha se pueden construir contra un doble de la API; las novedades y la corrección, no — dependen de datos que todavía no existe quién produzca.

| Aspecto | Impacto |
| --- | --- |
| Estructura | Cinco features de frontend (`CLAUDE.md` §5.2). **Ninguna nueva**: `manuscrito` y `canon` son las que se usan |
| Dependencias nuevas | React 19, TypeScript, Vite, TanStack Query, React Router, Vitest, Testing Library, `eslint-plugin-import`, generador de cliente OpenAPI, `axe-core` para accesibilidad. Requieren aprobación (`CLAUDE.md` §3, punto 7) |
| Contrato | **Se genera del OpenAPI de la 001.** Si aquel cambia, esto se regenera y el `typecheck` lo detecta. Es la ventaja de no escribir los tipos a mano |
| **Dependencia de la 001** | Dos cosas que esta spec necesita y **la 001 no promete hoy**. Están en Preguntas abiertas como P-01 y P-02 |
| Accesibilidad | Se comprueba con herramienta, **no a ojo**. `CLAUDE.md` §7 dice que renderizar no es ser accesible |
| `docs/` al cerrar | `verification.md` §4.1 gana las letras de lo que aquí se verifica; `architecture.md` §6 gana la estructura real del frontend |

---

## Vocabulario

Todos los términos existen en `docs/definitions.md` v2.1: `Destinatario`, `Comprador`, `Dedicatoria`, `VersionPublicada`, `PeticionDeCambio`, `FichaDeLectura`, `HechoCanon`, `CuadroDeDefectos`.

**Esta spec no introduce ningún término nuevo**, y eso es a propósito: lo que la interfaz enseña son conceptos que ya existen en el dominio. Si hubiera necesitado inventar uno, sería señal de que está enseñando algo que el sistema no modela.

**Un término que se usa aquí y conviene no confundir:** «lectura» es la página web; `FichaDeLectura` es el artefacto del dominio que el backend deriva al publicar. No son lo mismo y el nombre se parece demasiado.

---

## Preguntas abiertas

Mientras quede una, esta spec **no se aprueba** (`CLAUDE.md` §3.2).

| ID | Pregunta | Quién responde |
| --- | --- | --- |
| P-02 | **D-04 y RF-FIC-02 necesitan que la ficha diga, por entrada, en qué capítulos aparece.** La 001 promete la `FichaDeLectura` derivada y reproducible (RF-PUB-05), pero **no promete que lleve los capítulos**. El dato existe en el canon (RF-MEM-02). ¿Se añade a la ficha de la 001, o el frontend hace una consulta aparte al canon (RI-12)? | Autor |
| P-03 | ¿Se implementa esta spec **después** de la Fase 3 de la 001, o en paralelo contra un doble de la API, aceptando que la mitad no se puede probar de punta a punta hasta que aquella exista? | Autor |
| P-04 | El encargo §8 exige el PDF de una novela completa en `/ejemplos/novela-ejemplo.pdf`. ¿Ese fichero lo produce la corrida de evaluación de la 001 (RF-EVA-01) o es un paso aparte de la entrega? | Autor |

**P-02 es el hallazgo de escribir esta spec.** La 001 se escribió declarando que la interfaz era de la 002 y que aquí solo se consumía su API. Al detallar qué consume exactamente, **apareció algo que nadie prometió**. No es un fallo de la 001: es lo que pasa cuando dos specs se escriben con distancia y la segunda es la primera que mira el contrato de verdad.

*Había una P-01 —dos enlaces con permisos distintos, que la 001 no podía dar— y **la reversión de D-01 la disolvió**: sin dos modos, no hacen falta dos identificadores. Queda anotado porque es el caso más limpio del día de una pregunta que no se responde, se deja de necesitar.*

---

## Lo que esta spec no verifica

| Qué no se verifica | Por qué | Qué lo cubriría |
| --- | --- | --- |
| Que la lectura **sea agradable** | Ningún test juzga una tipografía ni un ritmo de página. El contraste y la medida se miden; que apetezca leer, no | Una persona mirándola. Es **U** |
| Que el destinatario **no adivine** que hay otra versión de la página | La ausencia de controles se comprueba; que no deduzca su existencia, no | Nada. Riesgo declarado |
| Que la ficha **no destripe por otra vía** | Se comprueba que no se envía lo no leído. Un título de capítulo puede destripar igual, y esos vienen del outline | Nada dentro de esta spec |
| Que el progreso de lectura **refleje lo leído** | Se registra al abrir el capítulo, no al leerlo. Abrir y cerrar cuenta como leído | Nada razonable. Medir lectura real es peor que el problema |
| Que la accesibilidad sea **real** | `axe-core` comprueba reglas mecánicas. Un lector de pantalla con una persona detrás encuentra cosas que ninguna regla ve | Una prueba con usuario. Es **U** |
| Que el PDF y la web **digan lo mismo** | Son dos artefactos de la misma versión, y nada compara sus contenidos | Nada hoy |

---

## Cierre

Pendiente. Esta spec está en `borrador` y tiene **cuatro preguntas abiertas**, dos de las cuales —P-01 y P-02— **no se pueden resolver dentro de esta spec**: obligan a decidir si se amplía la 001, que ya está aprobada y firmada.
