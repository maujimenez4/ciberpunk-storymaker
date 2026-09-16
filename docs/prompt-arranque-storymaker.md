# Prompt de arranque — StoryMaker

P�galo completo en la primera sesión del agente, con el repositorio vacío.

---

## Rol

Vas a construir StoryMaker en tres commits. Trabajas de forma proporcional: cada commit
añade solo lo que el siguiente necesita, y paras a esperarme entre uno y otro.

**El flujo ya está decidido y te lo doy abajo.** No lo rediseñes. Tu trabajo es derivar
de él todo lo demás: la especificación, la configuración y la implementación.

Tomas tú las decisiones que no estén fijadas. Cuando una te parezca relevante, la
propones en el plan y la justificas en una o dos frases. No me preguntes cosas que
puedes decidir; sí avísame cuando algo que decidas contradiga una invariante o el
diagrama.

---

## Qué es StoryMaker

Un sistema agéntico que escribe novelas largas, capítulo a capítulo, con investigación
web y supervisión humana configurable. El género inicial es thriller tecnológico
ciberpunk de registro neo-noir.

El problema real que resuelve no es la calidad de la prosa: es la **gestión de estado**.
Un modelo escribiendo treinta capítulos olvida lo que estableció en el tercero, inventa
un hermano, y suaviza al villano. StoryMaker trata la novela como un proceso de larga
duración con estado explícito en disco y puntos de control humanos.

---

## El flujo (dado)

```
---
title: StoryMaker - Agent Loop v2
---
flowchart TD
    START(["User: run novel"]) --> BOOT{"Bible exists?"}

    subgraph SETUP["Setup · runs once"]
        RES0["1 · Researcher<br/>thematic dossier"]
        ARCH["2 · Plot Architect<br/>acts + chapter outline"]
        PROF["3 · Character Profiler<br/>character sheets"]
        RES0 --> ARCH
        ARCH --> PROF
    end

    BOOT -->|no| RES0
    PROF --> LOAD
    BOOT -->|yes| LOAD["Load context<br/>bible + summaries + open threads"]

    LOAD --> BEAT["4 · Beat Planner<br/>goal · conflict · turn · hook"]
    BEAT --> GAP{"Research gaps?"}
    GAP -->|yes| RES1["1 · Researcher<br/>sourced notes"]
    RES1 --> GAP

    GAP -->|no| WRITE["5 · Scene Writer<br/>prose only"]
    WRITE --> VOICE["6 · Voice Editor<br/>rhythm · register · cuts only"]

    VOICE --> VAL1["7 · Continuity Keeper<br/>validate vs bible"]
    VOICE --> VAL2["8 · Technical Verifier<br/>prose vs sourced notes"]
    VAL1 --> REPORT["Merge issue report"]
    VAL2 --> REPORT

    REPORT --> BLOCK{"Blockers?"}
    BLOCK -->|yes · retries < 3| WRITE
    BLOCK -->|yes · retries = 3| FLAG["Flag as unresolved"]

    FLAG --> GATE{"Gate needed?<br/>config: approvalMode"}
    BLOCK -->|no| GATE

    GATE -->|no · auto-approve| COMMIT["7 · Continuity Keeper<br/>write bible + summary<br/>git commit per chapter"]
    GATE -->|end of act · or flagged| HUMAN["Present act in CLI"]

    HUMAN --> DEC{"Human decision"}
    DEC -->|approve| COMMIT
    DEC -->|revise with notes| WRITE
    DEC -->|rollback to chapter K| ROLL["Revert bible to K<br/>invalidate K+1..N"]
    ROLL --> LOAD

    COMMIT --> MORE{"More chapters?"}
    MORE -->|yes| LOAD
    MORE -->|no| COMP["9 · Compiler<br/>assemble manuscript.md"]

    COMP --> EXPORT["Export<br/>config: outputFormats"]
    EXPORT --> DONE(["manuscript.md<br/>+ pdf / epub"])
```

### Cómo leerlo

- Los nueve especialistas numerados son **subagentes**. El orquestador que recorre el
  bucle no aparece como caja porque *es* el bucle; en el inventario cuenta como décimo
  rol, el principal.
- El Researcher aparece dos veces (`RES0` y `RES1`): mismo agente, dos modos. Dossier
  amplio al arrancar, notas puntuales por capítulo.
- Los dos validadores salen en paralelo de `VOICE` y convergen en `REPORT`. Ninguno
  escribe nada, por eso pueden correr a la vez. Es la única paralelización del diseño.
- `GATE` lee la configuración y decide si interrumpe al humano. El diagrama no cambia
  entre modo prueba y novela completa: cambia la configuración.
- `COMMIT` hace un commit de git por capítulo aprobado. Eso es lo que hace viable
  `ROLL`: revertir es un revert, no una reconstrucción.

### Decisión abierta

Al hacer rollback, los capítulos K+1 a N se invalidan. Si su texto se borra o se
archiva es decisión tuya: propónla y justifícala.

---

## Invariantes

No las cambies sin decírmelo primero.

1. **Una sola fuente de verdad.** La biblia narrativa contiene el canon. Si no está
   ahí, no es canon.
2. **Un solo escritor del estado.** Solo `Continuity Keeper` escribe en la biblia, y
   solo después de aprobación. Todos los demás leen. Es el `yes` único del inventario.
3. **Un solo rol con acceso web.** Solo `Researcher`. Los hechos llegan a la prosa
   únicamente por notas con fuente y fecha. `Scene Writer` no busca, y por eso la
   verificación técnica significa algo: compara prosa contra notas.
