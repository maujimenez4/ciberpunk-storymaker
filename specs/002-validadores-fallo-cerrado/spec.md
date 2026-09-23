---
id: 002-validadores-fallo-cerrado
titulo: Los validadores mecánicos fallan cerrado y son deterministas
estado: borrador          # borrador | en-revision | aprobada | implementada
aprobada_por:             # lo rellena una persona, nunca un agente
fecha: 2026-09-23
---

# 002-validadores-fallo-cerrado — Los validadores mecánicos fallan cerrado y son deterministas

Seis defectos encontrados en `features/calidad/validadores.py`, cada uno con contraejemplo
ejecutado. **Aquí no se decide cómo se arreglan:** eso es el plan, y no se escribe hasta
que esta spec esté `aprobada`.

---

## Problema

La cabecera de `validadores.py` promete una cosa concreta: que el contraste es
**determinista**, aunque la extracción del Continuista sea probabilística
(`verification.md` §6.2). Hoy esa promesa no se cumple en seis sitios, y los seis fallan
en la misma dirección peligrosa: **el validador calla o se descuadra en vez de bloquear**.

Ninguno de los seis lo habría encontrado un test de ejemplo, porque los ejemplos se
escriben con la entrada que el autor tenía en la cabeza. Cinco salieron de sondear
invariantes en alcance pequeño —la técnica de Alloy, escrita con `hypothesis`— y el sexto
de leer el acoplamiento entre dos features. El catálogo de qué técnica se adoptó y por qué
está en
[`.claude/skills/verification-methods/references/lenguajes-formales.md`](../../.claude/skills/verification-methods/references/lenguajes-formales.md).

## Alcance

- Los seis defectos de §Hallazgos, en `features/calidad/validadores.py` y en el contrato
  de datos que `features/canon` le entrega.
- Las propiedades que los detectan, incorporadas a la suite como tests permanentes: un
  arreglo sin su propiedad vuelve a caer en cuanto alguien toque la función.

## Fuera de alcance

- La **precisión léxica** de VOZ-03 (qué expresiones regulares distinguen persona y tiempo
  verbal en español). Es un problema distinto —de calidad del criterio, no de fallo en
  abierto— y merece su propia spec.
- La **tasa de falsos negativos** del Continuista. Sigue sin medirse (`verification.md`
  §6.3) y nada de aquí la mueve.
- G1b y el Crítico. Siguen en la fase 4.
- Cualquier cambio en `defectos.py::citar` o en `puerta.py`: la comprobación de forma
  funciona y los seis hallazgos son anteriores a ella.

## Hallazgos

Cada uno reproducido contra el código en el árbol el 2026-09-23. La sonda que los produjo
está en [`sonda_invariantes.py`](sonda_invariantes.py), junto a esta spec y **fuera de
`testpaths`**: es evidencia del hallazgo, no parte de la suite.

### H-1 · `validar_giro_de_valor` revienta con texto vacío — *EST-01*

    validar_giro_de_valor("duda", "duda", "", "vt1")
    -> pydantic_core.ValidationError: 2 validation errors for Defecto

La escena entra y sale en el mismo valor, así que **debe** emitirse EST-01; lo que ocurre
es una excepción de validación de esquema que sube sin tipar. La cita sale de
`texto[:40].strip()`, que con texto vacío o solo espacios no puede anclar nada. Una prosa
vacía es un modo de fallo corriente del modelo, y hoy rompe la puerta en vez de cerrarla.

### H-2 · `validar_nivel_de_calor` falla **en abierto** con un nivel fuera de escala — *SEG-01*

    validar_nivel_de_calor("Se quito la ropa y quedo desnuda ante el.", "0", "vt1")
    -> []

`_vetados` devuelve la tupla vacía para cualquier nivel que no esté en `_ESCALA`, y una
tupla vacía significa «nada prohibido». Una errata en el `nivel_de_calor` de la obra
**desactiva por completo** el único validador mecánico de la regla 5 de `CLAUDE.md` §8,
sin ruido de ningún tipo. Es el hallazgo más grave de los cinco mecánicos: un guardarraíl
de seguridad que se apaga en silencio.

### H-3 · `validar_canon` no es determinista con empate en `orden_discurso` — *CAN-01*

