---
id: estado-del-entregable
titulo: "Qué falta para cumplir el encargo, y qué ya está"
estado: vivo              # se actualiza al cerrar cada fase; no se aprueba ni se archiva
fecha: 2026-09-24
fuente: docs/entregable/examen-final.md
---

# Estado del entregable

**Qué es este fichero.** El cruce entre lo que pide [`docs/entregable/examen-final.md`](../docs/entregable/examen-final.md) y lo que hay construido, sección a sección. No es una spec ni un plan: **no se aprueba, no se archiva y no dice lo que queremos hacer** — dice **dónde estamos**, con evidencia y a fecha de hoy.

Existe porque el encargo se corrige contra sí mismo —«si el repositorio y este documento discrepan, el que está mal es el repositorio»— y hasta ahora ese cruce **no lo había hecho nadie de una sentada**. Tres fases de backend cerradas y ningún sitio donde leer qué queda.

**Cómo se lee la columna de estado:**

| | |
| --- | --- |
| **Hecho** | Implementado y con test que cae si se rompe |
| **A medias** | Parte implementada; lo que falta está dicho |
| **Falta** | No existe |
| **Declarado fuera** | Existe la decisión de no hacerlo, con su porqué |

---

## Lo primero, porque es lo que decide si se aprueba

> «**Un proyecto sin evals con resultados medibles, o sin documentación de proceso en `/docs`, no aprueba.**»

Son las dos únicas condiciones que el encargo escribe como eliminatorias, y **las dos están sin cumplir**:

| | Estado | Qué falta exactamente |
| --- | --- | --- |
| **Evals con resultados medibles** (§5, *Evaluación del sistema*) | **Falta** | Los cinco briefs de prueba, la tabla de qué validador pasó por brief, y la iteración de *tuning* con antes y después |
| **Documentación de proceso en `/docs`** | **A medias** | `docs/` tiene los cuatro documentos de contexto —arquitectura, definiciones, dominio, verificación— y **ninguno de los seis que el encargo enumera**: spec inicial, *trade-offs*, *explainers*, diagramas, registro de iteraciones y *red-team log* |

**Y hay una cosa que ya existe y está en el sitio equivocado.** El encargo pide un «**registro de iteraciones**: qué cambió tras cada eval o contraejemplo, y por qué. **No un diario, sino un log de decisiones con causa y efecto**». Eso es, literalmente, las tablas de **Desviaciones** de los tres planes: **más de ciento cincuenta filas**, cada una con lo que se desvió y por qué. Está escrito; lo que falta es **extraerlo a `/docs` con la forma que el encargo pide**.

---

## §1 · Configuración — **Hecho**

| Exigencia | Estado | Dónde |
| --- | --- | --- |
| Agente entrevistador que recoge nombre, edad, rasgos, recuerdos, género, tono y extensión | Hecho | `features/obra/agents.py` · `Entrevistador` |
| Recoge las palabras que el cliente no quiere | Hecho | ámbito `brief` de `palabra_prohibida` |
| Detecta datos que faltan y al menos un tipo de contradicción | Hecho | devuelve faltantes **nombrados** y contradicciones **explicadas** |
| Texto libre tratado como **contenido no confiable** | Hecho | entra marcado como dato; probado contra «ignora tus instrucciones» |
| Brief estructurado y **validado con esquema** | Hecho | `BriefEntrada`, con `extra="forbid"` |

---

## §2 · Lectura interactiva — **Falta entera**

**`src/frontend/` no existe.** Es el track de [`specs/002-frontend/`](002-frontend/), cuya spec está `aprobada` y cuyo `plan-1-lectura.md` sigue en **`borrador`** desde el primer día.

| Exigencia | Estado |
| --- | --- |
| Índice de capítulos navegable | Falta |
| Ficha de personajes y lugares **con enlaces al capítulo** | Falta. *El dato sí existe*: `hecho_usado_en` lo registra desde la Fase 2 |
| Portada con dedicatoria personalizada | Falta |
| Petición de cambio desde la página, y regeneración acotada | Falta (backend: §CU-06, también pendiente) |
| Se conserva la versión anterior | Falta (backend: `VersionPublicada`, pendiente) |
| **PDF exportado** | Falta |

**Y arrastra un requisito del backend:** `RF-VAL-08` / `CA-27` —la validación visual que abre la lectura en un navegador— **no se puede cerrar sin esto**, aunque sea código de backend.

---

## §3 · Harness — **A medias**

