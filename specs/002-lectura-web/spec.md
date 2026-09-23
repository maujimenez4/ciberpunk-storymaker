---
id: 002-lectura-web
titulo: Lectura web de la novela publicada
estado: borrador          # borrador | en-revision | aprobada | implementada
aprobada_por:             # lo rellena una persona, nunca un agente
fecha: 2026-09-23
---

# 002-lectura-web — Lectura web de la novela publicada

Qué debe poder hacer quien recibe la novela, y cómo se sabrá que lo hace. **Aquí no se decide cómo se implementa:** eso es el plan, y no se escribe hasta que esta spec esté `aprobada`.

Es la primera spec de frontend del repositorio. Cubre **solo la lectura**: el taller del autor —inspector de contexto, panel de defectos, outline, auditoría— es una spec aparte, para que esta sea aprobable sin esperar a las dependencias de aquella.

**Número.** Esta spec nació como **003** porque el 002 estaba ocupado, y pasó a **002** el 2026-09-23 por decisión de `maujimenez4`, que movió `validadores-fallo-cerrado` al **005**. Se deja escrito porque los commits `82a1a49` y `ce2b810` nombran las rutas antiguas en el historial y no se pueden reescribir: quien los lea necesita saber que `003-lectura-web` y esta spec son la misma.

---

## Problema

La novela terminada existe hoy como filas en SQLite y, si alguien lanza `corrida.py`, como un fichero de texto en la máquina de quien la generó. Nadie más puede leerla.

Quien lo sufre es el **destinatario**: recibe un regalo que no puede abrir. Y lo sufre el **comprador**, que tampoco puede comprobar qué compró ni pedir que se corrija lo que no encaja —un nombre mal puesto, un perro que se llama de otra manera— sin hablar con quien operó el sistema.

`src/frontend/` existe y está **vacío**: no hay `package.json` ni ningún fichero. La arquitectura de frontend está decidida y documentada (`architecture.md` §6, `CLAUDE.md` §5.2 y §7) pero no se ha escrito ni una línea contra ella.

---

## Alcance

| Capacidad | Motivo |
| --- | --- |
| Portada con dedicatoria al destinatario | Es lo que convierte el manuscrito en un regalo |
| Índice de capítulos navegable | Sin él la novela no se recorre |
| Lectura de capítulo | Es el producto |
| Ficha de personajes y lugares, con enlace al capítulo donde aparece cada uno | Requisito de la entrega, y lo que hace útil el canon fuera del sistema |
| Enlace de descarga del PDF exportado | Decisión del autor: la web es la lectura, el PDF es el artefacto portable |
| Petición de cambio sobre un hecho, desde la propia lectura | Es la mitad interactiva del producto |
| Marcado de los capítulos que cambiaron respecto de la versión anterior | Sin él, una regeneración es invisible |
| Reversión a la versión anterior | Contrapeso de la publicación automática (D-03) |
| Validación visual con browser MCP sobre índice, ficha y portada | Comprueba lo único que ningún test de unidad ve: que la página renderiza |

**Ámbito:** frontend, features `manuscrito` y `canon` de `architecture.md` §6.1. El backend que esta spec necesita y no existe está en **Dependencias**, no en el alcance.

---

## Fuera de alcance

| Excluido | Motivo | Cuándo |
| --- | --- | --- |
| Taller del autor: `escena`, `revision`, `outline`, `auditoria` | Añade dos endpoints más y haría que la lectura esperase a la dependencia más lenta | Spec siguiente |
| Agente entrevistador y brief personalizado | Es la otra mitad del producto y no toca el frontend de lectura | Spec de configuración |
| Guardrail de palabras prohibidas | Se aplica en código sobre el capítulo, antes de que la lectura lo vea | Spec de guardrails |
| Observabilidad en Langfuse | Instrumenta el harness, no la lectura | Spec de observabilidad |
| Validadores formales (Lean, TLA+) | Verifican la historia y el harness, no la página | Spec de verificación formal |
| Autenticación y multiusuario | El modo de referencia es local (`architecture.md` §10) | — |
| Edición manual del texto por el lector | El lector pide cambios; no escribe prosa. Editar a mano abre la puerta a un texto que nadie validó | — |
| Servidor MCP de consulta | Requiere que esta spec exista antes | Después |

---

## Dependencias

**Esta spec no se puede implementar sola.** Lo que sigue es backend que hoy no existe. Se declara aquí con nombre y sitio para que quien lo implemente no tenga que redescubrirlo; **no se implementa en esta spec**.

> **Aviso.** Todo lo de abajo cuelga de `specs/001-backend-v1/`, que está en `estado: en-revision` y **no aprobada**, pese a tener su Cierre firmado. Quien apruebe esta spec debe saber que sus dependencias cuelgan de una spec que nadie ha firmado.

### DEP-01 · La capa de canon debe etiquetar por `hc_id`

Para saber qué capítulos hay que regenerar cuando cambia un hecho, hace falta la relación hecho → capítulos. **No se crea una tabla nueva:** duplicaría lo que `ejecucion` ya hace (`CLAUDE.md` §8, regla 7) y habría que mantenerla en sincronía. El dato casi existe, y el hueco es exacto:

