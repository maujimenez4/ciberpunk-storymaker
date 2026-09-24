---
id: problemas-abiertos
titulo: "Lo que está roto, a medias o sin dueño, y quién lo cierra"
estado: vivo              # se actualiza al cerrar cada fase; no se aprueba ni se archiva
fecha: 2026-09-24
---

# Problemas abiertos

**Qué es este fichero.** Lo que hoy está **roto, a medias o sin dueño**, con quién lo cierra y qué cuesta dejarlo. No es la lista de lo que falta por construir —eso es [`hoja-de-ruta.md`](hoja-de-ruta.md)— ni el cruce contra el encargo —eso es [`estado-del-entregable.md`](estado-del-entregable.md)—: es **lo que ya está construido y no está bien**.

Sale de las tablas de **Desviaciones** de los tres planes, que suman más de ciento cincuenta filas. Ahí está el detalle y el porqué; aquí está **lo que sigue vivo**, que es lo que nadie iba a leer de corrido.

**Las cinco primeras bloquean algo. El resto son deudas con su factura calculada.**

---

## P-1 · El CLI carga el `CLAUDE.md` del repositorio, y el flujo real no funciona

**Severidad: bloquea la corrida real, y con ella el PDF de la novela de ejemplo.**

Contra el servidor levantado, `POST /entrevistas/{id}/respuestas` responde **500**. El log dice:

```
SalidaMalFormada: He recibido y procesado el contexto completo del
proyecto **ciberpunk-storymaker**. Entiendo que:
```

**El modelo respondió sobre el repositorio, no sobre la entrevista.** El SDK lanza el binario `claude`, que está cargando el `CLAUDE.md` del proyecto como contexto — pese a que `claude_code.py` pasa `setting_sources=None` precisamente para evitarlo.

Lo bueno: **el esquema de salida lo rechazó**, que es para lo que existe. Un agente que devuelve prosa es un fallo, no una respuesta.

**Quién lo cierra:** antes de la corrida real, así que **Fase 4**. Y hasta entonces, cualquier verificación por HTTP contra un endpoint que llama al modelo **gasta cuota y falla**.

---

## P-2 · `elementos_obligatorios` no tiene columna, y eso abre una forma de decir que sí de balde

**Severidad: el validador de cobertura puede aprobar sin comprobar nada.**

`BriefEntrada.elementos_obligatorios` se valida al cerrar la entrevista y **no se persiste en ninguna columna**. La cobertura los lee del brief en bruto de `entrevista.respuestas`.

Funciona de extremo a extremo por el camino de CU-01. Pero **una obra creada sin entrevista no tiene elementos que cubrir**, y entonces `cobertura_de_personalizacion` dice que todo está bien **sin haber comprobado nada** — que es exactamente el defecto que **R-6 de la Fase 1** existía para impedir por el otro lado: «un validador que siempre pasa es peor que no tenerlo: ocupa su sitio».

**Quién lo cierra:** es esquema sobre `features/obra`. **Fase 4**, con su migración.

---

## P-3 · La spec dice catorce endpoints y hay quince

**Severidad: un criterio de aceptación que no se puede cumplir tal como está escrito.**

`CA-33` dice «los **catorce** endpoints aparecen en el OpenAPI», y hay **quince**: T9 añadió `POST /obras/{obra_id}/novela` porque `CA-1` «de principio a fin» y la corrida real necesitan **una** entrada — con solo `RI-05` son diez llamadas que alguien secuencia a mano sin saber los identificadores.

**Es un cambio de requisito y vuelve a firma**, como pasó con **P-07**. La spec necesita `RI-15` y `CA-33` con quince.

**Quién lo cierra:** una persona, al abrir la Fase 4.

---

## P-4 · `RF-VAL-06` está dado por cerrado y cubre un tercio

**Severidad: dos validadores que el requisito nombra viven solo en el prompt.**

El requisito dice «los validadores de canon, **continuidad y conocimiento** contrastan **contra el grafo**, no a ojo». El de **canon** sí es mecánico: el Continuista contrasta contra el grafo y el `hecho_canon_id` se comprueba en código.

Los otros dos **no**. Al Continuista le llega una proyección de `HechoCanon`, y la **regla de dominio 2** —nadie usa información sin `sabe_desde` con escena anterior— se decide contra el **ledger y `estado_en_t`**, que nadie le pasa. Tal como está, **un `CON-03` es una opinión del modelo cuya forma se comprueba pero cuyo fondo no.**

**Quién lo cierra:** las dos vistas existen desde la Fase 2. Es cablearlas. **Fase 6**, con el juez, que es donde el juicio semántico se mide.

---

## P-5 · El hook de policy no existe

**Severidad: §3 y `RF-GUA-07` piden dos hooks y hay uno.**

Existen `HOOK_DE_CAPITULO` y `PUERTA_G4` como puntos de ejecución, y el registro de auditoría *append-only*. **El motor de policy no.** El encargo §7 pide además «un audit log de las decisiones del policy engine»: el log está, las decisiones no.

**Quién lo cierra:** **Fase 7**.

---

## Deudas de esquema, que vencen al regenerar

### P-6 · `evento` y `hecho_canon` no tienen `run_id`

