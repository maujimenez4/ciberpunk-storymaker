---
id: 002-frontend-v1
titulo: Frontend, versión 1 — entregar una novela y dejar que quien la recibe pida cambios
estado: borrador          # borrador | en-revision | aprobada | implementada
aprobada_por:             # lo rellena una persona, nunca un agente
fecha: 2026-09-23
---

# 002-frontend-v1 — Frontend, versión 1: la lectura

Qué debe poder hacer quien recibe una novela, y cómo se sabrá que lo hace. **Aquí no se decide cómo se implementa:** eso es el plan, y no se escribe hasta que esta spec esté `aprobada`.

Es la segunda y última spec del repositorio. La primera, `001-backend-v1`, entrega **cómo se escribe** una novela; esta entrega **cómo se lee**. Entre las dos está el producto.

**Cubre las dos capas a propósito.** `CLAUDE.md` organiza por **feature** y no por capa, en backend (§5.1) y en frontend (§5.2). «Lectura» es una feature que cruza las dos: su API y su interfaz. Partirla en una spec de backend y otra de frontend obliga a describir el mismo endpoint dos veces, y dos descripciones del mismo hecho divergen.

---

## Problema

Una novela terminada existe hoy como filas en SQLite y, si alguien lanza `corrida.py`, como un fichero de texto en la máquina de quien la generó. **Nadie más puede leerla.**

Quien lo sufre es el **destinatario**: recibe un regalo que no puede abrir. Y el **comprador**, que no puede comprobar qué compró ni pedir que se corrija lo que no encaja —un nombre mal puesto, un perro que se llama de otra manera— sin hablar con quien operó el sistema.

Pero el problema no es de interfaz, es de concepto, y hay tres agujeros debajo:

**1 · No existe «lo que se entregó».** `RepositorioDeManuscrito.ensamblar(obra_id)` hace `JOIN version_texto v ON … AND v.vigente = 1` (`features/manuscrito/repository.py:53-64`). Eso contesta «el manuscrito **ahora**», no «el que se entregó el día 3». Dos llamadas separadas por una regeneración devuelven textos distintos para la misma obra, y la anterior deja de ser recuperable en cuanto otra se marca vigente. Un regalo no funciona así: quien lo recibe tiene que poder volver dentro de un año y encontrar lo mismo.

**2 · Se entrega prosa que no pasó la puerta.** La vigencia no sabe nada de puertas de calidad. En la corrida real del 2026-09-23 la escena 8 escaló por `SEG-01` y sus 2.038 palabras están en el entregable. Está declarado como desviación en el Cierre de la 001.

**3 · No se sabe qué capítulos usan un hecho.** Sin eso, «corrige el nombre del perro» no se puede resolver: no hay forma de saber qué hay que regenerar. `ejecucion.ids_recuperados` solo cubre la capa de memoria; la capa de canon etiqueta por posición y el `hc_id` **no llega nunca** desde el almacén.

Y el frontend no existe: `src/frontend/` está vacío, sin `package.json`. La arquitectura está decidida y documentada (`architecture.md` §6) y no se ha escrito una línea contra ella.

---

## Alcance

| Capacidad | Motivo |
| --- | --- |
| `VersionPublicada`: fijar de forma inmutable qué textos se entregaron | Es el concepto que falta y del que cuelga todo lo demás |
| Publicar **solo** lo que pasó la puerta | Hoy se entrega prosa escalada sin que nadie lo note |
| `Destinatario` y `Dedicatoria` en el esquema | La obra no tiene hoy dónde guardar de quién es el regalo |
| Portada con dedicatoria, índice navegable y lectura de capítulo | Es el producto que se regala |
| `FichaDeLectura` **derivable y reproducible**, con enlace al capítulo de cada aparición | Es lo que hace útil el canon fuera del sistema |
| Descarga del PDF de la versión que se está leyendo | La web es la lectura; el PDF es el artefacto portable |
| Petición de cambio del lector, con regeneración acotada | Es la mitad interactiva del producto |
| Distinguir defecto **preexistente** de **introducido** al revalidar | Sin esto, la primera petición se rechaza por deuda vieja |
| Marcado de los capítulos que cambiaron, y reversión | Sin marcado, una regeneración es invisible; sin reversión, la autopublicación no tiene contrapeso |
| `hc_id` en la capa de canon, persistido en `ejecucion` | Sin él no hay petición de cambio posible, y `RI-14` de la 001 queda a medias |
| Validación visual con browser MCP | Comprueba lo único que ningún test de unidad ve: que la página existe en un navegador |

**Ámbito:** la feature completa, backend e interfaz.

---

## Fuera de alcance

