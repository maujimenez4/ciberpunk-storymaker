# `Harness.tla` — la máquina del sistema, verificada con TLC

Lo que pide el encargo §5d: la especificación del flujo de generación como máquina de
estados, tres invariantes de seguridad, una propiedad de *liveness*, y TLC sobre un modelo
pequeño con su configuración en el repositorio.

---

## 1. Qué se verifica, y qué no

**Dos verificaciones formales, dos sujetos distintos** (`architecture.md` §9.3):

| | Sujeto | Qué pregunta |
| --- | --- | --- |
| **Lean 4** (`../lean/`) | La **historia** | ¿La cronología de *esta* novela es coherente? |
| **TLC** (aquí) | El **harness** | ¿La máquina que escribe novelas puede hacer algo que no debe? |

**TLC no bloquea nada en ejecución.** No corre en la publicación, no corre en CI de
producción y no tiene voto sobre una novela concreta. Su resultado es un cambio en el
código o en la especificación. Lean sí bloquea: si `lake build` falla, la versión no se
publica.

La consecuencia hay que tenerla presente: **una propiedad demostrada aquí lo está sobre el
modelo.** Lo que hace que el modelo se parezca al código es la §3, y lo que se sabe que no
se parece está en la §4.

---

## 2. Cómo se corre

**TLC 2.19** (08-08-2024, rev 5a47802) sobre **OpenJDK 21.0.12.1 Temurin**. El jar está
commiteado; instalación y versiones exactas en [`../README.md`](../README.md).

```bash
cd formal/tla
java -cp tla2tools.jar tlc2.TLC -workers auto -config harness.cfg Harness.tla
```

El modelo pequeño que pide el encargo está en `harness.cfg`: **cinco capítulos y dos
reintentos**, más dos cotas propias del modelo —`MaxRondas = 2` y `MaxPeticiones = 1`—.

### Números de la última corrida · 2026-09-24

| | `Juguete.tla` (humo) | `Harness.tla` |
| --- | --- | --- |
| Estados generados | 7 | **139.224** |
| Estados distintos | 6 | **65.601** |
| Profundidad | 6 | **45** |
| Tiempo | 1,2 s | **~3 s** con `-workers auto` |

`Juguete.tla` no modela nada del sistema: es la comprobación de que TLC parsea, explora y
verifica las dos clases de propiedad. Está para que un fallo de instalación no se confunda
con un fallo del modelo.

**La explosión de estados se midió y no hizo falta recortar nada.**
`PeticionDelLector` elige entre los **31** subconjuntos no vacíos de cinco capítulos, que
era el riesgo. Tres segundos: el modelo conserva los 31 y no se restringe a un capítulo,
así que cubre más de lo que la salida de emergencia habría cubierto.

---

## 3. La correspondencia con el código

La fuente es [`correspondencia.toml`](correspondencia.toml); esta tabla es su lectura. Un
test —[`test_correspondencia_tla.py`](../../src/backend/app/features/escritura/tests/test_correspondencia_tla.py)—
falla si las dos listas de transiciones dejan de coincidir, si una acción no aparece en la
tabla, si un símbolo emparejado no existe, o si uno declarado *previsto* empieza a existir.

**Lo que ese test comprueba es que las listas coincidan y que los símbolos existan. Que la
acción haga lo que su nombre dice sigue siendo inspección**, y así está clasificado en
`verification.md` §7.

La especificación abarca **tres sitios del código**, no uno: el ciclo (`maquina.py`), la
reanudación (`checkpoint.py`, `reanudacion.py`) y las versiones publicadas
(`features/manuscrito/`, Fases 4 y 5).