| Exigencia | Estado | Nota |
| --- | --- | --- |
| Tres roles mínimo: planner, writer, editor/critic | **Hecho**, y hay seis | Entrevistador, Arquitecto, Planificador, Escritor, Continuista, Extractor |
| `CLAUDE.md` | Hecho | Es el manual operativo, y el encargo dice que **es parte del examen** |
| **Una skill reutilizable** | Hecho | Ocho en `.claude/skills/`, con su procedencia en `SOURCES.md` |
| **Dos hooks**: validación de capítulo y policy | **A medias** | Existe `HOOK_DE_CAPITULO` y `PUERTA_G4`; **el de policy no** (RF-GUA-07) |
| Tools con esquema validado | **Declarado fuera** | `architecture.md` §3.5.1: ningún agente recibe herramientas, y va razonado |
| Retries con límite | Hecho | Dos reparaciones dirigidas por capítulo, y el contador no se hereda |
| Registro de tokens y coste **vía Langfuse** | **A medias** | El dato está en `ejecucion` —previsto y real—; **Langfuse no existe** |

---

## §4 · Memoria — **Hecho**

| Exigencia | Estado | Dónde |
| --- | --- | --- |
| *Story bible* en SQLite | Hecho | 21 tablas, 2 vistas derivadas, 3 disparadores |
| **Cada hecho registra en qué capítulos se usa** | Hecho | `hecho_usado_en`, y la cobertura lo consume por `numero` |
| Tabla de cronología que alimenta el validador formal | **A medias** | La vista `cronologia` existe y se deriva del ledger; **Lean no la consume todavía** |
| Resúmenes por capítulo para el contexto de los siguientes | Hecho | `resumen_capitulo`, exigiendo `version_texto` vigente |
| **Checkpoint por capítulo** y reanudación | Hecho | `CA-5` cerrado: se prueba matando el proceso en **los seis** estados no terminales |

---

## §5 · Validación y evaluación

### a) Programáticos (mínimo tres) — **Hecho, con una excepción**

Cinco validadores con **nombre y punto de ejecución declarado**, en dos catálogos:

| Validador | Punto | Estado |
| --- | --- | --- |
| Esquema del brief y de cada rol | al construir | Hecho |
| `extension_de_capitulo` | `HOOK_DE_CAPITULO` | Hecho |
| `nombres_literales` (con variantes declaradas) | `HOOK_DE_CAPITULO` | Hecho |
| Persona y tiempo verbal **comprobados en el texto** | `HOOK_DE_CAPITULO` | Hecho |
| `cobertura_de_personalizacion` | `PUERTA_G4` | Hecho |
| Guardarraíl de palabras prohibidas | en código, antes de aceptar | Hecho |
| **Validación visual vía browser MCP** | — | **Falta**: no hay lectura que abrir ni `.claude/mcp.json` |

**Lo que ningún validador emite todavía es su *score***, porque Langfuse no existe. El encargo lo pide para **todos**.

### b) Semánticos (mínimo dos) — **A medias**

| Exigencia | Estado |
| --- | --- |
| LLM-as-judge **con rúbrica**, puntuación por criterio y justificación | **Falta.** Decisión **P-B**: el juez no entra hasta poder calibrarse |
| **Revisión humana** de una novela completa con la misma rúbrica | **Falta** |
| Continuista que contrasta **contra el grafo** | **Hecho** (Fase 3), y es el que da el segundo validador semántico |

### c) Lean 4 — **Falta entera**

Generar el fichero Lean desde la cronología, dos invariantes, `lake build` **como puerta que impide publicar**, y **un caso real documentado**. Es `CA-21`, uno de los cinco criterios que deciden si el sistema existe.

### d) TLA+ / TLC — **Falta entera**

La especificación de la máquina, tres invariantes de seguridad, uno de *liveness*, TLC sobre un modelo pequeño con su configuración, y el README que empareja cada acción con su transición.

**Nota que ahorra trabajo:** la máquina de estados ya está **en código y cerrada** —`features/escritura/maquina.py`, con su tabla de transiciones explícita y 64 tests—, y `checkpoint.py` fija tres precondiciones más. Quien escriba el `.tla` parte de ahí, no de cero.

### Evaluación del sistema — **Falta entera**

Los cinco briefs (uno adversarial, uno con trampa temporal), la tabla por brief, y la iteración de *tuning* con antes y después. **Es una de las dos condiciones eliminatorias.**

---

## §6 · Observabilidad — **Falta entera**

Langfuse no está en el código. Lo que sí hay es **el dato que alimentaría las trazas**: `ejecucion` guarda plantilla con su hash, versión de biblia, IDs recuperados por capa, modelo, semilla, tokens **previstos y reales** y coste derivado.

---

## §7 · Guardrails — **Hecho, salvo dos piezas**

