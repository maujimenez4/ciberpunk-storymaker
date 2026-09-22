---
name: coherencia-docs
description: Detecta y resuelve inconsistencias entre los documentos de contexto del proyecto (definitions.md, domain-knowledge.md, architecture.md, verification.md y CLAUDE.md): referencias de sección rotas, contradicciones factuales, deriva terminológica, afirmaciones de estado obsoletas, invariantes condicionales que han dejado de cumplirse, requisitos sin clasificar y contenido colocado en el documento equivocado. Usar cuando el usuario pida revisar la coherencia de la documentación, sospeche que dos documentos no concuerdan, antes de un merge que toque docs/, tras renumerar secciones de un documento, o cuando aterrice código que convierta en obsoletas las afirmaciones de estado de verification.md. Produce primero un informe, después un plan, y solo aplica cambios con aprobación explícita.
---

# Coherencia documental

Comparas los documentos de contexto del proyecto entre sí, localizas inconsistencias, las clasificas y las resuelves. **Nunca editas sin aprobación explícita.**

## Alcance

Cinco documentos, no cuatro. `CLAUDE.md` está en la raíz pero es fuente de autoridad citada por los demás, así que entra:

| Documento | Papel |
| --- | --- |
| `docs/definitions.md` | Vocabulario del dominio |
| `docs/domain-knowledge.md` | Cómo funciona una novela |
| `docs/architecture.md` | Decisiones técnicas, agentes, proceso |
| `docs/verification.md` | Cómo se gana confianza: métodos y clasificación T/A/I/D/U |
| `CLAUDE.md` | Stack, convenciones y reglas de dominio que el código debe respetar |

Si existe `AGENTS.md`, inclúyelo como documento derivado (nunca gana un conflicto).

## Reglas innegociables

1. **Informe antes que plan, plan antes que edición.** Tres pasos separados, con parada en cada uno.
2. **Nada de escribir con el árbol sucio.** `git status` al empezar; si hay cambios sin commitear en los documentos del alcance, avisa antes de tocar nada.
3. **Una incidencia = una edición atómica con ID.** El usuario aprueba por lotes.
4. **Ante la duda, informar en vez de resolver.**
5. **No inventes contenido.** Si la resolución exige información que no está en ningún documento, es decisión del usuario.
6. **Cita siempre los dos lados:** fichero, sección y texto literal.

---

## Jerarquía de autoridad

Decide **por tipo de afirmación**, no por antigüedad:

| Tipo de afirmación | Manda | Los demás |
| --- | --- | --- |
| Qué significa un término, cómo se llama un concepto | `definitions.md` | Lo usan, no lo redefinen |
| Cómo funciona el dominio: estructura narrativa, género, arcos | `domain-knowledge.md` | Lo aplican |
| Decisiones técnicas: stack, estructura, agentes, proceso, almacenes, límites | `architecture.md` | Lo referencian |
| Reglas de dominio que el código debe respetar, convenciones, comandos | `CLAUDE.md` | Las invocan |
| Qué método de verificación aplica a cada requisito y con qué letra | `verification.md` | — |

**Regla declarada por el propio documento:** `verification.md` establece en su cabecera que se apoya en `architecture.md` para el *qué* verificar y en `CLAUDE.md` para las reglas de dominio, y que **si discrepa con `architecture.md`, gana `architecture.md`**. Respétalo: ante cualquier contradicción entre ambos, lo que se corrige es `verification.md`, nunca al revés.

Esto deja a `verification.md` como **documento derivado**: es autoridad sobre el *método* (qué es T, qué es A, qué es U y por qué), y subordinado sobre los *hechos* (qué dice la arquitectura, cuál es el límite de tokens, qué agentes existen). Casi todas sus filas citan explícitamente su origen (`arq. §2.1`, `CLAUDE §8.2`), y esas citas son el material más valioso de toda la revisión: ver `REF`.

Si el repositorio tiene `docs/_authority.md`, esa tabla prevalece sobre esta.

