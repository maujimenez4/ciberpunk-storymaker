# Cómo se usó Claude Code en este proyecto

**Qué cubre.** La sección «Claude Code» de `docs/entregable/examen-final.md`: que el repositorio
refleje el uso de Claude Code —`CLAUDE.md`, configuración MCP con un navegador, skills
referenciadas desde `/docs` y subagentes o comandos propios con su propósito y resultado—.

*El plan 7 T10 llamaba a este documento `docs/uso-de-claude-code.md`; se escribe como
`docs/claude-code.md` y la parte del navegador va aparte, en
[`validacion-visual.md`](validacion-visual.md), porque se rellena después de la corrida real.*

| Lo que pide el encargo | Dónde está | Estado |
| --- | --- | --- |
| `CLAUDE.md` en la raíz | [`CLAUDE.md`](../CLAUDE.md), único manual operativo; `AGENTS.md` solo apunta a él | Hecho |
| `.claude/mcp.json` con un navegador | [`.claude/mcp.json`](../.claude/mcp.json): Playwright MCP sobre Chromium | Hecho |
| Uso real del browser MCP, documentado | [`validacion-visual.md`](validacion-visual.md) §2 | **Pendiente de la corrida real**: procedimiento escrito, tablas vacías |
| Skills en el repo y referenciadas | `.claude/skills/`, §1 de este documento, procedencia en [`SOURCES.md`](../.claude/skills/SOURCES.md) | Hecho |
| Subagentes o comandos `/` propios | §3 y §4 de este documento | Hecho |

---

## 1 · Skills

Quince, commiteadas en `.claude/skills/` y copiadas fichero a fichero, clavadas a un commit de
origen. La procedencia, la licencia, lo que se excluyó y los conflictos con `CLAUDE.md` están en
[`.claude/skills/SOURCES.md`](../.claude/skills/SOURCES.md); la tabla de uso por área, en
`CLAUDE.md` §13 y `architecture.md` §7.2. Regla: **una skill no entra sin sus tres filas**
(`SOURCES.md`, `CLAUDE.md` §13, `architecture.md` §7.2).

| Skill | Origen | Para qué se usó |
| --- | --- | --- |
| [`python-fastapi-ops`](../.claude/skills/python-fastapi-ops/) | `0xDarkMatter/claude-mods` | Routers, `Depends()`, *lifespan*, `response_model` del backend |
| [`pydantic`](../.claude/skills/pydantic/) | `pydantic/skills` | Esquemas de entrada y salida, validadores (edad, calor, marca de dato) |
| [`sqlite-ops`](../.claude/skills/sqlite-ops/) | `0xDarkMatter/claude-mods` | WAL, `busy_timeout`, índices, migraciones Alembic en modo *batch* |
| [`sqlite-vec`](../.claude/skills/sqlite-vec/) | `existential-birds/beagle` (borrada en origen) | El almacén vectorial opcional (`CLAUDE.md` §4) |
| [`typescript-best-practices`](../.claude/skills/typescript-best-practices/) | `0xBigBoss/claude-code` | TypeScript estricto del frontend |
| [`react-best-practices`](../.claude/skills/react-best-practices/) | `0xBigBoss/claude-code` | Componentes de la lectura, efectos, hooks |
| [`frontend-design`](../.claude/skills/frontend-design/) | `anthropics/skills` | Dirección visual de la lectura («Cuaderno de viaje», T-30) |
| [`feature-sliced-design`](../.claude/skills/feature-sliced-design/) | `feature-sliced/skills` | **Referencia, no norma**: manda `CLAUDE.md` §5.2 |
| [`brainstorming`](../.claude/skills/brainstorming/) | superpowers | La puerta Spec de `CLAUDE.md` §3.2 |
| [`writing-plans`](../.claude/skills/writing-plans/) | superpowers | Los doce planes de `specs/`, en pasos del tamaño de un commit |
| [`test-driven-development`](../.claude/skills/test-driven-development/) | superpowers | Rojo → verde → refactor (`CLAUDE.md` §3.4) |
| [`verification-before-completion`](../.claude/skills/verification-before-completion/) | superpowers | El checklist de `CLAUDE.md` §16: evidencia antes de afirmar |
| [`coherencia-docs`](../.claude/skills/coherencia-docs/) | `maujimenez4/MyFactory` | Barridos de coherencia entre `docs/`, `CLAUDE.md` y las specs |
| [`verification-methods`](../.claude/skills/verification-methods/) | **Creada aquí** | Origen de `verification.md` y de la clasificación T/A/I/D/U |
| [`clarificar-spec`](../.claude/skills/clarificar-spec/) | **Creada aquí** | Barrido de ambigüedad de las specs 001 y 002 antes de firmarlas |

**Creadas en este repositorio: dos**, `verification-methods` y `clarificar-spec`. Ninguna skill
pública conocía `specs/NNN-slug/`, la nomenclatura `RF-*`/`CA-*` ni los estados de aprobación.

---

## 2 · El servidor MCP de navegador

