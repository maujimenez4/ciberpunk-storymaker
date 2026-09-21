# CLAUDE.md

Instrucciones de proyecto para Claude Code y para cualquier agente de código que trabaje en este repositorio. **Este fichero es el único manual operativo:** léelo entero antes de escribir o modificar código.

`agents.md` no contiene especificaciones: solo apunta aquí.

---

## 1. Qué es este proyecto

Sistema de generación asistida de novela larga (80.000–120.000 palabras), con el romance como género de referencia.

**Principio rector:** la unidad atómica de generación es la **escena**. Todo gira alrededor de ensamblar el contexto correcto para una escena, escribirla, validarla y extraer de ella los hechos que alimentan la siguiente.

| Necesitas… | Ve a |
| --- | --- |
| Qué significa un término | `docs/definitions.md` — **fuente de verdad** |
| Cómo funciona una novela (estructura, género, arcos) | `docs/domain-knowledge.md` |
| Cómo se construye el sistema, agentes, proceso | `docs/architecture.md` |
| Diagramas y árboles | `docs/diagrams.md` |
| Stack, límites técnicos, convenciones, agentes, checklist | este fichero |

---

## 2. Regla primera: el vocabulario no se improvisa

> **Si necesitas la definición de cualquier término del dominio, ve a [`docs/definitions.md`](docs/definitions.md).**

Aplica siempre que aparezca uno de estos conceptos: escena, beat, giro de valor, canon, hecho de canon, plantado, pago, revelación, hilo narrativo, estado en T, ledger, paquete de contexto, muestra ancla, deriva, perfil de voz, beat de género, tropo, nivel de calor, HEA/HFN, puerta de calidad, defecto, biblia, outline, ficha de escena.

- No inventes sinónimos ni traduzcas términos por tu cuenta: el mismo concepto se llama igual en el esquema de datos, en los prompts, en las rúbricas y en la interfaz.
- Si un término que necesitas **no está** en `docs/definitions.md`, no lo introduzcas: propón la definición y espera confirmación antes de escribir código con él.
- Si el código y `docs/definitions.md` se contradicen, **gana el documento**.

---

## 3. Cómo trabajar en este repositorio

1. **Lee antes de escribir.** Ante una tarea de dominio: `docs/definitions.md` → la feature afectada → sus tests.
2. **Respeta las fronteras.** Backend: una feature solo importa de `commons/` y del `__init__.py` de otra feature. Frontend: solo hacia capas inferiores, nunca entre features, siempre por `index.ts`. Detalle en §5. Si una tarea te obliga a saltarte una frontera, **para y pregunta**: casi siempre significa que el corte está mal.
3. **Cambios pequeños y verificables.** Un cambio por commit, con su test. Nada de refactorizaciones de oportunidad mezcladas con funcionalidad.
4. **Los tests son el contrato.** Toda regla de dominio de §8 tiene un test que la comprueba. No se borra un test para que pase el código.
5. **No llames al modelo en los tests.** El cliente de LLM se inyecta; en pruebas se usa un doble con respuestas fijas.
6. **Determinismo.** Cualquier ejecución debe poder reproducirse: prompt versionado, semilla, IDs recuperados.
7. **Pregunta ante:** añadir una dependencia, cambiar el esquema de la base de datos, tocar el presupuesto de contexto o crear una feature nueva.

---

## 4. Requisitos técnicos (no negociables)

| Requisito | Decisión | Implicación |
| --- | --- | --- |
| Backend | **FastAPI** (Python 3.12+), Pydantic v2 | Async por defecto, OpenAPI como contrato |
| Frontend | **React 19 + TypeScript + Vite** | SPA; cliente de API generado del OpenAPI |
| Contexto del modelo | **Límite duro de 100.000 tokens** | Presupuesto por capa, contador obligatorio, fallo antes de llamar |
| Persistencia | **SQLite**, con o sin extensión vectorial | El código debe funcionar en ambos modos |

### 4.1 El límite de 100.000 tokens

Es la restricción de diseño más importante del proyecto.

- **Nunca se llama al modelo sin haber contado los tokens del paquete.** El contador es una dependencia inyectada, no una estimación por caracteres.
- El presupuesto se reparte por capas y cada capa tiene tope propio. Si una se pasa, se recorta **esa** capa, no el resto:

  | Capa | Tope | Qué se recorta primero |
  | --- | --- | --- |
  | Constitucional | 5.000 | Nunca se recorta |
  | Estructural | 10.000 | Detalle de beats lejanos |
  | Canon relevante | 20.000 | Personajes mencionados, no presentes |
  | Estado en T | 15.000 | Conocimientos antiguos ya usados |
  | Continuidad local | 20.000 | Escena N-2 antes que N-1 |
  | Memoria recuperada | 10.000 | Resultados de menor puntuación |
  | Instrucción | 10.000 | Nunca se recorta |
  | Reserva | 10.000 | Reservado para reparación y reintento |