- `ejecucion.ids_recuperados` persiste qué entró en el paquete, **pero solo de la capa `MEMORIA_RECUPERADA`**: se construye filtrando por `ETIQUETA_RECUPERADO` (`features/contexto/service.py:173-180`).
- La capa `CANON_RELEVANTE` etiqueta sus piezas `canon-presente-{i}` / `canon-mencionado-{i}`, **por posición y no por `hc_id`** (`features/contexto/recoleccion.py:96-107`). El identificador del hecho se pierde en la frontera: `almacenes.canon_relevante(escena_id)` devuelve `(texto, presente)` y nada más.

**El hueco es más hondo que el formato de la etiqueta.** `canon_relevante(escena_id)` devuelve `list[tuple[str, bool]]` —texto y si está presente— en las tres implementaciones (`contexto/recoleccion.py:46`, `contexto/repository.py:103` y el doble de sus tests). El `hc_id` **no llega nunca** a `recoleccion.py`, así que no se puede etiquetar con algo que no se recibe: el cambio es **lo que devuelve el almacén**, y la etiqueta viene detrás.

El cambio es, entonces, que **el almacén devuelva el `hc_id`, la capa de canon etiquete con él y esos identificadores se persistan en `ejecucion`**.

**Y esto no es solo un problema de esta spec.** Con `ejecucion` sin registrar qué hechos de canon entraron en el paquete, **RI-14 de la 001 queda a medias** y la auditoría de una escena es parcial: se puede reconstruir qué se recuperó de memoria, no qué canon se envió. Arreglar DEP-01 cierra ese agujero de paso. El argumento ya está ganado en el propio repositorio para la otra capa: `recoleccion.py:178` guarda el identificador y no la posición precisamente porque «con una posición no se puede reconstruir qué se envió (CA-10)». Es el mismo argumento sin aplicar a canon, y aplicarlo refuerza CA-10 de la 001.

**Letra pequeña, y va en la spec porque cambia lo que se puede prometer.** Aun con DEP-01 implementado, la relación que se obtiene es **«recuperado»**, no **«usado»**: lo que entró al paquete no es necesariamente lo que el Escritor puso en la prosa. Es una **sobreaproximación**, y tiene dos consumidores con necesidades opuestas:

| Consumidor | Efecto de la sobreaproximación | Veredicto |
| --- | --- | --- |
| Decidir qué capítulos regenerar | Regenera de más, nunca de menos | **Seguro.** Es la dirección correcta del error |
| Marcar en la lectura qué capítulos cambiaron | Marca capítulos que no cambiaron | **Sobre-reporta.** Se mitiga marcando por diferencia real de `VersionDeTexto` (RF-LEC-08) |

### DEP-02 · Endpoints

| Endpoint | Para qué | Estado hoy |
| --- | --- | --- |
| `GET /obras/{id}/versiones` | Historial de `VersionPublicada` y qué capítulos cambió cada una | No existe |
| `GET /obras/{id}/versiones/{v}` | La novela publicada: portada, dedicatoria, índice y capítulos | No existe |
| `GET /obras/{id}/versiones/{v}/ficha` | `FichaDeLectura` congelada, con los capítulos de cada personaje y lugar | No existe |
| `GET /obras/{id}/versiones/{v}/pdf` | Descarga del PDF exportado | Endpoint no; **la generación sí** |
| `POST /obras/{id}/peticiones` | Registrar una `PeticionDeCambio`; devuelve un trabajo en segundo plano | No existe |
| `POST /obras/{id}/versiones/{v}/revertir` | Volver a la versión anterior (D-03) | No existe |
| `GET /trabajos/{id}` | Sondear el trabajo de regeneración | **Ya existe** |
| `GET /obras/{id}` | Datos de la obra | **Ya existe** |

**Lo que ya está hecho por debajo, y conviene no volver a escribir.** `features/manuscrito` expone por su `__init__.py` `a_markdown(manuscrito, titulo)`, `a_pdf(manuscrito, titulo)` —PDF 1.4 con la biblioteca estándar, sin dependencias nuevas— y `exportar(...)`, más `RepositorioDeManuscrito.ensamblar(obra_id)`. El endpoint de descarga **no genera nada**: llama a `a_pdf` y devuelve los bytes. Lo que sí falta entero es `router.py` y `schemas.py` de esa feature, que hoy son esqueletos de cuatro líneas.

**Y lo que falta de verdad es el histórico.** `Manuscrito` conoce hoy la versión *vigente* de cada escena, no una sucesión de publicaciones. `VersionPublicada` es **tabla nueva**, y por tanto migración de Alembic y pregunta de `CLAUDE.md` §3, punto 7 (P-06).

### DEP-03 · Revalidación de los capítulos posteriores

Regenerar el capítulo 4 no deja intactos el 5 al 10. El Extractor extrae del 4 regenerado hechos que citan al 4 (`CLAUDE.md` §9.1), y `estado_en_t` es vista derivada del ledger (`architecture.md` §4.2): las entradas de los capítulos posteriores **han cambiado por construcción**, no «podrían» haber cambiado.

La corrección del hecho viejo **no inventa mecanismo**: es el de `architecture.md` §4.7 —hecho nuevo que sustituye y cita al anterior, más invalidación de los *snapshots* posteriores a la escena de origen del sustituido—.

La regla que esta spec asume, y que el backend debe cumplir antes de publicar:

> Se **regeneran** los capítulos afectados. Se **revalida** G1a sobre todos los capítulos posteriores **a la escena de origen del hecho sustituido**. Si la revalidación abre defectos bloqueantes, la versión **no se publica** y el trabajo termina en `ESCALADA`.

**«Posteriores» se ancla en el origen, no en lo regenerado, y la diferencia importa.** Si el lector corrige un hecho establecido en el capítulo 2 y usado en el 4 y el 7, se regeneran el 4 y el 7, pero se revalidan **del 3 al 10**, no del 5 al 10. Es el mismo anclaje que `architecture.md` §4.7 usa para invalidar *snapshots* —la escena de origen del hecho sustituido—, y es el conjunto mayor de los dos: quien implemente esto elegirá el barato si la spec no lo dice, y el barato es el que deja fuera capítulos que sí pueden haber cambiado.

**`ESCALADA` es el estado que ya existe** (`architecture.md` §3.3: terminal hasta que el autor actúe, tras agotar los dos reintentos dirigidos). Esta spec **no introduce** ningún «vuelve al editor» que sea otra cosa: un segundo camino de vuelta sería un mecanismo nuevo para un problema ya resuelto.

**Coste, que no es gratis y por eso va aquí y no en el plan:** revalidar pasa por el Continuista, que es una llamada al modelo por capítulo, y `architecture.md` §2.2 fija una llamada en vuelo por proceso. Con diez capítulos, el peor caso es **diez llamadas en serie**. La lectura debe tolerar esa latencia (RNF-REN-02), no disimularla.

### DEP-04 · `CAN-01` y `CON-03` tienen que volver a bloquear

**La garantía de DEP-03 no se sostiene con el código de hoy, y este es el único punto de esta spec donde eso pasa.** DEP-03 protege la continuidad diciendo «si la revalidación abre defectos **bloqueantes**, no se publica». Pero hoy:

```
BLOQUEANTES_EN_G1A = {CON_01, CON_02, EST_01, SEG_01, VOZ_03}
```

(`features/calidad/defectos.py:61-69`). **Faltan dos**, y los dos importan aquí:

| Código | Qué detecta | Por qué esta spec lo necesita |
| --- | --- | --- |
| `CAN-01` | Contradicción de canon | Protege de que el capítulo 7 afirme de un personaje lo contrario que el 4 regenerado |
| `CON-03` | Personaje sabe lo que no debería (`definitions.md` §8) | **Pesa más aquí.** Regenerar el capítulo 4 cambia *qué se entera cada personaje y cuándo*. El 7 puede pasar a tener a un personaje usando algo que en la versión nueva ya no presenció: es la cadena de conocimiento, que es lo que una regeneración rompe con más facilidad |

Los dos se registran en `no_bloquean`, y ninguno bloquea. No es un olvido: el comentario de `defectos.py:41` lo declara decidido.

El escenario que DEP-03 dice cubrir queda así: se regenera el capítulo 4, el 7 pasa a contradecirlo, la revalidación **emite `CAN-01`**… y la versión **se publica igual**. El fallo queda detectado y no impedido. Lo que sí bloquea, `CON-01`, contrasta dos afirmaciones del propio Continuista entre sí: pilla a un personaje en dos sitios a la vez, no pilla que el capítulo 7 diga que Mara tiene los ojos negros después de que el 4 regenerado los haya puesto verdes.

**Dependencia, y ya no es una decisión pendiente: es una medición pendiente.** La P-3 de `specs/005-validadores-fallo-cerrado/` preguntaba «qué evidencia devuelve a `CAN-01` y `CON-03` a `BLOQUEANTES_EN_G1A`», y `maujimenez4` la contestó el 2026-09-23 en su **D-3**: *partir el campo, y **medir antes de volver a bloquear**; corrida real autorizada*.

Lo que falta **no es que alguien decida**. La historia, hasta hoy:

1. **Decidido** (D-3, 2026-09-23): partir el campo y medir antes de volver a bloquear.
2. **Medición intentada** y fracasada, a las 16:40: la corrida real murió **en la escena 1**, con `ValueError: el fragmento citado no aparece en la version`. Cero de diez escenas.
3. **Causa**: H-7. Los validadores de continuidad pasaban a `citar()` la cita que escribe el Continuista, y `citar` lanza si no la encuentra literal. La defensa contra la cita inventada —`comprobar_forma`, axiomas 11 y 12— vive **aguas abajo**, en `puerta.py`: para marcar un defecto como mal formado primero hay que construirlo, y ahí reventaba antes de existir. Que el modelo parafrasee es lo normal, así que cualquier corrida moría.
4. **H-7 arreglado** a las 16:46: `citar_del_modelo` construye el defecto anclado al principio y deja que `comprobar_forma` lo juzgue, con el razonamiento escrito de que una cita que no aparece **es el dato**, no un error de programación.

Lo que falta, por tanto, es **repetir la corrida**. DEP-03 cumple lo que promete el día que esa medición exista y los dos códigos vuelvan a bloquear.

**Ojo con la palabra «vuelvan».** Devolver `CAN-01` y `CON-03` a `BLOQUEANTES_EN_G1A` sería una **decisión nueva de `maujimenez4`**, no la restauración de un estado anterior: fue él quien los sacó, el 2026-09-23, y está declarado en `defectos.py:41`. Esta spec no pide deshacer nada; pide que se decida, porque su garantía depende de ello.

