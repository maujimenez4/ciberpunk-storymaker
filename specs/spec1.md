---
id: 001-backend-v1
titulo: Backend, versión 1 — el ciclo completo de una escena
estado: borrador          # borrador | en-revision | aprobada | implementada
aprobada_por:             # lo rellena una persona, nunca un agente
fecha: 2026-09-21
---

# 001-backend-v1 — Backend, versión 1

Qué debe hacer la primera versión del backend y cómo se sabrá que lo hace. **Aquí no se decide cómo se implementa:** eso es el plan, y no se escribe hasta que esta spec esté `aprobada`.

Es una spec completa y única: cubre el backend entero de la v1 en lugar de trocearse por funcionalidad, porque las piezas del ciclo de una escena no se pueden entregar por separado —un ensamblador sin orquestador no se puede probar, y un orquestador sin memoria no cierra el bucle.

---

## Problema

Hoy no se puede escribir una novela larga con un modelo de lenguaje sin que se deshaga por el camino. La novela terminada no cabe en una llamada, y meterla entera empeora el resultado: el modelo imita lo reciente y diluye lo importante (`domain-knowledge.md` §1 y §10).

Quien lo sufre es el autor: escribe veinte escenas, y en la veintiuna el personaje tiene otros ojos, sabe algo que nadie le contó y habla como el capítulo 3 no hablaba. Los fallos son baratos de cometer y carísimos de encontrar, porque cada escena por separado parece correcta.

No existe hoy en este repositorio nada ejecutable: ni ensamblado de contexto, ni memoria, ni validación. Solo documentación.

---

## Alcance

El objetivo es el de la fase 1 de la hoja de ruta (`architecture.md` §13): **un capítulo coherente**. El ciclo completo de una escena, de principio a fin, con la memoria cerrándose sobre sí misma.

| Capacidad | Motivo |
| --- | --- |
| Obra desde un brief, biblia y outline | Sin outline no hay ficha de escena |
| Planificar, ensamblar, escribir e integrar una escena | Es el bucle completo; sin él no hay producto |
| Presupuesto por capa y techo agregado | Restricción no negociable (`CLAUDE.md` §4.1) |
| Orquestador con estado persistido y reanudación | Sin él, una caída pierde trabajo y nada se puede depurar |
| Memoria de largo plazo: canon, ledger, resúmenes, índice | Es lo que cierra el bucle entre escenas |
| Validadores **mecánicos** | Son los que se cuentan, no los que se juzgan (`domain-knowledge.md` §11) |

**Ámbito:** backend. El frontend queda fuera.

---

## Fuera de alcance

| Excluido | Motivo | Cuándo |
| --- | --- | --- |
| Crítico con rúbrica y juez calibrado | Necesita escenas etiquetadas por un editor; sin calibrar, estorba | Fase 4 |
| Métricas de prosa: repetición, tics, variedad sintáctica, deriva de estilo | Son umbrales, no bloqueantes; sin corpus aprobado no hay referencia | Fase 4 |
| Validación de voz: distancia a muestras ancla, clasificador de POV | Exige criterio, no cuenta (`domain-knowledge.md` §11) | Fase 4 |
| Editor de línea | Introduce una segunda escritura sobre texto ya aprobado | Fase 6 |
| Auditoría de manuscrito: hitos, plantados, curva de temperatura | No tiene sentido con un capítulo | Fase 5 |
| Puertas G2 (capítulo) y G3 (manuscrito) | Mismo motivo | Fases 4–5 |
| `Serie` y canon compartido entre obras | Se decide al empezar una segunda obra | Sin fecha |
| Frontend | Spec aparte | — |
| Modo servidor multiusuario | El modo de referencia es local | Fase 6 |

**Aviso sobre `Serie`:** `definitions.md` §4.1 advierte que, si existe, el canon debe ser compartido **desde el primer día**. Excluirla es una decisión con coste futuro conocido, no un olvido; RD-10 limita el daño.

La exclusión no es «se hará mal»: es «no se hará», y el esquema de datos no debe impedirlo después.

---

## Requisitos

Convenciones de esta sección:

| Prefijo | Tipo | | Marca | Significado |
| --- | --- | --- | --- | --- |
| `CU-` | Caso de uso | | `M` | Imprescindible: si falta, no se cumple un criterio de aceptación |
| `RI-` | Interfaz externa | | `S` | Necesario pero degradable sin invalidar la entrega |
| `RF-` | Funcional | | **T/A/I/D** | Prueba / Análisis / Inspección / Demostración (`verification.md`) |
| `RD-` | Datos | | | |
| `RNF-` | No funcional | | | |

**Todo requisito cita su origen.** Uno sin origen es una invención y se rechaza en revisión. Las palabras **debe**, **no debe** y **puede** se usan en sentido normativo.

