# StoryMaker

Un sistema que escribe **novelas personalizadas para regalar**: a un hijo, a la pareja,
para una boda o una jubilación. Alguien las encarga y aporta los datos de quien va a
recibirlas; el sistema construye una historia que los contiene.

**Diez capítulos de 1.000–1.500 palabras.** Unas doce mil en total. La dificultad no está
en la extensión: está en el proceso.

**Se juzgan dos cosas a la vez, y ninguna rescata a la otra:**

| | Qué se pregunta | Cómo falla |
| --- | --- | --- |
| **Personalización** | ¿El destinatario se reconoce? ¿Siente que se escribió para él? | La novela es correcta y podría ser de cualquiera |
| **Calidad narrativa** | ¿Se lee de principio a fin sin tropezar? | El destinatario aparece en cada página de un texto que no funciona |

El sistema **no optimiza por que los datos aparezcan**. Colocar un dato no es narrarlo, y
una novela que menciona al destinatario quince veces sin sostenerse como historia ha
fallado igual que una impecable en la que no está.

---

## Estado

**Sin adornarlo.** El detalle vive en [`specs/estado-del-entregable.md`](specs/estado-del-entregable.md)
y los fallos conocidos en [`specs/problemas-abiertos.md`](specs/problemas-abiertos.md).

| Área del encargo | Estado |
| --- | --- |
| §1 Configuración y entrevista | Hecho |
| §2 Lectura interactiva (web) | **Falta entera.** `src/frontend/` está vacío |
| §3 Harness | A medias |
| §4 Memoria | Hecho |
| §5 Validación y evaluación | Parcial. Lean y TLA+ instalados y corriendo; los validadores formales, en curso |
| §6 Observabilidad (Langfuse) | **Falta entera** |
| §7 Guardarraíles | Hecho, salvo dos piezas |

**Y el que hay que leer antes de probar nada: [P-1](specs/problemas-abiertos.md).** Contra
el servidor levantado, el Entrevistador responde *sobre el repositorio* en lugar de sobre
la entrevista — el CLI carga el `CLAUDE.md` del proyecto como contexto pese a
`setting_sources=None`. El esquema de salida lo rechaza, que es para lo que existe, pero
**hasta que se arregle el flujo por HTTP no funciona con el proveedor real.** La secuencia
de abajo describe el sistema, no una corrida que hoy termine.

---

## El brief de ejemplo

Es el de los tests, y no es de nadie:

```json
{
  "nombre": "Marta",
  "edad": 34,
  "rasgos": ["terca", "curiosa"],
  "recuerdos_aportados": ["el verano en Cadiz"],
  "genero": "romance",
  "tono": "calido",
  "nivel_de_calor": 2,
  "elementos_obligatorios": ["el perro Luna", "la bufanda roja"]
}
```

La secuencia que lo convierte en novela:

```bash
ENT=$(curl -s -XPOST localhost:8000/entrevistas | python -c "import json,sys;print(json.load(sys.stdin)['id'])")
curl -s -XPOST localhost:8000/entrevistas/$ENT/respuestas \
  -H 'content-type: application/json' -d '{"respuestas": <el JSON de arriba>}'
OBRA=$(curl -s -XPOST localhost:8000/entrevistas/$ENT/cerrar | python -c "import json,sys;print(json.load(sys.stdin)['obra_id'])")
curl -s -XPOST localhost:8000/obras/$OBRA/outline
curl -s -XPOST localhost:8000/obras/$OBRA/novela
curl -s localhost:8000/trabajos/1
```

**Los dos elementos obligatorios están elegidos a propósito:** uno lo respalda un hecho del
canon y el otro no, así que `CA-15` —todo elemento obligatorio aparece en algún capítulo—
se ve por sus dos lados en la misma corrida.

### Los endpoints que existen hoy

**Ocho**, leídos de `openapi.json` el 2026-09-24. La spec especifica dieciséis (`CA-33`):
eso es lo que el sistema tendrá, no lo que tiene.