- El ensamblador devuelve siempre el desglose por capa junto al paquete; se guarda en la tabla `ejecucion`.
- Si tras recortar no cabe, se lanza `ContextBudgetExceeded`. **Nunca se trunca por el final en silencio.**
- La reserva del 10 % existe para que el reintento con el defecto añadido siga cabiendo.
- Ese tope es **por llamada**. Hay además un **techo agregado de tokens en vuelo** para todas las llamadas simultáneas del proceso, descrito en `docs/architecture.md` §2.2. Si no hay hueco, la llamada espera; **nunca se recorta el paquete para hacerla caber**.

### 4.2 SQLite con y sin vectores

- La búsqueda semántica vive detrás de la interfaz `VectorStore`, con dos implementaciones: `SqliteVecStore` (extensión `sqlite-vec` cargada) y `BruteForceStore` (NumPy sobre embeddings en BLOB).
- En arranque se detecta si la extensión carga; si no, se degrada y se registra un aviso. **El sistema nunca falla por falta de extensión vectorial.**
- Recuperación **híbrida y en este orden**: filtro estructural (presentes, lugar, hilos abiertos, rango de capítulos) → similitud semántica sobre el conjunto ya filtrado → fusión con recencia.
- WAL activado, `foreign_keys=ON`, `busy_timeout`. Migraciones con Alembic desde el primer commit.
- Toda escritura de estado pasa por el ledger *append-only*; `estado_en_t` es una vista derivada, **jamás** una tabla que se edita.

---

## 5. Arquitectura del código

Ambos lados se organizan **por feature**, no por tipo de fichero. La arquitectura completa y sus alternativas descartadas están en `docs/architecture.md`.

### 5.1 Backend: features + commons

```
backend/app/
  features/<feature>/   router.py · schemas.py · service.py · repository.py
                        agents.py · prompts/ · index → __init__.py · tests/
    obra · outline · escena · contexto · escritura
    calidad · canon · manuscrito · auditoria
  commons/              domain/ db/ llm/ errors/ jobs/ config/
  main.py               composición: monta routers y dependencias
```

Reglas (test de arquitectura con import-linter; falla la build):

1. Una feature solo importa de `commons/` y del `__init__.py` de otra feature. **Nunca** de sus ficheros internos.
2. `commons/` **no importa de ninguna feature**.
3. `commons/domain/` no importa FastAPI, SQLAlchemy ni clientes HTTP. Se prueba sin base de datos.
4. Código repetido: **se duplica primero**; sube a `commons/` al tercer uso real. `commons/` no es el cajón de sastre.
5. Un ciclo entre features es un error de diseño: se extrae el concepto a `commons/domain/` o se invierte con un evento.

### 5.2 Frontend: feature-first (Bulletproof React + 3 reglas de frontera)

```
frontend/src/
  app/                  router, providers, estilos globales
  features/
    escena/             api/ components/ hooks/ types/ index.ts
    revision/  outline/  canon/  manuscrito/  auditoria/
  shared/
    ui/primitives/      Button, Input, Select, Dialog, Badge
    ui/patterns/        DataTable, FormField, EmptyState, Toolbar
    api/                cliente generado del OpenAPI
    lib/  hooks/  types/
```

Reglas (ESLint `import/no-restricted-paths`; no se revisan a mano):

1. **`shared/` nunca importa de `features/`.** Un import en esa dirección es siempre un error.
2. **Las features no se importan entre sí.** Si dos lo necesitan, lo común baja a `shared/`.
3. **Se entra a una feature solo por su `index.ts`.** Nunca a un fichero interno.

No usamos Atomic Design: `primitives` = sin lógica de negocio, reutilizable en cualquier app; `patterns` = composición de primitivos para un patrón recurrente.

---

## 6. Convenciones de backend

- **Los endpoints no contienen lógica.** Validan entrada, llaman a un servicio de su feature, devuelven un modelo de respuesta.
- Una funcionalidad nueva es una feature nueva o un caso de uso dentro de una existente; nunca un fichero suelto en una carpeta global.
- Modelos de entrada y de salida separados; nunca se expone el modelo de base de datos.
- `async def` en todo lo que hace IO. Librería síncrona y bloqueante → *thread pool*, no *event loop*.
- Dependencias por `Depends()`, incluidos reloj, contador de tokens y cliente de modelo: es lo que permite probar sin llamar al proveedor.
- Errores de dominio: excepciones propias traducidas a HTTP por el handler central de `commons/errors/`. Nada de `HTTPException` dentro de los servicios.
- Operaciones largas (escribir un capítulo, auditar el manuscrito) son trabajos en segundo plano con estado consultable, no peticiones HTTP que esperan.
- Herramientas: `ruff` (lint + formato), `mypy` estricto sobre `commons/domain/` y los `service.py`, `pytest` con `pytest-asyncio`.