### Casos de uso

**CU-01 · Arrancar una obra.** *Precondición:* ninguna. *Flujo:* el autor envía un brief → se crea la `Obra` con sus parámetros de discurso → se lanza la biblia como trabajo. *Postcondición:* existe una obra con `persona`, `tiempo_verbal`, `esquema_de_pov` y `nivel_de_calor` fijados, y una biblia versionada. → RI-01, RI-02, RF-OBR-01 a 04.

**CU-02 · Generar el outline.** *Precondición:* biblia vigente. *Flujo:* se produce `Parte → Capitulo → Escena` y cada hito obligatorio de género se asigna a exactamente una escena. *Postcondición:* cada escena tiene `pov`, `lugar`, objetivo, obstáculo y giro previsto. *Excepción:* hito sin escena o duplicado → `FALLIDA` con `ReglaDeDominioViolada`. → RI-03, RF-OUT-01 a 05, RG-06.

**CU-03 · Escribir una escena** *(caso central)*. *Precondición:* la escena existe en el outline y la anterior está `INTEGRADA`.

*Flujo principal:* `PLANIFICANDO` (ficha) → `ENSAMBLANDO` (paquete presupuestado y recortado) → `ESCRIBIENDO` (reserva agregada, llamada, versión guardada) → `VALIDANDO` (validadores mecánicos) → `EXTRAYENDO` (canon, ledger, resumen, hilos e índice en una transacción) → `INTEGRADA`.

*Flujos alternativos:*
- Defecto bloqueante → `REPARANDO` con el defecto y su cita → vuelve a `ESCRIBIENDO`. Máximo dos veces; después `ESCALADA`.
- El paquete no cabe tras recortar → `FALLIDA` con `ContextBudgetExceeded`, **sin llamar al modelo**.
- Sin hueco agregado antes del *timeout* → `FALLIDA` con `PresupuestoAgregadoAgotado`, sin coste.
- Cancelación del autor → `CANCELADA` en el primer punto seguro.

*Postcondición de éxito:* la escena está en el manuscrito y la memoria de largo plazo la incluye. *Postcondición de fracaso:* **la memoria de largo plazo no ha cambiado.** → RI-05, RI-09, RF-ESC-*, RF-CTX-*, RF-ORQ-*, RF-CAL-*, RF-CAN-*.

**CU-04 · Resolver un escalado.** *Precondición:* un trabajo en `ESCALADA`. *Flujo:* el autor consulta el defecto con su cita, edita o acepta → versión nueva marcada vigente → se reanuda. *Postcondición:* la escena acaba `INTEGRADA` o `CANCELADA`, nunca indefinidamente en `ESCALADA`. → RI-07, RI-09, RF-ESC-03, RF-ESC-04. *(Por dónde se reanuda: pregunta abierta 8.)*

**CU-05 · Inspeccionar el contexto enviado.** *Precondición:* al menos una ejecución. *Flujo:* se consulta paquete y desglose. *Postcondición:* el desglose suma lo que dice y respeta los topes. → RI-06, RF-CTX-06, RF-CTX-10.

**CU-06 · Reanudar tras una caída.** *Precondición:* el proceso se detiene con trabajos no terminales. *Flujo:* al arrancar se leen los trabajos vivos y se repite entero el paso interrumpido. *Postcondición:* ninguna escritura duplicada; el trabajo avanza o falla, pero no queda colgado. → RF-ORQ-04 a 06, RNF-FIA-01.

### Interfaces externas

Identificadores opacos para el cliente. Toda operación larga devuelve un `trabajo` y **no** bloquea la petición.

| ID | Método y ruta | Entrada esencial | Salida | Pr. |
| --- | --- | --- | --- | --- |
| RI-01 | `POST /obras` | `Brief`: género, subgénero, tropo, tono, extensión, parámetros de discurso | 201 + `obra` | M |
| RI-02 | `POST /obras/{id}/biblia` | — | 202 + `trabajo` | M |
| RI-03 | `POST /obras/{id}/outline` | — | 202 + `trabajo` | M |
| RI-04 | `POST /escenas/{id}/planificar` | — | 202 + `trabajo` | M |
| RI-05 | `POST /escenas/{id}/escribir` | — | 202 + `trabajo` | M |
| RI-06 | `GET /escenas/{id}/contexto` | — | 200 + paquete y desglose por capa | M |
| RI-07 | `GET /escenas/{id}/versiones` | — | 200 + historial inmutable, con la vigente marcada | M |
| RI-08 | `GET /obras/{id}/canon` | filtros: entidad, atributo | 200 + hechos con `escena_de_origen` | S |
| RI-09 | `GET /trabajos/{id}` | — | 200 + estado del trabajo (RI-18) | M |

