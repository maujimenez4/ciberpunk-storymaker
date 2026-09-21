# SRS-1 · Especificación de requisitos del backend, versión 1

**Versión:** 2.0 · **Fecha:** 2026-09-21 · **Estado:** propuesta, pendiente de aprobación
**Ámbito:** backend. El frontend queda fuera de este documento.

---

## 1. Introducción

### 1.1 Propósito

Especifica **qué debe hacer la primera versión del backend** para que sea construible y verificable sin volver a discutir el diseño. No describe cómo se construye —eso es `docs/architecture.md`—, ni qué significa cada término —eso es `docs/definitions.md`—, ni por qué el dominio funciona así —eso es `docs/domain-knowledge.md`.

Destinatario: quien implemente el backend y quien lo revise.

### 1.2 Alcance de la versión 1

El objetivo es el de la fase 1 de la hoja de ruta (`architecture.md` §13): **un capítulo coherente**. Es decir, el ciclo completo de una escena, de principio a fin, con la memoria cerrándose sobre sí misma.

| Capacidad | v1 | Motivo |
| --- | --- | --- |
| Obra desde un brief, biblia y outline | **Sí** | Sin outline no hay ficha de escena |
| Planificar, ensamblar, escribir e integrar una escena | **Sí** | Es el bucle completo; sin él no hay producto |
| Presupuesto por capa y techo agregado | **Sí** | Restricción no negociable (`CLAUDE.md` §4.1) |
| Orquestador con estado persistido y reanudación | **Sí** | Sin él, una caída pierde trabajo y nada se puede depurar |
| Memoria de largo plazo: canon, ledger, resúmenes, índice | **Sí** | Es lo que cierra el bucle entre escenas |
| Validadores **mecánicos** | **Sí** | Son los que se cuentan, no los que se juzgan (`domain-knowledge.md` §11) |
| Validadores de **juicio**: Crítico con rúbrica | **No** | Fase 4; requiere escenas etiquetadas por un editor |
| Editor de línea | **No** | Introduce una segunda escritura sobre texto aprobado |
| Auditoría de manuscrito y curva de temperatura | **No** | Fase 5; no tiene sentido con un capítulo |
| `Serie` y canon compartido entre obras | **No** | Se decide al empezar una segunda obra |

Detalle y motivos en §11. La exclusión no es «se hará mal»: es «no se hará», y el esquema de datos no debe impedirlo después.

### 1.3 Vocabulario

**Este documento no define ningún término del dominio.** Los que aparecen en `PascalCase` o `snake_case` están en `docs/definitions.md`, que es la fuente de verdad. Si un requisito de aquí contradice una definición de allí, **gana `definitions.md`** y el requisito es defectuoso.

### 1.4 Documentos de referencia

| Documento | Qué aporta a esta especificación |
| --- | --- |
| `docs/definitions.md` | Ontología, atributos, cardinalidades, los diez axiomas y los árboles de la §14 |
| `docs/architecture.md` | Estructura del código, orquestación, memoria, presupuestos, rutas |
| `docs/domain-knowledge.md` | **El porqué narrativo** de las reglas: qué hace que una escena funcione y por qué un defecto lo es |
| `docs/verification.md` | Métodos de verificación y clasificación T/A/I/D/U |
| `CLAUDE.md` | Requisitos no negociables, convenciones y reglas de dominio |

### 1.5 Convenciones

| Prefijo | Tipo |
| --- | --- |
| `CU-` | Caso de uso |
| `RI-` | Interfaz externa |
| `RF-` | Funcional |
| `RD-` | Datos y persistencia |
| `RNF-` | No funcional |
| `RG-` | Regla de dominio |

**Prioridad:** `M` imprescindible para la v1 —si falta, no se cumple un criterio de aceptación del §9— y `S` necesario pero degradable sin invalidar la entrega.

**Verificación:** clasificación T/A/I/D/U de `docs/verification.md` — **T** prueba, **A** análisis, **I** inspección, **D** demostración, **U** no verificable.

**Origen:** todo requisito cita de dónde sale. Un requisito sin origen es una invención y se rechaza en revisión.

Las palabras **debe**, **no debe** y **puede** se usan en sentido normativo. «Debe» no admite excepción de implementación.

---

## 2. Descripción general

### 2.1 Perspectiva del producto

El backend es un servicio que orquesta llamadas al modelo, ensambla contexto de forma determinista, valida el resultado y persiste en SQLite. No tiene interfaz propia: se consume por API REST con OpenAPI como contrato.

La pieza que lo distingue de un envoltorio de API no es la generación, es el **ensamblado determinista**: seleccionar, de una novela que no cabe, exactamente lo que hace falta para escribir la escena siguiente, y poder demostrar después qué se envió.

### 2.2 Actores