| Excluido | Motivo | Cuándo |
| --- | --- | --- |
| Taller del autor: inspector de contexto, panel de defectos, outline, auditoría | `architecture.md` §6.1 los contempla; el encargo no los pide y duplicarían el trabajo | Después del entregable |
| Entrevistador y brief personalizado | Esta spec **guarda** el destinatario; no lo entrevista | Trabajo posterior, documentado en `docs/` |
| Guardrail de palabras prohibidas | Se aplica sobre el capítulo antes de que la lectura lo vea | Ídem |
| Observabilidad, evaluaciones, Lean y TLA+ | Instrumentan y verifican el harness, no la lectura | Ídem |
| El **filtro estructural** de `RF-CTX-07` | Desviación declarada en el Cierre de la 001. Esta spec no lo arregla ni lo empeora | Deuda de la 001 |
| El desbordamiento del tope de `memoria_recuperada` | Medido: 20.000–24.000 contra un tope de 10.000 al cerrar un capítulo de diez escenas | Deuda de la 001 |
| Devolver `CAN-01` y `CON-03` a `BLOQUEANTES_EN_G1A` | Decisión de `maujimenez4`, pendiente de la medición que pide su D-3 | Decisión suya |
| Autenticación y multiusuario | Fuera del encargo. Aquí solo se exige que el identificador no sea adivinable | — |
| Edición manual del texto por el lector | El lector pide cambios; no escribe prosa. Editar a mano abre la puerta a texto que nadie validó | — |

### Lo que el encargo pide y estas dos specs **no** cubren

Se escribe aquí para que nadie lea las dos specs y concluya que el producto está
especificado entero. **No lo está, a propósito.** Entre `001-backend-v1` y esta quedan
cubiertas la escritura y la lectura; el resto del encargo es trabajo posterior que **no
llevará spec**, por decisión de `maujimenez4` del 2026-09-23, y se documentará en `docs/`.

| Área del encargo | Estado |
| --- | --- |
| Configuración: agente entrevistador, detección de datos faltantes y de contradicciones, texto libre no confiable | **Sin cubrir.** Es la otra mitad del producto |
| Guardrail de palabras prohibidas en tres niveles, con normalización y audit log | **Sin cubrir** |
| Observabilidad en Langfuse: sesión, spans, tokens, coste, latencia, scores, prompts versionados | **Sin cubrir** |
| Evaluación: LLM-as-judge con rúbrica, revisión humana, cinco briefs, tabla de resultados, iteración de tuning | **Sin cubrir.** La 001 lo declara fuera de su alcance |
| Verificación formal: Lean 4 sobre la cronología, TLA+ sobre el harness | **Sin cubrir.** Falta además la tabla de cronología en el esquema |
| Hooks de validación de capítulo y de policy | **Sin cubrir** |
| Resúmenes por capítulo y reanudación por capítulo | **Parcial** en la 001: hay reanudación de trabajo, no checkpoint por capítulo |
| `README.md`, `.env.example`, `/ejemplos/novela-ejemplo.pdf`, `/presentacion`, vídeo, `.claude/mcp.json` | **Ninguno existe** |

Lo que sí cubren las dos specs: los roles del harness, las herramientas con esquema, los
reintentos con límite, el presupuesto de 100.000 tokens, la *story bible* en SQLite, los
validadores mecánicos, la relación hecho → capítulos, y la lectura interactiva entera con su
validación visual por browser MCP.

---

## Requisitos

Convenciones, las de `specs/001-backend-v1/spec.md`:

| Prefijo | Tipo | | Marca | Significado |
| --- | --- | --- | --- | --- |
| `CU-` | Caso de uso | | `M` | Imprescindible: si falta, no se cumple un criterio de aceptación |
| `RI-` | Interfaz externa | | `S` | Necesario pero degradable sin invalidar la entrega |
| `RF-` | Funcional | | **T/A/I/D/U** | Prueba / Análisis / Inspección / Demostración / No verificable (`verification.md` §4) |
| `RD-` | Datos | | | |
| `RNF-` | No funcional | | | |

**Todo requisito cita su origen.** Las palabras **debe**, **no debe** y **puede** se usan en sentido normativo. **Una letra por requisito:** la del método que lo **establece**; un segundo método que lo refuerza va entre paréntesis.

### Casos de uso

**CU-01 · Publicar una novela.** *Precondición:* la obra tiene capítulos integrados. *Flujo:* se fijan los `version_texto_id` de cada capítulo → se deriva la `FichaDeLectura` → se guarda el cuadro de defectos de esa publicación → queda una `VersionPublicada` inmutable. *Postcondición:* esa versión devuelve el mismo texto dentro de un año. *Excepción:* algún capítulo no pasó la puerta → **no se publica** y falla con error de dominio. → RI-07, RF-PUB-01, RF-PUB-02, RF-PUB-03, RF-PUB-04, RF-PUB-05, RF-PUB-06, RF-PUB-07.

**CU-02 · Abrir el regalo.** *Precondición:* existe una `VersionPublicada`. *Flujo:* el destinatario abre la URL → ve la portada con su dedicatoria → entra por el índice al capítulo 1. *Postcondición:* ha leído sin elegir versión ni entender el sistema, y lo que ve es **esa** versión, no lo vigente de hoy. → RI-01, RI-02, RF-LEC-01, RF-LEC-02, RF-LEC-03, RF-LEC-04, RF-LEC-05.

**CU-03 · Consultar quién es quién.** *Precondición:* la versión tiene ficha. *Flujo:* el lector la abre, ve personajes y lugares, pincha uno y llega al capítulo donde aparece. *Postcondición:* la ficha mostrada es la **congelada con esa versión**, no el canon de hoy. → RI-03, RF-FIC-01, RF-FIC-02, RF-FIC-03, RF-FIC-04, RF-LEC-06.