*Origen: `architecture.md` §5.4. Verificación: **T**.*

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RI-11 | Ningún servicio lanza `HTTPException`: las excepciones de dominio las traduce el handler central. `ContextBudgetExceeded` → 422 con la capa que desbordó; `PresupuestoAgregadoAgotado` → 503 relanzable sin coste; `ReglaDeDominioViolada` → 422 con el axioma incumplido; `RecursoNoEncontrado` → 404; `FalloDeProveedor` agotado → 502 | M | **T**, uno por caso |
| RI-12 | Modelos de entrada y de salida distintos; ninguno expone el modelo de base de datos | M | **A** |
| RI-13 | Cliente de modelo, contador de tokens y reloj se inyectan. Ninguna prueba llama al proveedor real | M | **A** más **T** |
| RI-14 | Toda llamada registra `run_id`, escena, versión de prompt, versión de biblia, IDs recuperados, modelo, parámetros, semilla, tokens por capa, coste y veredicto | M | **T** |
| RI-15 | Las claves se leen de entorno. Nunca del repositorio ni de la base de datos | M | **I** más **A** |
| RI-16 | SQLite con `WAL`, `foreign_keys=ON` y `busy_timeout`. Migraciones con Alembic desde el primer commit | M | **T** |
| RI-17 | La búsqueda semántica vive tras `VectorStore`, con `SqliteVecStore` y `BruteForceStore`. En arranque se detecta la extensión; si no carga, se degrada y se avisa. **El sistema nunca falla por falta de extensión vectorial** | M | **T** en ambos modos |
| RI-18 | La respuesta de RI-09 expone `id`, `tipo`, `estado` (uno de los diez de `architecture.md` §3.3), `intento`, `causa_fallo`, `creado_en`, `actualizado_en` y, en `ESCALADA`, los defectos con **código y cita** | M | **T** |
| RI-19 | Existe forma de cancelar un trabajo en curso; el efecto es `CANCELADA` en el primer punto seguro, nunca a mitad de una escritura | S | **T** |
| RI-20 | El proveedor de *embeddings* está tras una interfaz propia, y su consumo no cuenta contra ningún presupuesto de contexto | M | **A** |
| RI-21 | La configuración se lee de entorno con valores por defecto explícitos, y el arranque **falla de inmediato** si falta uno obligatorio: clave y punto de acceso del proveedor, modelo, techo agregado, *timeout* de reserva, plazo por paso, N de los *snapshots*, dimensión de los *embeddings* y ruta del fichero | M | **T** |
| RI-22 | El arranque registra, una vez, qué implementación de `VectorStore` quedó activa | M | **T** |

*Origen: `architecture.md` §3.2, §3.6, §5.4, §9, §11; `CLAUDE.md` §3.5, §4.2, §6.*

### Funcionales

**Feature `obra`** — *origen: `definitions.md` §4.1, §4.3, §9 y §12.*

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-OBR-01 | Crear una `Obra` desde un `Brief`, fijando `persona`, `tiempo_verbal`, `esquema_de_pov` y `nivel_de_calor`, que heredan todas sus escenas | M | **T** |
| RF-OBR-02 | Generar la `Biblia`: personajes con parte fija, lugares con `tiempo_de_viaje`, reglas de mundo, tropo y `promesa_de_apertura` | M | **T** |
| RF-OBR-03 | La biblia es **versionada**: cambiarla crea versión nueva de obra, no se edita en sitio | M | **T** |
| RF-OBR-04 | Registrar el catálogo de temas sensibles declarados | S | **T** |

**Feature `outline`** — *origen: `definitions.md` §4.1 y §6; el porqué del orden, `domain-knowledge.md` §8.1.*

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-OUT-01 | Generar el `Outline` jerárquico `Parte → Capitulo → Escena` | M | **T** |
| RF-OUT-02 | Asignar cada `BeatDeGenero` obligatorio a **exactamente una** `Escena`, dentro de su franja | M | **T** |
| RF-OUT-03 | Cada `Escena` nace con `pov`, `lugar`, `objetivo_del_pov`, `obstaculo` y giro previsto (`valor_entrada` ≠ `valor_salida`) | M | **T** |
| RF-OUT-04 | El outline de la v1 cubre al menos un capítulo completo; no se exige la novela entera | M | **D** |
| RF-OUT-05 | Respetar el orden de los hitos: ninguno se asigna a una escena anterior a la del hito que lo precede | S | **T** |

