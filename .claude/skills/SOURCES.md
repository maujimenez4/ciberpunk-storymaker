# Procedencia de las skills del proyecto

Skills instaladas en `.claude/skills/`, copiadas fichero a fichero (no symlinks) y
clavadas al commit indicado. Sin instalación global ni de usuario; no se ha
registrado ningún marketplace.

Criterio de selección: **una skill por requisito técnico no negociable de
`CLAUDE.md` §4**, más `feature-sliced-design` y `coherencia-docs` por decisión
explícita. Nada más.

Fecha de instalación: **2026-09-21** para todas las filas salvo `coherencia-docs`,
instalada el **2026-09-22**.

## Instaladas

| Skill | Repositorio | Commit | Licencia | Para qué la queremos |
| --- | --- | --- | --- | --- |
| `python-fastapi-ops` | `0xDarkMatter/claude-mods` | `a339d71272d12e88ed0503ffa4de50e9b9a030a3` | MIT | §4 Backend: patrones FastAPI (lifespan, `Depends()` con `Annotated`, `response_model`, routers). Es generativa, no de revisión |
| `pydantic` | `pydantic/skills` (oficial del equipo Pydantic) | `238d97102650c1caa51f35027aee13c469c59542` | MIT | §4 Backend: Pydantic v2 — restricciones, validadores, jerarquías de modelos, coerción |
| `sqlite-ops` | `0xDarkMatter/claude-mods` | `a339d71272d12e88ed0503ffa4de50e9b9a030a3` | MIT | §4 Persistencia: WAL, `busy_timeout`/`SQLITE_BUSY`, `EXPLAIN QUERY PLAN`, índices, tablas STRICT, `aiosqlite`, migraciones. Cubre el modo **sin** extensión vectorial |
| `typescript-best-practices` | `0xBigBoss/claude-code` | `2921eb8a685a2589c4c3e6ecbc8eaa12ffadde73` | Apache-2.0 | §4 Frontend: TypeScript estricto — type-first, uniones discriminadas, tipos marcados, estados ilegales irrepresentables |
| `react-best-practices` | `0xBigBoss/claude-code` | `2921eb8a685a2589c4c3e6ecbc8eaa12ffadde73` | Apache-2.0 | §4 Frontend: React 19 — los efectos como vía de escape, `useEffectEvent`, cuándo *no* usar `useEffect` |
| `feature-sliced-design` | `feature-sliced/skills` | `fd71da42a89e916f2ced63e5349fd865c87070a6` | **Sin licencia declarada** | Instalada por decisión explícita del equipo (2026-09-21). Ver el aviso de conflicto más abajo |
| `verification-methods` | Propia de este repositorio | — | — | Metodologías de verificación; origen de `docs/verification.md` |
| `coherencia-docs` | `maujimenez4/MyFactory` | `4ca2652f900a3d3586f3aa7980f5f3f5165bc899` | **Sin licencia declarada** | Instalada por decisión explícita (2026-09-22). Revisa la coherencia entre los cinco documentos de contexto: citas `§N` rotas, contradicciones factuales, deriva terminológica e invariantes condicionales caducadas. No es un requisito de §4 |

La licencia de cada origen se ha copiado como `LICENSE.upstream` dentro de la
carpeta de la skill, salvo en `feature-sliced-design`, cuyo repositorio no publica
ninguna.

## Conflictos con `CLAUDE.md`

Regla: **gana `CLAUDE.md`**. No se edita el texto de las skills; se anota aquí.

### `feature-sliced-design` — conflicto de arquitectura, no de detalle

1. `docs/architecture.md` §6.5 evaluó Feature-Sliced Design y **lo descartó**
   ("7 capas y taxonomía discutible sin experiencia previa"), dejándolo únicamente
   como ruta de migración futura.
2. `CLAUDE.md` §5.2 fija Bulletproof React: `app/ features/ shared/`, sin capa
   `pages/` ni `entities/`.
3. La skill manda colocar el código **primero en `pages/`** e introduce `entities/`.
   Su `description` dispara justamente en decisiones de ubicación y de fronteras de
   importación.