**CU-04 · Llevarse la novela.** *Precondición:* la versión existe. *Flujo:* el lector pulsa descargar. *Postcondición:* obtiene el PDF **de la versión que está leyendo**, no de la última. → RI-04, RF-PUB-09, RF-LEC-07.

**CU-05 · Pedir un cambio** *(caso central)*. *Precondición:* el lector lee una `VersionPublicada`.

*Flujo principal:* selecciona un fragmento o una entrada de la ficha → describe el cambio → se registra la `PeticionDeCambio` y arranca un trabajo → el lector ve el progreso **por capítulo** y sigue leyendo → el sistema determina los capítulos afectados, corrige el canon **sin editarlo**, los regenera, revalida G1a sobre los posteriores al origen del hecho sustituido y compara con el cuadro guardado → si no hay ningún defecto **introducido**, publica una versión nueva y la lectura ofrece saltar a ella con los capítulos cambiados marcados.

*Flujos alternativos:*
- Defecto **introducido** por la regeneración → no se publica, el trabajo termina en `ESCALADA`, la vigente no cambia y el lector ve que su petición no se atendió y por qué.
- Defecto **preexistente** → **no impide publicar.** Se registra y se le muestra al autor, no al lector.
- Se agota el límite de reintentos —máximo dos, `architecture.md` §8.3— → igual que el primero.

*Postcondición de éxito:* existe una `VersionPublicada` nueva que `sucede_a` la anterior, y la anterior sigue siendo legible entera. *Postcondición de fracaso:* la vigente es exactamente la de antes, y **la `PeticionDeCambio` se conserva con su resultado**. → RI-05, RI-06, RF-PET-01 a RF-PET-12, RF-LEC-08, RF-LEC-09.

**CU-06 · Arrepentirse.** *Precondición:* la versión vigente tiene anterior. *Flujo:* el lector revierte. *Postcondición:* la anterior vuelve a ser vigente y **ninguna se borra**. → RI-06, RF-PET-13, RF-PET-14.

**CU-07 · Auditar qué se envió al modelo.** *Precondición:* una fila de `ejecucion`. *Flujo:* se leen los identificadores de lo que entró en el paquete. *Postcondición:* se sabe **qué hechos de canon** se enviaron, no solo qué memoria se recuperó. → RF-AUD-01, RF-AUD-02, RF-AUD-03, RF-AUD-04, RF-AUD-05.

### Interfaces externas

| ID | Interfaz | Pr. | Verif. |
| --- | --- | --- | --- |
| RI-01 | `GET /obras/{id}/versiones` — historial de `VersionPublicada` y qué capítulos cambió cada una respecto de su anterior | M | Test |
| RI-02 | `GET /obras/{id}/versiones/{v}` — portada, dedicatoria, índice y capítulos de **esa** versión | M | Test |
| RI-03 | `GET /obras/{id}/versiones/{v}/ficha` — la `FichaDeLectura` de esa versión | M | Test |
| RI-04 | `GET /obras/{id}/versiones/{v}/pdf` — los bytes del PDF de esa versión | M | Test |
| RI-05 | `POST /obras/{id}/peticiones` — registra una `PeticionDeCambio` y devuelve un trabajo en segundo plano | M | Test |
| RI-06 | `POST /obras/{id}/versiones/{v}/revertir` | M | Test |
| RI-07 | `POST /obras/{id}/publicar` | M | Test |
| RI-08 | `GET /trabajos/{id}` — estado del trabajo, legible **por capítulo** *(el endpoint ya existe; se amplía su respuesta)* | M | Test |
| RI-09 | Los ocho aparecen en el OpenAPI con sus modelos, y el cliente de la interfaz **se genera de ahí**: no se escribe ningún tipo de respuesta a mano (`CLAUDE.md` §7) | M | Análisis (+Test) |

### Funcionales — publicación

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-PUB-01 | Publicar **fija** los `version_texto_id` de cada capítulo. No se recalcula por `vigente` al leer | M | Test |
| RF-PUB-02 | Publicar una versión **no altera** ninguna anterior: cada una devuelve siempre el mismo texto | M | Test |
| RF-PUB-03 | **No se publica ningún capítulo que no haya pasado la puerta.** Un intento con una escena en `ESCALADA` o `FALLIDA` falla con error de dominio y no crea versión | M | Test |
| RF-PUB-04 | Al publicar se guarda el **cuadro de defectos** de esa versión: todo defecto bien formado de cada capítulo, bloqueante o no | M | Test |
| RF-PUB-05 | Al publicar se deriva y se guarda la `FichaDeLectura` de esa versión | M | Test |
| RF-PUB-06 | Cada `VersionPublicada` apunta a la que sucede (`sucede_a`), o a ninguna si es la primera | M | Test |
| RF-PUB-07 | El identificador de una obra publicada **no es adivinable**: aleatorio, no correlativo. No es autenticación —fuera de alcance—: es que el enlace se pueda regalar sin publicar de paso las demás novelas | M | Test |
| RF-PUB-08 | Los capítulos que cambiaron respecto de la anterior se calculan por **diferencia de `version_texto_id`**, no por qué hechos se recuperaron, que sobre-reporta | M | Test |
| RF-PUB-09 | El PDF se genera con `a_pdf` sobre los textos fijados de la versión. **No se escribe un segundo generador**: ya existe y no arrastra dependencias | M | Análisis (+Test) |
| RF-PUB-10 | La `Dedicatoria` **no es una `VersionDeTexto`**: no entra en `ensamblar`, ni en el `.md`, ni como capítulo del `.pdf`, ni en `ngrama_vetado` | M | Test |