| Actor | Qué hace |
| --- | --- |
| Autor / editor | Crea la obra, lanza la generación, revisa, aprueba o resuelve escalados |
| Frontend (SPA) | Cliente de la API; no contiene lógica de dominio |
| Proveedor de modelo | Servicio externo de generación, tras una interfaz inyectada |
| Proveedor de *embeddings* | Servicio de vectorización; puede ser el mismo |

### 2.3 Funciones principales

1. Crear una obra y fijar sus parámetros de discurso.
2. Generar biblia y outline con cobertura de hitos de género.
3. Planificar, ensamblar, escribir, validar, reparar e integrar una escena.
4. Mantener la memoria de largo plazo y derivar el estado en T.
5. Presupuestar y acotar el consumo de contexto, por llamada y agregado.
6. Exponer el estado de los trabajos y el contexto enviado, para depuración.

### 2.4 Restricciones no negociables

Heredadas de `CLAUDE.md` §4. No se replantean aquí.

| Restricción | Consecuencia para la v1 |
| --- | --- |
| FastAPI, Python 3.12+, Pydantic v2, async por defecto | El contrato es el OpenAPI generado, no un documento aparte |
| Límite duro de 100.000 tokens por llamada | Contador inyectado y fallo explícito antes de llamar |
| Techo agregado de 100.000 tokens en vuelo | El sistema es secuencial por defecto (`architecture.md` §2.2) |
| SQLite, con o sin extensión vectorial | Todo el código funciona en ambos modos, y se prueba en los dos |
| Organización por feature + `commons` | Ninguna funcionalidad es un fichero suelto en carpeta global |

### 2.5 Supuestos y dependencias

1. Hay un proveedor de modelo accesible, con clave en variable de entorno.
2. Hay un proveedor de *embeddings*. Su consumo **no** cuenta contra el presupuesto de contexto.
3. El modo de referencia es local: un fichero SQLite por obra (`architecture.md` §10).
4. Hay un editor humano para resolver los escalados. Sin él, un trabajo en `ESCALADA` se queda ahí.
5. El brief lo aporta una persona; la v1 no lo genera ni lo juzga.

---

## 3. Casos de uso

Precondiciones y postcondiciones incluidas: son lo que hace verificable un caso de uso.

### CU-01 · Arrancar una obra

- **Actor:** autor. **Precondición:** ninguna.
- **Flujo:** envía un brief → se crea la `Obra` con sus parámetros de discurso → se lanza la generación de la `Biblia` como trabajo.
- **Postcondición:** existe una obra con `persona`, `tiempo_verbal`, `esquema_de_pov` y `nivel_de_calor` fijados, y una biblia versionada.
- **Requisitos:** RI-01, RI-02, RF-OBR-01 a 04.

### CU-02 · Generar el outline

- **Precondición:** existe biblia vigente.
- **Flujo:** se lanza el outline → se produce `Parte → Capitulo → Escena` → cada hito obligatorio de género se asigna a exactamente una escena.
- **Postcondición:** cada escena del outline tiene `pov`, `lugar`, objetivo, obstáculo y giro de valor previsto.
- **Excepción:** si un hito obligatorio queda sin escena o duplicado, el trabajo termina en `FALLIDA` con `ReglaDeDominioViolada`.
- **Requisitos:** RI-03, RF-OUT-01 a 04, RG-06.

### CU-03 · Escribir una escena *(caso central)*

- **Precondición:** la escena existe en el outline y la anterior está `INTEGRADA`.
- **Flujo principal:**
  1. `PLANIFICANDO` — se produce la `FichaDeEscena` a partir del outline y del estado en T.
  2. `ENSAMBLANDO` — se construye el paquete, se presupuesta y se recorta por capa.
  3. `ESCRIBIENDO` — se reserva presupuesto agregado, se llama al modelo, se guarda la versión.
  4. `VALIDANDO` — se pasan los validadores mecánicos.
  5. `EXTRAYENDO` — se escriben canon, ledger, resumen, hilos e índice en una transacción.
  6. `INTEGRADA`.
- **Flujos alternativos:**
  - *Defecto bloqueante* → `REPARANDO` con el defecto y su cita → vuelve a 3. Máximo dos veces; después `ESCALADA`.
  - *El paquete no cabe tras recortar* → `FALLIDA` con `ContextBudgetExceeded`, **sin llamar al modelo**.
  - *No hay hueco agregado antes del timeout* → `FALLIDA` con `PresupuestoAgregadoAgotado`, sin coste.
  - *Cancelación del autor* → `CANCELADA` en el primer punto seguro.
- **Postcondición de éxito:** la escena está en el manuscrito y la memoria de largo plazo la incluye.
- **Postcondición de fracaso:** **la memoria de largo plazo no ha cambiado** (RF-CAN-02).
- **Requisitos:** RI-05, RI-09, RF-ESC-*, RF-CTX-*, RF-ORQ-*, RF-CAL-*, RF-CAN-*.

### CU-04 · Resolver un escalado