## 7. Convenciones de frontend

- TypeScript estricto. Nada de `any` en código de producción.
- El cliente de API se **genera** desde el OpenAPI del backend; no se escriben tipos de respuesta a mano.
- Estado de servidor con TanStack Query; estado de UI con `useState`/`useReducer`. No se mezclan en un store global.
- Ningún `fetch` dentro de un componente: vive en `shared/api/` o en el `api/` de la feature, y se consume por hook.
- Componentes funcionales, exportaciones nombradas, test colocado junto al componente.
- El editor del manuscrito trabaja sobre versiones inmutables: editar crea versión nueva y marca la vigente.
- Accesibilidad mínima: foco visible, etiquetas en formularios, contraste AA.

## 8. Reglas de dominio que el código debe respetar

1. Una escena tiene exactamente un POV y un giro de valor no nulo.
2. Un personaje no puede usar información sin `sabe_desde` con escena anterior.
3. El estado en T se **deriva** del ledger; no se escribe a mano.
4. Todo hecho de canon cita la escena que lo estableció.
5. Ninguna escena puede exceder el `nivel_de_calor` declarado en la obra.
6. Ningún contenido romántico o sexual con personajes menores de 18 años: **validación de esquema**, no instrucción de prompt.
7. Cada ejecución guarda prompt, versión de biblia, IDs recuperados, modelo, semilla y coste.

Si el código y `docs/definitions.md` no coinciden, **gana el documento**.

---

## 9. Agentes narrativos del sistema

Cada rol tiene prompt propio, contexto propio y criterio de éxito propio. Están separados a propósito: quien escribe no ve sus contradicciones, y quien juzga no debe reparar.

| Agente | Entrada | Salida | Criterio de éxito | Escribe prosa |
| --- | --- | --- | --- | --- |
| **Arquitecto** | Brief | Premisa, biblia, outline | Estructura completa y beats cubiertos | No |
| **Planificador de escena** | Outline + estado en T | Ficha de escena | Objetivo, obstáculo y giro de valor definidos | No |
| **Ensamblador de contexto** | Ficha + almacenes | Paquete de contexto | Dentro de presupuesto, trazable | No (es código) |
| **Escritor** | Paquete de contexto | Prosa de escena | Voz consistente, escena dramatizada | Sí |
| **Continuista** | Prosa + canon | Defectos con código | Cero falsos negativos en CAN y CON | No |
| **Crítico** | Prosa + rúbrica | Puntuaciones y diagnóstico | Correlación con el editor humano | No |
| **Editor de línea** | Prosa aprobada | Prosa pulida | Mejora métricas de prosa sin tocar hechos | Sí, frase a frase |
| **Extractor** | Prosa aprobada | Hechos, estado, resumen, hilos | Todo hecho nuevo capturado y con origen | No |
| **Auditor de manuscrito** | Manuscrito + outline | Informe de auditoría | Cobertura de beats y cabos sueltos | No |

### 9.1 Reglas transversales

- **El Ensamblador es código, no modelo.** Debe ser determinista y auditable; si fuera un modelo, no se podría reproducir un fallo.
- **El Escritor solo ve lo que hay en el paquete.** Nunca accede a la base de datos: si le falta un dato, es un fallo del ensamblado, no del escritor. Esto hace que los defectos sean atribuibles.
- **El Continuista devuelve códigos** (`CAN-01`, `CON-03`, `VOZ-02`…) con cita del pasaje, nunca prosa corregida.
- **El Crítico no repara.** Puntúa y diagnostica; la reparación vuelve al Escritor con el defecto concreto en el prompt.
- **Máximo dos reintentos dirigidos** por escena; después, escalado a revisión humana.
- **El Extractor cierra el bucle:** cada hecho nuevo entra al grafo citando su escena de origen. Sin esto la memoria no crece y la coherencia se pierde hacia el capítulo 10.

### 9.2 Flujo

```mermaid
flowchart LR
  A["Arquitecto"] --> B["Planificador"]
  B --> C["Ensamblador"]
  C --> D["Escritor"]
  D --> E["Continuista + Crítico"]
  E -->|defecto| D
  E -->|2 fallos| H["Humano"]
  E -->|aprobada| F["Extractor"]
  F --> C
  F --> G["Editor de línea"]
```

### 9.3 Dónde vive cada agente

Cada agente narrativo pertenece a la feature que lo orquesta: su código en `features/<feature>/agents.py` y sus prompts en `features/<feature>/prompts/`.