### Funcionales — ficha

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-FIC-01 | La ficha lista los `Personaje` y `Lugar` de la versión, con **todos** los capítulos donde aparece cada uno, no solo el primero | M | Test |
| RF-FIC-02 | La ficha es **derivable**: existe una operación que la reconstruye desde el ledger y la `VersionPublicada` | M | Test |
| RF-FIC-03 | La ficha es **reproducible**: reconstruirla da exactamente lo guardado. Si no se puede reconstruir no es un *snapshot*, es un **original**, y entonces es una segunda verdad sobre el canon — lo que `CLAUDE.md` §8 regla 3 prohíbe y lo que `canon/repository.py` dice explícitamente que el índice no debe ser | M | Test |
| RF-FIC-04 | La ficha guardada **nunca se edita**. Una corrección de canon crea versión nueva; no modifica la ficha de una versión ya entregada | M | Test |

### Funcionales — petición del lector

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-PET-01 | El lector puede seleccionar un fragmento del capítulo, o una entrada de la ficha, y abrir la petición desde ahí, con el hecho afectado ya identificado | M | Test |
| RF-PET-02 | La petición se registra con el `hecho_canon_id`, la `VersionPublicada` de origen y el texto pedido | M | Test |
| RF-PET-03 | El texto del lector es **contenido no confiable**: se guarda como dato y nunca se concatena a un prompt sin marcar (`RNF-SEG-06` de la 001, CA-12) | M | Análisis (+Test) |
| RF-PET-04 | La petición **no edita** el `HechoCanon`. La corrección es un hecho nuevo que sustituye y cita al anterior (`architecture.md` §4.7), con la invalidación de *snapshots* que eso arrastra | M | Test |
| RF-PET-05 | Los capítulos afectados se determinan por los `hc_id` persistidos en `ejecucion` (RF-AUD-*) | M | Test |
| RF-PET-06 | Se revalida G1a sobre los capítulos posteriores **a la escena de origen del hecho sustituido**, no a los regenerados. Son conjuntos distintos, y el segundo deja fuera capítulos que sí pueden haber cambiado | M | Test |
| RF-PET-07 | Cada defecto de la revalidación se clasifica en **preexistente** —estaba en el cuadro de RF-PUB-04— o **introducido** | M | Test |
| RF-PET-08 | **Solo un defecto introducido impide publicar.** Un preexistente se registra y se le muestra al autor: el lector no debe pagar una deuda anterior a su petición | M | Test |
| RF-PET-09 | Si no se publica, el trabajo termina en **`ESCALADA`**, el estado que ya existe (`architecture.md` §3.3). No se introduce ningún camino de vuelta nuevo | M | Test |
| RF-PET-10 | Si no se publica, la versión vigente no cambia y la regeneración descartada **no deja rastro** en canon, ledger ni índice —como CA-7 de la 001 exige para una escena rechazada—. La `PeticionDeCambio` **sí se conserva**, con su resultado | M | Test |
| RF-PET-11 | Enviar la petición **no bloquea la lectura**: devuelve un trabajo y el lector sigue leyendo. Una petición en curso no impide abrir otra, y la interfaz dice cuántas hay vivas | M | Test |
| RF-PET-12 | El progreso es visible **por capítulo** —«regenerando el capítulo 4 de 7»—, no como un indicador indistinto: en el peor caso son diez llamadas en serie y un indicador mudo se confunde con un cuelgue | M | Test |
| RF-PET-13 | El lector puede revertir a la versión anterior desde la lectura | M | Test |
| RF-PET-14 | Revertir **no borra** la revertida: sigue siendo navegable | M | Test |

### Funcionales — lectura

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-LEC-01 | La portada muestra el título de la `Obra` y la `Dedicatoria` de su `Destinatario`, **fuera del cuerpo del manuscrito** | M | Test |
| RF-LEC-02 | El índice lista los capítulos con su número y título, y cada entrada navega a su capítulo | M | Test |
| RF-LEC-03 | El capítulo se muestra íntegro, con la `VersionDeTexto` que la `VersionPublicada` fijó para él | M | Test |
| RF-LEC-04 | Se lee siempre una `VersionPublicada` concreta: la URL la identifica, y recargar devuelve el mismo texto | M | Test |
| RF-LEC-05 | El lector puede abrir una versión anterior y leerla completa | M | Test |
| RF-LEC-06 | Cada entrada de la ficha enlaza a cada capítulo donde aparece | M | Test |
| RF-LEC-07 | La descarga entrega el PDF **de la versión que se está leyendo** | M | Test |
| RF-LEC-08 | Los capítulos que difieren de la versión anterior van marcados en el índice y en el capítulo | M | Test |
| RF-LEC-09 | Si el trabajo publica, la lectura **ofrece** saltar a la versión nueva; no salta sin que el lector lo pida | M | Test |
| RF-LEC-10 | Ningún `fetch` vive dentro de un componente: las llamadas están en `api/` y se consumen por hook (`CLAUDE.md` §7) | M | Análisis |