**Y esa evidencia todavía no la ha medido nadie.** No se puede obtener con `corrida.py --seco`: el doble pasa `AFIRMACIONES_FALSAS = "[]"`, los validadores devuelven cero por construcción, y ese cero parece una buena noticia sin serlo. Hace falta una corrida real con el Continuista dentro del bucle.

Hasta entonces, la protección de continuidad de esta spec es **parcial y está declarada como tal** en «Lo que esta spec no verifica».

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

**Una letra por requisito:** la del método que lo **establece**. Un segundo método que lo refuerza va entre paréntesis y no sustituye a la letra.

### Casos de uso

**CU-01 · Abrir el regalo.** *Precondición:* existe una `VersionPublicada`. *Flujo:* el destinatario abre la URL → ve la portada con su dedicatoria → entra por el índice al capítulo 1. *Postcondición:* ha leído sin haber tenido que elegir versión ni entender el sistema. → RI-01, RI-02, RF-LEC-01, RF-LEC-02, RF-LEC-03, RF-LEC-04.

**CU-02 · Consultar quién es quién.** *Precondición:* la versión tiene `FichaDeLectura`. *Flujo:* el lector abre la ficha → ve personajes y lugares → pincha uno y llega al capítulo donde aparece. *Postcondición:* la ficha mostrada es la **congelada con esa versión**, no el canon de hoy. → RI-03, RF-FIC-01, RF-FIC-02, RF-FIC-03, RF-FIC-04.

**CU-03 · Llevarse la novela.** *Precondición:* la versión tiene PDF. *Flujo:* el lector pulsa descargar. *Postcondición:* obtiene el PDF **de la versión que está leyendo**, no de la última. → RI-04, RF-LEC-09.

**CU-04 · Pedir un cambio** *(caso central)*. *Precondición:* el lector está leyendo una `VersionPublicada`. *Flujo principal:* selecciona un fragmento o un hecho → describe el cambio → se registra la `PeticionDeCambio` y arranca un trabajo → el lector ve su progreso → al terminar, la nueva versión se publica sola y la lectura ofrece saltar a ella con los capítulos cambiados marcados.

*Flujos alternativos:*
- La regeneración abre defectos bloqueantes, o la revalidación de DEP-03 los abre en capítulos posteriores → **no se publica**; el lector ve que su petición no se atendió y por qué, y sigue leyendo la versión anterior intacta.
- El trabajo falla o se agota el límite de reintentos → igual que el anterior: la petición queda registrada y la versión vigente no cambia. **El límite lo fija el backend** (`architecture.md` §8.3: reintento dirigido, máximo 2, después humano); esta spec no lo define, solo muestra su resultado (RF-PET-06).

*Postcondición de éxito:* existe una `VersionPublicada` nueva que `sucede_a` la anterior. *Postcondición de fracaso:* **la versión vigente es exactamente la de antes.** → RI-05, RI-06, RF-PET-01, RF-PET-02, RF-PET-03, RF-PET-04, RF-PET-05, RF-PET-06, RF-PET-07, RF-PET-08.

**CU-05 · Ver qué cambió.** *Precondición:* existen dos `VersionPublicada`. *Flujo:* el lector ve marcados los capítulos que difieren de la versión anterior. *Postcondición:* la marca corresponde a diferencia **real** de texto, no a la relación sobreaproximada de DEP-01. → RF-LEC-07, RF-LEC-08.

**CU-06 · Arrepentirse.** *Precondición:* la versión vigente tiene una anterior. *Flujo:* el lector revierte. *Postcondición:* la anterior vuelve a ser la vigente, **y ninguna se borra**. → RI-07, RF-PET-09, RF-PET-10.

### Interfaces externas

| ID | Interfaz | Pr. | Verif. |
| --- | --- | --- | --- |
| RI-01 | `GET /obras/{id}/versiones` — historial de versiones publicadas | M | T |
| RI-02 | `GET /obras/{id}/versiones/{v}` — portada, dedicatoria, índice y capítulos | M | T |
| RI-03 | `GET /obras/{id}/versiones/{v}/ficha` — `FichaDeLectura` congelada | M | T |
| RI-04 | `GET /obras/{id}/versiones/{v}/pdf` — descarga | M | T |
| RI-05 | `POST /obras/{id}/peticiones` — registra una `PeticionDeCambio`, devuelve trabajo | M | T |
| RI-06 | `GET /trabajos/{id}` — estado del trabajo de regeneración *(ya existe)* | M | T |
| RI-07 | `POST /obras/{id}/versiones/{v}/revertir` | M | T |
| RI-08 | El cliente de API se **genera** del OpenAPI del backend; no se escribe ningún tipo de respuesta a mano (`CLAUDE.md` §7) | M | A (+T) |

### Funcionales

