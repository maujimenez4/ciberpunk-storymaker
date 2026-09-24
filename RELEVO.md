# Relevo

**Para quien recoja la orquestación de este repositorio.** No es documentación de contexto —eso vive en [`docs/`](docs/)— ni una spec. Es **cómo se está trabajando hoy**, para que el proceso no se pare al cambiar de máquina o de sesión.

Fecha: **2026-09-24**. Rama: **`seed-context-v2-backend-v2`**.

---

## Lo primero: lee esto, en este orden

1. **[`CLAUDE.md`](CLAUDE.md)** entero. Es el manual operativo y no hay otro.
2. **[`docs/definitions.md`](docs/definitions.md)** si vas a tocar dominio. El vocabulario no se improvisa.
3. **[`docs/entregable/examen-final.md`](docs/entregable/examen-final.md)** — lo que pide el encargo, sin interpretar.
4. **[`specs/problemas-abiertos.md`](specs/problemas-abiertos.md)** — los fallos conocidos, numerados.
5. **[`specs/estado-del-entregable.md`](specs/estado-del-entregable.md)** — el cruce contra el encargo.

---

## Cómo se trabaja aquí, y por qué

### Hay varias sesiones a la vez, y el árbol es uno

Siete sesiones de Claude han trabajado hoy sobre **el mismo directorio**. Eso funciona, y tiene dos reglas que se pagaron caras:

**1 · `git add <rutas> && git commit -F <fichero> -- <las mismas rutas>`**

Nunca `git add` por carpeta, y nunca `git commit` sin rutas. **El índice de git es compartido entre las sesiones**: un `git add` seguido de un `commit` que otra sesión atraviesa se lleva ficheros ajenos dentro. Pasó dos veces hoy. El `--` limita lo que entra aunque el índice tenga más.

**2 · Restaurar desde git solo es seguro sobre lo que está en git**

Se perdió una tarea entera con `git checkout --` sobre ficheros sin commitear. **Commitea en cuanto tengas verde**, no al final. Los respaldos van al directorio temporal, con nombres que difieran en algo más que mayúsculas —en Windows `Harness.bak` y `harness.bak` son el mismo fichero, y eso también costó trabajo— y la restauración se verifica con `sha256sum`.

### Cada sesión corre lo suyo, el integrador corre todo

La suite completa tarda **cinco minutos** y hay varias sesiones tocando el árbol, así que siete personas repitiéndola es tiempo tirado. Cada una corre los tests de su feature; quien integra pasa la suite entera antes de empujar.

Lo que **no** se relaja: cada cambio lleva su test, y se ve el rojo antes.

### Las puertas

```bash
uv run pytest                 # 923 en verde a fecha de hoy
uv run ruff check . && uv run ruff format .
uv run mypy src/backend/app   # 98 ficheros
uv run lint-imports           # 3 contratos de frontera
cd src/frontend && pnpm typecheck && pnpm lint && pnpm test
```

### Lo que un agente no puede hacer

**Firmar una spec o un plan.** `CLAUDE.md` §15. La puerta la abre una persona, y el campo `aprobado_por:` lo rellena ella. Si `maujimenez4` autoriza que se commitee la firma, **se escribe en el mensaje del commit que él lo decidió y con qué palabras** — hay dos ejemplos: `24a915f` y el de `plan-3-una-pagina`.

---

## El hallazgo que define este proyecto

**La familia de fallo dominante aquí son los tests con el nombre correcto que no pueden fallar.** Se cazaron **diez** en un solo día, en siete áreas distintas. Está escrito como método en [`docs/verification.md` §5.1](docs/verification.md).

Los casos, por si sirven de patrón:

| Qué parecía | Qué era |
| --- | --- |
| Cuatro ablaciones de TLA+ en verde | El `sed` **no sustituyó nada** en ninguna de las cuatro |
| El test de correspondencia en verde | **20 de 31 transiciones** no pasaban por la tabla que comparaba |
| 7/7 en la correspondencia | Una fila apuntaba a un nombre **inventado**, que no existe nunca |
| El PDF conservaba la tipografía sin red | Leía la **caché** de la corrida con red |
| Un hash de rúbrica | Solo miraba la versión: **dejaba pasar un cambio de ancla** |
| El coste por modelo | `TARIFAS` indexada por constantes de rol: **5× en silencio** al unificarlas |
| Seis tests de Lean en verde | **Se saltaban**: `shutil.which("lean")` daba `None` con Lean instalado |
| Tres agentes probados | **Nadie podía llamarlos**: no salían por el `__init__` |
| «Una obra sin capítulos no da 500» | Pasaba **con la ruta sin escribir**: un 404 también es `>= 400` |
| El brief de ejemplo del README | **No validaba** desde que se escribió |

**Las cuatro comprobaciones que los destapan**, y que salen gratis al escribir el test:

1. **Un control que cuenta coincidencias.** Si sustituyes algo, cuenta cuántas veces.
2. **Medir sobre el artefacto, no a través de una capa.** El shell entre tú y lo que mides es una fuente de error en los dos sentidos.
3. **Ejecutar en vez de leer una representación.** Un test contra una tabla que describe el código no ve lo que el código hace por fuera.
4. **Quitar la pieza y mirar qué cae.** Si no cae nada, el test no la estaba comprobando.

Ninguna comprueba el sistema: **comprueban la comprobación**.

---

## Lo que hay hoy