### Funcionales — auditoría del paquete

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-AUD-01 | El almacén devuelve el `hc_id` de cada pieza de canon. Hoy `canon_relevante(escena_id)` devuelve `list[tuple[str, bool]]` y el identificador **no llega nunca** a `recoleccion.py`: no se puede etiquetar con algo que no se recibe | M | Test |
| RF-AUD-02 | La capa `CANON_RELEVANTE` etiqueta **por `hc_id`**, no por posición. La posición cambia con el recorte y el identificador no — es el argumento ya escrito en `recoleccion.py` para la capa de memoria | M | Test |
| RF-AUD-03 | `ejecucion` persiste esos identificadores, y **solo los de las piezas que sobrevivieron al recorte**: registrar una descartada diría que se envió algo que no se envió | M | Test |
| RF-AUD-04 | De cada identificador persistido se sabe **de qué capa vino** | M | Test |
| RF-AUD-05 | La pieza sintética de la primera escena, que no tiene `hc_id`, **no** acaba en el registro | M | Test |

### Funcionales — transversales de interfaz

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-UI-01 | TypeScript estricto; ningún `any` en producción (`CLAUDE.md` §7) | M | Análisis |
| RF-UI-02 | Estado de servidor con TanStack Query; estado de interfaz con `useState`/`useReducer`, sin store global que los mezcle | M | Análisis |
| RF-UI-03 | Se respetan las tres reglas de frontera de `CLAUDE.md` §5.2, impuestas por ESLint `import/no-restricted-paths` y no por revisión manual | M | Análisis (+Test) |
| RF-UI-04 | Accesibilidad mínima: foco visible al tabular, etiqueta en cada campo de formulario, contraste AA | M | Inspección |
| RF-UI-05 | Un fallo de red o un 5xx se muestra como tal y deja reintentar; no se queda en blanco ni finge contenido | M | Test |
| RF-UI-06 | Las cuatro pantallas —portada, índice, capítulo y ficha— **renderizan en un navegador real**, no solo en el renderizador de los tests | M | Demostración |
| RF-UI-07 | Ningún texto escrito por el lector se interpreta como HTML al renderizarse | M | Test |

### Datos

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RD-01 | Tablas nuevas: `version_publicada`, `capitulo_publicado`, `peticion_de_cambio`, `ficha_de_lectura`, `defecto_publicado`, `destinatario`, `dedicatoria`. **De las 27 de `0001_inicial`, ninguna sirve** | M | Test |
| RD-02 | `obra` gana referencia a `destinatario`. Hoy no tiene ni `destinatario_id` ni dedicatoria | M | Test |
| RD-03 | Migración de Alembic, con `foreign_keys=ON` respetado | M | Test |
| RD-04 | El ledger **no cambia**: sigue siendo *append-only* y `estado_en_t` sigue siendo vista derivada | M | Análisis |
| RD-05 | `version_publicada` guarda `version_texto_id` por capítulo, no `escena_id` a resolver después | M | Test |
| RD-06 | El frontend **no persiste nada** del dominio ni deriva la ficha: toda la verdad vive en el backend | M | Análisis |

### No funcionales

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RNF-REN-01 | La revalidación respeta el límite de una llamada en vuelo (`architecture.md` §2.2). **No se recorta ningún paquete para hacerla caber** | M | Test |
| RNF-REN-02 | Clasificar preexistente/introducido **no cuesta llamadas**: se hace contra el cuadro guardado al publicar | M | Análisis (+Test) |
| RNF-REN-03 | Abrir un capítulo no espera a los demás | M | Test |
| RNF-SEG-01 | Ninguna clave de proveedor llega al navegador: solo habla con el backend propio | M | Análisis |
| RNF-FIA-01 | Publicar es atómico: o queda la versión entera con su ficha y su cuadro, o no queda nada | M | Test |
| RNF-MAN-01 | El test vive junto al componente y las exportaciones son nombradas | M | Análisis |

---

## Criterios de aceptación

