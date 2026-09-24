---
id: estado-del-entregable
titulo: "Qué falta para cumplir el encargo, y qué ya está"
estado: vivo              # se actualiza al cerrar cada fase; no se aprueba ni se archiva
fecha: 2026-09-24
fuente: docs/entregable/examen-final.md
---

# Estado del entregable

**Qué es este fichero.** El cruce entre lo que pide [`docs/entregable/examen-final.md`](../docs/entregable/examen-final.md) y lo que hay construido, sección a sección. No es una spec ni un plan: **no se aprueba, no se archiva y no dice lo que queremos hacer** — dice **dónde estamos**, con evidencia y a fecha de hoy.

Existe porque el encargo se corrige contra sí mismo —«si el repositorio y este documento discrepan, el que está mal es el repositorio»—. **Reescrito entero el 2026-09-24 por la tarde**: la versión anterior se escribió antes de las Fases 4 a 7 del backend y antes de que existiera `src/frontend/`, y afirmaba como ausentes el frontend, Langfuse, Lean, TLA+, el hook de policy, `docs/proceso/`, el `README.md`, `.env.example` y `.claude/mcp.json`. Todo eso existe hoy. Cada fila de abajo se ha comprobado contra el código, los tests o `git log`, no contra el `RELEVO.md`.

**Cómo se lee la columna de estado:**

| | |
| --- | --- |
| **Hecho** | Implementado y con test que cae si se rompe |
| **A medias** | Parte implementada; lo que falta está dicho |
| **Falta** | No existe |
| **Declarado fuera** | Existe la decisión de no hacerlo, con su porqué |

---

## Veredicto, en cinco líneas

1. **Hoy no se puede entregar.** El sistema está construido pieza a pieza y con puertas en verde, pero **nunca ha escrito una novela de principio a fin**: la base tiene dos obras y **cero capítulos**, cero versiones de texto y cero versiones publicadas (lectura directa de `storymaker.db`, 2026-09-24).
2. **Una de las dos condiciones eliminatorias está sin cumplir** —las evals— y **no se puede cumplir sin antes generar novelas**.
3. **La otra —`/docs` con la documentación de proceso— se cumple en forma**, con los seis documentos, pero **se ha quedado atrás**: afirma cosas que ya no son verdad y no recoge lo aprendido en la primera corrida real.
4. **Lo que impide generar la novela de ejemplo son dos defectos de producto y uno operativo**, no una fase entera: el nombre del destinatario sale anonimizado, una escalada no deja nada que revisar, y la cuota de la cuenta está agotada.
5. **Y falta el PDF**, que es la forma en la que el encargo pide la novela de ejemplo: la ruta responde `501`.

---

## Lo que impide generar la novela de ejemplo

`/ejemplos/novela-ejemplo.pdf` es «la evidencia de que el sistema funciona de principio a fin». Estos son los obstáculos, en el orden en que se encontrarían:

| # | Obstáculo | Evidencia | Detalle |
| --- | --- | --- | --- |
| 1 | **El nombre del destinatario sale como `[NOMBRE_ANONIMIZADO]`** | El outline real sale así; `grep` de cualquier marcador en `src/` no encuentra nada | [`problemas-abiertos.md`](problemas-abiertos.md) **P-19**. Una novela de regalo con el protagonista sin nombre no es entregable |
| 2 | **Una escalada no deja nada que revisar** | `ciclo._retirar_lo_descartado` borra las `version_texto` del intento; no hay tabla `defecto` | **P-20**. Si un capítulo escala, la novela se para (`DETIENEN_LA_NOVELA`) y no hay con qué decidir |
| 3 | **La cuota de la cuenta está agotada** | Dato de la sesión de hoy; no verificable desde el repositorio | Operativo. Una novela son **~80–90 minutos** medidos (~8 por capítulo) |
| 4 | **Nadie ha visto pasar los capítulos 2 a 10 contra el modelo real** | `storymaker.db`: 0 capítulos tras el arreglo del Arquitecto (`0513035`) | Lo que venga después del outline es desconocido. La corrida anterior escaló en el capítulo 1 |
| 5 | **El PDF no existe** | `GET /lectura/{token}/pdf` responde `501` (`manuscrito/router.py`) | La tarea está **firmada** (`24a915f`, plan-4 T10) y sin ejecutar |

