# Evals del sistema

Encargo §5, «Evaluación del sistema»: cinco briefs (uno adversarial, uno temporal), una tabla
por brief y una iteración de *tuning* con antes y después. Plan: `specs/001-backend-v1/plan-6-medir.md`
T9–T11, recortado por **T-31** (`docs/proceso/trade-offs.md`): **dos o tres novelas completas** y
el resto hasta el outline y el capítulo 1, para que los cinco existan y la tabla tenga cinco filas.

**Gasta cuota. Lo lanza una persona**, nunca un agente ni un test. La suite (`evals/tests/`) corre
sin red y sin modelo.

## Los cinco briefs

Ficheros en `briefs/`, cada uno un `BriefEntrada` puro (la misma forma que `ejemplos/`). Lo que no es
del comprador —modo, texto aportado, dónde se diseñó que fallara— vive en `briefs/manifiesto.json`.

| Brief | Modo | Se diseñó para fallar en | Qué mide |
| --- | --- | --- | --- |
| `b1-jubilacion` | **completa** | ninguno | Control: recorre todas las puertas y publica |
| `b3-trampa-temporal` | **completa** | `cronologia_lean` | RF-FOR-04 contra los invariantes **que existen** (P-27): `sinUbicuidad` y `sinReaparecidos` |
| `b5-cobertura-imposible` | **completa si hay cuota**, si no `capitulo_1` | `cobertura_de_personalizacion` | 12 elementos para 10 capítulos; G4 dice cuál falta |
| `b2-inyeccion` | `capitulo_1` | ninguno (y ése es el resultado) | Inyección en `texto_aportado` **y** en `recuerdos_aportados`; testigos: `discurso` (VOZ-03) y `testigo_inyeccion` |
| `b4-veto-colision` | `capitulo_1` | `palabras_vetadas` | El recuerdo central pasa en un hospital y el comprador veta «hospital» |

**B3, rediseñado por P-27.** El plan lo diseñaba contra un invariante de edad que Lean no tiene. Ahora
apunta a los dos que sí:

- **`sinUbicuidad`**: la noche de San Juan de 1996 con Julián en la hoguera de la playa **y** en el
  faro. El `momento` del fichero Lean es el texto de `evento.tiempo_historia`, así que salta si el
  Extractor registra los dos eventos con el mismo `tiempo_historia` y lugares distintos.
- **`sinReaparecidos`**: la partida definitiva del abuelo Tomás (un `excluye[]`) y él presente
  después en el muelle. Ojo: `momento` es **orden de aparición**, no tiempo de la historia
  (`plantilla.lean` lo dice), así que un salto atrás posterior a la partida también salta. Si pasa
  eso, es un falso positivo de Lean y se escribe como tal.

**Las dos cosas dependen del Extractor.** Si no registra los eventos así, Lean no ve nada, y la
respuesta que pide el encargo §5c es la otra: «justificar por qué no se encontró ninguno».
También puede ser que el Entrevistador marque B3 como contradictorio al cerrar: la tabla lo pone
en la columna `entrevista`, y eso también es un resultado (lo cazó antes que Lean).

## Cómo se corre, en orden

Prefijo de cada consola:

```powershell
cd C:\Users\mauricio.jimenez\ciberpunk-storymaker
$env:Path = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe;$env:Path"
```

**1. Backend levantado**, en una consola aparte y con el `claude` CLI autenticado (P-15). Las
variables de Langfuse en el entorno si se quiere el juez en la tabla. Lean instalado
(`formal/README.md`): sin Lean, `publicar` no publica.

```powershell
uv run alembic upgrade head
uv run uvicorn --factory app.main:crear_app --app-dir src/backend
```

**2. Los cinco briefs**, en paralelo contra ese mismo proceso:

```powershell
uv run python evals/correr.py
```

Va dejando cada paso en `evals/resultados/corridas.json`. Si algo se cae (el corredor, el backend),
se reanuda sin repetir lo hecho:

```powershell
uv run python evals/correr.py --reanudar
```

Si no da la cuota para tres novelas, B5 al modo parcial **antes** de lanzar:

```powershell
uv run python evals/correr.py --modo b5-cobertura-imposible=capitulo_1
```

Opciones: `--solo b1-jubilacion b3-trampa-temporal`, `--en-serie`, `--sondeo 60`,
`--base http://127.0.0.1:8000`.

**3. La tabla** (se puede regenerar cuantas veces se quiera, también a mitad de corrida):

```powershell
uv run python evals/tabla.py              # solo la base
uv run python evals/tabla.py --langfuse   # + la media del juez, leída de Langfuse
```

Escribe `evals/resultados/tabla.md`: por brief, qué validador pasó, falló (y se reparó), escaló o no
corrió; y tokens, caché, coste imputado, reloj y latencia de modelo.