Con dos hechos sobre `Mara.ojos` en el mismo `orden_discurso`, el `hecho_canon_id` que
sale en el defecto depende del **orden de la lista** que se le pase:

    canon=[h2 "verdes" orden 1, h1 "negros" orden 1]  -> prevalece "verdes"
    barajado=[h1 "negros" orden 1, h2 "verdes" orden 1] -> prevalece "negros"

`sorted` es estable y `setdefault` se queda con el primero, así que el arbitraje «gana el
de menor orden» no está definido cuando hay empate. Rompe el punto 6 de `CLAUDE.md` §3
—cualquier ejecución debe poder reproducirse— y contamina el `hecho_canon_id` que el
axioma 12 obliga a declarar.

### H-4 · `validar_continuidad_fisica` no es determinista con empate en `momento` — *CON-01*

    afirmaciones=[Mara en taller (t=0), Mara en puerto (t=0)]
    -> "Mara esta en taller y puerto a la vez"
    barajado
    -> "Mara esta en puerto y taller a la vez"

El defecto se emite en los dos casos —la detección es correcta—, pero el `detalle` y la
afirmación citada cambian. El texto que llega al prompt de reparación depende del orden en
que el Continuista listó las afirmaciones, y eso hace irreproducible el reintento.

### H-5 · `validar_conocimiento` compara objetos físicos contra descripciones de evento — *CON-03*

**Hallazgo de la sesión Nubia el 2026-09-23, verificado aquí de forma independiente.**

`canon/repository.py::derivar_estado_en_t` llena `conocimientos[testigo]` con
`evento.descripcion`: texto libre escrito por el Extractor. `validar_conocimiento`
compara contra ese texto el campo `Afirmacion.objeto`, que según
`prompts/continuista.v1.md` son «objetos que se usan». Dos conceptos distintos en el mismo
campo, contrastados con **igualdad exacta de cadenas**:

    CON-03 EMITIDO <- "la carpeta"                                    (objeto fisico corriente)
    CON-03 EMITIDO <- "la confesion de Iker"                          (info que SI presencio)
    limpio         <- "Mara presencia la confesion de Iker en el puerto"  (literal del Extractor)

Solo queda limpio cuando el Continuista reproduce palabra por palabra lo que escribió el
Extractor: dos llamadas independientes a un modelo generando texto libre.

**Mitigación ya aplicada, y no la hizo esta spec.** El 2026-09-23 `maujimenez4` sacó
CON-03 y CAN-01 de `BLOQUEANTES_EN_G1A` —con RF-CAL-09 incumplido a propósito y anotado
en el código—, así que hoy el falso positivo ya **no** cuesta dos reintentos ni una
escalada. Lo que queda en pie es el fondo: el contraste sigue siendo igualdad exacta de
cadenas sobre texto libre, los dos códigos siguen registrándose en `no_bloquean`, y no
pueden volver a bloquear mientras el contraste sea ese. Esta spec cubre el fondo, no la
mitigación.

Es además un ejemplo de libro de lo que `verification.md` §6.2 llama *una señal con
varianza haciéndose pasar por determinista*: el contraste es código, pero sus dos entradas
son prosa generada.

### H-6 · `solo_narracion` se traga la narración entera desde la raya — *VOZ-03*

    texto     : —Yo no fui —dijo ella. Yo camine hasta la puerta y yo espere.
    narracion : ' '
    defectos  : []

`_DIALOGO` incluye `—[^\n]*`, que casa desde la primera raya **hasta el fin de línea**. En
español la raya abre el diálogo y la narración continúa detrás en la misma línea, de modo
que todo lo que sigue desaparece del análisis. VOZ-03 queda ciego en cualquier párrafo con
diálogo —es decir, en casi toda escena— y falla en abierto igual que H-2: devuelve lista
vacía, que la puerta lee como «sin defectos».

## Requisitos

- **RF-CAL-13** — Ningún validador mecánico devuelve lista vacía ante una entrada que no
  pertenece a su dominio declarado. Si no puede evaluar, **lanza** un error de dominio
  tipado de `commons/errors/`. *(Corrige H-2 y H-6; es la precondición explícita de §2.3
  del catálogo.)*