- **Precondición:** un trabajo en `ESCALADA`.
- **Flujo:** el autor consulta el defecto con su cita, edita o acepta el texto → se crea versión nueva y se marca vigente → se reanuda desde `EXTRAYENDO`.
- **Postcondición:** la escena queda `INTEGRADA` o `CANCELADA`, nunca indefinidamente en `ESCALADA`.
- **Requisitos:** RI-07, RI-09, RF-ESC-03, RF-ESC-04.

### CU-05 · Inspeccionar el contexto enviado

- **Precondición:** existe al menos una ejecución para la escena.
- **Flujo:** se consulta el paquete y su desglose por capa.
- **Postcondición:** el desglose suma lo que dice y respeta los topes.
- **Requisitos:** RI-06, RF-CTX-06, RF-CTX-10.

### CU-06 · Reanudar tras una caída

- **Precondición:** el proceso se detiene con trabajos en estado no terminal.
- **Flujo:** al arrancar, se leen los trabajos vivos y se repite entero el paso interrumpido.
- **Postcondición:** ninguna escritura duplicada; el trabajo avanza o falla, pero no queda colgado.
- **Requisitos:** RF-ORQ-04 a 06, RNF-FIA-01.

---

## 4. Requisitos de interfaces externas

### 4.1 API REST

Identificadores opacos para el cliente. Toda operación larga devuelve un `trabajo` y **no** bloquea la petición.

| ID | Método y ruta | Entrada esencial | Salida | Pr. | v1 |
| --- | --- | --- | --- | --- | --- |
| RI-01 | `POST /obras` | `Brief`: género, subgénero, tropo, tono, extensión objetivo, parámetros de discurso | 201 + `obra` | M | Sí |
| RI-02 | `POST /obras/{id}/biblia` | — | 202 + `trabajo` | M | Sí |
| RI-03 | `POST /obras/{id}/outline` | — | 202 + `trabajo` | M | Sí |
| RI-04 | `POST /escenas/{id}/planificar` | — | 202 + `trabajo` | M | Sí |
| RI-05 | `POST /escenas/{id}/escribir` | — | 202 + `trabajo` | M | Sí |
| RI-06 | `GET /escenas/{id}/contexto` | — | 200 + paquete y desglose por capa | M | Sí |
| RI-07 | `GET /escenas/{id}/versiones` | — | 200 + historial inmutable, con la vigente marcada | M | Sí |
| RI-08 | `GET /obras/{id}/canon` | filtros: entidad, atributo | 200 + hechos con `escena_de_origen` | S | Sí |
| RI-09 | `GET /trabajos/{id}` | — | 200 + `estado`, `intento`, `causa_fallo`, defectos | M | Sí |
| RI-10 | `POST /obras/{id}/auditoria` | — | — | — | **No** |

**RI-18 · Contrato de `trabajo`.** La respuesta de RI-09 expone, como mínimo: `id`, `tipo`, `estado` (uno de los diez de `architecture.md` §3.3), `intento`, `causa_fallo` cuando procede, `creado_en`, `actualizado_en` y, en `ESCALADA`, la lista de defectos con **código y cita**. *Origen: `architecture.md` §3.2. Pr. M. Verificación: **T**.*

**RI-19 · Cancelación.** Debe existir forma de cancelar un trabajo en curso; el efecto es `CANCELADA` en el primer punto seguro, nunca a mitad de una escritura. *Origen: `architecture.md` §3.6. Pr. S. Verificación: **T**.*

### 4.2 Errores

**RI-11.** Ningún servicio lanza `HTTPException`. Las excepciones de dominio las traduce el handler central de `commons/errors/`.

| Excepción de dominio | HTTP | Cuerpo |
| --- | --- | --- |
| `ContextBudgetExceeded` | 422 | Capa que desbordó y desglose |
| `PresupuestoAgregadoAgotado` | 503 | Tiempo esperado; relanzable sin coste |
| `ReglaDeDominioViolada` | 422 | Axioma incumplido, por su número del §8 |
| `RecursoNoEncontrado` | 404 | — |
| `FalloDeProveedor` tras agotar reintentos | 502 | Número de intentos consumidos |

*Origen: `architecture.md` §5.4 y §3.6; `CLAUDE.md` §6. Pr. M. Verificación: **T**, un test por fila.*

**RI-12.** Modelos de entrada y de salida distintos; ninguno expone el modelo de base de datos. *Origen: `CLAUDE.md` §6. Pr. M. Verificación: **A**.*

### 4.3 Proveedores externos

**RI-13.** Cliente de modelo, contador de tokens y reloj se inyectan por `Depends()`. Ninguna prueba llama al proveedor real: se usa un doble con respuestas fijas. *Origen: `CLAUDE.md` §3.5 y §6. Pr. M. Verificación: **A** más **T**.*

**RI-14.** Toda llamada registra `run_id`, escena, versión de prompt, versión de biblia, IDs recuperados, modelo, parámetros, semilla, tokens por capa, coste y veredicto. *Origen: `architecture.md` §9. Pr. M. Verificación: **T**.*