| Acción | Dónde vive en el código | Estado |
| --- | --- | --- |
| `FaltaUnDato` | `obra.service.responder_entrevista` | Implementado |
| `Planificar` | `obra.service.cerrar_entrevista` · `outline.service.planificar_obra` | Implementado |
| `SiguienteCapitulo` | `escritura.checkpoint.siguiente_capitulo` · `.empezar_capitulo` · `escritura.novela.escribir_novela` | Implementado |
| `Escribir` | `escritura.ciclo.ejecutar_ciclo` · `escritura.service.escribir_capitulo` | Implementado |
| `Aprobar` | `calidad.puerta.cruzar_g1a` · `canon.service.consolidar_escena` · `escritura.checkpoint.registrar_checkpoint` | Implementado |
| `Reparar` | `escritura.service.escribir_capitulo` | Implementado |
| `Escalar` | `escritura.maquina.transitar` · `.exigir_que_la_novela_siga` | Implementado |
| `Reanudar` | `escritura.reanudacion.reanudar` · `.descartar` | Implementado |
| `Verificar` | `manuscrito.lean.generador.generar_cronologia` | **Previsto** — Fase 4 |
| `Publicar` | `manuscrito.service.publicar` | **Previsto** — Fase 4 |
| `LeanFalla` | `manuscrito.service.publicar` | **Previsto** — Fase 4 |
| `PeticionDelLector` | `manuscrito.peticiones.registrar_peticion` | **Previsto** — Fase 5 |
| `RehacerCapitulo` | `manuscrito.peticiones.atender_peticion` | **Previsto** — Fase 5 |
| `DescartarPeticion` | `manuscrito.reversion.revertir` | **Previsto** — Fase 5 |
| `Fin` | `escritura.maquina.ESTADOS_TERMINALES` | Implementado |

**Quince acciones, no catorce.** El plan de la fase dice «las catorce acciones del `Next`»
en cuatro sitios; son quince desde que T3 añadió las tres de la regeneración. La cuenta que
manda es la del `.toml`, porque es la que el test compara.

**Cinco transiciones del código que ninguna acción reclama** están declaradas en el `.toml`
con su motivo: la avería técnica (`ENSAMBLANDO → FALLIDA` por contexto excedido) y las
cuatro cancelaciones del Autor. No es que se hayan olvidado: §3.9 no las tiene, y el modelo
no inventa estados que su documento no dibuja.

---

## 4. Qué NO modela, y por qué

Declarado aquí porque un modelo que no dice lo que deja fuera promete más de lo que
demuestra.

1. **La cancelación del Autor.** `_TRANSICIONES` la tiene en cuatro estados; §3.9, la
   máquina de la novela, no. Declarada en el `.toml`, no modelada.
2. **La avería técnica.** `ENSAMBLANDO → FALLIDA` por presupuesto de contexto excedido. Un
   capítulo `FALLIDA` detiene la novela por la vía de `escribir_novela`, que exige
   `INTEGRADA`; el modelo no distingue esa detención de la de `Escalar`.
3. **Si un capítulo regenerado hereda su contador de reintentos.** `RehacerCapitulo` no
   toca `intento`. **Es pregunta abierta de la Fase 5**, no una decisión tomada aquí.
4. **La regeneración siempre aprueba.** `RehacerCapitulo` no tiene rama de fallo, así que
   el modelo no puede exhibir una petición del lector que deje un capítulo sin validar.
   Esto es lo que hace **redundante** la guarda `TodosValidados` de `Publicar` — ver §5.
5. **Una caída en `ESCRIBIENDO_CAPITULO` es *stuttering*.** No cambia ninguna variable
   observable, porque la prosa no llegó a confirmarse; por eso no es una acción.

**Y una cota que no es del modelo, sino una decisión pendiente de firma.** `MaxRondas`
acota el bucle de la entrevista. `architecture.md` §3.9 ganó el 2026-09-24 la flecha
`CONFIGURANDO → DETENIDA` —antes el bucle no tenía salida, y **una máquina con un bucle no
acotado no puede cumplir ninguna propiedad de *liveness***—. Pero ese mismo apartado
declara que `spec.md` **no tiene requisito** para ese límite y que **el código no lo
implementa todavía**. Así que la cota del modelo corresponde a una decisión de arquitectura
escrita y sin firmar, no a código: es la tercera categoría, y conviene no confundirla con
las otras dos.

---

## 5. Los contraejemplos