**En toda decisión sobre dónde va un fichero, qué capas existen o cómo se cruzan
las fronteras, manda `CLAUDE.md` §5.2.** La skill se consulta como referencia de
FSD para preparar la migración descrita en §4.5, no como norma vigente.

Además: el repositorio de origen **no declara licencia**. Se ha copiado el
`SKILL.md` y sus 9 ficheros de `references/`; se han excluido `evals/` (25 KB de
datos de prueba de la propia skill).

### `sqlite-vec` — **retirada** el 2026-09-22

D-02 de la spec 001 retiró la búsqueda vectorial: no hay extensión, ni almacén de
vectores, ni proveedor de *embeddings*. La ordenación semántica la resuelve el
proveedor de modelo (`CLAUDE.md` §4.2, `architecture.md` §4.6).

**Se desinstala, no se conserva.** Una skill no es documentación inerte: se carga
sola cuando alguien toca el área que su `description` describe —aquí,
`features/contexto/` y `commons/db/`— y enseñaría a construir tablas `vec0` y
consultas `MATCH` contra un diseño que ya no existe. Dejarla instalada es peor
que no tenerla: no sobra, engaña.

Si algún día aparece una credencial de *embeddings*, se reinstala desde el commit
que esta entrada conserva. `fragmento` guarda el texto y RF-CAN-12 lo hace
reconstruible, así que volver costaría un reindexado.

### `python-fastapi-ops`

- Declara `depends-on: python-typing-ops, python-async-ops`. **No se han
  instalado**: son tipado y asyncio genéricos, que no son requisitos de §4. La
  skill funciona sin ellos; sus apartados "See Also" quedan como punteros muertos.
- Sus ejemplos de manejo de errores usan `HTTPException`. `CLAUDE.md` §6 lo
  permite en el endpoint pero lo **prohíbe dentro de los servicios**: los errores
  de dominio son excepciones propias traducidas por `commons/errors/`.
- No se han copiado `scripts/scaffold-api.sh`, `assets/fastapi-template.py` ni
  `tests/`. El `SKILL.md` los menciona; son punteros muertos a propósito.

### `sqlite-ops`

- Excluidos `references/d1-edge.md` y `references/d1-production-patterns.md`
  (~40 KB sobre Cloudflare D1, que no usamos) y `scripts/eqp-triage.py`. El
  `SKILL.md` los cita; punteros muertos a propósito.
- Es agnóstica de motor: sus ejemplos cubren varios anfitriones. El nuestro es
  `aiosqlite` sobre SQLite local, según `CLAUDE.md` §4.2.

### `sqlite-vec`