`.claude/mcp.json` declara Playwright MCP (`npx -y @playwright/mcp@latest --browser chromium`).
Es el navegador **del agente de código**, no el del sistema: la validación visual automática es
código que conduce otro Chromium y no pasa por MCP (`architecture.md` §3.5.1, T-13). El
procedimiento, lo que se inspecciona y las tablas de resultados están en
[`validacion-visual.md`](validacion-visual.md).

---

## 3 · Subagentes

No hay definiciones propias en `.claude/agents/`. Los subagentes se lanzaron desde la sesión
principal con el tipo general, **un prompt por tarea copiado del plan aprobado**, y en olas.

### Cómo se repartió

Cada plan trae una tabla de olas: las tareas sin dependencias entre sí van a la vez, un agente
por tarea. La sesión principal **integra y no escribe features**: commitea, pasa las puertas,
cierra junturas y decide lo que cruza fronteras.

| Plan | Olas | Máximo de agentes a la vez |
| --- | --- | --- |
| `001/plan-1-encargo` | 5 | 4 |
| `001/plan-2-capitulo` | 5 | 5 |
| `001/plan-3-novela` | 4 | 4 |
| `001/plan-4-publicar` | 4 | 3 |
| `001/plan-7-harness` | 7 | 3 |
| `002/plan-1-lectura` | 4 | 4 |

Además de las olas de plan, **el último día se trabajó con varias sesiones en paralelo sobre el
mismo árbol** (siete a la vez según `RELEVO.md`), cada una dueña de unas rutas: canon,
manuscrito, escritura, frontend, documentación de proceso, validación visual.

**Propiedad de ficheros.** La regla era *un agente por fichero dentro de la ola*: el prompt de
cada agente lista los ficheros que puede tocar, y lo demás no se toca aunque haga falta; se dice
en el informe. Los primeros planes usaron *worktrees* aislados (`.claude/worktrees/`, ignorados
desde `20329ff`); después, árbol compartido con commits por ruta.

**Medido:** la ganancia realista fue **del orden de 2×**, no de «n agentes»: cada plan tiene
cuatro o cinco eslabones de ruta crítica y dos olas anchas.

### Resultado

Las integraciones son commits propios —`26196af`, `5ce55f4`, `2404eca`, `4f34b9f`, `cba1984`,
`f63a3e9`, `ad9177f`, `76b5fe8`, entre otros— y lo que cada una destapó está en
[`proceso/registro-de-iteraciones.md`](proceso/registro-de-iteraciones.md) §E y §F.

**Lo que salió bien:**

- **Cinco veces el subagente corrigió el encargo que recibió** en vez de obedecerlo (§F del
  registro): una regla de dominio en su forma antigua, una cita a una sección equivocada, un rojo
  anunciado que no era el que `pytest` imprime.
- **«Enséñame el rojo» en el informe** hizo que varios agentes cazaran sus propios tests que no
  podían fallar.

**Lo que falló, y la regla que dejó:**

| Qué pasó | Regla que quedó |
| --- | --- |
| **El índice de git es compartido.** Un `git add` de una sesión y un `commit` de otra se llevaron ficheros ajenos, dos veces | `git add <rutas>` y `git commit -F <msg> -- <las mismas rutas>`; nunca por carpeta ni sin rutas |
| Un `git checkout --` sobre ficheros sin commitear **borró una tarea entera** | Commitear en cuanto hay verde; respaldos en el temporal, verificados con hash |
| En Windows `Harness.bak` y `harness.bak` son el mismo fichero | Nombres de respaldo que difieran en algo más que mayúsculas |
| **Junturas sin dueño** en cinco a siete olas: el cable entre dos features no era de ninguna tarea | O la juntura tiene dueño en el plan, o se declara que la cierra el integrador |
| Un `__init__.py` que tres agentes dejaron sin exportar, **a propósito** | Se exporta al integrar y entra en la tabla de dueños de la fase siguiente |
| Resolver un conflicto concatenando los dos lados dejó **prosa dentro de un `__init__.py`** | Concatenar vale para tablas de filas, no para código |
| Un `uvicorn` de otra ola ocupaba el puerto y servía la aplicación **sin rutas**; el nuevo murió en su log | Comprobar quién escucha antes de fiarse de un 200 |
| Un aviso falso sobre `Protocol` **propagado a dos agentes** | Se comprueba en el intérprete antes de repetirlo, y se convierte en test |
| **Agentes que se paraban** sin informe final, o a mitad de tarea | El integrador retoma desde lo commiteado; por eso se commitea en cuanto hay verde |
| Siete sesiones corriendo la suite completa (cinco minutos) | Cada sesión corre los tests de su feature; el integrador, todo |

**Lo que un agente no hace:** firmar una spec o un plan (`CLAUDE.md` §15). Cuando `maujimenez4`
autorizó commitear una firma, el mensaje del commit dice que lo decidió él y con qué palabras.

---

## 4 · Comandos `/` propios y hooks

- **No hay comandos `/` propios.** No existe `.claude/commands/`; se usaron las skills de §1 y
  los comandos integrados.
- **No hay hooks de Claude Code.** Los «dos hooks» de `CLAUDE.md` §11 —validación de capítulo y
  *policy*— son **puntos de enganche en el código del sistema**, fuera del bucle del modelo, no
  hooks del editor (`proceso/trade-offs.md` T-15).