**RI-15.** Las claves se leen de entorno. Nunca del repositorio ni de la base de datos. *Origen: `architecture.md` §11. Pr. M. Verificación: **I** más **A**.*

**RI-20.** El proveedor de *embeddings* está tras una interfaz propia, distinta de la del modelo de generación, y su consumo no cuenta contra ningún presupuesto de contexto. *Origen: `architecture.md` §2.2 y §3.8. Pr. M. Verificación: **A**.*

### 4.4 Persistencia

**RI-16.** SQLite con `WAL`, `foreign_keys=ON` y `busy_timeout` configurado. Migraciones con Alembic desde el primer commit. *Origen: `CLAUDE.md` §4.2. Pr. M. Verificación: **T** al abrir conexión.*

**RI-17.** La búsqueda semántica vive tras `VectorStore`, con `SqliteVecStore` y `BruteForceStore` (NumPy sobre *embeddings* en BLOB). En arranque se detecta la extensión; si no carga, se degrada y se registra un aviso. **El sistema nunca falla por falta de extensión vectorial.** *Origen: `CLAUDE.md` §4.2. Pr. M. Verificación: **T**, y la suite entera en los dos modos.*

### 4.5 Configuración y arranque

**RI-21.** Toda la configuración se lee de entorno con valores por defecto explícitos, y el arranque **falla de inmediato** si falta un valor obligatorio. Parámetros mínimos: clave y punto de acceso del proveedor, modelo por defecto, techo agregado de tokens, *timeout* de reserva, plazo por paso, N de los *snapshots*, dimensión de los *embeddings* y ruta del fichero de la obra. *Origen: `architecture.md` §2.2, §3.6 y §4.3; `CLAUDE.md` §5.1. Pr. M. Verificación: **T**.*

**RI-22.** El arranque registra, una vez, qué implementación de `VectorStore` quedó activa. *Origen: `CLAUDE.md` §4.2. Pr. M. Verificación: **T**.*

---

## 5. Requisitos funcionales

Por feature (`architecture.md` §5.1). Ningún requisito cruza una frontera sin pasar por el `__init__.py` de la otra feature.

### 5.1 Feature `obra`

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-OBR-01 | Crear una `Obra` desde un `Brief`, fijando `persona`, `tiempo_verbal`, `esquema_de_pov` y `nivel_de_calor`, que heredan todas sus escenas | M | **T** |
| RF-OBR-02 | Generar la `Biblia`: personajes con parte fija, lugares con `tiempo_de_viaje`, reglas de mundo, tropo y `promesa_de_apertura` | M | **T** |
| RF-OBR-03 | La biblia es **versionada**: cambiarla crea versión nueva de obra, no se edita en sitio | M | **T** |
| RF-OBR-04 | Registrar el catálogo de temas sensibles declarados | S | **T** |

*Origen: `definitions.md` §4.1, §4.3, §9 y §12.*

### 5.2 Feature `outline`

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-OUT-01 | Generar el `Outline` jerárquico `Parte → Capitulo → Escena` | M | **T** |
| RF-OUT-02 | Asignar cada `BeatDeGenero` obligatorio a **exactamente una** `Escena`, dentro de su franja | M | **T**, RG-06 |
| RF-OUT-03 | Cada `Escena` nace con `pov`, `lugar`, `objetivo_del_pov`, `obstaculo` y giro previsto (`valor_entrada` ≠ `valor_salida`) | M | **T**, RG-08 |
| RF-OUT-04 | El outline de la v1 cubre al menos un capítulo completo; no se exige la novela entera | M | **D** |
| RF-OUT-05 | Respetar el orden de los hitos: un hito no puede asignarse a una escena anterior a la del hito que lo precede | S | **T** |

*Origen: `definitions.md` §4.1 y §6; el porqué del orden, `domain-knowledge.md` §8.1.*

### 5.3 Feature `escena`

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-ESC-01 | Producir la `FichaDeEscena` desde el outline y el estado en T | M | **T** |
| RF-ESC-02 | La ficha declara las restricciones duras: `pov`, `presentes[]`, `lugar`, `distancia_psiquica`, `densidad_de_dialogo_objetivo`, `extension_objetivo` y el `nivel_de_calor` heredado | M | **T** |
| RF-ESC-03 | Guardar cada `VersionDeTexto` como **inmutable**, con su `run_id` y una sola versión `vigente` | M | **T** |
| RF-ESC-04 | Editar **crea versión nueva** y marca la vigente. No existe ruta de código que modifique texto en sitio | M | **A** más **T** |
| RF-ESC-05 | Los dos relojes son campos distintos: `tiempo_historia` y `orden_discurso`. La coherencia se calcula por el primero | M | **A** más **T** |

*Origen: `definitions.md` §4.1, §4.4 y §9; `CLAUDE.md` §14. El porqué de los dos relojes, `domain-knowledge.md` §3.1.*