#### Lectura (`features/manuscrito`)

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-LEC-01 | La portada muestra el título de la `Obra` y la `Dedicatoria` de su `Destinatario` | M | T |
| RF-LEC-02 | La dedicatoria se muestra **fuera del cuerpo del manuscrito**: no es el capítulo 1 ni se cuenta como tal | M | T |
| RF-LEC-03 | El índice lista los diez capítulos con su número y título, y cada entrada navega a su capítulo | M | T |
| RF-LEC-04 | El capítulo se muestra íntegro, con la `VersionDeTexto` que la `VersionPublicada` agrupa para él | M | T |
| RF-LEC-05 | Se lee siempre una `VersionPublicada` concreta; la URL la identifica, y recargar la página devuelve el mismo texto | M | T |
| RF-LEC-06 | El lector puede abrir una versión anterior y leerla completa | M | T |
| RF-LEC-07 | Los capítulos que difieren de la versión anterior van marcados en el índice y en el propio capítulo | M | T |
| RF-LEC-08 | La marca de RF-LEC-07 se calcula por **diferencia de `version_texto_id`** entre las dos versiones publicadas, no por la relación de DEP-01, que sobre-reporta | M | T |
| RF-LEC-09 | La descarga entrega el PDF **de la versión que se está leyendo** | M | T |
| RF-LEC-10 | Ningún `fetch` vive dentro de un componente: las llamadas están en `api/` y se consumen por hook (`CLAUDE.md` §7) | M | A |

#### Ficha (`features/canon`)

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-FIC-01 | La ficha lista los `Personaje` y `Lugar` de la versión, separados | M | T |
| RF-FIC-02 | Cada entrada enlaza a **cada** capítulo donde aparece, no solo al primero | M | T |
| RF-FIC-03 | La ficha que se muestra es la **congelada con esa `VersionPublicada`**; abrir una versión anterior muestra la ficha de aquella | M | T |
| RF-FIC-04 | La ficha no consulta el canon vigente en tiempo de lectura | M | A (+T) |

#### Petición de cambio (`features/manuscrito`)

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-PET-01 | El lector puede seleccionar un fragmento del capítulo, o una entrada de la ficha, y abrir la petición desde ahí | M | T |
| RF-PET-02 | La petición se registra con el `hecho_canon_id` afectado, la `VersionPublicada` de origen y el texto pedido | M | T |
| RF-PET-03 | Enviar la petición **no bloquea la lectura**: devuelve un trabajo y el lector sigue leyendo | M | T |
| RF-PET-04 | El progreso del trabajo es visible **por capítulo** —«regenerando el capítulo 4 de 7»—, no como un indicador indistinto, y se sondea con RI-06 | M | T |
| RF-PET-05 | Si el trabajo termina publicando, la lectura ofrece saltar a la versión nueva; no salta sin que el lector lo pida | M | T |
| RF-PET-06 | Si el trabajo termina **sin** publicar, se muestra que la petición no se atendió y el motivo, y la versión vigente no cambia | M | T |
| RF-PET-07 | El texto que el lector escribe en la petición se trata como **contenido no confiable**: se envía como dato, nunca concatenado a un prompt desde el frontend | M | A (+T) |
| RF-PET-08 | Una petición en curso no impide abrir otra, pero la interfaz dice cuántas hay vivas | M | T |
| RF-PET-09 | El lector puede revertir a la versión anterior desde la lectura | M | T |
| RF-PET-10 | Revertir **no borra** la versión revertida: sigue siendo navegable | M | T |

#### Transversales

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-UI-01 | TypeScript estricto; ningún `any` en código de producción (`CLAUDE.md` §7) | M | A |
| RF-UI-02 | Estado de servidor con TanStack Query; estado de interfaz con `useState`/`useReducer`, sin store global que los mezcle | M | A |
| RF-UI-03 | Se respetan las tres reglas de frontera de `CLAUDE.md` §5.2, impuestas por ESLint `import/no-restricted-paths` y no por revisión manual | M | A (+T) |
| RF-UI-04 | Accesibilidad mínima: foco visible, etiquetas en formularios, contraste AA | M | I |
| RF-UI-05 | Un fallo de red o un 5xx se muestra como tal y deja reintentar; no se queda en blanco ni finge contenido | M | T |
| RF-UI-06 | Las cuatro pantallas —portada, índice, capítulo y ficha— **renderizan en un navegador real**, no solo en el renderizador de los tests | M | D |

### Datos

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RD-01 | El frontend **no persiste nada** del dominio: toda la verdad vive en el backend | M | A |
| RD-02 | La `VersionPublicada` que se lee viaja en la URL, de modo que un enlace compartido abre exactamente el mismo texto | M | T |
| RD-03 | El frontend no deriva la `FichaDeLectura` ni recalcula el canon: la recibe hecha (RI-03) | M | A |
| RD-04 | La URL de una novela lleva un **identificador no adivinable** (aleatorio, no correlativo): `obra/1` deja leer la novela ajena probando números. **No es autenticación**, que sigue fuera de alcance; es que el enlace se pueda compartir sin publicar de paso todas las demás | M | T |

### No funcionales

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RNF-REN-01 | Abrir un capítulo no espera a que carguen los otros nueve | M | T |
| RNF-REN-02 | La interfaz tolera que una petición tarde el peor caso de DEP-03 —diez llamadas en serie— sin dar el trabajo por perdido ni por terminado | M | T |
| RNF-SEG-01 | Ningún texto escrito por el lector se interpreta como HTML al renderizarse | M | T |
| RNF-SEG-02 | Ninguna clave de proveedor llega al frontend: el navegador solo habla con el backend propio | M | A |
| RNF-MAN-01 | El test vive junto al componente y las exportaciones son nombradas (`CLAUDE.md` §7) | M | A |

