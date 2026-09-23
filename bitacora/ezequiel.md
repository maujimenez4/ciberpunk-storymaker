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

## 17:15 · DEP-04 gana `CON-03`, cita la P-3 de la 002, y entra el hueco del Auditor

- **Qué:** tercera ronda de Mario, verificada antes de aplicar. Tres cosas: (1) DEP-04 ahora **nombra la P-3 de `specs/002-*/`** en vez de decir «territorio de aquella spec» — esa pregunta es literalmente mi dependencia, y nombrarla la convierte en bloqueante de otra entrega; (2) entra **`CON-03`** junto a `CAN-01`, y para esta spec pesa más: regenerar el capítulo 4 cambia qué se entera cada personaje y cuándo, así que el 7 puede pasar a usar algo que ya no presenció; (3) fila nueva en «lo que no verifica» por el **Auditor de manuscrito**.
- **Ficheros:** `specs/003-lectura-web/spec.md`
- **Estado:** terminado
- **Ojo:** el hueco del Auditor no es de capítulos, es de nivel. DEP-03 revalida **G1a, que es por escena**. Se puede quitar un objeto del capítulo 4, revalidar del 3 al 10, pasar los diez, y dejar sin plantar el beat de clímax del 9: **diez escenas correctas y una novela rota**. Queda declarado, no resuelto: invocar al Auditor en cada petición es otra spec.

## 17:20 · Verificado el árbol y las herramientas de la 002, sin commitear

- **Qué:** me trasladan que el usuario quiere que Mario y yo commiteemos los validadores de la 002. **No lo he hecho**: me lo pide una sesión, no él, y el propio mensaje dice que Julio es quien sube. Se lo he preguntado directamente. Lo que sí hice fue verificar en vez de fiarme: `ruff check` limpio, **444 tests en verde** —lo que Nubia reportó a las 16:30 (23 errores, 4 rojos) ya está resuelto—, y `validar_spec.py` da **12/12** en la 002 con un aviso de cuatro requisitos sin CA.
- **Ficheros:** ninguno tocado
- **Estado:** bloqueado — esperando a `maujimenez4` para saber quién commitea
- **Ojo:** `sonda_dominio.py` **sale con código 0 y no imprime nada**. No puedo confirmar por su salida que pasen las siete propiedades que dice cubrir; solo que no falla. Quien la dé por evidencia en la spec 002 debería saberlo.

## 17:35 · Orquestación: decisión de no renumerar, y DEP-01 más hondo

- **Qué:** el usuario me pone a orquestar todas las specs con prioridad de decisión. Primera decisión: **no se renumera nada**. La 002 sigue siendo validadores y el frontend sigue siendo la 003. Verifiqué el coste: **23 ficheros citan la ruta**, 15 reales, incluidos `test_invariantes.py` —dentro de los 444 verdes— y una skill. Creo además que «la 002 de frontend» es como el usuario llama a mi spec desde antes de que existiera la de Gustavo, no una instrucción de renumerar; se lo he preguntado igualmente.
- **Ficheros:** `specs/003-lectura-web/spec.md`
- **Estado:** terminado
- **Ojo:** **las bitácoras no se tocan.** Son registro histórico y envejecen a propósito; reescribir las referencias viejas sería falsificar justo el registro que esta convención existe para tener. Y queda levantada la congelación de Hernán sobre crear referencias nuevas a `002-validadores-*`: si no se renumera, no hay razón para no citarla.

## 17:40 · DEP-01 no era el formato de la etiqueta, era la firma del almacén

- **Qué:** Nubia afinó DEP-01 y es un punto más hondo del que yo escribí. Verificado: `canon_relevante(escena_id) -> list[tuple[str, bool]]` en `contexto/recoleccion.py:46`, `contexto/repository.py:103` y el doble de `test_recoleccion.py:35`. El `hc_id` **no llega nunca** a `recoleccion.py`, así que no se puede etiquetar con algo que no se recibe: lo que cambia es lo que devuelve el almacén. Y añadido el efecto que va más allá de mi spec: con `ejecucion` sin registrar qué canon entró, **RI-14 de la 001 queda a medias** y la auditoría de una escena es parcial.
- **Ficheros:** `specs/003-lectura-web/spec.md`
- **Estado:** terminado
- **Ojo:** los commits los lleva **Nubia** desde ahora, por encargo del usuario. No commiteo yo. `ce2b810` **no incluye** la tercera ronda de Mario ni estos dos arreglos; se lo he dicho para que no dé la 003 por cerrada.

## 18:05 · Segunda mitad de la renumeración: soy la 002

- **Qué:** el usuario revocó mi decisión de no renumerar, así que la ejecuté. `git mv specs/003-lectura-web specs/002-lectura-web`, `id:` al día, y las **tres referencias en prosa** que Mario señaló: la nota de numeración, la P-04 y —la que más importaba— la fila que apuntaba a «la P-3 de la spec 002», que tras el movimiento se habría apuntado a sí misma. `validar_spec.py`: **13/13**.
- **Ficheros:** `specs/002-lectura-web/spec.md` (antes `003-lectura-web`)
- **Estado:** terminado
- **Ojo:** el aviso de Mario era el bueno y conviene repetirlo: una ruta muerta falla a gritos, una **referencia válida y equivocada** no falla nunca. Las tres mías eran de ese segundo tipo en cuanto ocupara el número. Y queda escrito en la spec que `82a1a49` y `ce2b810` nombran las rutas viejas para siempre: quien lea el historial necesita saber que `003-lectura-web` y la 002 son la misma.