- **RF-CAL-14** — Todo validador es una función **total** sobre `texto`: para cualquier
  cadena, incluida la vacía y la de solo espacios, devuelve defectos o lanza un error de
  dominio, nunca un `ValidationError` de Pydantic. *(Corrige H-1.)*
- **RF-CAL-15** — La salida de un validador **no depende del orden** de sus colecciones de
  entrada: misma entrada como conjunto, misma lista de defectos con los mismos `detalle`,
  `cita` y `hecho_canon_id`. *(Corrige H-3 y H-4.)*
- **RF-CAL-16** — CON-03 contrasta **información conocida** contra **información usada**, y
  no objetos físicos contra descripciones de evento. El campo que transporta cada concepto
  está separado en el esquema y en el prompt. *(Corrige H-5.)*
- **RF-CAL-17** — Las seis propiedades viven en la suite como tests basados en
  propiedades, no como ejemplos. *(Evita la reaparición: un ejemplo arreglado no protege
  la función.)*

## Criterios de aceptación

- [ ] **CA-1** — La sonda de [`sonda_invariantes.py`](sonda_invariantes.py) pasa entera
      sobre el código de producción, sin relajar ninguna invariante. *(Test)*
- [ ] **CA-2** — `validar_nivel_de_calor(texto, nivel_no_valido, vt)` lanza, y existe un
      test que lo comprueba con un nivel que no está en la escala. *(Test)*
- [ ] **CA-3** — `validar_giro_de_valor` con `""` y con `"   "` devuelve EST-01 o lanza un
      error de dominio; en ningún caso un `ValidationError`. *(Test)*
- [ ] **CA-4** — Barajar `canon` y barajar `afirmaciones` no cambia la salida de
      `validar_canon` ni la de `validar_continuidad_fisica`, comprobado con `hypothesis`
      sobre alcance pequeño. *(Test)*
- [ ] **CA-5** — Una afirmación cuyo `objeto` es un objeto físico corriente **no** produce
      CON-03; una que usa información sin `sabe_desde` anterior **sí**, aunque esté
      redactada con otras palabras que la `descripcion` del Extractor. *(Test)*
- [ ] **CA-6** — Un párrafo con diálogo y narración en la misma línea conserva la narración
      en `solo_narracion`, y VOZ-03 la evalúa. *(Test)*
- [ ] **CA-7** — La tasa de defectos mal formados sobre la corrida de CA-1 de la spec 001
      no empeora. *(Demostración)*

## Reglas de dominio afectadas

| Regla de `CLAUDE.md` §8 | Hallazgo | Cómo se respeta |
| --- | --- | --- |
| 2 — sin `sabe_desde` anterior no se usa información | H-5 | El contraste pasa a comparar información con información |
| 5 — ninguna escena excede el `nivel_de_calor` | H-2 | El validador deja de apagarse ante un nivel fuera de escala |
| 8 — la `cita` es subcadena exacta en su desplazamiento | H-1 | Un texto que no puede anclar cita no produce un defecto mal construido |
| 9 — todo `CAN-01` declara un `hecho_canon_id` existente | H-3 | El `hecho_canon_id` deja de depender del orden de la lista |
| 10 — persona y tiempo verbal se comprueban en el texto | H-6 | La narración deja de desaparecer del análisis |

## Impacto técnico

- **Presupuesto de contexto (§4.1):** sin impacto. Ninguna capa crece; nada de esto llama
  al modelo.
- **Esquema:** RF-CAL-16 probablemente sí. Separar objeto físico de información toca
  `Afirmacion` y el contrato con `canon`. Si la separación llega al ledger, hay migración
  de Alembic.
- **Prompts:** RF-CAL-16 obliga a una **versión nueva** de `continuista.v1.md`, no a
  editarlo en sitio (`CLAUDE.md` §10).
- **Fronteras (§5):** el acoplamiento de H-5 es entre `calidad` y `canon` a través del
  estado en T. Hoy no es un import entre features y no debe convertirse en uno.
- **Dependencias:** ninguna nueva. `hypothesis` ya está en `pyproject.toml`.

## Vocabulario

Todos los términos usados —escena, canon, hecho de canon, estado en T, defecto, cita,
puerta de calidad, nivel de calor, ledger— existen en `docs/definitions.md`. Esta spec
**no introduce ninguno nuevo**.

## Preguntas abiertas

Mientras quede una, esta spec no se aprueba (`CLAUDE.md` §3.2).

