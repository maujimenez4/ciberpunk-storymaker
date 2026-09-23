# Ezequiel — adaptación al encargo y spec de frontend

Llevo la distancia entre lo que el repositorio es hoy y lo que pide el encargo
final, y de ahí salió la spec de lectura web. **No escribo código de producción
ni cambio ningún `estado:`** (§3.2 y §14: eso lo firma una persona).

---

## 15:20 · Análisis de huecos contra el encargo final

- **Qué:** cruzar el enunciado del examen con el repositorio y proponer un camino en cuatro fases. Lo que falta, en corto: entrevistador y brief personalizado, lectura web, Langfuse, Lean, TLA+, guardrail de palabras prohibidas, hooks, browser MCP, README y `.env.example` —no existe ninguno de los dos—, `/ejemplos`, `/presentacion`. Lo que hay es sólido: el ciclo de escena entero, presupuesto de contexto, ledger, orquestador reanudable.
- **Ficheros:** solo lectura — `docs/`, `specs/001-*`, `src/backend/`, `CLAUDE.md`
- **Estado:** terminado

## 15:45 · Cuatro decisiones de producto de `maujimenez4`

- **Qué:** capítulo **=** escena, 1.000–1.500 palabras, diez capítulos por novela; género romance personalizado por brief; lectura web con enlace de descarga del PDF; aprobado proponer el vocabulario nuevo.
- **Ficheros:** ninguno
- **Estado:** terminado
- **Ojo:** la primera contradice tres documentos que siguen sin actualizarse: `CLAUDE.md` §1 y `domain-knowledge.md:78` dicen 80.000–120.000 palabras, `architecture.md:736` habla de un outline de 40 escenas, y `definitions.md:74` da al capítulo 2.500–4.000. **Si alguien está dando por cierta la escala vieja, ya no lo es.** No los he tocado yo: `CLAUDE.md` y `architecture.md` los tiene modificados Hernan ahora mismo.

## 16:05 · `definitions.md` v1.4 — entra el vocabulario de la entrega

- **Qué:** seis términos nuevos en §9, con sus predicados en §10, su glosario en §13 y el árbol de §14.7 al día: `Destinatario`, `Comprador`, `Dedicatoria`, `VersionPublicada`, `PeticionDeCambio`, `FichaDeLectura`. Van **antes** de la spec que los usa, que es lo que manda §2.
- **Ficheros:** `docs/definitions.md`
- **Estado:** terminado
- **Ojo:** se llama `VersionPublicada` y **no** `VersionDeNovela` a propósito: ya existen `VersionDeTexto` (texto de una escena) y `VersionDeObra` (biblia congelada), más una tabla `version_obra` en la migración inicial. Una tercera «versión de» era deriva terminológica servida. Me lo señaló Mario y tenía razón.

## 16:20 · `specs/003-lectura-web/spec.md` en borrador

- **Qué:** la spec de lectura web. Portada con dedicatoria, índice, capítulo, ficha congelada por versión, marcado de capítulos cambiados, descarga del PDF, petición de cambio del lector con autopublicación y reversión. Alcance **solo lectura**: el taller del autor va a otra spec, para que esta sea aprobable sin esperar a las dependencias de aquella.
- **Ficheros:** `specs/003-lectura-web/spec.md` (nuevo), `docs/definitions.md`
- **Estado:** en curso — en `borrador`, con cinco preguntas abiertas para `maujimenez4`
- **Ojo:** **es la 003 y no la 002** porque `specs/002-validadores-fallo-cerrado/` ya ocupaba ese número cuando fui a escribir la cabecera. Me avisó Mario antes de que colisionara.

## 16:25 · Tres dependencias declaradas que son de backend, no mías

