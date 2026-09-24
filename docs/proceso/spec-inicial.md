# Spec inicial — qué se decidió construir, y por qué, antes de escribir código

**Qué es este documento.** El resumen de las dos especificaciones del repositorio tal y como
se firmaron **antes de la primera línea de código**, con el razonamiento que las sostiene.
No las sustituye: las fuentes son [`specs/001-backend-v1/spec.md`](../../specs/001-backend-v1/spec.md)
y [`specs/002-frontend/spec.md`](../../specs/002-frontend/spec.md), y si algo discrepa, gana
la spec.

**Por qué hay spec, y por qué solo dos.** `CLAUDE.md` §3.2 pone cuatro puertas —Spec, Plan,
Código, Cierre— y la tercera dice literalmente que no se escribe código hasta que el plan
**de esa fase** esté aprobado por una persona en un commit suyo. La decisión de
`maujimenez4` del 2026-09-23 fija que el repositorio tendrá **exactamente dos** specs, una
por lado, y que el resto del entregable se construye sin ceremonia de spec y se documenta en
`docs/`. El motivo está escrito y contradice lo que `CLAUDE.md` decía antes: cuatro puertas
por área no caben en el plazo, y el encargo **no pide una spec por área** — pide `docs/` con
la documentación de proceso. Lo que se retiró fue la ceremonia, no el rigor: el TDD, las
fronteras, el vocabulario y el checklist siguen enteros.

---

## 1. El problema, antes que la solución

**Una novela personalizada se rompe por dos sitios a la vez, y ninguno se ve mirando un
capítulo suelto.**

**Por la coherencia.** La novela no cabe en una llamada, y meterla entera empeora el
resultado. Se escribe por partes, y cada parte por separado parece correcta: el capítulo
siete no sabe que el cuatro dijo otra cosa. A diez capítulos esto **no se afloja, se
aprieta** — el destinatario se la lee de una sentada y compara sin esfuerzo.

**Por la personalización.** El destinatario existe, conoce de primera mano la mitad de los
hechos y **detecta errores que ningún editor podría detectar**. Si el perro se llama Luna en
el capítulo siete, no lo lee como un descuido: lo lee como que el regalo no era para él.

Lo sufren tres personas distintas, y el vocabulario las separa a propósito
(`docs/definitions.md`): el **Comprador**, que encarga y no sabe si lo que pidió llegó al
texto; el **Destinatario**, que recibe; y el **Autor**, que no puede responder por qué una
novela salió como salió.

**Y el criterio que gobierna todo lo demás:** el sistema **no optimiza por que los datos
aparezcan**. Una novela que menciona al destinatario quince veces sin sostenerse como
historia ha fallado igual que una impecable en la que no está. De ahí salen dos familias de
validadores que se miden por separado y ninguna rescata a la otra.

---

## 2. La 001 — el backend: de la entrevista a la novela publicada

**Estado:** `aprobada`, v3.2 firmada por `maujimenez4` el 2026-09-24. **125 requisitos** —14
de interfaz, 99 funcionales, 6 de datos, 6 no funcionales— y **37 criterios de aceptación**.

### 2.1 Es una spec única y grande a propósito

Cubre **el backend entero**, y eso fue una decisión, no una omisión: las piezas no se pueden
entregar por separado —un ensamblador sin orquestador no se prueba, un orquestador sin
memoria no cierra el bucle, y una publicación sin validadores no es una publicación— y
trocearlas habría multiplicado las puertas sin añadir información.

**Y reemplaza a una spec anterior, aprobada el 2026-09-22, que describía otro producto:** el
ciclo completo de una escena para una novela larga de 80.000–120.000 palabras. El producto
es otro —diez capítulos personalizados para una persona concreta, con entrevista,
guardarraíles, observabilidad, verificación formal y publicación— y casi nada de aquel
alcance sobrevivió. Mantenerla en `aprobada` con este contenido habría sido **afirmar que
alguien firmó algo que no leyó**.

### 2.2 Qué entra en el alcance, y con qué justificación