- **P-1 (H-3)** — Empate en `orden_discurso`: ¿se desempata en el validador (por ejemplo
  por `hc_id`) o se prohíbe el empate en el esquema, haciendo `orden_discurso` único por
  obra? Lo segundo es más fuerte y toca migración.
- **P-2 (H-1)** — Prosa vacía: ¿es EST-01 con una cita convencional, o un error de dominio
  que escala directamente a una persona sin gastar reintento? Un texto vacío no es una
  escena mal escrita: es una llamada que no devolvió nada.
- **P-3 (H-5)** — La mitigación está **decidida y aplicada**: `maujimenez4` sacó CON-03 y
  CAN-01 de `BLOQUEANTES_EN_G1A` el 2026-09-23. Queda el fondo, y es pregunta del punto 7
  de `CLAUDE.md` §3 porque toca prompt y probablemente esquema: ¿se parte
  `Afirmacion.objeto` en `objeto` + `informacion` con prompt nuevo, o se cambia el
  contraste a algo que no sea igualdad de cadenas, o ambas? Y la que hay que responder
  con ella: **qué evidencia devuelve a CAN-01 y CON-03 a `BLOQUEANTES_EN_G1A`.** El
  comentario del código dice «cuando ese contraste deje de comparar cadenas»; eso es una
  condición, no un umbral, y sin umbral no se puede incumplir (`verification.md` §5).

  La forma que tendría que tener la respuesta la aporta la sesión **Jose** (2026-09-23), y
  conviene que quede escrita porque convierte la pregunta en algo medible: el dato que
  falta es **cuántos de esos defectos son falsos positivos sobre una corrida real con el
  Continuista dentro**. Es justo para eso que hoy se registran en `no_bloquean` aunque no
  bloqueen. Sin esa tasa, cualquier umbral que se fije ahora sería inventado; con ella, la
  condición pasa a ser un número y el regreso a `BLOQUEANTES_EN_G1A` deja de depender del
  criterio de quien mire. Nótese que esa medición **no** la da `corrida.py --seco`: el
  doble pasa `AFIRMACIONES_FALSAS = "[]"` y el Continuista no afirma nada, así que los
  validadores devuelven cero por construcción. Hace falta una corrida real.
- **P-4 (H-6)** — ¿Cuál es el criterio correcto de diálogo en español? La raya abre pero
  no cierra, y el inciso del narrador va detrás de una segunda raya. Hace falta decidir la
  regla antes de escribir la expresión regular.
- **P-5 (H-2)** — ¿El nivel de calor se tipa como enum en el esquema de la obra —y
  entonces un nivel inválido no llega nunca al validador— o el validador lanza igualmente?
  Las dos cosas no sobran: la primera impide, la segunda detecta.

## Trazabilidad

| Hallazgo | Técnica que lo encontró | Origen |
| --- | --- | --- |
| H-1, H-2 | Precondición declarada y función total (Dafny, SPARK) | Sonda de esta spec |
| H-3, H-4 | Alcance pequeño e independencia del orden (Alloy) | Sonda de esta spec |
| H-5 | Lectura del acoplamiento entre features | Sesión **Nubia**, 2026-09-23; verificado aquí |
| H-6 | Precondición declarada (Dafny, SPARK) | Sonda de esta spec |

## Lo que esta spec no verifica

| Qué | Por qué | Qué lo cubriría |
| --- | --- | --- |
| Que el criterio de cada validador sea el **correcto** | Una propiedad comprueba lo que se enunció, no si enunciarlo era lo acertado | Inspección humana sobre el capítulo de CA-1 |
| La tasa de **falsos negativos** del Continuista | Sigue sin existir un conjunto de defectos conocidos | Evals de la fase 4 |
| La precisión léxica de VOZ-03 | Fuera de alcance por decisión | Spec propia |

## Cierre

Pendiente. Al cerrar hay que revisar los cuatro documentos de `docs/` (`CLAUDE.md` §3.1) y,
como mínimo, actualizar en `verification.md`:

- la fila «Tests basados en propiedades» de §2, hoy dirigida solo al ensamblador;
- la fila «Una contradicción de canon pasa desapercibida» de §7, si H-3 y H-5 cambian su
  estado;
- el registro de cambios de §8.