El guardia de idempotencia los reconoce **por escena**, no por corrida. **Hoy es exacto** —solo se escriben en `EXTRAYENDO`, una vez por escena, y una escena rechazada no escribe nada— y **deja de serlo el día que se regenere un capítulo ya integrado**, que es justo lo que hace la petición del lector.

**Quién lo cierra: Fase 5**, y es de las primeras cosas que hay que mirar ahí.

### P-7 · `resumen_capitulo` tiene `UNIQUE(capitulo_id)` y siempre inserta

Consolidar dos veces el mismo capítulo **salta `IntegrityError`** en vez de no hacer nada. Hoy **no se puede provocar** —la consolidación y la transición a `INTEGRADA` comparten transacción, y la reanudación arranca por el primer capítulo no integrado—, y el agente de T8 **no añadió guardia a propósito**, porque habría sido la décima restricción inalcanzable del proyecto.

**Regenerar un capítulo ya integrado sí llega con el resumen puesto.** **Fase 5**, y entonces la guardia se escribe con su test.

### P-8 · `hecho_canon.sustituye_a` existe y nadie lo ha ejercitado

La columna y `escribir_hecho_que_sustituye` entraron en la Fase 3 con un test de cadena de tres correcciones. **Ningún camino de producción lo usa todavía**: corregir un hecho es lo que pasa cuando el lector dice «el perro se llama Nala».

**Fase 5.**

### P-9 · `hecho_canon` vive en `features/obra` y su único escritor es el Extractor

Que es `features/canon`. **Hoy dos features escriben la misma tabla.** Mover la tabla es migración y `modelos.py` tiene un solo dueño por fase, así que `canon` entra por el `__init__.py` de `obra`, que respeta la frontera pero no la intención.

**Sin fecha. Decidir antes de que una tercera feature escriba ahí.**

---

## Deudas de vocabulario y de forma

### P-10 · `SalidaMalFormada` va por **cinco** copias

`CLAUDE.md` §5.1 regla 4 dice que sube a `commons/` **al tercer uso real**. Van cinco, y la deuda estaba vencida antes de la Fase 3. Nadie la paga porque `commons/llm/` siempre pertenece a otra tarea.

**Es el caso de libro de la regla, y lleva dos fases sin pagarse.**

### P-11 · `checkpoint` no está en `docs/definitions.md`

No es un término inventado: `architecture.md` §3.9 titula «Checkpoint por capítulo» y `verification.md` lo usa en dos invariantes. Pero **no figura en la lista de §2**, y ahora hay código que lo produce. `CLAUDE.md` §2 dice que un término que no está **no se introduce sin confirmación**.

**Una persona, cuando le venga bien.**

### P-12 · `Senal` no tiene causa para «el proceso murió»

La reanudación cierra el trabajo muerto con `TIEMPO_AGOTADO` **por descarte**: §3.6 no contempla la caída, `CONTEXTO_EXCEDIDO` sería falso y `CANCELACION` miente sobre quién lo pidió **y no tiene flecha desde `REPARANDO` ni `EXTRAYENDO`**.

**Es la clase de detalle que hace que una traza mienta un poco** — y con Langfuse en la Fase 6, esa traza es lo que alguien va a mirar. **Fase 6.**

---

## Cosas que el entorno impone y conviene saber

### P-13 · `tiktoken` descarga su vocabulario la primera vez

El contador previo es **local**, pero no local del todo: `cl100k_base` se descarga y se cachea. La suite no lo paga —inyecta su BPE en memoria— pero **el contador de producción en una máquina sin red y sin caché falla al primer `contar()`**. Cerrarlo pide vendorizar ~1,6 MB.

### P-14 · La semilla no hace reproducible la llamada

Se registra en `Consumo` por `RF-OBS-06`, y **el proveedor no la admite**. Si alguna fase posterior da por hecho «misma semilla → mismo texto», es falso. `CA-12` se salva porque habla de reconstruir **el paquete**, no la prosa.

### P-15 · «Ya autenticado» no está definido fuera de la máquina del autor

**P-08** dice que el cliente invoca el Claude Agent SDK «ya autenticado». El SDK **no habla HTTP: lanza el binario `claude`**, que aquí existe y está autenticado — y `pyproject.toml` **no lo declara** y **ninguna puerta lo comprueba**: sin el binario, la corrida real falla y **la suite sigue verde**. El entregable necesita esa línea escrita.

---

## Una del proceso, no del código

### P-16 · El reparto por fichero corta las tareas justo por donde pasa el cable

**Ha pasado en las cinco olas de las dos fases**, y siempre igual: una juntura vive entre dos features, ninguna de las dos tareas puede tocarla sin saltarse la regla 1, y la cierra el integrador. Ejemplos: `vectorizar` sin cablear, `trabajo.capitulo_id` sin rellenar, `CA-15` sin la consulta que lo une, el `__init__.py` que ningún agente podía tocar.

La regla dice «un agente por fichero **dentro de la ola**» y **no dice qué pasa cuando la juntura vive en fichero ajeno**.

**Para los planes que quedan: o las junturas tienen dueño explícito desde el plan, o se declara que las cierra el integrador.** Las dos valen; lo que no vale es descubrirlo al integrar, que es lo que llevamos haciendo.