### Criterio de pertenencia

Para detectar contenido en el documento equivocado:

- Cambiaría al cambiar de framework, de modelo o de base de datos → `architecture.md`.
- Cambiaría aunque la novela se escribiera a mano → `domain-knowledge.md`.
- Es «X significa Y» → `definitions.md`.
- Describe con qué método se comprueba algo y qué letra recibe → `verification.md`.
- Es una instrucción operativa para quien escribe código → `CLAUDE.md`.

---

## Taxonomía de inconsistencias

| Código | Tipo | Qué es | Resolución |
| --- | --- | --- | --- |
| `REF` | Referencia rota o desplazada | Una cita `arq. §N` o `CLAUDE §N` apunta a una sección inexistente, o a una sección que ya no dice lo que la cita afirma | Automática si la sección correcta es identificable; si no, decisión |
| `COB` | Cobertura de verificación | Un requisito o regla de dominio existe en `architecture.md` o `CLAUDE.md` y no aparece clasificado en la tabla §4.1 de `verification.md` | Propuesta de fila nueva; la letra la decide el usuario |
| `EDO` | Estado obsoleto | `verification.md` afirma «Previsto», «Aplazado» o «las carpetas están vacías» y el repositorio ya dice otra cosa | Decisión del usuario |
| `CND` | Invariante condicional caducada | Una fila es cierta *porque* algo no existe («no hay sandbox porque no hay herramienta que aislar»), y esa condición ha cambiado | **Máxima prioridad.** Decisión del usuario |
| `FAC` | Factual | Dos documentos afirman cosas incompatibles | Decisión del usuario |
| `TER` | Terminológica | Mismo concepto con nombres distintos, o término usado sin definir | Automática si hay canónico en `definitions.md` |
| `AUT` | Autoridad | El mismo asunto desarrollado a fondo en dos documentos | Propuesta: cuál manda, el otro enlaza |
| `ALC` | Alcance | Contenido en el documento equivocado según el criterio de pertenencia | Propuesta de movimiento |
| `OBS` | Obsolescencia | Un documento refleja una decisión que otro ya cambió | Decisión del usuario |
| `HUE` | Hueco | Término definido que nadie usa, o concepto usado que nadie define | Solo informar |
| `EST` | Estructural | Enlaces rotos, numeración descuadrada, anclas inexistentes | Automática |

**Severidad:** alta → `CND`, `REF`, `FAC`, `OBS`, `COB`. Media → `EDO`, `TER`, `AUT`, `ALC`. Baja → `HUE`, `EST`.

**Cubos:** *automática* (`REF` resoluble, `TER` con canónico, `EST`) · *requiere decisión* (`CND`, `FAC`, `OBS`, `EDO`, `COB`) · *solo informar* (`HUE`, y todo lo que no llegue a confianza suficiente).

### Por qué `REF` es la comprobación de mayor valor aquí

`verification.md` cita secciones de otros documentos en casi todas sus filas. Esas citas se rompen **en silencio** cada vez que alguien renumera una sección, y nada en el repositorio lo detecta. Una cita rota no es un enlace feo: es una afirmación que ya no está respaldada. Empieza siempre por aquí.

Comprobar `REF` tiene dos mitades, y las dos son necesarias:

1. **Existencia** — la sección citada existe en el documento citado. Mecánico.
2. **Sustancia** — la sección citada sigue diciendo lo que la cita afirma. Semántico. Una cita que apunta a una sección existente pero equivocada es peor que una rota, porque parece correcta.

### Por qué `CND` es lo más urgente

`verification.md` marca varias filas como fuertes **precisamente porque una capacidad no existe**: no hay sandbox porque ningún agente tiene herramientas; el radio de impacto se elimina en vez de contenerse. El propio documento advierte de que esas filas dejan de ser ciertas el mismo día en que un agente reciba acceso de fichero o de red, y de que hay que reabrirlas **antes** de conceder el permiso.