| Área del encargo | Estado |
| --- | --- |
| §1 Configuración y entrevista | Hecho |
| §2 Lectura web | Hecha: una dirección, tres pestañas. **Falta el PDF** |
| §3 Harness | Hecho |
| §4 Memoria | Hecho |
| §5a Validadores programáticos | Hecho |
| §5b Semánticos | Hecho: Continuista y Crítico, **corriendo en producción** |
| §5c Lean 4 | Hecho, **y detiene la publicación** (`CA-21`) |
| §5d TLA+ / TLC | Hecho, con correspondencia comprobada contra el código |
| §5 Evals | **Parcial**: falta la tabla de los cinco briefs y el *tuning* |
| §6 Observabilidad | Hecho: observador, *scores*, coste y latencia |
| §7 Guardarraíles | Hecho: hook de policy, vetos normalizados, auditoría |

### Lo que falta, por orden de importancia

1. **Una novela completa generada.** Es lo único que demuestra que el sistema funciona de principio a fin, y el encargo la pide como `ejemplos/novela-ejemplo.pdf`, con esa ruta exacta.
2. **El PDF**, que está escrito como tarea firmada y sin ejecutar sobre una novela real.
3. **La petición de cambio del lector** (`CA-25`), que es la Fase 5 entera.
4. **La tabla de los cinco briefs y la iteración de *tuning***.
5. **`/presentacion/`** — lo escribe `maujimenez4`, no un agente.

---

## Los dos bloqueos vivos

### 1 · El modelo anonimiza el nombre del destinatario

Con el brief de ejemplo, el outline sale **correcto y personalizado** —usa el perro Luna y el verano en Cádiz— y el protagonista se llama `[NOMBRE_ANONIMIZADO]`, con sufijo numerado para distinguir personajes.

**No es un defecto del código.** Es una política de protección de datos personales aplicándose sobre la salida del modelo. Hace bien su trabajo; lo que pasa es que aquí **el nombre es el producto**, y una novela de regalo cuyo protagonista se llama así no es una novela con un fallo, es un objeto inservible.

**La solución acordada:** que el nombre no lo escriba el modelo. Los agentes trabajan con un marcador y el sistema lo sustituye **en código** al servir. Cumple la política mejor que lo de hoy —el nombre real deja de entrar en el prompt y de subir con la traza a Langfuse (`CLAUDE.md` §4.3)— y es comprobable con un test, que es lo que §10 pide de cualquier regla que importe.

Dos cosas a decidir al hacerlo: **si el canon guarda el marcador o el nombre** —recomendado el marcador, para que la sustitución siga siendo un único punto— y **contra qué texto comparan los vetos y `nombres_literales`**.

### 2 · La escalada no deja nada que revisar

El capítulo 1 escaló a revisión humana tras tres intentos. El ciclo hizo lo que `CLAUDE.md` §9.1 manda. **Lo que no funciona es lo que viene después:** trabajo en `ESCALADA`, cero texto, tres ejecuciones marcadas `rechazada` **sin un solo código de defecto**, y ni una fila en `defecto`.

Así que **no se sabe si el modelo escribió mal tres veces o si hay un validador atascado rechazando siempre**. Con los datos de hoy las dos hipótesis son indistinguibles.

«Revisión humana» es hoy un estado al que se llega y del que no se sale. El arreglo —conservar el último texto y los defectos de los tres intentos— estaba en curso al escribir esto.

---

## Datos medidos, no estimados

| | |
| --- | --- |
| **Un capítulo** | ~8 minutos con los cinco roles |
| **Una novela** | **hora y media larga**. No hay novela «en diez minutos» |
| **Llamada del Escritor** | 0,0198 USD · 3.970 tokens |
| **Novela entera** | ~1,5 USD todo en Haiku, frente a ~8,8 con el reparto Haiku/Opus |
| **Sobrecarga del CLI** | 33.000–49.000 tokens por llamada, medidos en corrida real |
| **TLC** | 65.601 estados distintos, profundidad 45, sin error |
| **Lean** | 1,1 s con 2 eventos · 2,4 s con 40. Lo cuadrático no muerde a esta escala |

**El capítulo 1 sale con el paquete de contexto a cero en todas las capas de memoria.** Es correcto siendo el primero, pero significa que **el Continuista del capítulo 1 no tiene nada contra qué contrastar**: su valor empieza en el 2, y un `CON-*` en el capítulo 1 es imposible por construcción.

---

## Cómo levantarlo

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn --factory app.main:crear_app --app-dir src/backend

cd src/frontend && pnpm install && pnpm dev
```

Hace falta el binario `claude` instalado y autenticado: el sistema usa **consumo de cuenta, sin clave de API** (P-02, P-08).

`pnpm install` regenera el cliente de API desde `openapi.json`, que **sí** está en el repositorio. El cliente generado no: se regenera y commitearlo invita a tocarlo.

**Si tocas un endpoint, regenera `openapi.json`.** Hoy nadie lo comprueba, y un contrato que nadie comprueba deja de ser un contrato — queda apuntado como deuda.

---

## Cómo se reparte el trabajo entre sesiones

Lo que ha funcionado, por si se repite:

- **Una tarea por sesión, y una feature por sesión dentro de una ola.** Dos agentes en el mismo fichero es el problema, no dos agentes.
- **Las junturas tienen dueño desde el reparto.** Quién exporta qué por el `__init__`, quién cablea. Descubrirlo al integrar es lo que costó tres de los diez fallos de arriba.
- **El que integra no escribe features.** Commitea, pasa las puertas, resuelve junturas y decide lo que cruza fronteras.
- **Pedir el rojo en el informe.** «Enséñame el rojo» cambió lo que se entregaba: varios agentes cazaron sus propios tests inútiles al tener que enseñar el fallo.
- **Lo que un agente encuentra y no puede arreglar, lo dice y no lo toca.** Tres de los hallazgos de hoy salieron así.