**Lo que ya no bloquea, y lo bloqueaba esta mañana:** el CLI cargando el `CLAUDE.md` del repositorio (`bf0edc8`), el formulario enviando otro contrato (`e275c8e`), `database is locked` durante la llamada del Entrevistador (`596faba`), el frontend publicando sin haber escrito (`d887bb0`, `38a260d`), una obra sin capítulos publicable (`b0871ac`) y el Arquitecto rechazado por `tipo_de_corte_final` (`0513035`).

---

## Las dos condiciones eliminatorias

> «**Un proyecto sin evals con resultados medibles, o sin documentación de proceso en `/docs`, no aprueba.**»

| | Estado | Evidencia | Qué falta exactamente |
| --- | --- | --- | --- |
| **Evals con resultados medibles** (§5, *Evaluación del sistema*) | **Falta** | No existe `evals/` ni `docs/proceso/evaluacion.md`. Plan-6 T10 y T11 sin commit | Los cinco briefs, el corredor, `evals/RESULTADOS.md`, y la iteración de *tuning* con antes y después. **Y un rediseño**: el brief de trampa temporal (B3) está pensado para que lo cace el invariante de edad contra fecha de nacimiento, **que la plantilla Lean no incluye a propósito** (P-27). Tal como está diseñado, no fallaría donde el plan dice |
| **Documentación de proceso en `/docs`** | **Hecho en forma, desactualizada en fondo** | `docs/proceso/` con los seis: `spec-inicial`, `trade-offs`, `explainers`, `diagramas`, `registro-de-iteraciones`, `red-team-log` y su `README` (`63363e8`) | `registro-de-iteraciones.md` §«Lo que este registro todavía no puede tener» dice «no hay `.tla`» y «ningún fallo de Lean», y los dos existen. No recoge los seis arreglos de la primera corrida real de hoy. Y el uso real del browser MCP **no está documentado** porque no ha ocurrido (P-30) |

**Veredicto:** la segunda se defiende con una tarde de trabajo. **La primera depende de todo lo demás**: necesita novelas reales, y las novelas reales necesitan P-19 y P-20.

---

## §1 · Configuración — **Hecho**

| Exigencia | Estado | Dónde |
| --- | --- | --- |
| Agente entrevistador que recoge nombre, edad, rasgos, recuerdos, género, tono y extensión | Hecho | `features/obra/agents.py` · `Entrevistador`, con `entrevistador.v2.md` |
| Recoge las palabras o temas que el comprador no quiere | Hecho | ámbito `brief` de `palabra_prohibida` |
| Detecta datos que faltan y al menos un tipo de contradicción | Hecho | faltantes **nombrados** y contradicciones **explicadas** (`8485f0b`) |
| Texto libre tratado como **contenido no confiable** | Hecho | entra marcado como dato (`e65e3d5`), con `verbatim_prompts=True` en el cliente |
| Brief estructurado y **validado con esquema** | Hecho | `BriefEntrada`, `extra="forbid"`; `elementos_obligatorios` con columna propia (`edb8edc`, `0d25b26`) |
| Probado contra el modelo real | **A medias** | El formulario y el Entrevistador funcionan contra el proveedor desde hoy (`e275c8e`, `596faba`). **Sin traza en Langfuse** (P-22) |

---

## §2 · Lectura interactiva — **A medias**

`src/frontend/` existe: React 19 + TypeScript + Vite, **14 ficheros de test y 233 tests en verde**, `tsc` y `eslint` limpios (comprobado hoy). Una sola dirección `/l/{token}` con tres pestañas —Creación, Leer, Quién es quién— y la apariencia «Cuaderno de viaje» (plan 4 del frontend, `completado`).