---

## Criterios de aceptación

- [ ] **CA-1** — Cuando se abre la URL de una `VersionPublicada`, entonces se ve la portada con la dedicatoria de su destinatario, y el índice lleva a los diez capítulos. *(Test)* → RF-LEC-01, RF-LEC-02, RF-LEC-03, RF-LEC-04.
- [ ] **CA-2** — Cuando se abre la ficha de una versión y se pincha un personaje, entonces se llega a un capítulo donde ese personaje aparece. *(Test)* → RF-FIC-01, RF-FIC-02.
- [ ] **CA-3** — Cuando se abre una versión anterior, entonces su ficha es la de aquella versión y no la del canon de hoy. *(Test)* → RF-FIC-03, RF-FIC-04.
- [ ] **CA-4** — Cuando se pide un cambio y el trabajo termina publicando, entonces existe una `VersionPublicada` nueva que `sucede_a` la anterior, y la anterior sigue siendo legible entera. *(Test)* → RF-PET-02, RF-PET-03, RF-PET-04, RF-PET-05, RF-LEC-06.
- [ ] **CA-5** — Cuando la regeneración o la revalidación de DEP-03 abren un defecto bloqueante, entonces las tres cosas: **(a)** no existe ninguna `VersionPublicada` nueva, ni siquiera creada sin marcar vigente; **(b)** el puntero de versión vigente no se ha movido; y **(c)** la regeneración rechazada **no ha dejado rastro** en canon, ledger ni índice. **La `PeticionDeCambio` sí se conserva, con su resultado:** lo que no deja rastro es la prosa descartada y lo que se extrajo de ella, no la petición del lector, que CU-04 pide guardar. *(Test)* → RF-PET-06.
- [ ] **CA-6** — Cuando dos versiones difieren en tres capítulos, entonces se marcan exactamente esos tres, ni uno más. *(Test)* → RF-LEC-07, RF-LEC-08.
- [ ] **CA-7** — Cuando el lector revierte, entonces la versión anterior vuelve a ser la vigente y la revertida sigue siendo navegable. *(Test)* → RF-PET-09, RF-PET-10.
- [ ] **CA-8** — Cuando se descarga el PDF desde una versión concreta, entonces el PDF es el de esa versión. *(Test)* → RF-LEC-09.
- [ ] **CA-9** — `pnpm typecheck` y `pnpm lint` pasan en limpio, y `lint` **falla** si se añade a propósito un import de `shared/` hacia `features/`, uno entre dos features, o uno a un fichero interno de otra feature. *(Test)* → RF-UI-01, RF-UI-03.
- [ ] **CA-10** — El agente abre la lectura con el browser MCP, recorre portada, índice, un capítulo y la ficha, y **registra un fallo** cuando cualquiera de los cuatro no renderiza. *(Demostración)* → RF-UI-06.
- [ ] **CA-22** — En esas mismas cuatro pantallas se inspecciona **foco visible al tabular, etiqueta en cada campo de formulario y contraste AA**, y cada incumplimiento se registra como fallo. **Renderizar no es ser accesible:** un contraste 2:1 pinta perfectamente, así que CA-10 en verde no dice nada de esto. *(Inspección)* → RF-UI-04.
- [ ] **CA-11** — Cuando el texto de una petición contiene `<script>` o una instrucción dirigida al modelo, entonces se muestra como texto plano y llega al backend como dato, sin alterar ningún prompt. *(Test)* → RF-PET-07, RNF-SEG-01.
- [ ] **CA-12** — La suite del frontend pasa **sin backend levantado**: las respuestas se sirven con dobles construidos desde el esquema OpenAPI. *(Test)* → RI-08.
- [ ] **CA-13** — Cuando falla la red al abrir un capítulo, entonces se ve el error y un reintento, no una página en blanco. *(Test)* → RF-UI-05.
- [ ] **CA-14** — Cuando hay una petición en curso, entonces la lectura sigue siendo navegable y la interfaz indica cuántas peticiones hay vivas. *(Test)* → RF-PET-03, RF-PET-08.
- [ ] **CA-15** — Abrir un capítulo no espera a los demás: se comprueba que la vista pinta con una sola respuesta de capítulo. *(Test)* → RNF-REN-01.

- [ ] **CA-16** — Cuando se recarga la página de un capítulo, o se abre el mismo enlace en otra pestaña, entonces se ve exactamente el mismo texto. *(Test)* → RF-LEC-05, RD-02.
- [ ] **CA-17** — Ningún componente contiene un `fetch` ni un cliente HTTP; no hay store global que mezcle estado de servidor con estado de interfaz; cada test vive junto a su componente; **ningún módulo escribe estado de dominio en almacenamiento local**; y **ninguno deriva ni recalcula la `FichaDeLectura`**, que se recibe hecha. *(Análisis)* → RF-LEC-10, RF-UI-02, RNF-MAN-01, RD-01, RD-03.
- [ ] **CA-18** — Cuando el lector selecciona un fragmento del capítulo o una entrada de la ficha, entonces la petición se abre con el hecho afectado ya identificado. *(Test)* → RF-PET-01.
- [ ] **CA-19** — Cuando un trabajo tarda el peor caso de DEP-03, entonces la interfaz lo sigue dando por vivo —no lo declara perdido ni terminado— y muestra **por qué capítulo va**, no un indicador indistinto. Se comprueba con un doble que retrasa la respuesta y devuelve avance parcial. *(Test)* → RNF-REN-02, RF-PET-04.
- [ ] **CA-20** — El *bundle* construido no contiene ninguna clave de proveedor, y la única URL de red que usa es la del backend propio. *(Análisis)* → RNF-SEG-02.
- [ ] **CA-21** — Cuando se piden identificadores de dos obras seguidas, entonces no son correlativos ni derivables uno del otro. *(Test)* → RD-04.