| Capacidad | Encargo | Por qué entra |
| --- | --- | --- |
| Entrevista: datos del Destinatario, vetos, texto libre no confiable, brief validado | §1 | Es la mitad del producto |
| Detección de faltantes y de al menos un tipo de contradicción | §1 | Una contradicción del brief **no se arregla escribiendo mejor** |
| Ciclo de capítulo: planificar, ensamblar, escribir, validar, reparar, integrar | §3 | Es el motor |
| Presupuesto por capa y **los dos techos de 100.000 tokens** | §7 | Restricción no negociable, y el concurrente es literal del encargo |
| Orquestador con estado persistido y **checkpoint por capítulo** | §4 | Sin él, una caída pierde la novela |
| *Story bible* en SQLite: canon con uso por capítulos, ledger, cronología, resúmenes | §4 | Cierra el bucle entre capítulos, y es la entrada de Lean |
| Guardarraíles en tres ámbitos con normalización, y registro de auditoría | §7 | Se aplican en código, antes de aceptar el capítulo |
| Validadores programáticos, con nombre y punto de ejecución | §5a | Son los que se cuentan |
| Juez con rúbrica, revisión del Autor y aceptación del Comprador | §5b | Sin revisión con rúbrica, el juez emite números que nadie contrastó |
| **Lean** sobre la cronología y **TLA+** sobre el harness | §5c, §5d | Dos sujetos distintos |
| Observabilidad en Langfuse | §6 | Sin ella no hay *tuning* documentable |
| Publicación inmutable y petición de cambio del lector | §2 | El flujo es backend; la interfaz es de la 002 |

**Fuera de alcance, con su motivo:** la interfaz de lectura (es la 002), el servidor MCP,
login y multiusuario, *linters* de prosa más allá de los obligatorios, edición manual con
*linter* en vivo, y despliegue, pagos, ilustraciones y audio —excluidos por escrito en el
encargo—.

**Y una fila de «fuera de alcance» que dice lo contrario y por eso importa:** el **filtro
estructural** de la recuperación híbrida **no está excluido, se implementa aquí**
(`RF-CTX-04`). Se nombra porque en la versión anterior de la spec quedó como deuda declarada
**con un requisito que decía estar probado**, y ese error no debía repetirse.

### 2.3 Los cinco criterios que deciden si el sistema existe

De los treinta y siete, cinco son el producto y los otros treinta protegen partes:

| | Qué afirma | Estado hoy |
| --- | --- | --- |
| **CA-1** | Sale una novela entera de diez capítulos, de principio a fin | **Cerrado** (Fase 3) |
| **CA-5** | Se mata el proceso y se reanuda sin duplicar ni perder capítulos | **Cerrado** (Fase 3) |
| **CA-7** | El presupuesto falla **antes** de llamar, nunca trunca en silencio | **Cerrado** (Fase 1–2) |
| **CA-21** | Lean detiene una publicación con una cronología imposible | **Falta entero** |
| **CA-25** | Una petición del lector no rompe lo que ya estaba | **Falta entero** |

### 2.4 Lo que la spec declaró que **no** verifica

Se escribió en la propia spec, antes de implementar nada, y sigue siendo cierto:

- Que la novela **se lea bien** — ningún test juzga prosa. Es **U** y sigue siéndolo.
- Que el **Destinatario se reconozca** — la cobertura comprueba que el dato **está**, no que
  haga algo. Solo lo sabe él.
- Que un hecho nuevo **deba** entrar en el canon — el grafo solo sabe si algo **choca**.
- Que el juez **acierte** — la revisión humana mide la distancia entre dos jueces.
- El **coste total** de una novela — el techo es por llamada; nada acota la suma.
- Que la especificación **TLA+ siga correspondiendo al código** — es una inspección que
  nadie repite cuando el orquestador cambia.
- Que «fuera de Langfuse no sale nada» **se cumpla** — es una promesa que ningún método
  vigila.

---

## 3. La 002 — el frontend: la lectura del regalo

**Estado:** `aprobada`, firmada por `maujimenez4` el 2026-09-24. **Su plan sigue en
`borrador`, y `src/frontend/` no existe.**

**El problema que resuelve, dicho en una frase:** *un regalo deja de serlo cuando se le ve la
máquina.* Si la página parece un panel de administración —con versiones, estados y botones de
regenerar— el regalo se convierte en una demostración de producto. Y si la ficha de
personajes enseña en la portada al personaje del capítulo nueve, le ha destripado el regalo
antes de empezarlo.

**Y hay una segunda persona con necesidades opuestas.** El Comprador es quien detecta que el
perro se llama Luna y debería llamarse Nala, y necesita exactamente lo que el Destinatario no
debe ver: el hecho concreto, el botón de corregirlo y la respuesta de qué capítulos
cambiaron. Los dos llegan por un enlace, sin cuenta y sin contraseña —el login está fuera del
encargo—, y **la misma novela tiene que presentarse de dos maneras**.