## 18:10 · Cuatro preguntas cerradas, una a medias

- **Qué:** `maujimenez4` contestó. **P-01:** identificador no adivinable en la URL — no es autenticación, es que el enlace se pueda regalar sin publicar de paso las demás novelas; entra **RD-04** y **CA-21**. **P-02:** la revalidación de DEP-03 se especifica en la spec de backend, aquí solo se declara. **P-03:** progreso por capítulo. **P-06:** cambio de esquema aprobado, migración en la spec de backend.
- **Ficheros:** `specs/002-lectura-web/spec.md`
- **Estado:** en curso — queda **P-05** a medias
- **Ojo:** **P-05 sigue abierta y no la doy por contestada.** El usuario aprobó las ocho dependencias «solamente en el generador del cliente, vamos a utilizar el consumo de la propia cuenta». No sé qué significa y no lo voy a interpretar: si quiere decir que el cliente lo genere un modelo en vez de una herramienta, choca con `CLAUDE.md` §7, que prohíbe escribir tipos de respuesta a mano. Le he pedido que lo aclare.

## 18:15 · Bloqueo sobre la 001: RF-CTX-07 no está implementado

- **Qué:** el usuario decidió pasar la 001 a `implementada`. **Mario lo paró con medición y lo verifiqué yo:** `RF-CTX-07` es `M` (imprescindible) y `T` (establecido por prueba), y el filtro estructural no existe. `canon/repository.py:511` declara `candidatos_para_ordenar(self, tope: int)` — **no recibe `escena_id`**, así que no puede filtrar por presentes, lugar, hilos abiertos ni rango de capítulos. Tres docstrings prometen el filtro y cada uno apunta a otra capa.
- **Ficheros:** ninguno tocado
- **Estado:** bloqueado — esperando decisión de `maujimenez4`
- **Ojo:** marcar `implementada` con RF-CTX-07 incumplido deja por escrito que un requisito imprescindible está probado cuando no existe, y `CLAUDE.md` §4.2 declara ese orden filtrar→ordenar→fusionar **no negociable**. Se lo he pasado al usuario con las tres salidas antes de que ejecute. **Yo no cambio ningún `estado:` en ningún caso.**

## 18:40 · La firma me la deniega el harness, y hace bien

- **Qué:** `maujimenez4` me autorizó de viva voz a firmar la 002 como `aprobada` y a cerrar la 001 como `implementada`. **El harness lo denegó con motivo literal `[Self-Approval]`.** No lo he rodeado ni lo voy a rodear con otra herramienta: es exactamente la barrera que describe §3.2, y esquivarla sería saltármela a propósito. Las dos specs siguen donde estaban.
- **Ficheros:** ninguno — la edición no llegó a aplicarse
- **Estado:** bloqueado — esperando a que `maujimenez4` teclee las dos líneas
- **Ojo:** efecto secundario bueno: **el repaso completo de Mario vuelve a ir por delante de la firma**, que es el orden acordado y que yo iba a saltarme. Lo que sí quedó escrito es la desviación de `RF-CTX-07` en el Cierre de la 001, que es documentación y no estado.

## 18:45 · Las D-1 a D-5 de la 005 llevaban horas contestadas

- **Qué:** el usuario me pidió firmar «la P-1 a P-5» de la spec de validadores. Fui a leerlas antes de tocarlas y **ya estaban contestadas por él el 2026-09-23**, convertidas en D-1 a D-5. Mario, Hernán y yo llevábamos la tarde tratando la P-3 como abierta. Reescrito mi **DEP-04**: ya no pide una decisión, pide una **medición**, porque **D-3** dice «partir el campo, y medir antes de volver a bloquear; corrida real autorizada».
- **Ficheros:** `specs/002-lectura-web/spec.md`
- **Estado:** terminado
- **Ojo:** el patrón que nos costó una hora: una spec en `estado: borrador` con la sección de **Decisiones completa**. `validar_spec.py` comprueba que no queden preguntas si está aprobada, pero nada avisa de lo contrario. Se lo he propuesto a Hernán como invariante.

## 18:50 · Canal único: todo al usuario pasa por Jose

- **Qué:** encargo suyo. Comunicado a las seis sesiones —Jose, Mario, Hernán, Nubia, Gustavo y Julio—: las peticiones y preguntas abiertas se le mandan a **Jose**, que las agrupa y se las presenta, para que solo tenga que abrir una conversación.
- **Ficheros:** ninguno
- **Estado:** terminado
- **Ojo:** le he pedido a Jose que agrupe antes de llevárselo, que cada petición vaya con dueño, bloqueo y recomendación, y que distinga lo que **bloquea** de lo que **informa**. Hoy se mezclaron las dos cosas y por eso hizo falta el embudo.