- **Qué:** la spec no se puede implementar sola y lo dice en una sección propia. Quien lleve `contexto`, `canon` o `manuscrito` debería saber que existen:
  1. **DEP-01 — la capa de canon tiene que etiquetar por `hc_id`.** Hoy `CANON_RELEVANTE` etiqueta `canon-presente-{i}` por **posición** (`contexto/recoleccion.py:96-107`) y `ejecucion.ids_recuperados` solo recoge `MEMORIA_RECUPERADA` (`contexto/service.py:173-180`). Sin eso no se sabe qué capítulos usan un hecho, y la petición de cambio del lector no se puede implementar. **No hace falta tabla nueva:** el argumento ya está escrito en `recoleccion.py:178` para la otra capa.
  2. **DEP-02 — seis endpoints que no existen**, entre ellos el historial de versiones publicadas y la descarga del PDF. `manuscrito/router.py` sigue vacío.
  3. **DEP-03 — regenerar un capítulo obliga a revalidar G1a en los posteriores.** No es un riesgo: el Extractor cambia `estado_en_t` para todos los siguientes, por construcción. Peor caso, diez llamadas en serie por el límite de §2.2.
- **Ficheros:** ninguno tocado — todo verificado en solo lectura
- **Estado:** terminado
- **Ojo:** las tres cuelgan de `specs/001-backend-v1/`, que **sigue en `en-revision`** con su Cierre firmado y sus commits citados. Lo he escrito en la spec en vez de disimularlo, pero es de las cosas que solo `maujimenez4` puede cerrar.

## 16:40 · Corrijo lo que dije de `manuscrito`, y entra P-06

- **Qué:** escribí a las 16:25 que `manuscrito` estaba «prácticamente vacío». **Falso a medias.** Nubia me corrigió y lo verifiqué: `service.py` son 245 líneas suyas de hoy, con `a_markdown`, `a_pdf` —PDF 1.4 con la biblioteca estándar, sin dependencias nuevas— y `exportar`, todo público por el `__init__`. Vacíos siguen `router.py` y `schemas.py`, de cuatro líneas. Corregida la spec: el endpoint de descarga no genera nada, llama a `a_pdf` y devuelve bytes.
- **Ficheros:** `specs/003-lectura-web/spec.md`
- **Estado:** terminado
- **Ojo:** de ahí sale una **pregunta abierta nueva, P-06**. Lo que de verdad falta no es el PDF sino el **histórico**: `Manuscrito` conoce la versión vigente de cada escena, no una sucesión de publicaciones. `VersionPublicada` es tabla nueva, y `version_obra` **no sirve** para eso —guarda la biblia congelada—. Cambio de esquema, o sea §3 punto 7: lo aprueba `maujimenez4`, no una sesión.

## 16:55 · DEP-04: `CAN-01` no bloquea, y eso rompía la garantía de DEP-03

- **Qué:** Mario encontró el único punto de la spec donde yo prometía algo que el código no da, y lo verifiqué: `BLOQUEANTES_EN_G1A` es `{CON_01, CON_02, EST_01, SEG_01, VOZ_03}` (`calidad/defectos.py:61-69`). **`CAN-01` no está.** Como DEP-03 decía «si la revalidación abre defectos bloqueantes, no se publica», el escenario que decía cubrir —regenero el 4, el 7 pasa a contradecirlo— se detecta y **se publica igual**. Entra DEP-04 y una fila en «Lo que esta spec no verifica». Además: «posteriores» ahora se ancla en la escena de origen del hecho sustituido, como §4.7, y no en lo regenerado (son conjuntos distintos); y «vuelve al editor» pasa a ser `ESCALADA`, que es el estado que ya existe.
- **Ficheros:** `specs/003-lectura-web/spec.md`
- **Estado:** terminado
- **Ojo:** para quien lleve `specs/002-validadores-fallo-cerrado/`: **mi spec 003 depende de que `CAN-01` vuelva a `BLOQUEANTES_EN_G1A`.** Mientras no vuelva, la protección de continuidad de la lectura es parcial y así queda escrito.

## 17:00 · CA-5 reescrito: pasaba siempre

- **Qué:** CA-5 decía «la vigente es byte a byte la de antes». No era un criterio flojo: era uno que **no puede fallar**, porque §14 prohíbe editar en sitio y los bytes de una versión anterior no pueden cambiar. Reescrito en tres asertos observables —ninguna `VersionPublicada` nueva, el puntero de vigente sin mover, y ningún rastro en canon, ledger ni índice—, el tercero calcado de **CA-7 de la 001**.
- **Ficheros:** `specs/003-lectura-web/spec.md`
- **Estado:** terminado
- **Ojo:** P-04 queda contestada: la 002 es de **Gustavo**, así que el taller del autor toma el **004**.