### 5.4 Feature `contexto`

El corazón de la v1, y el único componente cuyo fallo es silencioso si no se mide.

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
| RF-CTX-10 | Exponer paquete y desglose para depuración (RI-06) | M | **D** |
| RF-CTX-11 | La reserva del 10 % permanece libre en la primera llamada: el reintento con el defecto añadido debe caber | M | **T** |
| RF-CTX-12 | El paquete se **reconstruye entero** en cada llamada, también en un reintento. Nada se arrastra de la llamada anterior | M | **A** más **T** |

*Origen: `definitions.md` §7; `architecture.md` §2.1, §4.2 y §4.6. El porqué del orden de recuperación, `domain-knowledge.md` §7.*

### 5.5 Feature `escritura` — el orquestador

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-ORQ-01 | El orquestador es **código determinista**, máquina de estados explícita. Ningún agente decide el siguiente paso | M | **A** |
| RF-ORQ-02 | **Topología en estrella**: ningún agente invoca a otro | M | **A** |
| RF-ORQ-03 | Implementar los diez estados y las transiciones de `architecture.md` §3.3. **No se salta ningún estado** | M | **T** |
| RF-ORQ-04 | El estado del `trabajo` se persiste tras cada paso, nunca solo en memoria | M | **T** |
| RF-ORQ-05 | Al arrancar, retomar los trabajos no terminales desde su último estado persistido | M | **T** |
| RF-ORQ-06 | Un paso interrumpido se **repite entero**; la idempotencia por `run_id` evita duplicados | M | **T** |
| RF-ORQ-07 | Reparación dirigida con el **defecto concreto y su cita**. Máximo dos; después `ESCALADA` | M | **T** |
| RF-ORQ-08 | Prohibido el reintento genérico: no existe ruta que reintente sin defecto adjunto | M | **A** |
| RF-ORQ-09 | Tratar cada causa de fallo de `architecture.md` §3.6 con su acción declarada | M | **T**, una por fila |
| RF-ORQ-10 | `ESCALADA` y `FALLIDA` son estados distintos y se cuentan por separado | M | **T** |
| RF-ORQ-11 | Una escena en vuelo por obra; escrituras serializadas con cerrojo por obra, sin confiar en `busy_timeout` | M | **T** de concurrencia |
| RF-ORQ-12 | El `router.py` solo crea el trabajo y consulta su estado | M | **A** |
| RF-ORQ-13 | Reservar presupuesto agregado antes de llamar y liberarlo al responder o fallar, incluso si el paso lanza excepción | M | **T** |
| RF-ORQ-14 | Cada paso recibe y devuelve un modelo Pydantic; el orquestador **persiste la salida y la vuelve a leer** en vez de pasar objetos vivos | M | **A** |

*Origen: `architecture.md` §3.*

### 5.6 Feature `calidad` — validadores de la v1

Solo los **mecánicos**: los de la columna izquierda de `domain-knowledge.md` §11. Los de juicio quedan fuera (§11 de este documento).

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

*Origen: `definitions.md` §8 y §11; `architecture.md` §8.3. El porqué de cada familia, `domain-knowledge.md` §12.*

### 5.7 Feature `canon` — memoria de largo plazo

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-CAN-01 | **Solo el Extractor** escribe memoria de largo plazo, y solo desde `EXTRAYENDO` | M | **A** más **T** |
| RF-CAN-02 | Una escena rechazada **no deja rastro**: ni canon, ni ledger, ni índice | M | **T** |
| RF-CAN-03 | Escribir en una transacción por escena: canon → ledger → resumen → hilos → *embeddings*. O entra todo, o nada | M | **T** |
| RF-CAN-04 | Todo `HechoCanon` cita la `escena_de_origen` | M | **T** |
| RF-CAN-05 | El `Ledger` es *append-only*: no existe ruta que actualice ni borre un evento | M | **A** más **T** |
| RF-CAN-06 | `EstadoEnT` es **derivado**, con *snapshots* cada N escenas. No es una tabla editable | M | **A** más **T** |
| RF-CAN-07 | Corregir un hecho **no lo edita**: registra uno nuevo que lo sustituye y cita al anterior | M | **T** |
| RF-CAN-08 | Generar resumen de escena al integrarla y de capítulo al cerrarlo | M | **T** |
| RF-CAN-09 | No se compactan nunca la capa constitucional, los hechos de canon ni el ledger | M | **A** |
| RF-CAN-10 | Registrar `Plantado`, `Pago` y `HiloNarrativo` con su estado. La v1 los **registra**; no los audita | S | **T** |
| RF-CAN-11 | Derivar el conocimiento de los `testigos[]` de cada `Evento`: es lo que alimenta RF-CAL-05 | M | **T** |
| RF-CAN-12 | El índice vectorial es **reconstruible entero** desde el texto aprobado | S | **T** |