- [ ] **CA-1** — Cuando se publica y después se regenera un capítulo, entonces pedir la versión antigua devuelve **el mismo texto que devolvía antes**. *(Test)* → RF-PUB-01, RF-PUB-02, RD-05, RF-LEC-05.
- [ ] **CA-2** — Cuando se intenta publicar con una escena en `ESCALADA`, entonces **no se crea ninguna versión** y falla con error de dominio. Se comprueba contra el caso real: la escena 8 de la corrida del 2026-09-23. *(Test)* → RF-PUB-03, RI-07.
- [ ] **CA-3** — Cuando se reconstruye la ficha de una versión desde el ledger, entonces sale **exactamente** la guardada. *(Test)* → RF-PUB-05, RF-FIC-02, RF-FIC-03.
- [ ] **CA-4** — Cuando se publica una versión nueva, entonces la ficha de la anterior sigue siendo la suya y no se ha tocado. *(Test)* → RF-FIC-04.
- [ ] **CA-5** — Cuando se abre la URL de una versión, entonces se ve la portada con la dedicatoria de su destinatario y el índice lleva a los capítulos. *(Test)* → RI-02, RF-LEC-01, RF-LEC-02, RF-LEC-03.
- [ ] **CA-6** — Cuando se recarga la página de un capítulo, o se abre el mismo enlace en otra pestaña, entonces se ve exactamente el mismo texto. *(Test)* → RF-LEC-04.
- [ ] **CA-7** — Cuando se abre la ficha y se pincha un personaje, entonces se llega a un capítulo donde aparece, y la ficha es la de **esa** versión y no el canon de hoy. *(Test)* → RI-03, RF-FIC-01, RF-LEC-06.
- [ ] **CA-8** — Cuando se descarga el PDF desde una versión concreta, entonces el PDF es el de esa versión, producido por `a_pdf`; **no existe un segundo generador en el repositorio**. *(Test)* → RI-04, RF-PUB-09, RF-LEC-07.
- [ ] **CA-9** — Cuando un lector pide cambiar un hecho usado en dos capítulos, entonces se regeneran **esos dos** y se revalidan todos los posteriores al **origen** del hecho sustituido. *(Test)* → RI-05, RF-PET-01, RF-PET-02, RF-PET-05, RF-PET-06.
- [ ] **CA-10** — Cuando la revalidación encuentra un defecto que **ya estaba** en el cuadro de la versión anterior, entonces **la publicación sigue adelante** y el defecto se registra para el autor. *(Test)* → RF-PUB-04, RF-PET-07, RF-PET-08.
- [ ] **CA-11** — Cuando encuentra uno que **no estaba**, entonces no se publica, el trabajo queda en `ESCALADA`, la vigente no cambia y la `PeticionDeCambio` sigue existiendo con su resultado. *(Test)* → RF-PET-07, RF-PET-09, RF-PET-10.
- [ ] **CA-12** — Cuando una petición está en curso, entonces la lectura sigue navegable, la interfaz dice cuántas hay vivas y el progreso dice **por qué capítulo va**. *(Test)* → RF-PET-11, RF-PET-12, RI-08.
- [ ] **CA-13** — Cuando el trabajo publica, entonces la lectura **ofrece** saltar y no salta sola, y los capítulos cambiados van marcados: si difieren tres, se marcan exactamente esos tres. *(Test)* → RF-PUB-06, RF-PUB-08, RF-LEC-08, RF-LEC-09, RI-01.
- [ ] **CA-14** — Cuando el lector revierte, entonces la anterior vuelve a ser vigente y la revertida sigue siendo navegable. *(Test)* → RI-06, RF-PET-13, RF-PET-14.
- [ ] **CA-15** — Una corrección pedida por el lector **no edita** ningún `HechoCanon`: crea uno nuevo que cita al anterior e invalida los *snapshots* posteriores. *(Test)* → RF-PET-04.
- [ ] **CA-16** — Desde una fila de `ejecucion` se sabe **qué hechos de canon** entraron en el paquete, con su `hc_id` y su capa, y no aparece ninguno que el recorte descartara ni el sintético de la primera escena. *(Test)* → RF-AUD-01, RF-AUD-02, RF-AUD-03, RF-AUD-04, RF-AUD-05.
- [ ] **CA-17** — Cuando se piden dos identificadores de obra seguidos, entonces no son correlativos ni derivables uno del otro. *(Test)* → RF-PUB-07.
- [ ] **CA-18** — La dedicatoria **no aparece** en el manuscrito ensamblado, ni en el `.md`, ni como capítulo del `.pdf`, ni en `ngrama_vetado`. *(Test)* → RF-PUB-10.
- [ ] **CA-19** — Cuando el texto de una petición contiene `<script>` o una instrucción dirigida al modelo, entonces se muestra como texto plano y llega al backend como dato, sin alterar ningún prompt. *(Test)* → RF-PET-03, RF-UI-07.
- [ ] **CA-20** — `pnpm typecheck` y `pnpm lint` pasan en limpio, y `lint` **falla** si se añade a propósito un import de `shared/` hacia `features/`, uno entre dos features, o uno a un fichero interno de otra feature. *(Test)* → RF-UI-01, RF-UI-03.
- [ ] **CA-21** — La suite de la interfaz pasa **sin backend levantado**: las respuestas se sirven con dobles construidos desde el esquema OpenAPI. *(Test)* → RI-09.
- [ ] **CA-22** — El agente abre la lectura con el browser MCP, recorre portada, índice, capítulo y ficha, y **registra un fallo** cuando alguna no renderiza. *(Demostración)* → RF-UI-06.
- [ ] **CA-23** — En esas cuatro pantallas se inspeccionan foco visible, etiquetas de formulario y contraste AA, y cada incumplimiento se registra. **Renderizar no es ser accesible:** un contraste 2:1 pinta perfectamente, así que CA-22 en verde no dice nada de esto. *(Inspección)* → RF-UI-04.
- [ ] **CA-24** — Cuando falla la red al abrir un capítulo, entonces se ve el error y un reintento, no una página en blanco. *(Test)* → RF-UI-05.
- [ ] **CA-25** — Ningún componente contiene un `fetch` ni un cliente HTTP; no hay store global que mezcle estado de servidor con estado de interfaz; ningún módulo escribe estado de dominio en almacenamiento local ni deriva la ficha; el *bundle* no contiene ninguna clave. *(Análisis)* → RF-LEC-10, RF-UI-02, RD-06, RNF-SEG-01, RNF-MAN-01.
- [ ] **CA-26** — Con el turno ocupado, la revalidación **espera**; no se lanza en paralelo ni se recorta ningún paquete. Y clasificar preexistente/introducido **no llama al modelo**. *(Test)* → RNF-REN-01, RNF-REN-02.
- [ ] **CA-27** — Abrir un capítulo no espera a los demás: la vista pinta con una sola respuesta. *(Test)* → RNF-REN-03.
- [ ] **CA-28** — Si publicar falla a mitad, entonces no queda ni versión, ni ficha, ni cuadro: el estado es el de antes. *(Test)* → RNF-FIA-01.
- [ ] **CA-29** — Tras la migración existen las siete tablas nuevas y la referencia de `obra` a `destinatario`, `foreign_keys=ON` sigue activo, y el ledger sigue siendo *append-only*. *(Test)* → RD-01, RD-02, RD-03, RD-04.
- [ ] **CA-30** — `ruff`, `mypy`, `pytest`, `lint-imports` y las migraciones pasan en limpio. *(Test)* → RD-03.