**Feature `escena`** — *origen: `definitions.md` §4.1, §4.4 y §9; `CLAUDE.md` §14; los dos relojes, `domain-knowledge.md` §3.1.*

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-ESC-01 | Producir la `FichaDeEscena` desde el outline y el estado en T | M | **T** |
| RF-ESC-02 | La ficha declara las restricciones duras: `pov`, `presentes[]`, `lugar`, `distancia_psiquica`, `densidad_de_dialogo_objetivo`, `extension_objetivo` y el `nivel_de_calor` heredado | M | **T** |
| RF-ESC-03 | Guardar cada `VersionDeTexto` como **inmutable**, con su `run_id` y una sola versión `vigente` | M | **T** |
| RF-ESC-04 | Editar **crea versión nueva** y marca la vigente. Ninguna ruta modifica texto en sitio | M | **A** más **T** |
| RF-ESC-05 | Los dos relojes son campos distintos: `tiempo_historia` y `orden_discurso`. La coherencia se calcula por el primero | M | **A** más **T** |

**Feature `contexto`** — el corazón de la v1, y el único componente cuyo fallo es silencioso si no se mide. *Origen: `definitions.md` §7; `architecture.md` §2.1, §4.2 y §4.6; el orden de recuperación, `domain-knowledge.md` §7.*

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-CTX-01 | Ensamblar el `PaqueteDeContexto` **por código**: mismo estado de almacenes y misma semilla producen el mismo paquete | M | **T**, propiedad |
| RF-CTX-02 | Respetar los topes por capa de `architecture.md` §2.1 (5.000 / 10.000 / 20.000 / 15.000 / 20.000 / 10.000 / 10.000 / 10.000) | M | **T** |
| RF-CTX-03 | El recorte es **por capa**: si una se pasa, se recorta esa y no las vecinas, en el orden declarado | M | **T**, propiedad |
| RF-CTX-04 | Las capas **constitucional** e **instrucción** no se recortan nunca | M | **A** más **T** |
| RF-CTX-05 | Si tras recortar no cabe, lanzar `ContextBudgetExceeded`. **Nunca truncar por el final** | M | **T** |
| RF-CTX-06 | Devolver el desglose por capa junto al paquete y persistirlo en `ejecucion` | M | **T** |
| RF-CTX-07 | Recuperación **híbrida en este orden**: filtro estructural → similitud semántica sobre lo ya filtrado → fusión con recencia | M | **T** |
| RF-CTX-08 | Inyectar `MuestraAncla` de prosa aprobada del mismo POV | M | **T** |
| RF-CTX-09 | Colocar lo importante al **principio y al final** | S | **I** |
| RF-CTX-10 | Exponer paquete y desglose para depuración | M | **D** |
| RF-CTX-11 | La reserva del 10 % permanece libre en la primera llamada: el reintento con el defecto añadido debe caber | M | **T** |
| RF-CTX-12 | El paquete se **reconstruye entero** en cada llamada, también en un reintento. Nada se arrastra | M | **A** más **T** |

**Feature `escritura` — el orquestador** — *origen: `architecture.md` §3.*

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-ORQ-01 | El orquestador es **código determinista**, máquina de estados explícita. Ningún agente decide el siguiente paso | M | **A** |
| RF-ORQ-02 | **Topología en estrella**: ningún agente invoca a otro | M | **A** |
| RF-ORQ-03 | Implementar los diez estados y transiciones de `architecture.md` §3.3. **No se salta ningún estado** | M | **T** |
| RF-ORQ-04 | El estado del `trabajo` se persiste tras cada paso, nunca solo en memoria | M | **T** |
| RF-ORQ-05 | Al arrancar, retomar los trabajos no terminales desde su último estado persistido | M | **T** |
| RF-ORQ-06 | Un paso interrumpido se **repite entero**; la idempotencia por `run_id` evita duplicados | M | **T** |
| RF-ORQ-07 | Reparación dirigida con el **defecto concreto y su cita**. Máximo dos; después `ESCALADA` | M | **T** |
| RF-ORQ-08 | Prohibido el reintento genérico: ninguna ruta reintenta sin defecto adjunto | M | **A** |
| RF-ORQ-09 | Tratar cada causa de fallo de `architecture.md` §3.6 con su acción declarada | M | **T**, una por caso |
| RF-ORQ-10 | `ESCALADA` y `FALLIDA` son estados distintos y se cuentan por separado | M | **T** |
| RF-ORQ-11 | Una escena en vuelo por obra; escrituras serializadas con cerrojo por obra, sin confiar en `busy_timeout` | M | **T** de concurrencia |
| RF-ORQ-13 | Reservar presupuesto agregado antes de llamar y liberarlo al responder o fallar, incluso si el paso lanza excepción | M | **T** |
| RF-ORQ-14 | El orquestador **persiste la salida de cada paso y la vuelve a leer** en vez de encadenar objetos en memoria: es lo que hace que reanudar sea idéntico a ejecutar | M | **A** |

**Feature `calidad` — validadores de la v1.** Solo los mecánicos. *Origen: `definitions.md` §8 y §11; `architecture.md` §8.3; el porqué de cada familia, `domain-knowledge.md` §12.*