*Origen: `architecture.md` §4; `definitions.md` §4.5 y §7. El porqué de la corrección sin edición, `domain-knowledge.md` §7.1.*

### 5.8 Feature `manuscrito`

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RF-MAN-01 | Ensamblar el manuscrito con las versiones vigentes, en `orden_discurso` | M | **T** |
| RF-MAN-02 | Registrar la autoría de cada fragmento: generado, editado o humano | M | **T** |

*Origen: `architecture.md` §11.*

---

## 6. Requisitos de datos

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RD-01 | El esquema implementa las clases de `definitions.md` necesarias en la v1: `Obra`, `Parte`, `Capitulo`, `Escena`, `Personaje` (parte fija), `PerfilDeVoz`, `Relacion`, `Lugar`, `Objeto`, `ReglaDeMundo`, `Evento`, `HechoCanon`, `Plantado`, `HiloNarrativo`, `VersionDeTexto`, `Ejecucion`, `Prompt`, y la tabla `trabajo` | M | **A** |
| RD-02 | Nombres de tablas, columnas y enumeraciones **son los de `definitions.md`**: no se traducen, no se abrevian, no se inventan sinónimos | M | **I** más **A** |
| RD-03 | Parte fija y parte móvil del `Personaje` en estructuras separadas | M | **A** |
| RD-04 | `tiempo_historia` y `orden_discurso` son campos distintos en `Escena` | M | **A** |
| RD-05 | Tabla `trabajo` con los campos de `architecture.md` §3.2 | M | **T** |
| RD-06 | Tabla `ejecucion` con el registro completo de RI-14, una fila por llamada | M | **T** |
| RD-07 | Los *embeddings* se guardan de forma legible por **ambas** implementaciones de `VectorStore` | M | **T** en los dos modos |
| RD-08 | Toda migración lleva su revisión de Alembic y **funciona con y sin extensión vectorial** | M | **T** |
| RD-09 | Los identificadores son estables y opacos; no se reutilizan tras un borrado | M | **T** |
| RD-10 | El esquema **no impide** añadir después `Serie`, la auditoría de plantados ni el arco romántico: las claves de canon no asumen una sola obra | S | **A** |

*Origen: `definitions.md` completo; `architecture.md` §3.2 y §5.5; `CLAUDE.md` §2 y §15.*

---

## 7. Requisitos no funcionales

### 7.1 Presupuesto de contexto

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RNF-TOK-01 | Ninguna llamada supera los 100.000 tokens | M | **T** |
| RNF-TOK-02 | El contador es una dependencia inyectada, **no** una estimación por caracteres | M | **A** |
| RNF-TOK-03 | El total en vuelo de todas las llamadas simultáneas no supera **100.000** | M | **T** de concurrencia |
| RNF-TOK-04 | Sin hueco agregado, la llamada **espera**; nunca se recorta por carga del sistema | M | **T** |
| RNF-TOK-05 | La espera tiene *timeout*; al vencer, `FALLIDA` con `PresupuestoAgregadoAgotado` | M | **T** |
| RNF-TOK-06 | Nunca se llama al modelo sin haber contado antes los tokens | M | **A** más **T** |

*Origen: `architecture.md` §2.1 y §2.2; `CLAUDE.md` §4.1.*

### 7.2 Rendimiento

> **Provisional.** Estos valores son objetivos de ingeniería propuestos, no medidos. Confirmarlos o sustituirlos es la cuestión abierta 7 del §12.

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RNF-REN-01 | El ensamblado de un paquete, sin contar la llamada al modelo, termina en **menos de 2 s** para una obra de 40 escenas | S | **T** |
| RNF-REN-02 | La derivación del estado en T desde el último *snapshot* termina en **menos de 1 s** | S | **T** |
| RNF-REN-03 | `GET /trabajos/{id}` y `GET /escenas/{id}/contexto` responden en **menos de 300 ms** | S | **T** |
| RNF-REN-04 | La búsqueda por fuerza bruta se mantiene utilizable hasta **10.000 fragmentos**; por encima, se registra un aviso | S | **T** |

RNF-REN-04 recoge un riesgo ya abierto en `architecture.md` §12: el modo degradado deja de ser viable a partir de cierto tamaño de índice, y conviene saber cuándo.

### 7.3 Fiabilidad

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RNF-FIA-01 | Una caída no pierde trabajo: se reanuda desde el último estado persistido | M | **T** |
| RNF-FIA-02 | `FalloDeProveedor` se reintenta con espera creciente, hasta 3 veces; después `FALLIDA` | M | **T** |
| RNF-FIA-03 | Ninguna ejecución depende de que la extensión vectorial esté cargada | M | **T** en ambos modos |
| RNF-FIA-04 | Un paso que supera su plazo termina en `FALLIDA` con el paso anotado; no queda colgado | M | **T** |