**Sobre CA-5.** Su primera redacción decía «la vigente es byte a byte la de antes», y eso no era un criterio: `CLAUDE.md` §14 prohíbe editar en sitio, así que los bytes de una versión anterior **no pueden** cambiar y la comprobación pasaba siempre, hubiera funcionado el mecanismo o no. Un criterio que no puede fallar no verifica nada. Los tres riesgos reales son los de arriba, y el tercero es el que muerde: hechos extraídos de una prosa que se descartó. La letra (c) es **CA-7 de la 001** —«una escena rechazada no ha dejado rastro en canon, ledger ni índice»— aplicada a una regeneración rechazada.

**Sobre CA-9.** No basta con que `lint` pase: si se introduce el import prohibido y sigue en verde, la regla no estaba comprobando nada. Es el equivalente frontend de CA-4 de la 001, y por el mismo motivo.

---

## Reglas de dominio afectadas

Ninguna regla de `CLAUDE.md` §8 se implementa en el frontend: todas viven en el backend y esta spec no las mueve. Tres, sin embargo, la condicionan y se respetan así:

| Regla §8 | Cómo la respeta esta spec |
| --- | --- |
| 3 — el estado en T se **deriva** del ledger, no se escribe a mano | La `FichaDeLectura` se recibe hecha (RD-03) y el frontend no la recalcula (RF-FIC-04) |
| 4 — todo hecho de canon cita la escena que lo estableció | La ficha enlaza al capítulo de cada aparición (RF-FIC-02); es esa cita hecha navegable |
| 6 — nada romántico con menores: **validación de esquema**, no de prompt | El frontend no valida nada de esto y **no debe intentarlo**: una comprobación en el navegador daría falsa confianza sobre una regla que se cumple en el esquema |

Y una regla nueva que esta spec introduce sobre sí misma, derivada de `architecture.md` §4.7: **una `PeticionDeCambio` nunca edita un `HechoCanon`.** La corrección es un hecho nuevo que sustituye al anterior. Si el frontend ofreciera «editar el hecho», estaría ofreciendo algo que el sistema no hace.

---

## Impacto técnico

| Aspecto | Impacto |
| --- | --- |
| Presupuesto de contexto (§4.1) | **Ninguno directo.** El frontend no ensambla paquetes ni llama al modelo. El impacto es de DEP-03: la revalidación consume llamadas, acotadas por §2.2 a una en vuelo |
| Esquema y migración de Alembic | **Ninguna en esta spec**, pero sí una que esta spec provoca: `VersionPublicada`, `PeticionDeCambio` y `FichaDeLectura` son **tablas nuevas**. `version_obra` no sirve, porque guarda el estado congelado de la biblia y no una publicación. La migración pertenece a la spec de backend que implemente DEP-02, y su aprobación es P-06 |
| Fronteras (`CLAUDE.md` §5.2) | Se crean `features/manuscrito` y `features/canon` en el frontend, más `shared/api` con el cliente generado. **Ninguna feature nueva fuera de `architecture.md` §6.1** |
| La petición de cambio, ¿dónde vive? | Dentro de `features/manuscrito`. **No** porque no pudiera ser feature propia —`app/` puede componer dos features sin que se importen entre sí—, sino porque la petición produce una `VersionPublicada`, que es el agregado de `manuscrito`. La propiedad sigue al dato, no al disparador |
| Dependencias nuevas | React 19, Vite, TypeScript, TanStack Query, Vitest, Testing Library, ESLint con `import/no-restricted-paths`, y el generador de cliente OpenAPI. **Todas requieren aprobación** (`CLAUDE.md` §3, punto 7): la spec las declara, no las instala |
| Agentes y prompts (`CLAUDE.md` §9 y §10) | **Ninguno.** Esta spec no crea, modifica ni versiona ningún prompt, y no toca ninguno de los nueve agentes. El único que aparece es el Continuista, y lo hace dentro de DEP-03, que es backend |
| **La escala de diez capítulos** | RF-LEC-03 y CA-1 fijan **diez capítulos** de 1.000–1.500 palabras, por decisión de `maujimenez4` del 2026-09-23. **Tres documentos siguen diciendo lo contrario:** `CLAUDE.md` §1 y `domain-knowledge.md:78` hablan de 80.000–120.000 palabras, y `definitions.md:75` da al capítulo 2.500–4.000. Un requisito `M` no debe apoyarse en una cifra que la documentación contradice: **corregir los tres es condición de cierre de esta spec**, y hasta entonces manda la decisión, no los documentos |
| `docs/` que habrá que tocar al cerrar | `architecture.md` §6.1 pasa a describir algo construido; `verification.md` gana la validación visual por browser MCP como método en uso |

---

## Vocabulario