| ID | Requisito | Defecto | Pr. | Verif. |
| --- | --- | --- | --- | --- |
| RF-CAL-01 | Rechazar la escena sin giro de valor | EST-01 | M | **T** |
| RF-CAL-02 | Rechazar contenido que exceda el `nivel_de_calor` declarado | SEG-01 | M | **T** |
| RF-CAL-03 | Rechazar contenido romántico o sexual con menores de 18, **por esquema** | SEG-01 | M | **T** |
| RF-CAL-04 | Detectar desplazamiento en menos del `tiempo_de_viaje`, o presencia simultánea en dos lugares | CON-01 | M | **T** |
| RF-CAL-05 | Detectar uso de información sin `sabe_desde` de escena anterior | CON-03 | M | **T** |
| RF-CAL-06 | Detectar contradicción de canon; prevalece el hecho de menor `orden_discurso` | CAN-01 | M | **T** |
| RF-CAL-07 | Detectar uso de `Objeto` en estado `perdido`, `roto` o `destruido` sin evento que lo recupere | CON-02 | S | **T** |
| RF-CAL-08 | Emitir cada defecto con **código de la taxonomía y cita del pasaje**. Un defecto sin cita no es reparable | M | **T** |
| RF-CAL-09 | Puerta G1: los defectos de RF-CAL-01 a 07 son **bloqueantes** | M | **T** |
| RF-CAL-10 | Un defecto de calidad **no** es un fallo técnico: produce `REPARANDO`/`ESCALADA`, nunca `FALLIDA` | M | **T** |

**Feature `canon` — memoria de largo plazo** — *origen: `architecture.md` §4; `definitions.md` §4.5 y §7; la corrección sin edición, `domain-knowledge.md` §7.1.*

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-CAN-01 | **Solo el Extractor** escribe memoria de largo plazo, y solo desde `EXTRAYENDO` | M | **A** más **T** |
| RF-CAN-02 | Una escena rechazada **no deja rastro**: ni canon, ni ledger, ni índice | M | **T** |
| RF-CAN-03 | Escribir en una transacción por escena: canon → ledger → resumen → hilos → *embeddings*. O entra todo, o nada | M | **T** |
| RF-CAN-04 | Todo `HechoCanon` cita la `escena_de_origen` | M | **T** |
| RF-CAN-05 | El `Ledger` es *append-only*: ninguna ruta actualiza ni borra un evento | M | **A** más **T** |
| RF-CAN-06 | `EstadoEnT` es **derivado**, con *snapshots* cada N escenas. No es una tabla editable | M | **A** más **T** |
| RF-CAN-07 | Corregir un hecho **no lo edita**: registra uno nuevo que lo sustituye y cita al anterior | M | **T** |
| RF-CAN-08 | Generar resumen de escena al integrarla y de capítulo al cerrarlo | M | **T** |
| RF-CAN-09 | No se compactan nunca la capa constitucional, los hechos de canon ni el ledger | M | **A** |
| RF-CAN-10 | Registrar `Plantado`, `Pago` y `HiloNarrativo` con su estado. La v1 los **registra**; no los audita | S | **T** |
| RF-CAN-11 | Derivar el conocimiento de los `testigos[]` de cada `Evento`: es lo que alimenta RF-CAL-05 | M | **T** |
| RF-CAN-12 | El índice vectorial es **reconstruible entero** desde el texto aprobado | S | **T** |

**Feature `manuscrito`** — *origen: `architecture.md` §11.*

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-MAN-01 | Ensamblar el manuscrito con las versiones vigentes, en `orden_discurso` | M | **T** |
| RF-MAN-02 | Registrar la autoría de cada fragmento: generado, editado o humano | M | **T** |

### Datos

*Origen: `definitions.md` completo; `architecture.md` §3.2 y §5.5; `CLAUDE.md` §2 y §15.*

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RD-01 | El esquema implementa las clases necesarias en la v1: `Obra`, `Parte`, `Capitulo`, `Escena`, `Personaje` (parte fija), `PerfilDeVoz`, `Relacion`, `Lugar`, `Objeto`, `ReglaDeMundo`, `Evento`, `HechoCanon`, `Plantado`, `HiloNarrativo`, `VersionDeTexto`, `Ejecucion`, `Prompt`, y la tabla `trabajo` | M | **A** |
| RD-02 | Nombres de tablas, columnas y enumeraciones **son los de `definitions.md`**: no se traducen, no se abrevian, no se inventan sinónimos | M | **I** más **A** |
| RD-03 | Parte fija y parte móvil del `Personaje` en estructuras separadas | M | **A** |
| RD-04 | `tiempo_historia` y `orden_discurso` son campos distintos en `Escena` | M | **A** |
| RD-05 | Tabla `trabajo` con los campos de `architecture.md` §3.2 | M | **T** |
| RD-06 | Tabla `ejecucion` con el registro completo de RI-14, una fila por llamada | M | **T** |
| RD-07 | Los *embeddings* se guardan de forma legible por **ambas** implementaciones de `VectorStore` | M | **T** en ambos modos |
| RD-08 | Toda migración lleva su revisión de Alembic y **funciona con y sin extensión vectorial** | M | **T** |
| RD-09 | Los identificadores son estables y opacos; no se reutilizan tras un borrado | M | **T** |
| RD-10 | El esquema **no impide** añadir después `Serie`, la auditoría de plantados ni el arco romántico | S | **A** |