| Agente | Feature |
| --- | --- |
| Arquitecto | `obra`, `outline` |
| Planificador de escena | `escena` |
| Ensamblador de contexto | `contexto` |
| Escritor, Editor de línea | `escritura` |
| Continuista, Crítico | `calidad` |
| Extractor | `canon` |
| Auditor de manuscrito | `auditoria` |

## 10. Prompts

- Viven en `features/<feature>/prompts/`, uno por rol, versionados (`escritor.v3.md`). **No se editan en sitio:** versión nueva y se cambia la referencia.
- Todo prompt declara: rol, restricciones duras (POV, tiempo verbal, nivel de calor), formato de salida y qué **no** debe hacer.
- Las restricciones duras se repiten al principio y al final: el centro del prompt es donde más información se pierde.
- Ninguna regla de seguridad depende solo del prompt. Edad, nivel de calor y consentimiento se validan además en código.

## 11. Definición de «hecho» para un agente

Un agente solo puede afirmar algo si procede de: `docs/definitions.md`, el grafo de canon, el paquete de contexto recibido o una instrucción explícita del usuario. Todo lo demás se marca como propuesta, no como hecho.

---

## 12. Skills del proyecto

Las skills instaladas viven en `.claude/skills/` (compartidas, commiteadas) o llegan por plugin. Procedencia, commit exacto y licencia de cada una: `.claude/skills/SOURCES.md`. Ver `docs/architecture.md` §7.2 para el detalle por área.

Hay una skill por requisito técnico de §4, y ninguna más:

| Skill | Requisito de §4 | Área del repo |
| --- | --- | --- |
| `python-fastapi-ops` | Backend FastAPI | `backend/app/features/*/router.py`, `service.py` |
| `pydantic` | Pydantic v2 | `schemas.py`, `commons/domain/` |
| `sqlite-vec` | Persistencia **con** extensión vectorial | `features/contexto/`, `commons/db/` |
| `sqlite-ops` | Persistencia **sin** extensión: WAL, índices, migraciones | `commons/db/`, `repository.py`, Alembic |
| `typescript-best-practices` | Frontend TypeScript estricto | `frontend/src/` |
| `react-best-practices` | Frontend React 19 | `frontend/src/features/*/components/` |
| `feature-sliced-design` | — (referencia, no norma) | Ver aviso abajo |

**`feature-sliced-design` no es la arquitectura de este proyecto.** Está instalada como referencia para la migración descrita en `docs/architecture.md` §6.5. En cualquier decisión sobre dónde va un fichero, qué capas existen o cómo se cruzan las fronteras, **manda §5.2 de este fichero**.

Lo específico de este proyecto —presupuesto de 100.000 tokens, ontología de escena y canon, las reglas de frontera de §5, el ledger append-only— **no lo cubre ninguna skill pública**: vive en este fichero.

## 13. Comandos

```bash
# backend
uv sync
uv run uvicorn app.main:app --reload
uv run pytest
uv run ruff check --fix . && uv run ruff format .
uv run lint-imports                 # reglas de frontera entre features
uv run alembic upgrade head

# frontend
pnpm install
pnpm dev
pnpm test
pnpm typecheck
pnpm lint                            # incluye import/no-restricted-paths
```

## 14. Qué no hacer

- No llamar al modelo sin contar tokens.
- No truncar contexto por el final sin registrar qué se ha quitado.
- No guardar prosa generada sin `run_id` asociado.
- No añadir una segunda base de datos «temporalmente».
- No introducir términos de dominio que no estén en `docs/definitions.md`.
- No editar escenas en sitio: siempre versión nueva.
- No usar reintentos genéricos («mejóralo»): el reintento lleva el defecto concreto con cita del pasaje.
- No importar entre features ni desde `shared`/`commons` hacia una feature.
- No meter nada en `shared/` o `commons/` con menos de tres usos reales.

## 15. Antes de dar una tarea por terminada

- [ ] Los términos usados existen en `docs/definitions.md`.
- [ ] Hay test de la regla de dominio afectada (§8).
- [ ] Backend: `ruff`, `mypy`, `pytest` y `lint-imports` pasan.
- [ ] Frontend: `pnpm typecheck` y `pnpm lint` pasan (incluye las reglas de frontera).
- [ ] No se ha creado ningún import entre features, ni de `shared`/`commons` hacia una feature.
- [ ] Si se tocó el contexto: el desglose de tokens por capa sigue dentro de los topes de §4.1.
- [ ] Si se tocó el esquema: hay migración de Alembic y funciona con y sin extensión vectorial.
- [ ] Ninguna clave, prompt de producción ni fragmento de manuscrito ha quedado en el repositorio.
