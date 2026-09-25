# Spec inicial — qué se decidió construir, y por qué, antes de escribir código

**Qué es este documento.** El resumen de las dos especificaciones del repositorio tal y como
se firmaron **antes de la primera línea de código**, con el razonamiento que las sostiene.
No las sustituye: las fuentes son [`specs/001-backend-v1/spec.md`](../../specs/001-backend-v1/spec.md)
y [`specs/002-frontend/spec.md`](../../specs/002-frontend/spec.md), y si algo discrepa, gana
la spec.

**Es historia, y se deja como historia.** Lo que se enmendó después de firmar no se reescribe
aquí encima: va en [§7, «Qué cambió desde la spec inicial»](#7-qué-cambió-desde-la-spec-inicial).
Solo se han corregido las frases que afirmaban algo falso **sobre hoy**.

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

**Estado al firmarse:** `aprobada`, v3.2 firmada por `maujimenez4` el 2026-09-24. **125
requisitos** —14 de interfaz, 99 funcionales, 6 de datos, 6 no funcionales— y **37 criterios de
aceptación**. Hoy rige la v3.3, que añade `RI-15` (§7).

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
| **CA-1** | Sale una novela entera de diez capítulos, de principio a fin | **Cerrado con dobles** (Fase 3). **Contra el modelo real no ha salido ninguna todavía** |
| **CA-5** | Se mata el proceso y se reanuda sin duplicar ni perder capítulos | **Cerrado** (Fase 3) |
| **CA-7** | El presupuesto falla **antes** de llamar, nunca trunca en silencio | **Cerrado** (Fase 1–2) |
| **CA-21** | Lean detiene una publicación con una cronología imposible | **Cerrado** (`4c6ff5c`), con una cronología provocada en test |
| **CA-25** | Una petición del lector no rompe lo que ya estaba | **Falta entero.** Obligatorio y programado al final ([`trade-offs.md`](trade-offs.md) T-32) |

### 2.4 Lo que la spec declaró que **no** verifica

Se escribió en la propia spec, antes de implementar nada, y sigue siendo cierto:

- Que la novela **se lea bien** — ningún test juzga prosa. Es **U** y sigue siéndolo.
- Que el **Destinatario se reconozca** — la cobertura comprueba que el dato **está**, no que
  haga algo. Solo lo sabe él.
- Que un hecho nuevo **deba** entrar en el canon — el grafo solo sabe si algo **choca**.
- Que el juez **acierte** — la revisión humana mide la distancia entre dos jueces.
- El **coste total** de una novela — el techo es por llamada; nada acota la suma.
- Que la especificación **TLA+ siga correspondiendo al código** — es una inspección que
  nadie repite cuando el orquestador cambia. *Hoy un test compara las transiciones del código
  con las reclamadas por la especificación (`e76ab85`); que el modelo capture lo que importa
  sigue siendo inspección.*
- Que «fuera de Langfuse no sale nada» **se cumpla** — es una promesa que ningún método
  vigila.

---

## 3. La 002 — el frontend: la lectura del regalo

**Estado:** `aprobada`, firmada por `maujimenez4` el 2026-09-24. Cuando se firmó,
`src/frontend/` no existía; hoy existe, con cuatro planes (§6).

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
| Anthropic por consumo de cuenta, **sin clave de API**; Haiku escribía y Opus juzgaba. **Hoy, Haiku 4.5 en todos los roles** (§7) | **Nuestro** (P-02) |
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

**El estado vive en un solo sitio**, [`specs/estado-del-entregable.md`](../../specs/estado-del-entregable.md),
y no se copia aquí: la primera versión de esta sección copió cifras (`63363e8`) y pocas horas
después ya eran falsas. En grueso, a 2026-09-24 por la tarde:

- **Construido:** los planes 1 a 3 del backend completos y la mayor parte de los 4, 6, 7 y 8
  —publicación, Lean, TLA+, hook de policy, Crítico y Continuista en el ciclo, Langfuse en
  código—; el frontend con una dirección, tres pestañas y la apariencia del plan 4.
- **Falta:** la petición de cambio (`CA-25`), el PDF, la revisión humana, las evals, la
  validación visual y **una novela entera contra el modelo real**, que es de lo que cuelga casi
  todo lo demás.

---

## 7. Qué cambió desde la spec inicial

Lo que se enmendó o se decidió **después** de firmar, en orden. Cada entrada apunta a donde
está razonada; aquí solo se dice qué dejó de ser cierto de lo de arriba.

| Qué | Cuándo y dónde | Qué cambia de este documento |
| --- | --- | --- |
| **v3.3 de la 001:** entra `RI-15` (`POST /obras/{id}/novela`) y `CA-33` pasa de catorce a **dieciséis** endpoints | Spec 001, §Cierre, firmada | «14 de interfaz» pasa a 15. **`CA-33` sigue sin cumplirse (P-3, reabierto):** `openapi.json` publica hoy dieciséis operaciones, pero no las de la spec —faltan `RI-09`, `RI-10` y `RI-12`, `RI-11` se sirve como `/lectura/{token}/…` y hay dos que la spec no nombra, `GET /obras/{id}/novela` y `GET /trabajos/{id}/intentos`—. Cerrarlo es cambio de requisito y vuelve a firma |
| **P-02 revisada:** Haiku 4.5 en todos los roles, por coste medido | Spec 001, P-02; `b80e911` | La fila de §4. El juez comparte modelo con el Escritor ([`trade-offs.md`](trade-offs.md) T-16) |
| **P-09:** una versión publicada puede llevar menos de diez capítulos, salvo por veto | Spec 001, P-09; `fc596a7` | Matiza `CA-1`: publicar no exige diez capítulos si uno escaló |
| **D-06 y D-07 de la 002:** la lectura deja de tener cinco rutas; una dirección y tres pestañas | Spec 002 | Lo que §3 separa entre Comprador y Destinatario se separa **por estado dentro de una sola página**, no por rutas: la entrevista no se muestra a quien llega con un enlace que no generó ([`trade-offs.md`](trade-offs.md) T-3) |
| **Enmienda 1 del plan 4 del frontend:** «Cuaderno de viaje», interfaz en serif y siempre en claro | `plan-4-apariencia-de-lectura.md`; `d5207bd`, `cd2f38c` | Nada de la spec: cambia la piel, no los requisitos ([`trade-offs.md`](trade-offs.md) T-30) |
| **Enmienda `trato` del plan 8:** el brief gana `trato ∈ {ella, el, neutro}` | `plan-8-corrida-real.md` T2, **firmada y no ejecutada** | Ninguno: la sonda (`38924c3`) mostró que el marcador no resolvía el anonimizado, y T2–T3 no se hicieron. **La spec no tiene hoy ese campo** ([`trade-offs.md`](trade-offs.md) T-26) |
| **Las evals, en dos o tres novelas completas** en vez de cinco briefs | `maujimenez4`, 2026-09-24 | §2.2 y la lista de §6: el encargo §5 pide cinco, y la entrega quedará por debajo de esa letra ([`trade-offs.md`](trade-offs.md) T-31) |