Por eso: cuando detectes una fila cuya validez dependa de una ausencia, comprueba si esa ausencia sigue siendo real (en `architecture.md`, en `CLAUDE.md` y en el repositorio). Si ha cambiado, va la primera del informe, por encima de cualquier contradicción factual.

---

## Procedimiento

### Fase 0 — Preparación

1. `git status`. Si hay cambios sin commitear en los documentos del alcance, avisa.
2. Por cada documento: extrae el árbol de encabezados **con su numeración literal**, el tamaño y la fecha del último commit (`git log -1 --format=%cd -- <fichero>`). El más reciente suele ser el correcto en conflictos `OBS`.
3. Comprueba si existe `docs/_authority.md`.
4. Mira si `src/backend/` y `src/frontend/` tienen contenido: es lo que decide si las afirmaciones de estado de `verification.md` siguen siendo válidas.

### Fase 1 — Pasada determinista

Barata, con `grep`/`rg` y `git`, antes de gastar contexto en razonar.

- **Mapa de citas.** Extrae toda referencia con la forma `arq. §N`, `CLAUDE §N`, `§N`, `sección N`, `decisión N del §N`, o enlace relativo con ancla. Para cada una, comprueba que el encabezado existe en el documento destino. Toda no resuelta → `REF` candidata.
- **Índice de términos.** Términos definidos en `definitions.md` (encabezados, entradas de tabla, negritas). Cuenta apariciones en los demás. Cero → `HUE`.
- **Variantes de escritura.** Mismo término con y sin acento, singular/plural, `snake_case` frente a prosa, inglés frente a castellano. → `TER`.
- **Números con unidad.** Tokens, porcentajes, palabras, plazos, topes, número de agentes, número de estados, número de reintentos. Agrupa por concepto; dos cifras distintas para el mismo concepto → `FAC` alta.
- **Listas enumeradas.** Roles de agente, fases, puertas, códigos de defecto, estados de la máquina, reglas de dominio. Compara elementos y orden entre documentos.
- **Inventario de requisitos.** Todas las reglas numeradas de `CLAUDE.md` y las decisiones de `architecture.md`, contra las filas de la tabla §4.1 de `verification.md`. Lo que falte → `COB`.
- **Marcadores de estado.** En `verification.md`: `Previsto`, `Aplazado`, `No aplicable`, `Aplicado por diseño`, `vacío`, `todavía`, `hoy`, `por ahora`. Cruza con el estado real del repositorio → `EDO`.
- **Marcadores condicionales.** `mientras`, `porque no`, `en cuanto`, `si algún día`, `deja de ser cierto`, `se reconsidera si`. Cada uno es una `CND` a verificar.
- **Marcadores de pendiente.** `TODO`, `TBD`, `pendiente`, `por confirmar`, casillas sin marcar.

### Fase 2 — Pasada semántica

Solo sobre lo que la Fase 1 no ve, y siempre por **pares**, en este orden:

1. `verification.md` ↔ `architecture.md` — el par con más citas explícitas: mitad de sustancia de `REF`, más `EDO` y `CND`.
2. `verification.md` ↔ `CLAUDE.md` — reglas de dominio frente a su clasificación.
3. `definitions.md` ↔ `domain-knowledge.md` — el par que más deriva terminológicamente.
4. `architecture.md` ↔ `CLAUDE.md` — decisiones frente a convenciones.
5. `domain-knowledge.md` ↔ `architecture.md`
6. `definitions.md` ↔ `architecture.md` / `verification.md`

No releas documentos enteros. Trabaja sobre los **conceptos compartidos** del índice de términos y sobre los **destinos de las citas** del mapa: para cada uno, extrae lo que afirma cada documento y compáralo.

En cada par busca: afirmaciones incompatibles (`FAC`), decisiones ya revisadas en el otro (`OBS`), solapamiento (`AUT`), contenido mal ubicado (`ALC`), y citas que apuntan a la sección equivocada (`REF` de sustancia).

### Fase 3 — Informe (PARADA)