### No funcionales

**Presupuesto de contexto** — *origen: `architecture.md` §2.1 y §2.2; `CLAUDE.md` §4.1.*

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RNF-TOK-01 | Ninguna llamada supera los 100.000 tokens | M | **T** |
| RNF-TOK-02 | El contador es una dependencia inyectada, **no** una estimación por caracteres | M | **A** |
| RNF-TOK-03 | El total en vuelo de todas las llamadas simultáneas no supera **100.000** | M | **T** de concurrencia |
| RNF-TOK-04 | Sin hueco agregado, la llamada **espera**; nunca se recorta por carga del sistema | M | **T** |
| RNF-TOK-05 | La espera tiene *timeout*; al vencer, `FALLIDA` con `PresupuestoAgregadoAgotado` | M | **T** |
| RNF-TOK-06 | Nunca se llama al modelo sin haber contado antes los tokens | M | **A** más **T** |

**Rendimiento.** Objetivos propuestos, **no medidos**; confirmarlos es la pregunta abierta 7.

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RNF-REN-01 | El ensamblado de un paquete, sin la llamada al modelo, termina en **menos de 2 s** para una obra de 40 escenas | S | **T** |
| RNF-REN-02 | La derivación del estado en T desde el último *snapshot* termina en **menos de 1 s** | S | **T** |
| RNF-REN-03 | `GET /trabajos/{id}` y `GET /escenas/{id}/contexto` responden en **menos de 300 ms** | S | **T** |
| RNF-REN-04 | La búsqueda por fuerza bruta se mantiene utilizable hasta **10.000 fragmentos**; por encima, se avisa | S | **T** |

**Fiabilidad, observabilidad y seguridad** — *origen: `architecture.md` §3.6, §3.7, §9 y §11; `domain-knowledge.md` §13.*

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RNF-FIA-01 | Una caída no pierde trabajo: se reanuda desde el último estado persistido | M | **T** |
| RNF-FIA-02 | `FalloDeProveedor` se reintenta con espera creciente, hasta 3 veces; después `FALLIDA` | M | **T** |
| RNF-FIA-03 | Ninguna ejecución depende de que la extensión vectorial esté cargada | M | **T** en ambos modos |
| RNF-FIA-04 | Un paso que supera su plazo termina en `FALLIDA` con el paso anotado; no queda colgado | M | **T** |
| RNF-OBS-01 | Métricas: coste por escena, tokens medios por capa, defectos por código, tasa de reintento, escalados por cada cien escenas, latencia por fase, porcentaje de contexto por capa | M | **D** |
| RNF-OBS-02 | Métricas del techo agregado: tokens en vuelo, pico y tiempo de espera por reserva | M | **D** |
| RNF-OBS-03 | La traza es **estructural, no textual**: ni prompts de producción ni fragmentos de manuscrito en los logs por defecto | M | **A** |
| RNF-SEG-01 | Edad mínima y nivel de calor se validan **en esquema**, no solo en el prompt | M | **T** |
| RNF-SEG-02 | Ninguna regla de seguridad depende únicamente del prompt | M | **A** |
| RNF-SEG-03 | Claves de proveedor solo desde entorno | M | **I** |
| RNF-SEG-04 | El repositorio no contiene claves, prompts de producción ni fragmentos de manuscrito | M | **A** más **I** |

---

## Criterios de aceptación

Observables y comprobables: cada uno acabará siendo un test.

- [ ] **CA-1** — Un **capítulo completo** se genera de principio a fin, con todas sus escenas en `INTEGRADA`. *(Demostración)*
- [ ] **CA-2** — La suite pasa **en los dos modos de `VectorStore`**, con y sin extensión cargada.
- [ ] **CA-3** — Se puede matar el proceso en cualquier estado no terminal y el trabajo se reanuda **sin duplicar escrituras**.
- [ ] **CA-4** — Toda regla de dominio marcada «Sí» tiene test, y el test **falla** si se quita la validación.
- [ ] **CA-5** — El desglose por capa **suma lo que dice** y respeta los topes.
- [ ] **CA-6** — Una escena con defecto bloqueante se repara dirigidamente y a la tercera acaba en `ESCALADA`, no en bucle.
- [ ] **CA-7** — Una escena rechazada **no ha dejado rastro** en canon, ledger ni índice.
- [ ] **CA-8** — Con el techo agregado saturado, la llamada nueva **espera**; no se recorta ni se lanza.
- [ ] **CA-9** — `ruff`, `mypy`, `pytest`, `lint-imports` y las migraciones pasan en limpio.