### 7.4 Observabilidad

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RNF-OBS-01 | Métricas: coste por escena, tokens medios por capa, defectos por código, tasa de reintento, escalados por cada cien escenas, latencia por fase, porcentaje de contexto por capa | M | **D** |
| RNF-OBS-02 | Métricas del techo agregado: tokens en vuelo, pico y tiempo de espera por reserva | M | **D** |
| RNF-OBS-03 | La traza es **estructural, no textual**: ni prompts de producción ni fragmentos de manuscrito en los logs por defecto | M | **A** |

*Origen: `architecture.md` §9 y §11.*

### 7.5 Seguridad y cumplimiento

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RNF-SEG-01 | Edad mínima y nivel de calor se validan **en esquema**, no solo en el prompt | M | **T** |
| RNF-SEG-02 | Ninguna regla de seguridad depende únicamente del prompt | M | **A** |
| RNF-SEG-03 | Claves de proveedor solo desde entorno | M | **I** |
| RNF-SEG-04 | El repositorio no contiene claves, prompts de producción ni fragmentos de manuscrito | M | **A** más **I** |

*Origen: `architecture.md` §11; `domain-knowledge.md` §13.*

### 7.6 Mantenibilidad

| ID | Requisito | Pr. | Verif. |
| --- | --- | --- | --- |
| RNF-MAN-01 | Las fronteras entre features se comprueban con `import-linter` y **fallan la build** | M | **A** |
| RNF-MAN-02 | `commons/domain/` no importa FastAPI, SQLAlchemy ni clientes HTTP, y se prueba sin base de datos | M | **A** más **T** |
| RNF-MAN-03 | `mypy` estricto sobre `commons/domain/` y los `service.py` | M | **A** |
| RNF-MAN-04 | Código repetido: se duplica primero; sube a `commons/` al tercer uso real | S | **I** |
| RNF-MAN-05 | Toda operación larga es un trabajo en segundo plano con estado consultable | M | **A** |

*Origen: `CLAUDE.md` §5.1, §6 y §13.*

---

## 8. Reglas de dominio

Los axiomas de `definitions.md` §11. Cada uno comprobable mecánicamente, y cada uno con su test.

| ID | Regla | v1 | Implementada por |
| --- | --- | --- | --- |
| RG-01 | Un personaje solo usa un hecho si existe `sabe_desde` de escena anterior | Sí | RF-CAL-05, RF-CAN-11 |
| RG-02 | Todo `Plantado` de importancia alta tiene `Pago` antes del final | **No** | Se registra (RF-CAN-10); se audita en fase 5 |
| RG-03 | Dos `HechoCanon` sobre el mismo atributo no difieren | Sí | RF-CAL-06 |
| RG-04 | Nadie está en dos lugares a la vez ni viaja en menos del `tiempo_de_viaje` | Sí | RF-CAL-04 |
| RG-05 | Un objeto `perdido`, `roto` o `destruido` no se usa sin evento que lo recupere | Sí | RF-CAL-07 |
| RG-06 | Cada `BeatDeGenero` obligatorio se asigna a exactamente una `Escena` | Sí | RF-OUT-02 |
| RG-07 | El arco romántico no se resuelve antes del 90 % del manuscrito | **No** | Requiere manuscrito completo |
| RG-08 | Toda `Escena` tiene un `pov` y un giro de valor no nulo | Sí | RF-OUT-03, RF-CAL-01 |
| RG-09 | Ningún contenido romántico o sexual con menores de 18 años | Sí | RF-CAL-03, sin excepción |
| RG-10 | Ninguna escena excede el `nivel_de_calor` declarado | Sí | RF-CAL-02 |

Las dos diferidas lo están porque **no son comprobables con un solo capítulo**, no porque sean opcionales. El esquema debe permitir comprobarlas después sin migración destructiva (RD-10).

---

## 9. Criterios de aceptación

### 9.1 De la entrega

La v1 está terminada cuando, y solo cuando:

| # | Criterio | Método |
| --- | --- | --- |
| CA-01 | Un **capítulo completo** se genera de principio a fin, con todas sus escenas en `INTEGRADA` | **D** |
| CA-02 | La suite pasa **en los dos modos de `VectorStore`** | **T** |
| CA-03 | Se puede matar el proceso en cualquier estado no terminal y el trabajo se reanuda sin duplicar escrituras | **T** |
| CA-04 | Toda regla del §8 marcada «Sí» tiene test, y el test **falla** si se quita la validación | **T** |
| CA-05 | El desglose por capa **suma lo que dice** y respeta los topes | **T** |
| CA-06 | Una escena con defecto bloqueante se repara dirigidamente y a la tercera acaba en `ESCALADA`, no en bucle | **T** |
| CA-07 | Una escena rechazada no ha dejado rastro en canon, ledger ni índice | **T** |
| CA-08 | Con el techo agregado saturado, la llamada nueva **espera**; no se recorta ni se lanza | **T** |
| CA-09 | `ruff`, `mypy`, `pytest`, `lint-imports` y las migraciones pasan en limpio | **T** |