| Exigencia | Estado | Evidencia |
| --- | --- | --- |
| Índice de capítulos navegable | Hecho | `Leer.tsx` · `Sumario`, con la marca de «reescrito» que da el backend |
| Portada con dedicatoria personalizada | Hecho | `Leer.tsx` pinta `dedicatoria`; el backend la guarda como dato (`e720d8d`) |
| Ficha de personajes y lugares **generada desde la story bible** | Hecho | `GET /lectura/{token}/ficha`, que no envía lo no revelado |
| …**con enlaces al capítulo donde aparece cada uno** | **A medias** | `QuienEsQuien` acepta `onIrACapitulo` y lo prueba, pero **`Paginas.tsx` no se lo pasa**: en producción los números salen como texto, no como enlace (P-24) |
| Petición de cambio desde la página, que regenera solo lo afectado | **Falta** | Backend plan 5 **aprobado y sin una sola tarea hecha**: no hay `POST /obras/{id}/peticiones`, ni `vigente`, ni llamador de `una_sola_vez`. Frontend plan 2 T4–T7 sin hacer |
| Marca en la lectura qué capítulos cambiaron | **A medias** | El índice pinta `cambiado`, pero sin petición nadie lo pone a `true` |
| Se conserva la versión anterior | Hecho en backend | `VersionPublicada` inmutable con `sucede_a_id`; `GET /lectura/{token}/versiones`. Sin interfaz que la abra |
| **PDF exportado** (obligatorio aunque se elija web) | **Falta** | `501`. Plan-4 T10 firmado (`24a915f`), sin implementar |

---

## §3 · Harness — **Hecho, con dos reservas**

| Exigencia | Estado | Nota |
| --- | --- | --- |
| Tres roles mínimo: planner, writer, editor/critic | Hecho | Ocho de los diez de `CLAUDE.md` §9: Entrevistador, Arquitecto, Planificador, Ensamblador (código), Escritor, Continuista, Crítico, Extractor. **No existen el Editor de línea ni el Auditor de manuscrito** (no hay `class` ni feature `auditoria`) |
| `CLAUDE.md` | Hecho | Es parte del examen |
| **Una skill reutilizable** | Hecho | Quince en `.claude/skills/`, procedencia en `SOURCES.md`; dos propias (`clarificar-spec`, `coherencia-docs`) |
| **Dos hooks**: validación de capítulo y policy | Hecho **en código** | `HOOK_DE_CAPITULO` y el hook de policy declarado (`168461a`). **Reserva:** el encargo nombra los hooks junto a `CLAUDE.md` y la skill, que son artefactos de Claude Code; no hay `.claude/settings.json` con hooks y ningún documento razona esa otra lectura (P-31) |
| Tools con esquema validado | **Declarado fuera** | `architecture.md` §3.5.1: ningún agente recibe herramientas |
| Retries con límite | Hecho | Dos reparaciones dirigidas; el Arquitecto repara una vez (`0513035`) |
| Tokens y coste por novela **vía Langfuse** | **A medias** | El dato está en `ejecucion` y sube a los spans (`ebcb27c`, `07fa40e`). **Nunca se ha visto en un Langfuse real**, y el coste se queda corto con caché (P-18) |

---

## §4 · Memoria — **Hecho**

| Exigencia | Estado | Dónde |
| --- | --- | --- |
| *Story bible* en SQLite | Hecho | Trece migraciones de Alembic, una sola base (P-07) |
| **Cada hecho registra en qué capítulos se usa** | Hecho | `hecho_usado_en`; la ficha lo consume |
| Tabla de cronología que alimenta el validador formal | Hecho | Vista `cronologia` derivada del ledger; `manuscrito/lean/generador.py` la convierte en Lean |
| Resúmenes por capítulo | Hecho | `resumen_capitulo` |
| **Checkpoint por capítulo** y reanudación | Hecho | Reanudación probada en los estados no terminales; `PROCESO_INTERRUMPIDO` para la caída (`2de6027`). **Dos bordes sueltos** en la reanudación vista desde el frontend (P-25) |

---

## §5 · Validación y evaluación

### a) Programáticos (mínimo tres) — **Hecho, salvo la validación visual**