4. **`Voice Editor` no añade.** Solo quita y afila. Si pudiera añadir, metería hechos
   después de que los validadores ya corrieron.
5. **El contexto se ensambla, no se acumula.** Ningún rol recibe el manuscrito
   completo. Un turno recibe biblia, resúmenes previos y notas de ese capítulo.
6. **Todo ciclo tiene tope.** Los tres del diagrama están acotados. Al agotarse,
   escala al humano en vez de seguir intentando.
7. **Solo `blocker` dispara reescritura.** `warning` y `note` se imprimen en la
   compuerta para que el humano juzgue. Si toda observación forzara reintento, se
   gastarían los tres intentos en comas.
8. **Markdown es el formato canónico.** PDF y EPUB son derivados regenerables.
9. **Worldbuilding original.** El pack de género codifica convenciones (identidad
   sintética, soberanía corporativa, la memoria como evidencia), nunca nombres propios,
   términos acuñados ni elementos de obras existentes. Incluye lista de términos
   prohibidos que la validación comprueba.

---

## Entorno

- Modelos de Anthropic a través del acceso a Claude de esta cuenta. No uses OpenRouter
  ni otros proveedores.
- git obligatorio: el commit por capítulo es parte del diseño, no una convención.
- Español para specs y documentación. Inglés para el diagrama, identificadores, claves
  de configuración y nombres de fichero.
- Identificadores en kebab-case: `scene-writer`, no `sceneWriter`.

---

## Commit 1 — Diagrama

- Guarda el diagrama tal cual, en su propio fichero.
- Verifica que parsea antes de commitear.
- README mínimo con el diagrama embebido y una explicación breve de dónde entra el
  input del usuario y dónde sale el output.
- Decide la estructura de carpetas del repositorio pensando en que va a crecer: otros
  géneros, otras novelas, otros formatos. Explica las decisiones en el README.

Para cuando termines.

---

## Commit 2 — Spec y configuración

### La spec

Un documento en español, ejecutable: alguien que solo lo lea debe poder implementar el
sistema. Derívala del diagrama, no de cero. Como mínimo:

- **Inventario de agentes**: los diez roles, con id, responsabilidad, qué lee, qué
  escribe, qué tiene prohibido y si accede a la web. Los `yes` de las columnas
  "escribe biblia" y "acceso web" deben ser uno cada una.
- **Inventario de skills o conocimiento compartido**, y qué agente carga cada una.
  Distingue lo que define *quién es* un agente de lo que es un *procedimiento
  compartido* entre varios. No dupliques: si algo lo usa un solo agente, va en su
  prompt.
- **Contrato de handoff**: qué payload recibe cada agente y qué devuelve, con formato
  literal. Sin esto, diez prompts inventan diez formatos y el desastre aparece al
  integrar.
- **Formato del reporte de incidencias**, con la semántica de severidad de la
  invariante 7.
- **Inputs**: qué escribe el usuario a mano y en qué formato.
- **Outputs**: cada fichero generado, con ruta y momento en que aparece.
- **Reanudación**: cómo se retoma una corrida interrumpida sin regenerar lo aprobado.
- **Criterios de aceptación** comprobables.
- **Limitaciones conocidas**, escritas y no disimuladas.

### La configuración

Un fichero JSON que cambie el comportamiento de una corrida **sin tocar la spec ni los
prompts**. Cubre al menos:

- Número de capítulos, número de actos y extensión de cada capítulo.
- Modo de supervisión: parar en todos los capítulos, parar solo por excepción y al
  cerrar acto, o no parar.
- Qué validaciones corren.
- Si la investigación web está activa y con qué tope de búsquedas.
- Tope de reescrituras.
- Topes de coste y de tokens, y qué hacer al superarlos.
- Formatos de salida.
- Un **modo en seco** que recorra el bucle escribiendo ficheros marcador sin llamar a
  ningún modelo.

Agrupa esos parámetros para que pasar de "prueba pequeña" a "novela completa" sea
cambiar lo mínimo posible.

La prueba objetivo es **3 capítulos de 3 o 4 párrafos cada uno**, y debe quedar
configurada y lista para correr. En esa configuración, decide qué apagar para no gastar
de más y justifica cada apagado: apagar de más deja caminos del bucle sin probar, que es
justo donde se rompen las cosas.

Para cuando termines.

---

## Commit 3 — Harness

Lo necesario para que la prueba corra de principio a fin y produzca la mini novela.

Restricciones:

- Se lanza con un solo comando.
- El comportamiento de los agentes vive en ficheros de texto editables, no incrustado
  en código. El código, si hace falta, se limita a lo mecánico: leer configuración,
  encadenar llamadas, escribir ficheros, hacer commits.
- Las invariantes 2 y 3 tienen que ser ciertas en la implementación, no solo en el
  prompt: un agente sin herramienta de búsqueda no puede buscar aunque quiera.

**Propón en tu plan cómo vas a montar el harness y por qué**, antes de escribir nada.
Hay varias formas razonables y quiero ver tu razonamiento sobre cuál encaja con las
restricciones de arriba.

Verifica el modo en seco antes de gastar en llamadas reales. Si el bucle falla vacío,
falla gratis.

---

## Cómo trabajamos

- **Un commit por vez.** Terminas, paras, esperas.
- **Plan antes de código.** Para cada commit, dime qué vas a crear y por qué antes de
  crearlo.
- **Cuando algo sea ambiguo o contradictorio, dilo.** Prefiero una pregunta a una
  suposición silenciosa.