**4. La revisión humana** de al menos una novela completa (B1), con la rúbrica del juez:

```powershell
uv run python evals/revision_humana.py rubrica                                  # leerla antes de leer la novela
uv run python evals/revision_humana.py puntuar --obra <ID_B1> --revisor maujimenez4
uv run python evals/revision_humana.py comparar --obra <ID_B1> --langfuse
```

`puntuar` pregunta criterio a criterio (valor 1–5 y justificación obligatoria), o lee
`--desde notas.json` con `{"criterio": {"valor": 4, "justificacion": "..."}}`. `comparar`
escribe `evals/resultados/distancia-obra-<ID>.md` con la distancia **criterio a criterio**. El
`<ID_B1>` está en `corridas.json` y lo imprime el corredor al terminar.

**5. Commit de los resultados**: `evals/resultados/tabla.md`, `corridas.json` y `distancia-*.md`.
Llevan ids, estados, códigos y números; **ninguna prosa** (RD-06). Las novelas se quedan en
`storymaker.db`, que no entra al repositorio.

## Cómo para un brief en `capitulo_1`

**No hay endpoint de cancelar.** `POST /obras/{id}/novela` lanza una tarea de fondo que sigue con
los diez capítulos, así que el modo parcial **no la usa**: escribe con
`POST /capitulos/{capitulo_id}/escribir`, que es un único capítulo y para, y sondea
`GET /trabajos/{id}`. El `capitulo_id` del número 1 se lee de la base en solo lectura, porque
`OutlineCreado` no lo devuelve. En este modo Lean y G4 **no corren nunca**, y la tabla lo dice
(`no corrio`), no lo esconde.

## Lo que la tabla no puede saber, y por qué

- **El juez no está en la base.** `_juzgar` emite sus *scores* a Langfuse y nadie escribe
  `puntuacion` con `origen='juez'`. Por eso `--langfuse` (sesión `obra-<id>`, scores
  `juez_con_rubrica.<criterio>`). El juez **no bloquea** (RF-JUZ-06).
- **T9 no existe** (`registrar_revision_humana`, `distancia_con_el_juez`, sus endpoints).
  `revision_humana.py` escribe directamente en las tablas de T2 (`revision_humana`, `puntuacion`
  con `origen='humana'`) y siembra la rúbrica vigente si falta. Se retira cuando T9 exista.
- **Coste por capítulo**: hasta P-31 la fila del Escritor guardaba el consumo del último juez. Está
  corregido (`_foto_del_consumo`); una corrida anterior a ese commit tiene esas cifras mal.
- **`latencia_ms`** solo está donde alguien llamó a `cerrar_llamada`; donde falte, cuenta el reloj
  del corredor.

## La iteración de *tuning* (plan 6 T11)

**Qué se cambia: la plantilla del Continuista, `continuista.v1` contra `continuista.v2`**
(`features/calidad/prompts/`). Las dos existen y la v2 es la que usa el ciclo. La v2 recibe
`estado_en_t` con identificadores; la v1 no.

**Hipótesis:** con la v2 hay menos `CON-03` **mal formados** (el defecto no cita un id que exista en
la proyección, así que no bloquea y no se puede reparar) y más `CON-03` **bien formados**.

**Qué se compara, sobre los mismos capítulos:** por plantilla, `mal_formados`, `bien_formados` y
`coste_usd`. Mismas entradas, dos plantillas: se reevalúan con cada versión los capítulos ya
escritos de B1 y B3, en vez de escribir dos veces la novela. Cuesta dos llamadas por capítulo y
no diez novelas. Cada span lleva `prompt_id`, `prompt_version` y `prompt_hash`, que es lo que
permite decir qué plantilla produjo qué (CA-19, R-8).

**No se mide prosa**: sería juicio, y eso aquí es **U** (`verification.md`).

**Estado: diseñado, sin script.** `evals/tuning.py` no está escrito: montar el
`CapituloAContrastar` con el grafo y el conocimiento en T de un capítulo ya escrito exige leer las
mismas proyecciones que monta el ciclo, y no dio tiempo antes de la corrida. Lo que hay que
escribir: por cada capítulo integrado de la obra, `Continuista(cliente, plantilla=plantilla_v1())`
y `Continuista(cliente, plantilla=plantilla_v2())` sobre el mismo `CapituloAContrastar`, y contar
`RevisionDeContinuidad.defectos` y `.mal_formados`. (`plantilla_v1` vive en `calidad/agents.py`
y hoy **no sale** por `calidad/__init__.py`; `plantilla_v2` sí.) El resultado, sea bueno o malo, va a
`evals/resultados/` y su razonamiento a `docs/proceso/`.
