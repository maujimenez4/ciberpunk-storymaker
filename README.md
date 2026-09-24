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
| §2 Lectura interactiva (web) | **Hecha**: una dirección, tres pestañas. Falta el PDF |
| §3 Harness | Hecho |
| §4 Memoria | Hecho |
| §5a Validadores programáticos | Hecho |
| §5b Validadores semánticos | Hecho: Continuista y Crítico, los dos corriendo en producción |
| §5c Lean 4 | Hecho, **y detiene la publicación** |
| §5d TLA+ / TLC | Hecho, con correspondencia comprobada contra el código |
| §5 Evals | **Parcial**: falta la tabla de los cinco briefs y la iteración de *tuning* |
| §6 Observabilidad (Langfuse) | Hecho: observador, *scores* por validador, coste y latencia |
| §7 Guardarraíles | Hecho: hook de policy, vetos normalizados, registro de auditoría |

**Lo que todavía no existe, y conviene saberlo antes de probar:**

- **`ejemplos/novela-ejemplo.pdf`**, que el encargo pide con esa ruta exacta como evidencia
  de que el sistema funciona de principio a fin. La generación del PDF está escrita y sin
  ejecutar sobre una novela completa.
- **Una novela completa generada**. El outline de diez capítulos sí sale, con el
  destinatario dentro; los capítulos están bloqueados por lo de abajo.
- **La petición de cambio del lector** (`CA-25`).

### El fallo que hay que conocer antes de lanzar una corrida

**El modelo anonimiza el nombre del destinatario.** Con el brief de ejemplo, el outline sale
correcto y personalizado —usa el perro y el recuerdo aportado— pero el protagonista se llama
`[NOMBRE_ANONIMIZADO]`, con sufijo numerado para distinguir personajes.

No es un defecto del código: es una **política de protección de datos personales** aplicándose
sobre la salida del modelo. Hace bien su trabajo; lo que pasa es que aquí el nombre **es el
producto**, y una novela de regalo cuyo protagonista se llama así no es una novela con un
fallo, es un objeto inservible.

La solución en curso es que el nombre **no lo escriba el modelo**: los agentes trabajan con un
marcador y el sistema lo sustituye en código al servir. Cumple la política mejor que lo de hoy
—el nombre real deja de entrar en el prompt y de subir con la traza a Langfuse (§4.3)— y es
comprobable con un test, que es lo que `CLAUDE.md` §10 pide de cualquier regla que importe.

---

## El brief de ejemplo

Vive en [`ejemplos/brief-marta.json`](ejemplos/brief-marta.json), no aquí, y **una prueba lo
carga y construye el modelo con él**. Es el de los tests, y no es de nadie:

```json
{
  "destinatario": {
    "nombre": "Marta",
    "edad": 34,
    "rasgos": ["terca", "curiosa"],
    "recuerdos_aportados": ["el verano en Cadiz"]
  },
  "genero": "romance",
  "tono": "calido",
  "nivel_de_calor": 2,
  "vetos": ["sangre"],
  "elementos_obligatorios": ["el perro Luna", "la bufanda roja"],
  "dedicatoria": "Para Marta, que nunca se rinde."
}
```

**Este bloque estuvo mal desde que se escribió** — ponía `nombre`, `edad`, `rasgos` y
`recuerdos_aportados` al nivel de arriba, cuando `BriefEntrada` los quiere dentro de
`destinatario`, y **no validaba**. Nadie lo notó porque nada lo ejecutaba: un bloque de
código dentro de un documento no falla nunca.

Por eso el ejemplo se mudó a [`ejemplos/`](ejemplos/) y la copia de arriba es solo eso, una
copia. La que manda es el fichero, y [`test_ejemplos.py`](src/backend/app/features/obra/tests/test_ejemplos.py)
lo pone en rojo el día que `BriefEntrada` cambie.

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