**Sobre CA-2.** Es el único criterio de esta spec que se comprueba contra un fallo **que ya ocurrió y está en un entregable**: 2.038 palabras de una escena escalada que un lector recibiría hoy.

**Sobre CA-3.** Es el que impide que la ficha se convierta en una fuente de verdad paralela al manuscrito. Una ficha que no se puede reconstruir no es un *snapshot*: es un original.

**Sobre CA-20.** No basta con que `lint` pase: si se introduce el import prohibido y sigue verde, la regla no comprobaba nada. Es el equivalente de CA-4 de la 001, y por el mismo motivo.

---

## Reglas de dominio afectadas

| Regla `CLAUDE.md` §8 | Cómo la respeta esta spec |
| --- | --- |
| 3 — el estado en T se **deriva** del ledger, no se escribe a mano | La ficha es derivable y reproducible (RF-FIC-02, RF-FIC-03, CA-3) y el ledger no cambia (RD-04) |
| 4 — todo hecho de canon cita la escena que lo estableció | Se conserva: la corrección del lector es hecho nuevo que sustituye, no edición (RF-PET-04, CA-15). La ficha enlaza al capítulo de cada aparición, que es esa cita hecha navegable |
| 7 — cada ejecución guarda los IDs recuperados | Se **completa**: hoy solo cubre `MEMORIA_RECUPERADA` y pasa a cubrir también el canon (RF-AUD-*) |
| 6 — nada romántico con menores: **validación de esquema** | El frontend no valida esto y **no debe intentarlo**: una comprobación en el navegador daría falsa confianza sobre una regla que se cumple en el esquema |

**Regla nueva que esta spec introduce sobre sí misma:** una `PeticionDeCambio` **nunca edita** un `HechoCanon`. Si la interfaz ofreciera «editar el hecho», estaría ofreciendo algo que el sistema no hace.

---

## Impacto técnico

| Aspecto | Impacto |
| --- | --- |
| Esquema | **Siete tablas nuevas y una columna en `obra`.** Es `CLAUDE.md` §3 punto 7 entero. Aprobado por `maujimenez4` el 2026-09-23 |
| Presupuesto de contexto (§4.1) | La revalidación **consume llamadas**, acotadas por §2.2 a una en vuelo. **No consume paquete nuevo**: la clasificación se resuelve contra el cuadro guardado |
| Coste declarado | Peor caso de la revalidación: **diez llamadas en serie**. La interfaz debe tolerarlo sin darlo por perdido (RF-PET-12, CA-12) |
| Fronteras backend (§5.1) | Toca `manuscrito`, `canon` y `contexto`. **RF-AUD-01 cruza una frontera de firma**, no de import: cambia un `Protocol`, y al ser estructural `mypy` caza sus tres implementaciones a la vez |
| Efecto lateral conocido de RF-AUD-02 | Hoy la etiqueta de canon lleva `presente`/`mencionado` y eso se lee en `descartado_por_capa` para saber **qué criterio de §2.1 recortó**. Con `hc_id` esa lectura se pierde: o etiqueta compuesta, o se acepta y se dice. Lo que no vale es perderla en silencio |
| Fronteras frontend (§5.2) | Se crean `features/manuscrito` y `features/canon`, más `shared/api`. **Ninguna feature fuera de `architecture.md` §6.1.** La petición de cambio vive en `manuscrito` porque produce la `VersionPublicada`, que es su agregado: la propiedad sigue al dato, no al disparador |
| Dependencias nuevas | React 19, Vite, TypeScript, TanStack Query, Vitest, Testing Library, ESLint con `import/no-restricted-paths`, y un generador estándar de cliente OpenAPI. Aprobadas en bloque por `maujimenez4` el 2026-09-23 |
| Lo que se rompe al implementar | `src/backend/app/tests/test_demostraciones.py` compara `ids_recuperados` con una lista literal |
| La escala | RF-LEC-02 y CA-5 no fijan número de capítulos a propósito. La decisión de `maujimenez4` es **diez de 1.000–1.500 palabras**, y `CLAUDE.md` §1, `domain-knowledge.md` y `definitions.md` siguen diciendo 80.000–120.000. **Corregir esos tres documentos es condición de cierre de esta spec** |
| `docs/` al cerrar | `architecture.md` §5.4 gana los ocho endpoints, §5.5 las siete tablas y §6.1 pasa a describir algo construido; `verification.md` gana la validación visual por browser MCP como método en uso |