### 9.2 Prueba de que los tests sirven

CA-04 exige algo que conviene subrayar: **no basta con que el test pase**. Si se desactiva la validación y el test sigue verde, el test no comprobaba nada. Es la única salvaguarda barata contra una suite que da confianza sin darla.

---

## 10. Trazabilidad

Todo requisito nace de un documento anterior. Ninguno es original de aquí.

| Bloque | Origen | Caso de uso |
| --- | --- | --- |
| RI-01 a RI-22 | `architecture.md` §3.2, §3.6, §5.4, §9, §11; `CLAUDE.md` §3.5, §4.2, §6 | CU-01 a CU-06 |
| RF-OBR, RF-OUT, RF-ESC | `definitions.md` §4, §6, §9; `domain-knowledge.md` §3, §8 | CU-01, CU-02, CU-04 |
| RF-CTX | `definitions.md` §7; `architecture.md` §2.1, §4.2, §4.6; `domain-knowledge.md` §7 | CU-03, CU-05 |
| RF-ORQ | `architecture.md` §3 | CU-03, CU-06 |
| RF-CAL | `definitions.md` §8, §11; `architecture.md` §8.3; `domain-knowledge.md` §11, §12 | CU-03 |
| RF-CAN | `architecture.md` §4; `definitions.md` §4.5, §7; `domain-knowledge.md` §7.1 | CU-03 |
| RF-MAN | `architecture.md` §11 | CU-03 |
| RD-01 a RD-10 | `definitions.md` completo; `architecture.md` §3.2, §5.5 | — |
| RNF-TOK | `architecture.md` §2.1, §2.2; `CLAUDE.md` §4.1 | CU-03 |
| RNF-REN | Propuesta de este documento, **sin medir** | — |
| RNF-FIA, RNF-OBS, RNF-SEG, RNF-MAN | `architecture.md` §3.6, §3.7, §9, §11; `CLAUDE.md` §5.1, §6, §13 | CU-06 |
| RG-01 a RG-10 | `definitions.md` §11 | CU-02, CU-03 |

Lo que `docs/verification.md` clasifica como **U — no verificable** (calidad narrativa, ausencia de fallos semánticos sutiles, comportamiento del modelo entre versiones) **no aparece como requisito**: un requisito que nadie puede comprobar no es un requisito, es un deseo.

---

## 11. Fuera del alcance de la v1

| Excluido | Motivo | Cuándo |
| --- | --- | --- |
| Crítico con rúbrica y juez calibrado | Necesita escenas etiquetadas por un editor; sin calibrar, estorba | Fase 4 |
| Métricas de prosa: repetición, tics, variedad sintáctica, deriva de estilo | Son umbrales, no bloqueantes; sin corpus aprobado no hay referencia | Fase 4 |
| Editor de línea | Introduce una segunda escritura sobre texto ya aprobado | Fase 6 |
| Auditoría de manuscrito: hitos, plantados, curva de temperatura | No tiene sentido con un capítulo | Fase 5 |
| Puertas G2 (capítulo) y G3 (manuscrito) | Mismo motivo | Fases 4–5 |
| Validación de voz: distancia a muestras ancla, clasificador de POV | Exige criterio, no cuenta (`domain-knowledge.md` §11) | Fase 4 |
| `Serie` y canon compartido | Se decide al empezar una segunda obra | Sin fecha |
| Frontend | Documento aparte | — |
| Modo servidor multiusuario | El modo de referencia es local | Fase 6 |

**Aviso sobre `Serie`:** `definitions.md` §4.1 advierte que, si existe, el canon debe ser compartido **desde el primer día**. Excluirla es una decisión con coste futuro conocido, no un olvido; RD-10 limita el daño.

---

## 12. Cuestiones abiertas

Ninguna bloquea el diseño; todas bloquean una parte concreta del código.

| # | Cuestión | Bloquea |
| --- | --- | --- |
| 1 | Valor de N para los *snapshots* de `EstadoEnT` | RF-CAN-06, RI-21 |
| 2 | Proveedor y dimensión de los *embeddings*, y si coincide con el de generación | RI-17, RI-20, RD-07 |
| 3 | *Timeout* de la espera por reserva de presupuesto agregado | RNF-TOK-05, RI-21 |
| 4 | Plazo por paso antes de `TiempoAgotado` | RF-ORQ-09, RNF-FIA-04 |
| 5 | Si el nivel de calor se valida por clasificador o por lista de términos | RF-CAL-02 |
| 6 | Formato de la cita del pasaje: desplazamiento de caracteres o identificador de beat | RF-CAL-08, RI-18 |
| 7 | **Confirmar o sustituir los objetivos de rendimiento del §7.2**, que hoy son propuestas sin medir | RNF-REN-01 a 04 |
| 8 | Si la reanudación de un trabajo `ESCALADA` tras edición humana entra por `EXTRAYENDO` o vuelve a validar | CU-04 |