| Validador | Punto | Estado |
| --- | --- | --- |
| Esquema del brief y de cada rol | al construir | Hecho |
| `extension_de_capitulo`, `nombres_literales`, persona y tiempo verbal en el texto | `HOOK_DE_CAPITULO` | Hecho |
| `cobertura_de_personalizacion` | `PUERTA_G4` | Hecho, y ya no aprueba de balde sin entrevista (P-2 cerrado) |
| Guardarraíl de palabras prohibidas | hook de policy | Hecho |
| *Score* a Langfuse de cada uno | en su span | Hecho en código (`6389a00`, `e12a978`); sin ejercitar contra Langfuse real |
| **Validación visual vía browser MCP** (`RF-VAL-08`, `CA-27`) | — | **Falta.** `.claude/mcp.json` declara Playwright MCP; el validador en código (plan-7 T9) no existe |

### b) Semánticos (mínimo dos) — **A medias**

| Exigencia | Estado |
| --- | --- |
| LLM-as-judge **con rúbrica**, puntuación por criterio y justificación | Hecho en código: el Crítico puntúa contra `RUBRICA_V1`, justifica y **no bloquea** (`0d0f4df`, `4f35669`). **Pero en Langfuse las seis puntuaciones llegan con el mismo nombre**: `_SpanLangfuse.puntuar` descarta `criterio` (P-22) |
| Continuista contra el grafo y contra el ledger | Hecho: corre en el ciclo (`1899ccf`, `bab4dd7`) y `CON-03` se contrasta contra `estado_en_t` (`1d92785`) |
| **Revisión humana** de una novela completa con la misma rúbrica | **Falta.** Las tablas `revision_humana` y `aceptacion_de_entrega` existen (migración del juicio); el servicio y los endpoints (plan-6 T9) no. Y no hay novela que revisar |

### c) Lean 4 — **A medias**

| Exigencia | Estado |
| --- | --- |
| Se genera un fichero Lean desde SQLite | Hecho (`b6b1463`) |
| …con eventos, momento, personajes, lugar **y fechas de nacimiento** | **A medias.** Las fechas de nacimiento **no entran**, a propósito: `plantilla.lean` explica que hoy solo el destinatario tiene fecha y no es un `Personaje` (P-27) |
| Al menos dos invariantes | Hecho: `sinUbicuidad` y `sinReaparecidos` |
| Automático, y si falla **la versión no se publica** | Hecho: `CronologiaIncoherente` detiene `publicar` (`4c6ff5c`, `CA-21`) |
| …**y el fallo vuelve al editor como feedback** | **Falta.** El fallo termina en un `409`; nada lo devuelve a ningún rol (P-28) |
| **Un caso real** detectado, o por qué no hubo ninguno | **Falta.** Lo que hay es un fallo provocado en test. El caso real estaba previsto para B3 de las evals, que depende de P-27 |

### d) TLA+ / TLC — **Hecho**

`formal/tla/Harness.tla` con `harness.cfg`, tres invariantes de seguridad y *liveness*, TLC en verde (65.601 estados distintos), correspondencia con el código **mecanizada** en `test_correspondencia_tla.py` (`e76ab85`) y README con la tabla acción → transición y cuatro contraejemplos de laboratorio. **Ningún contraejemplo real**, y el README lo dice.

### Evaluación del sistema — **Falta entera**

Ver la condición eliminatoria, arriba.

---

## §6 · Observabilidad — **A medias**

| Exigencia | Estado |
| --- | --- |
| Una traza por generación, **sesión por novela** | Hecho en código para outline, ciclo de capítulo y publicación (`8a85586`). **El Entrevistador no tiene traza**: la sesión se deriva de `obra_id`, que no existe mientras dura la entrevista (`architecture.md` §9.2.1, decisión pendiente) |
| Cada rol y cada tool, un span con nombre | Hecho: `arquitecto`, `planificador`, `ensamblador`, `escritor`, `policy`, `continuista`, `puerta_g1a`, `critico`, `extractor`, `cronologia_lean` |
| Tokens, coste y latencia por llamada, capítulo y novela | Hecho en código (`ebcb27c`); coste corto con caché (P-18) |
| Scores de todos los validadores | Hecho en código; los del juez pierden el criterio (P-22) |
| **Prompts versionados en Langfuse** | **Falta.** El protocolo `Span` solo tiene `entrada`, `salida`, `consumo` y `puntuar`: **ningún span lleva `prompt_id`, versión ni hash**, y nada registra plantillas en Langfuse. Es justo lo que la iteración de *tuning* necesita (`CA-19`) |
| Probado contra un Langfuse real | **Nunca.** Además no hay `flush` al apagar (P-22) |