Los seis términos que esta spec necesita **ya están en `docs/definitions.md`**, incorporados en su v1.4 antes de escribirla, como exige `CLAUDE.md` §2:

`Destinatario` · `Comprador` · `Dedicatoria` · `VersionPublicada` · `PeticionDeCambio` · `FichaDeLectura`

**`VersionPublicada` se llama así a propósito.** El vocabulario ya tiene `VersionDeTexto` (el texto de una escena) y `VersionDeObra` (el estado congelado de la biblia). Una tercera «versión de» habría sido deriva terminológica del tipo que §2 existe para evitar; «publicada» nombra lo que la distingue, que es el acto de entregarla al lector.

El resto de términos usados —`Obra`, `Capitulo`, `Escena`, `HechoCanon`, `VersionDeTexto`, `Personaje`, `Lugar`, `PuertaDeCalidad`, `Defecto`— son los de siempre.

---

## Decisiones

**No queda ninguna pregunta abierta.** Las seis se cerraron el 2026-09-23 y cada una conserva quién la respondió, qué se decidió, por qué y dónde aterriza — que es lo que permite cambiarla después sabiendo qué se rompe (`CLAUDE.md` §3.2).

| ID | Pregunta | Quién responde |
| --- | --- | --- |
| P-01 | ~~¿Cómo llega el destinatario a la URL?~~ **Contestada por `maujimenez4` el 2026-09-23: identificador no adivinable.** No es autenticación —sigue fuera de alcance—: evita leer la novela ajena probando números, y el enlace se sigue pudiendo regalar. Aterriza en RD-04 y CA-21 | — |
| P-02 | ~~¿Dónde se especifica la revalidación de DEP-03?~~ **Contestada por `maujimenez4` el 2026-09-23: en la spec de backend.** Aquí se declara como dependencia y no como requisito: el frontend no especifica comportamiento de orquestación que no puede implementar ni probar | — |
| P-03 | ~~¿Qué ve el lector mientras su petición se procesa?~~ **Contestada por `maujimenez4` el 2026-09-23: progreso por capítulo.** Un indicador mudo durante diez llamadas en serie se confunde con un cuelgue. Aterriza en RF-PET-04 y CA-19 | — |
| P-04 | ~~¿Qué número toma la spec del taller?~~ **Contestada por verificación:** la spec de validadores es de Gustavo, reclama `RF-CAL-13` a `RF-CAL-18` y sigue en `borrador`; tras la renumeración es la **005**. El taller toma el **004** | — |
| P-05 | ~~¿Cómo se aprueban las dependencias de frontend?~~ **Contestada por `maujimenez4` el 2026-09-23: aprobadas en bloque, y el cliente se genera con una herramienta estándar desde el OpenAPI**, no escribiéndolo un modelo. Es lo que exige `CLAUDE.md` §7, y además hace que un cambio de contrato del backend lo cace el `typecheck` en vez de nadie | — |
| P-06 | ~~¿Se aprueba el cambio de esquema?~~ **Contestada por `maujimenez4` el 2026-09-23: aprobado, y la migración vive en la spec de backend que implemente DEP-02.** Sin esas tablas no hay versión anterior que conservar, y conservarla es requisito del encargo | — |

---

## Lo que esta spec no verifica

Va escrito aquí, y no escondido, porque es lo que un revisor debe poder ver de un vistazo.

| Qué no se verifica | Por qué | Qué lo cubriría |
| --- | --- | --- |
| Que la petición del lector se haya **atendido de verdad** | Las puertas de calidad responden «está bien formado y es coherente», no «es lo que se pidió». Un capítulo regenerado puede pasar G1a entero sin haber cambiado el nombre del perro | La reversión (RF-PET-09) devuelve el veto al lector. Comprobarlo de verdad exige un juez con rúbrica, que es otra spec |
| Que una contradicción de canon, o una cadena de conocimiento rota, **impidan** publicar | `CAN-01` y `CON-03` no están hoy en `BLOQUEANTES_EN_G1A` (DEP-04): se detectan y se registran, no bloquean | DEP-04, que es la P-3 de la spec **005**. Hasta que se firme, la protección de DEP-03 es parcial |
| Que **la novela siga funcionando como novela** tras una regeneración | DEP-03 revalida **G1a, que es por escena**: mira canon, continuidad, conocimiento y voz. Ninguna de sus comprobaciones pregunta si el manuscrito sigue cubriendo sus beats. Se puede quitar un objeto del capítulo 4, revalidar del 3 al 10, pasar los diez, y dejar sin plantar el beat de clímax del 9: diez escenas correctas y una novela rota | El **Auditor de manuscrito** (`CLAUDE.md` §9), que **no entra en este flujo**. Invocarlo en cada petición es caro y es otra spec |
| Que la novela **se lea bien** | Ningún test de frontend juzga prosa | Lectura humana, y el LLM-as-judge de la spec de evaluación |
| Que la relación de DEP-01 sea exacta | Es «recuperado», no «usado»: sobre-reporta por construcción | Nada dentro de esta spec. Se mitiga usando diferencia real de texto para marcar (RF-LEC-08) |
| Que la ficha congelada siga siendo cierta | Congelarla garantiza que **concuerda con su texto**, no que fuese correcta al publicarse | El validador formal de la cronología, en la spec de verificación formal |

---

## Cierre

Pendiente. Esta spec está en `borrador`.