---

## Vocabulario

Todos en `docs/definitions.md` desde su v1.4: `Destinatario`, `Comprador`, `Dedicatoria`, `VersionPublicada`, `PeticionDeCambio`, `FichaDeLectura`. El resto son los de siempre.

**`VersionPublicada` se llama así a propósito.** El vocabulario ya tiene `VersionDeTexto` (el texto de una escena) y `VersionDeObra` (la biblia congelada), más una tabla `version_obra`. Una tercera «versión de» habría sido la deriva terminológica que §2 existe para evitar; «publicada» nombra lo que la distingue, que es el acto de entregarla.

**Un término que esta spec necesita y no existe:** el **cuadro de defectos** de una versión publicada (RF-PUB-04). No se introduce hasta decidir su nombre y su definición (§2). Está en P-03.

---

## Preguntas abiertas

Mientras quede una sin responder, esta spec **no se aprueba** (`CLAUDE.md` §3.2).

| ID | Pregunta | Quién responde |
| --- | --- | --- |
| P-01 | `ids_recuperados` es una lista plana. ¿Prefijo en el valor (`canon:…`, `memoria:…`), columna nueva, o diccionario por capa? El prefijo no toca esquema; la columna es migración y toca `RI-14` de la 001 | Autor |
| P-02 | `estado_en_t` devuelve también `list[tuple[str, bool]]` y sus eventos tienen `evt_id`: **mismo problema de auditabilidad**. ¿Entra o se declara fuera y por qué? Si no se dice, reaparece en dos semanas | Autor |
| P-03 | ¿Cómo se llama el **cuadro de defectos** de una versión, y entra en `definitions.md`? | Autor |
| P-04 | `ids_recuperados` **deja de ser un nombre exacto**: el canon no se «recupera», se filtra. ¿Se renombra —migración— o se documenta en el campo? | Autor |
| P-05 | RF-AUD-02, ¿etiqueta compuesta que conserve `presente`/`mencionado`, o solo `hc_id` aceptando la pérdida en `descartado_por_capa`? | Autor |

---

## Lo que esta spec no verifica

| Qué no se verifica | Por qué | Qué lo cubriría |
| --- | --- | --- |
| Que la petición del lector se haya **atendido de verdad** | Las puertas responden «está bien formado y es coherente», no «es lo que se pidió». Un capítulo regenerado puede pasar G1a entero sin haber cambiado el nombre del perro | La reversión (RF-PET-13) devuelve el veto al lector. Comprobarlo exige un juez con rúbrica |
| Que un defecto **preexistente** sea inocuo | Se le deja pasar por no ser culpa de la regeneración, no por ser falso. La deuda sigue ahí | La medición que pide D-3 de la 001, y la decisión sobre `CAN-01`/`CON-03` |
| Que una contradicción de canon **impida** publicar | `CAN-01` y `CON-03` no están hoy en `BLOQUEANTES_EN_G1A`: se detectan, se registran en `no_bloquean` y no bloquean | La misma decisión. Hasta entonces la protección de continuidad es **parcial**, y así queda dicho |
| Que **«bien formado» signifique «cierto»** | `comprobar_forma` verifica que la cita esté donde dice y que `CAN-01` traiga hecho. Mide **fidelidad de transcripción**, no **acierto del juicio** | Nada dentro de esta spec. Corregido en `verification.md` §6.3 |
| Que **la novela siga funcionando como novela** tras una regeneración | Se revalida G1a, que es **por escena**. Se puede quitar un objeto del capítulo 4, revalidar del 3 al 10, pasar los diez, y dejar sin plantar el beat de clímax del 9: diez escenas correctas y una novela rota | El **Auditor de manuscrito** (`CLAUDE.md` §9), que **no entra en este flujo** |
| Que la novela **se lea bien** | Ningún test juzga prosa | Lectura humana, y un juez con rúbrica |
| Que el paquete enviado quepa en su presupuesto | `memoria_recuperada` pide 20.000–24.000 contra un tope de 10.000 al cerrar un capítulo de diez escenas, y lo registrado en `ejecucion` es lo **posterior** al recorte, así que la pérdida no consta | Deuda de la 001, fuera de alcance |

---

## Cierre

Pendiente. Esta spec está en `borrador`.