**Depende de la 001 y no la duplica.** Todo lo que consume —versiones publicadas, ficha, PDF,
peticiones de cambio— lo produce el backend, y donde necesita algo que la 001 no promete, se
dice con todas las letras en vez de darlo por hecho.

---

## 4. Lo que la spec fijó y no se decide dos veces

**El stack es fijo, y la columna de origen no es adorno:** separa lo que impone el encargo
—que no se reinterpreta— de lo que elegimos nosotros —que se cambia con ceremonia, pero se
puede cambiar—. Confundir las dos cosas produjo el error que corrigió P-06.

| Restricción | Origen |
| --- | --- |
| **SQLite**, sin segundo motor | **Encargo §4, literal:** «story bible en SQLite (obligatorio)» |
| **Techo de 100.000 tokens concurrentes** | **Encargo §7, literal** |
| **Langfuse**, **Lean 4**, **TLA+/TLC** | **Encargo §6, §5c y §5d** |
| FastAPI + Pydantic v2 | **Nuestro**, presupuesto por el encargo |
| React 19 + TypeScript + Vite | **Nuestro.** El encargo dice «web o PDF» y no nombra tecnología |
| Techo de 100.000 tokens **por llamada** | **Nuestro**, derivado del presupuesto por capas |
| Anthropic por consumo de cuenta, **sin clave de API**; Haiku escribe, Opus juzga | **Nuestro** (P-02) |
| `sqlite-vec` **opcional** | **Nuestro.** El encargo no menciona vectores en ninguna parte |

---

## 5. Lo que se descubrió escribiendo la spec, y cambió la spec

Esto es lo que `CLAUDE.md` §3.4 manda hacer —«si al implementar descubres que la spec está
equivocada, **para**: se corrige, se vuelve a aprobar»— y ocurrió **tres veces antes de
escribir código**, que es el momento más barato:

1. **P-07 · «Un fichero por obra» se retira.** Lo destapó escribir el plan de la Fase 1 al
   preguntarse dónde vive una **entrevista que existe antes que su obra**. Y al tirar del
   hilo apareció que el encargo nunca lo pidió: lo obligatorio es SQLite. **No es aditivo:
   retira algo que estaba firmado**, y por eso la spec volvió a `en-revision` y se firmó otra
   vez.
2. **P-06 · Los dos techos de tokens no eran el mismo.** Los documentos decían que los
   100.000 eran «por llamada» y «el único techo de tokens». El encargo §7 dice
   «**concurrentes**», que es una suma. Mientras la concurrencia fue 1 los dos números
   coincidían y el sistema cumplía **por consecuencia, no por regla**.
3. **P-05 · Quién aprueba la novela y quién calibra al juez son dos personas distintas.** Se
   había asumido que el Comprador puntuaría la rúbrica criterio a criterio. Se había
   declarado como **supuesto** en vez de darlo por hecho, y por eso se pudo preguntar y
   corregir el mismo día: de un sí o un no no sale ninguna comparación por criterio, así que
   la revisión con rúbrica la hace el **Autor** y el Comprador acepta o rechaza la entrega.

El razonamiento completo de las tres, con sus alternativas, está en
[`trade-offs.md`](trade-offs.md).

---

## 6. Qué se ha construido de esta spec, y qué no

A 2026-09-24, tres fases del backend cerradas y **ninguna del frontend**:

| | |
| --- | --- |
| **670 tests** | `pytest`, y 669 + 1 *skipped* sin la extensión vectorial |
| **21 tablas, 2 vistas derivadas, 3 disparadores** | migradas, con `upgrade → downgrade base → upgrade` en limpio |
| **8 rutas** de las quince previstas | el servidor levanta y las publica |
| `CA-1`, `CA-5`, `CA-7` | tres de los cinco criterios que deciden si el sistema existe |
| `mypy` estricto, `ruff`, `lint-imports` | en verde sobre 78 ficheros de producción |

**Lo que falta entero:** la lectura web, Lean, TLA+, Langfuse, el juez con rúbrica, la
revisión humana y las cinco evals. El cruce completo, sección a sección del encargo, está en
[`specs/estado-del-entregable.md`](../../specs/estado-del-entregable.md), y no se duplica
aquí porque dos copias de un estado divergen.