- **La skill está borrada en origen.** Vivía en `existential-birds/beagle` y
  desapareció en el commit `3076d0afe361` (2026-02-06, "split monolith into 10
  focused plugins"). Está clavada al último commit en que existía,
  `065636181813…` (2025-12-21). Incumple la regla de "commits en los últimos seis
  meses" y se instala a sabiendas: la API de `sqlite-vec` (`vec0`, `MATCH`, `k=`)
  es estable y no hay alternativa pública.
- **No cubre** lo nuestro de `CLAUDE.md` §4.2: la interfaz `VectorStore` con
  `SqliteVecStore`/`BruteForceStore`, la detección de la extensión en arranque con
  degradación, ni el orden de la recuperación híbrida (filtro estructural →
  similitud → fusión con recencia). Eso vive en `CLAUDE.md` y en el código.

### `typescript-best-practices`

- Su texto dice "Follows type-first, functional, and error handling patterns from
  CLAUDE.md". Se refiere al `CLAUDE.md` **del autor**, no al nuestro. Nuestras
  convenciones de frontend son `CLAUDE.md` §7 y `docs/architecture.md` §6.
- Pide cargar `react-best-practices` en paralelo: instalada, requisito satisfecho.
- Procede de un repositorio de configuración personal (dotfiles). Se han copiado
  únicamente los dos `SKILL.md`, sin nada del resto del repositorio.

### `pydantic`

Sin conflicto. Nota a favor: desaconseja usar Pydantic para clases instanciadas
desde el propio código, lo que concuerda con `CLAUDE.md` §5.1 regla 3
(`commons/domain/` se prueba sin base de datos y sin framework).

### `coherencia-docs` — resuelto el conflicto con `CLAUDE.md` §12

`CLAUDE.md` §12 afirmaba «una skill por requisito técnico de §4, y ninguna más» y
su tabla enumeraba siete. `coherencia-docs` no responde a ningún requisito de §4:
es una skill de proceso sobre la documentación. **Resuelto el 2026-09-22**
ampliando el criterio a «una skill por requisito de §4, más tres por decisión
explícita» en `CLAUDE.md` §12 y en `docs/architecture.md` §7.2. En la misma
revisión se añadió `verification-methods`, que estaba instalada desde el
2026-09-21 y no figuraba en ninguna de las dos tablas.

Además: el repositorio de origen **no declara licencia**, igual que
`feature-sliced-design`. La skill es un único fichero (`SKILL.md`, 14,9 KB); el
repositorio no contiene `references/`, `scripts/` ni `evals/`, así que no hay nada
excluido ni punteros muertos.

No hay conflicto de contenido: su jerarquía de autoridad reproduce la de
`CLAUDE.md` §3.1 (`definitions.md` manda sobre vocabulario, `architecture.md`
sobre estructura y decisiones) y su regla de no editar sin aprobación explícita
concuerda con §3.2 y §14.

## Evaluadas y descartadas

Para que no se vuelvan a proponer sin argumento nuevo.

| Candidata | Motivo del descarte |
| --- | --- |
| `Mindrally/skills` → `fastapi-python` | Regla de Cursor autoconvertida; incluye "Omit curly braces for single-line conditionals" (Python no tiene llaves) y asume asyncpg + SQLAlchemy 2.0 |
| `Mindrally/skills` → `react` | Se contradice (`function` vs `const`) y asume Next.js con Server Components y Tailwind obligatorio |
| `Mindrally/skills` → `tanstack-query` | Buena, pero impone un árbol `src/` por tipo que choca con `CLAUDE.md` §5.2 |
| `existential-birds/beagle` → `python-code-review` | Exige línea ≤79 caracteres; `ruff` usa 88 |
| `existential-birds/beagle` → `fastapi-code-review` | Solapa con `python-fastapi-ops`, que además genera en vez de solo revisar |
| `obra/superpowers` → `test-driven-development`, `systematic-debugging` | Buenas y activas, pero son skills de proceso, no requisitos técnicos de §4 |
| `anthropics/skills` → `frontend-design` | Va de identidad visual distintiva; el frontend es herramienta interna |
| `awesome-skills/code-review-skill` | Megaskill de 25+ lenguajes; solapa con la `code-review` integrada |
| `tanstack-skills`, `rafaelkamimura/claude-tools` | Sin commits en los últimos seis meses |
| `wshobson/agents` | Colección enorme pensada para instalarse entera |
| `Impertio-Studio/React-Claude-Skill-Package` | `main` sin mover desde 2026-03-30; su cobertura de TanStack Query es §7, no un requisito de §4 |

## Sin cobertura

Ninguna skill pública cubre esto; vive en `CLAUDE.md` y
`docs/architecture.md`:

- El **presupuesto de 100.000 tokens por capas** y el fallo previo a la llamada
  (`CLAUDE.md` §4.1).
- Las **reglas de frontera**: `import-linter` en backend e
  `import/no-restricted-paths` en frontend (§5.1 y §5.2).
- El **ledger append-only** con `estado_en_t` como vista derivada (§4.2).
- **Alembic en modo batch sobre SQLite**: solo lo roza
  `sqlite-ops/references/migration-patterns.md`.
- La **ontología de escena y canon** (`docs/definitions.md`).
- **Vite** como herramienta de construcción: no se ha encontrado nada que aporte
  sobre la documentación oficial.

## Pendiente de revisión humana

No se han leído íntegros los ~330 KB de ficheros `references/` copiados. Si se
quiere descartar contenido inyectado o instrucciones indeseadas, hay que revisarlos
aparte.