```
POST /entrevistas
POST /entrevistas/{entrevista_id}/respuestas
POST /entrevistas/{entrevista_id}/cerrar
POST /obras/{obra_id}/outline
POST /obras/{obra_id}/novela
GET  /capitulos/{capitulo_id}/contexto
POST /capitulos/{capitulo_id}/escribir
GET  /trabajos/{trabajo_id}
```

---

## Instalación

**El proveedor se usa por consumo de cuenta, sin clave de API.** El Claude Agent SDK lanza
el binario `claude`, así que hace falta tenerlo **instalado y autenticado** en la máquina.
Compruébalo antes de nada:

```bash
claude --version
```

Sin eso, las llamadas al modelo no salen, y el fallo aparece a mitad de una corrida en vez
de al arrancar (**P-15**).

```bash
# backend
uv sync
uv run alembic upgrade head
uv run uvicorn --factory app.main:crear_app --reload --app-dir src/backend

# pruebas y estilo
uv run pytest
uv run ruff check . && uv run lint-imports

# frontend (todavía no existe)
pnpm install && pnpm dev
```

Copia `.env.example` a `.env`. **No lleva ningún valor real y no debe llevarlo.**

---

## Arquitectura

La **escena** es la unidad de generación: lo que cabe en una llamada. El **capítulo** es la
unidad de lectura. A esta escala coinciden, pero siguen siendo dos conceptos.

Un orquestador **determinista** —una máquina de estados explícita, no un agente que
decide— recorre para cada capítulo: planificar → ensamblar contexto → escribir → validar →
reparar si hace falta → extraer los hechos nuevos → integrar. Diez roles con prompt propio
participan en ese ciclo, y están separados a propósito: **quien escribe no ve sus
contradicciones, y quien juzga no repara.**

La memoria es un **ledger *append-only***; el estado en un momento dado y la cronología son
**vistas derivadas**, nunca tablas que se editan. Corregir un hecho no lo modifica: registra
uno nuevo que lo sustituye y cita al anterior, para que se pueda encontrar la escena que se
apoyaba en el viejo.

El ensamblado tiene un **techo duro de 100.000 tokens**, repartido en ocho capas con tope
propio. Si no cabe, falla antes de llamar al modelo: **nunca trunca en silencio.**

| Para el detalle | Ve a |
| --- | --- |
| Vocabulario (fuente de verdad) | [`docs/definitions.md`](docs/definitions.md) |
| Cómo funciona una novela | [`docs/domain-knowledge.md`](docs/domain-knowledge.md) |
| Agentes, esquema, diagramas | [`docs/architecture.md`](docs/architecture.md) |
| Cómo se gana confianza | [`docs/verification.md`](docs/verification.md) |
| Cómo se trabaja | [`CLAUDE.md`](CLAUDE.md) |

---

## Verificación

Tres niveles, y el catálogo con su método —prueba, análisis, inspección, demostración— está
en [`docs/verification.md`](docs/verification.md), que es donde se cuenta cuántos hay y qué
cubre cada uno.

**Validadores mecánicos**, en código sobre cada capítulo: continuidad, canon, conocimiento,
nivel de calor, persona y tiempo verbal, palabras vetadas. Corren con la suite:

```bash
uv run pytest
```

**Lean 4 · la cronología de la historia.** Invariantes sobre los eventos: que respetan el
orden temporal y que nadie está en dos lugares en el mismo momento. Si una prueba no cierra,
el *build* falla y la versión no se publica.

```bash
cd formal/lean && lake build
```

**TLA+ / TLC · la máquina del harness.** La especificación describe el flujo de generación
como máquina de estados y TLC la comprueba sobre el modelo pequeño que pide el encargo,
cinco capítulos y dos reintentos.

```bash
cd formal/tla && java -cp tla2tools.jar tlc2.TLC -config harness.cfg Harness.tla
```

Versiones exactas, instalación y tiempos medidos: [`formal/README.md`](formal/README.md).

---

## Qué NO hace

Pagos, cuentas de usuario, impresión, ilustraciones, audio y despliegue. Tampoco edita
prosa a mano: quien lee **pide** cambios, y el sistema regenera y vuelve a validar.

---

## Demo y presentación

Pendiente. El vídeo y el material de presentación se añaden aquí cuando exista una corrida
real de principio a fin, que hoy bloquea **P-1**.