---

## §7 · Guardrails — **Hecho**

| Exigencia | Estado |
| --- | --- |
| Listas en SQLite, tres niveles | Hecho |
| Normaliza antes de comparar | Hecho, por palabra y no por subcadena |
| Devuelve al escritor con límite; agotado, **se detiene y se informa** | Hecho |
| Cada coincidencia en el audit log **y en Langfuse** | Hecho en código (score de `policy`) |
| Tests de cada nivel y de variante | Hecho |
| **Audit log de las decisiones del policy engine** | Hecho: `registro_auditoria` recibe cada decisión del hook de policy, permitida o bloqueada |
| **Máximo 100.000 tokens concurrentes** | Hecho, contando tokens y no llamadas (`PresupuestoConcurrente`). Hoy la concurrencia real es 1 porque todo corre en serie (P-21) |

---

## Los repositorios deben incluir también

| Exigencia | Estado |
| --- | --- |
| **`/ejemplos/novela-ejemplo.pdf`** | **Falta.** Existen `ejemplos/brief-marta.json`, `brief-menor.json` y su `README.md`; el PDF no |
| `README.md` con brief de ejemplo reproducible | Hecho, y el brief valida (`d0ae57a`) |
| `.env.example` | Hecho, con las claves vacías y el aviso de que el backend **no carga** el fichero solo |
| `/docs` con la documentación de proceso | Hecho en forma, desactualizado (arriba) |
| `.claude/` commiteada | Hecho: skills y `mcp.json`. **No hay comandos `/` propios ni ficheros de memoria**: si el encargo los espera, no están |
| `.claude/mcp.json` con un MCP de navegador | Hecho: Playwright MCP |
| **Uso real del browser MCP documentado en `/docs`** | **Falta.** `explainers.md` §24 explica el concepto; ninguna inspección real consta |
| Skills referenciadas desde `/docs` | Hecho: `architecture.md` §7.2 |
| Subagentes documentados en `/docs` | A medias: `explainers.md` §23 los cuenta; no hay registro por subagente con propósito y resultado |
| **Vídeo de demo** en `/presentacion/` | **Falta** |
| **Presentación y anexos** en `/presentacion/` | **Falta.** La escribe `maujimenez4`, no un agente |
| Sin claves en el repositorio | Hecho: `*.db` ignorado, `.env.example` vacío, consumo de cuenta sin clave |
| Repositorio **MyFactory** | Fuera de este repositorio: no verificable desde aquí |

---

## Las puertas, hoy

| Puerta | Resultado | Cómo se comprobó |
| --- | --- | --- |
| `pytest` | **983 en verde** | Suite completa sobre `HEAD`, 2026-09-24 |
| `mypy` | Sin errores en 99 ficheros | Corrido para este documento |
| `ruff check` | Limpio | Ídem |
| `ruff format --check` | **Dos ficheros sin formatear**: `escena/agents.py`, `obra/agents.py` (P-26) | Ídem |
| `lint-imports` | 3 contratos, 0 rotos | Ídem |
| Frontend `vitest` · `tsc` · `eslint` | 233 en verde en 14 ficheros · 0 · 0 | Ídem |
| Lean · TLC | Verdes según `formal/README.md`; no se han vuelto a correr para este documento | — |

---

## Dónde sigue esto

- [`hoja-de-ruta.md`](hoja-de-ruta.md) — el orden de lo que queda, **desde hoy**, y qué plan cubre cada tramo.
- [`problemas-abiertos.md`](problemas-abiertos.md) — lo construido que **no está bien**, con dueño y coste.