**Sobre CA-4.** No basta con que el test pase. Si se desactiva la validación y el test sigue verde, el test no comprobaba nada. Es la salvaguarda más barata contra una suite que da confianza sin darla.

---

## Reglas de dominio afectadas

Los axiomas de `definitions.md` §11. Las dos diferidas lo están porque **no son comprobables con un solo capítulo**, no porque sean opcionales.

| Regla | Cómo se respeta |
| --- | --- |
| RG-01 · Un personaje solo usa un hecho si existe `sabe_desde` anterior | RF-CAL-05 sobre el conocimiento derivado en RF-CAN-11 |
| RG-02 · Todo `Plantado` de importancia alta tiene `Pago` | **Diferida.** Se registra (RF-CAN-10); se audita en fase 5 |
| RG-03 · Dos `HechoCanon` sobre el mismo atributo no difieren | RF-CAL-06, con arbitraje por `orden_discurso` |
| RG-04 · Nadie está en dos lugares a la vez ni viaja en menos del `tiempo_de_viaje` | RF-CAL-04, contra los `tiempo_de_viaje` de la biblia (RF-OBR-02) |
| RG-05 · Un objeto `perdido`, `roto` o `destruido` no se usa sin recuperarlo | RF-CAL-07 |
| RG-06 · Cada `BeatDeGenero` obligatorio en exactamente una `Escena` | RF-OUT-02, comprobado al generar el outline |
| RG-07 · El arco romántico no se resuelve antes del 90 % | **Diferida.** Requiere manuscrito completo |
| RG-08 · Toda `Escena` tiene un `pov` y un giro de valor no nulo | RF-OUT-03 al planificar y RF-CAL-01 al validar |
| RG-09 · Ningún contenido romántico o sexual con menores de 18 | RF-CAL-03, **por esquema**, sin excepción |
| RG-10 · Ninguna escena excede el `nivel_de_calor` declarado | RF-CAL-02, contra el valor fijado en RF-OBR-01 |

---

## Impacto técnico

**Presupuesto de contexto (`CLAUDE.md` §4.1).** Esta spec no añade capas ni cambia los topes: los implementa por primera vez. La capa que más riesgo tiene de crecer es **canon relevante** (20.000), porque su tamaño depende de cuántos personajes estén presentes; se recorta por personajes mencionados y no presentes, según `architecture.md` §2.1. El techo agregado se estrena aquí, y su consecuencia —el sistema es secuencial por defecto— es lo que hace que la v1 no necesite paralelismo.

**Esquema.** Es la migración inicial: no hay esquema previo que migrar. Debe funcionar **con y sin `sqlite-vec`** (RD-08), lo que obliga a que el almacenamiento de *embeddings* sea legible por las dos implementaciones (RD-07). Las claves de canon no deben asumir una sola obra (RD-10), para no bloquear `Serie`.

**Fronteras (`CLAUDE.md` §5).** Features implicadas: `obra`, `outline`, `escena`, `contexto`, `escritura`, `calidad`, `canon`, `manuscrito`, más `commons/` para orquestación, base de datos, cliente de modelo y errores. **Ninguna necesita cruzar una frontera.** Las convenciones permanentes —`import-linter` que falla la build, `commons/domain/` sin framework, `mypy` estricto, promoción al tercer uso, operaciones largas como trabajo en segundo plano— son de `CLAUDE.md` §5, §6 y §13: aplican, pero no son requisitos de esta spec. Tampoco lo es dónde vive cada pieza de código: eso es el plan.

**Agentes narrativos (`architecture.md` §7).** Intervienen seis de los nueve: **Arquitecto** (biblia y outline), **Planificador** (ficha), **Ensamblador** (paquete, y es código, no modelo), **Escritor** (prosa), **Continuista** (defectos mecánicos) y **Extractor** (memoria). Quedan fuera **Crítico**, **Editor de línea** y **Auditor**.

Cambio en sus contratos: ninguno existía antes, así que todos se definen aquí por primera vez. Lo que sí se fija y no debe relajarse después: el **Escritor no accede a la base de datos**, solo ve el paquete recibido (`architecture.md` §3.5), y el **Extractor es el único que escribe memoria de largo plazo** (RF-CAN-01).

---

## Vocabulario