Presenta y **detente**. Orden fijo: `CND` primero, después el resto por severidad.

```markdown
# Informe de coherencia
Documentos: 5 · Citas verificadas: N · Conceptos comparados: N · Incidencias: N (A/M/B)

## Resumen
Dos o tres frases con el patrón dominante.

## Invariantes condicionales (revisar primero)
| ID | Condición que la sostiene | ¿Sigue siendo cierta? | Fila afectada |

## Incidencias
| ID | Tipo | Concepto | Documentos | Sev. | Cubo |

**INC-001 · REF · Límite de contexto**
- `verification.md` §4.1: «[cita literal]» → remite a `arq. §2.1`
- `architecture.md` §2.1 dice hoy: «[cita literal]»
- La sección existe, pero trata de otra cosa: el contenido citado está ahora en §N.
- Confianza: alta.

## Huecos detectados
Términos usados sin definir · Términos definidos sin usar · Requisitos sin letra.

## No revisado
Qué ha quedado fuera y por qué.
```

Termina preguntando: **«¿Sigo con el plan de resolución, o quieres ajustar el diagnóstico primero?»**

### Fase 4 — Plan (PARADA)

Agrupado por cubo, no por documento:

- **Lote A · Automáticas** (`REF` resolubles, `TER`, `EST`): ediciones concretas con fichero y línea. Una aprobación para todo el lote.
- **Lote B · Requieren decisión** (`CND`, `FAC`, `OBS`, `EDO`, `COB`): una pregunta por incidencia, con las dos opciones, la recomendación según la jerarquía y qué ficheros cambiarían.
- **Lote C · Reestructuración** (`AUT`, `ALC`): movimientos de contenido con origen y destino. Revisión individual siempre: mover texto entre documentos es lo que más fácil rompe la narrativa del documento origen.
- **Lote D · Solo informar.**

Indica líneas afectadas por lote. Si superas 30 incidencias, propón dos tandas empezando por severidad alta.

### Fase 5 — Aplicación

Solo tras aprobación explícita, y solo de los lotes aprobados.

1. Aplica lote por lote, en orden A → B → C.
2. Conserva el estilo del documento: tono, formato de tabla, nivel de encabezado, longitud de párrafo. `verification.md` tiene un formato muy marcado (tabla de cuatro columnas con enlace a la explicación del método, una letra por requisito): respétalo exactamente, y si añades una fila, incluye su enlace de referencia.
3. **Al tocar `verification.md`, mantén separados los dos sujetos** —agentes narrativos y agente de código—: una fila que los mezcle es un defecto, no una corrección. El propio documento lo advierte.
4. Tras cada lote, muestra `git diff --stat`.
5. Si aparece una inconsistencia nueva al aplicar, **para y repórtala**; no la resuelvas sobre la marcha.
6. Propón un commit por lote citando los IDs (`docs: resolver INC-003, INC-007 (referencias)`). No commitees sin permiso.

### Fase 6 — Cierre

Tres líneas: qué se resolvió, qué quedó pendiente de decisión, qué debe revisar el usuario a mano.

---

## Uso del contexto

- La Fase 1 trabaja con `grep` y `git`, no con documentos en contexto.
- La Fase 2 trabaja con **extractos por concepto y por destino de cita**, no con documentos completos.
- Nunca compares los cinco a la vez: siempre por pares.
- Si un documento no cabe cómodamente, procésalo por secciones manteniendo un índice de sus afirmaciones.

## Qué no es esto

- No es un corrector de estilo: no propongas mejoras de redacción que no resuelvan una inconsistencia.
- No es un generador de documentación: no rellenes huecos escribiendo contenido nuevo. Una fila `COB` se propone vacía, con la letra a decidir.
- No es un linter de markdown: formato y ortografía quedan fuera salvo que rompan una referencia.
- **No reclasifiques letras.** Cambiar una `U` por una `T` es una afirmación sobre lo que el proyecto puede demostrar, y la decide una persona.