**Los cuatro de abajo son de laboratorio:** el modelo se rompió a propósito para ver caer
cada comprobación. Un invariante que nunca se vio fallar no comprueba nada, y en TLA+ el
riesgo es mayor que en un test, porque es fácil escribir uno verdadero por vacuidad.

**Si aparece un contraejemplo de verdad, va en esta sección con el commit que lo arregló.**
Hoy no hay ninguno: la máquina se escribió contra código ya probado.

| # | Qué se rompió | Resultado |
| --- | --- | --- |
| 1 | `Reanudar` sin su guarda `actual \notin integrados` | `Invariant ReanudacionIntegra is violated` |
| 2 | `DescartarPeticion` sin devolver `integrados` a la vigente | `Invariant LecturaIgualALaVigente is violated` |
| 3 | `Aprobar` integra sin validar, y `Publicar` sin `TodosValidados` | `Invariant PublicadaSoloConPuertas is violated` |
| 4 | `Reanudar` reinicia el contador, con `WF` en vez de `SF` sobre `Aprobar` | `Temporal properties were violated` |

### Los dos que hubo que diagnosticar

**S1 es redundante, no vacua — y la diferencia importa.** Quitar solo `TodosValidados` de
`Publicar` **no** da contraejemplo. El motivo no es que el invariante sea débil: es que en
este modelo **integrar y validar son el mismo evento**. `Aprobar` y `RehacerCapitulo` fijan
`validado` e `integrados` atómicamente, y `DescartarPeticion` los restaura desde una versión
cuyos capítulos estaban todos validados. Luego `Pendientes = {}` ya implica
`TodosValidados`, y la guarda no aporta nada. Que el invariante **sí** tiene dientes está
probado por el contraejemplo 3, que rompe además la atomicidad.

Lo que esto deja declarado: **el modelo no puede exhibir un capítulo publicado sin pasar su
puerta**, porque fusiona `EXTRAYENDO` e `INTEGRADA` en `Aprobar`. El sistema real sí
distingue los dos, así que esa garantía se apoya en la §3 y no en TLC.

**La terminación la sostiene la equidad, no la cota de reintentos.** Reiniciar el contador
en `Reanudar` —que es la forma plausible de modelar «se cayó y se relanza»— **no viola
nada**. Con `SF_vars(Aprobar)`, `Aprobar` acaba ocurriendo esté como esté el contador. La
*liveness* solo cae cuando además se baja a `WF` (contraejemplo 4). Así que el contador
sostiene **la cota** —`TypeOK`, que es el cuarto ejemplo del encargo §5d— y **no** la
terminación.

---

## 6. Las hipótesis de equidad, en prosa

Un modelo sin equidad no demuestra ninguna *liveness*: nada obliga a que una acción
habilitada llegue a ocurrir, y «se queda parado para siempre» es una ejecución válida.
`Spec` declara por eso `Equidad`, y **la propiedad de terminación vale exactamente lo que
valga esa hipótesis**.

`WF` —equidad débil— sobre una acción significa: *si está habilitada de forma continua,
acaba ocurriendo*. Basta para `Planificar`, `SiguienteCapitulo`, `Escribir`, `Escalar`,
`Verificar`, `Publicar` y `RehacerCapitulo`.

**`SF` —equidad fuerte— sobre `Aprobar`, y es la única.** `Aprobar` no está habilitada de
forma continua: entre dos habilitaciones hay una vuelta por `ESCRIBIENDO_CAPITULO`, donde
está deshabilitada. La equidad débil no la forzaría, y los dos bucles que pueden no
terminar —el de reparación y el de caída— quedarían abiertos.

**Qué significa eso, dicho sin adornos.** La propiedad **no** dice que las caídas cesen ni
que el escritor acabe acertando. Dice: **si el sistema puede aprobar infinitas veces,
aprueba.** El escenario que queda fuera no es exótico —un capítulo que el escritor nunca
logra dejar aceptable— y quien lo acota **no es el modelo**: son los dos reintentos y el
escalado a una persona, que son mecanismo del código.

`verification.md` clasifica por eso la terminación como condicional y no como demostrada a
secas. Una propiedad temporal que depende de una hipótesis de equidad sin decirlo parece
más fuerte de lo que es.