Términos del dominio usados en esta spec. Todos existen ya en `docs/definitions.md`; **ninguno es nuevo**, así que no hay nada que proponer ni confirmar.

`Obra` · `Parte` · `Capitulo` · `Escena` · `Beat` · `Biblia` · `Brief` · `Outline` · `FichaDeEscena` · `Personaje` · `PerfilDeVoz` · `Relacion` · `Lugar` · `Objeto` · `ReglaDeMundo` · `Evento` · `HechoCanon` · `Plantado` · `Pago` · `Revelacion` · `HiloNarrativo` · `EstadoEnT` · `Ledger` · `PaqueteDeContexto` · `MuestraAncla` · `BeatDeGenero` · `NivelDeCalor` · `Tropo` · `PuertaDeCalidad` · `Defecto` · `Ejecucion` · `VersionDeTexto` · `Prompt` · `Serie`

Atributos citados: `pov` · `lugar` · `presentes[]` · `testigos[]` · `objetivo_del_pov` · `obstaculo` · `valor_entrada` · `valor_salida` · `orden_discurso` · `tiempo_historia` · `tiempo_de_viaje` · `escena_de_origen` · `sabe_desde` · `persona` · `tiempo_verbal` · `esquema_de_pov` · `nivel_de_calor` · `distancia_psiquica` · `densidad_de_dialogo_objetivo` · `extension_objetivo` · `promesa_de_apertura` · `run_id`

Un término que aquí no aparece y conviene no confundir: `trabajo` es una tabla de orquestación (`architecture.md` §3.2), **no** una clase del dominio.

---

## Preguntas abiertas

Mientras quede una sin cerrar, **esta spec no se aprueba**.

- [ ] **1 — Valor de N para los *snapshots* de `EstadoEnT`.** Bloquea RF-CAN-06 y RI-21.
- [ ] **2 — Proveedor y dimensión de los *embeddings*, y si coincide con el de generación.** Bloquea RI-17, RI-20 y RD-07.
- [ ] **3 — *Timeout* de la espera por reserva de presupuesto agregado.** Bloquea RNF-TOK-05 y RI-21.
- [ ] **4 — Plazo por paso antes de `TiempoAgotado`.** Bloquea RF-ORQ-09 y RNF-FIA-04.
- [ ] **5 — Si el nivel de calor se valida por clasificador o por lista de términos.** Bloquea RF-CAL-02.
- [ ] **6 — Formato de la cita del pasaje: desplazamiento de caracteres o identificador de beat.** Bloquea RF-CAL-08 y RI-18.
- [ ] **7 — Confirmar o sustituir los objetivos de rendimiento**, hoy propuestos sin medir. Bloquea RNF-REN-01 a 04.
- [ ] **8 — Si un trabajo `ESCALADA`, tras la edición humana, entra por `EXTRAYENDO` o vuelve a validar.** Bloquea CU-04.

---

## Trazabilidad

Todo requisito nace de un documento anterior. Ninguno es original de esta spec, salvo los objetivos de rendimiento, que están marcados como propuestos.

| Bloque | Origen |
| --- | --- |
| RI-01 a RI-22 | `architecture.md` §3.2, §3.6, §5.4, §9, §11; `CLAUDE.md` §3.5, §4.2, §6 |
| RF-OBR, RF-OUT, RF-ESC | `definitions.md` §4, §6, §9; `domain-knowledge.md` §3, §8 |
| RF-CTX | `definitions.md` §7; `architecture.md` §2.1, §4.2, §4.6; `domain-knowledge.md` §7 |
| RF-ORQ | `architecture.md` §3 |
| RF-CAL | `definitions.md` §8, §11; `architecture.md` §8.3; `domain-knowledge.md` §11, §12 |
| RF-CAN | `architecture.md` §4; `definitions.md` §4.5, §7; `domain-knowledge.md` §7.1 |
| RF-MAN | `architecture.md` §11 |
| RD-01 a RD-10 | `definitions.md` completo; `architecture.md` §3.2, §5.5 |
| RNF-TOK | `architecture.md` §2.1, §2.2; `CLAUDE.md` §4.1 |
| RNF-REN | **Propuesta de esta spec, sin medir** |
| RNF-FIA, RNF-OBS, RNF-SEG | `architecture.md` §3.6, §3.7, §9, §11; `domain-knowledge.md` §13 |
| RG-01 a RG-10 | `definitions.md` §11 |

Lo que `docs/verification.md` clasifica como **U — no verificable** (calidad narrativa, ausencia de fallos semánticos sutiles, comportamiento del modelo entre versiones) **no aparece como requisito**: un requisito que nadie puede comprobar no es un requisito, es un deseo.

---

## Cierre

Se rellena al implementar (`CLAUDE.md` §3.5).

- **Commits:**
- **Documentos actualizados en `docs/`:**