| Exigencia | Estado |
| --- | --- |
| Listas en SQLite, **tres niveles** | Hecho |
| Normaliza antes de comparar: mayúsculas, acentos, plurales | Hecho, **comparando por palabra y no por subcadena** |
| Devuelve al escritor con límite de intentos; agotado, **se detiene y se informa** | Hecho |
| Cada coincidencia en el **audit log** | Hecho (`registro_auditoria`, *append-only*) |
| …y en **Langfuse** | Falta |
| Tests de cada nivel y de variante | Hecho |
| **Audit log de las decisiones del policy engine** | **A medias**: el registro existe; **el policy engine no** |
| **Máximo 100.000 tokens concurrentes** | **Hecho**, y contando **tokens, no llamadas** |

---

## Los repositorios deben incluir también

| Exigencia | Estado |
| --- | --- |
| **`/ejemplos/novela-ejemplo.pdf`** — el PDF de una novela de diez capítulos | **Falta.** Requiere §2 y una corrida real |
| **`README.md`** con brief de ejemplo reproducible | **Falta** |
| **`.env.example`** | **Falta** |
| **`/docs`** con los seis documentos de proceso | **A medias** (ver arriba) |
| **`.claude/`** commiteada | Hecho: ocho skills con su procedencia |
| **`.claude/mcp.json`** con un servidor MCP de navegador | **Falta** |
| **Uso real del browser MCP documentado en `/docs`** | **Falta** |
| **Subagentes y comandos propios documentados en `/docs`** | **Falta**, y hay mucho que contar: veinticinco subagentes en tres fases |
| **Vídeo de demo** en `/presentacion/` | **Falta** |
| **Presentación y anexos** en `/presentacion/` | **Falta** |
| Sin claves en el repositorio | **Hecho**, y por diseño: P-08 elige consumo de cuenta **sin clave de API** |

---

## Lo que yo haría, y en este orden

**No es el orden de lo que falta: es el orden de lo que decide si esto aprueba.**

1. **`/docs` con los seis documentos.** Es eliminatorio y es lo más barato: **el material ya existe**. El registro de iteraciones son las tablas de Desviaciones; los *trade-offs* son las decisiones P-01 a P-08 de la spec más las de los planes; los diagramas están en `architecture.md`. Falta **extraerlos con la forma que el encargo pide**, no inventarlos.
2. **Las evals.** La otra eliminatoria. Cinco briefs, la tabla y una iteración.
3. **La publicación** (`CU-05`) **con Lean como puerta** — cierra `CA-21` — y la **petición del lector** (`CU-06`) — cierra `CA-25`. Con eso, los cinco criterios que deciden si el sistema existe.
4. **El frontend.** Su plan ya está escrito y cortado para cuatro agentes, y **no comparte un solo fichero con el backend**: es el único sitio del proyecto donde el paralelismo da más de 2×.
5. **Langfuse**, que desbloquea el *score* de todos los validadores.
6. **TLA+**, partiendo de la máquina que ya existe.
7. Los ficheros sueltos: `README.md`, `.env.example`, `.claude/mcp.json`, `/presentacion/`, `/ejemplos/`.

**Y una advertencia sobre el orden.** El PDF de la novela de ejemplo es «la evidencia de que el sistema funciona de principio a fin», y **depende de casi todo lo anterior**: necesita el frontend o el PDF, la publicación, y una corrida real contra el proveedor. Es el último en poder hacerse y el primero que alguien va a mirar.

---

## Qué está cerrado, para que el hueco se lea en contexto

Tres fases del backend, **completadas** y con evidencia:

| | |
| --- | --- |
| **670 tests** | `pytest`, y 669 + 1 *skipped* sin la extensión vectorial |
| **21 tablas, 2 vistas, 3 disparadores** | migrados, con `upgrade → downgrade base → upgrade` en limpio |
| **8 rutas** en el OpenAPI | el servidor levanta y las publica |
| `CA-1`, `CA-5`, `CA-7` | tres de los cinco criterios que deciden si el sistema existe |
| `mypy` estricto, `ruff`, `lint-imports` | en verde sobre 78 ficheros de producción |

**Y un fallo de producción encontrado al cerrar la Fase 3, que es lo primero que hay que mirar:** contra el servidor levantado, el Entrevistador responde **sobre el repositorio en vez de sobre la entrevista** — el CLI está cargando el `CLAUDE.md` del proyecto como contexto pese a `setting_sources=None`. El esquema de salida lo rechaza, que es para lo que existe, pero **hasta arreglarlo el flujo por HTTP no funciona con el proveedor real**.
