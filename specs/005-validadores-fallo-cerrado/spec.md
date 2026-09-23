---
id: 005-validadores-fallo-cerrado
titulo: Los validadores mecánicos fallan cerrado y son deterministas
estado: borrador          # borrador | en-revision | aprobada | implementada
aprobada_por:             # lo rellena una persona, nunca un agente
fecha: 2026-09-23
---

# 005-validadores-fallo-cerrado — Los validadores mecánicos fallan cerrado y son deterministas

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
es una excepción de validación de esquema que sube sin tipar. Una prosa vacía es un modo
de fallo corriente del modelo, y hoy rompe la puerta en vez de cerrarla.

**Son dos casos distintos, y la primera redacción los confundía** (lo señaló la sesión
**Mario** el 2026-09-23). La cita sale de `texto[:40].strip() or texto`:

| Entrada | Qué hacía | Por qué está mal |
| --- | --- | --- |
| `""` | `ValidationError` de Pydantic | La cita queda vacía y `Defecto` la rechaza |
| `"   "` | EST-01 con `cita="   "` | **No revienta**: emite un defecto bien formado según la regla 8 y del todo inútil para reparar, porque el pasaje citado son tres espacios |

El segundo es el peor de los dos para quien lo sufre: no hay traza de que algo fuera mal.

### H-2 · `validar_nivel_de_calor` falla **en abierto** con un nivel fuera de escala — *SEG-01*

    validar_nivel_de_calor("Se quito la ropa y quedo desnuda ante el.", "0", "vt1")
    -> []

`_vetados` devuelve la tupla vacía para cualquier nivel que no esté en `_ESCALA`, y una
tupla vacía significa «nada prohibido». Una errata en el `nivel_de_calor` de la obra
**desactiva por completo** el único validador mecánico de la regla 5 de `CLAUDE.md` §8,
sin ruido de ningún tipo. Es el hallazgo más grave de los cinco que salieron de la sonda: un
guardarraíl de seguridad que se apaga en silencio.

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
  tipado de `commons/errors/`. *(Corrige H-2; es la precondición explícita de §2.3 del
  catálogo.)*
- **RF-CAL-14** — Todo validador es una función **total** sobre `texto`: para cualquier
  cadena, incluida la vacía y la de solo espacios, devuelve defectos o lanza un error de
  dominio, nunca un `ValidationError` de Pydantic. *(Corrige H-1.)*
- **RF-CAL-15** — La salida de un validador **no depende del orden** de sus colecciones de
  entrada: misma entrada como conjunto, misma lista de defectos con los mismos `detalle`,
  `cita` y `hecho_canon_id`. *(Corrige H-3 y H-4.)*
- **RF-CAL-16** — CON-03 contrasta **información conocida** contra **información usada**, y
  no objetos físicos contra descripciones de evento. El campo que transporta cada concepto
  está separado en el esquema y en el prompt. *(Corrige H-5.)*

  **Arrastra CON-02, y la primera versión de esta spec no lo decía.** `validar_objetos`
  (CON-02, RF-CAL-07) lee el mismo `Afirmacion.objeto` que este requisito parte, y CON-02
  **sí bloquea G1a**: está en `BLOQUEANTES_EN_G1A`. Partir el campo sin decidir cuál de
  los dos alimenta a CON-02 lo rompe, y lo rompe en una feature distinta. Lo señaló la
  sesión **Mario** el 2026-09-23, con `escritura/tests/test_continuidad_en_g1a.py` en rojo
  como prueba.
- **RF-CAL-17** — Las **cuatro** invariantes de totalidad y de orden —H-1 a H-4— viven en
  la suite como tests basados en propiedades. H-5 y H-6 entran como ejemplos, y se dice
  por qué: el criterio de CON-03 y el de diálogo no están enunciados como propiedad
  todavía, y enunciarlos mal protege menos que un ejemplo honesto. *(Evita la
  reaparición: un ejemplo arreglado no protege la función.)*
- **RF-CAL-18** — `solo_narracion` conserva la narración que sigue al inciso del
  narrador, y VOZ-03 la evalúa. *(Corrige H-6.)* **Dependía de P-4, hoy resuelta en D-4:** el fallo no está en la entrada sino en el criterio de qué es diálogo en
  español, y ese criterio es la pregunta abierta. RF-CAL-13 no sirve aquí —un párrafo con
  diálogo y narración en la misma línea es entrada perfectamente **de dominio**, así que
  no hay nada que lanzar—, y darlo por cubierto fue un error de esta spec que señaló la
  sesión **Mario** el 2026-09-23.

## Criterios de aceptación

- [ ] **CA-1** *(transversal)* — La sonda de [`sonda_invariantes.py`](sonda_invariantes.py), **actualizada
      con las decisiones firmadas D-1 a D-5**, pasa entera sobre el código de
      producción. *(Test)*

      La redacción anterior —«pasa entera, sin relajar ninguna invariante»— era
      incumplible, y lo señaló la sesión **Mario** el 2026-09-23: la sonda codificaba
      **una** respuesta a la entonces abierta P-2 (con texto vacío se **devuelve** un
      defecto) y el código eligió la otra (**lanza**, hoy D-2). Con aquella redacción, o se
      relajaba la invariante —prohibido por el propio criterio— o P-2 no estaba abierta. Un criterio de
      aceptación no puede prejuzgar una pregunta que la spec declara abierta.
- [ ] **CA-2** *(RF-CAL-13)* — `validar_nivel_de_calor(texto, nivel_no_valido, vt)` lanza un error de
      dominio **de `commons/errors/`**, y el test nombra el tipo: `pytest.raises` sobre esa
      clase, no sobre `Exception`. *(Test)*

      «Lanza», a secas, era demasiado flojo y lo señaló la sesión **Hernán** vía **Mario**
      el 2026-09-23: un `ValueError` pelado —o el `KeyError` que tenía `validar_discurso`—
      pasaría el criterio sin cumplir RF-CAL-13, que pide el error **tipado**. La clase
      concreta la fijó D-5: `EntradaFueraDeDominio`, subclase de `ErrorDeDominio`.

      Alcanza a los cuatro puntos donde hoy se lanza, no solo al nivel de calor: la sonda
      usaba `pytest.raises(Exception)` con un `noqa: B017` porque el tipo estaba sin
      decidir. **Con D-5 firmada, ese `noqa` sobra y el `raises` debe nombrar la clase.**
- [ ] **CA-3** *(RF-CAL-14)* — `validar_giro_de_valor` trata los **dos** casos de H-1 y los trata igual:
      ni `""` produce un `ValidationError` ni `"   "` produce un defecto cuya cita sean
      espacios. Qué hace en su lugar lo fijó D-2: lanza. *(Test)*
- [ ] **CA-4** *(RF-CAL-15)* — Barajar `canon` y barajar `afirmaciones` no cambia la salida de
      `validar_canon` ni la de `validar_continuidad_fisica`, comprobado con `hypothesis`
      sobre alcance pequeño. *(Test)*
- [ ] **CA-5** *(RF-CAL-16)* — Una afirmación cuyo `objeto` es un objeto físico corriente **no** produce
      CON-03; una que usa información sin `sabe_desde` anterior **sí**, aunque esté
      redactada con otras palabras que la `descripcion` del Extractor. *(Test)*
- [ ] **CA-6** *(RF-CAL-18)* — Un párrafo con diálogo y narración en la misma línea conserva la narración
      en `solo_narracion`, y VOZ-03 la evalúa. *(Test)*
- [ ] **CA-7** *(RF-CAL-16)* — Ninguna afirmación con objeto físico deja de producir CON-02 por el corte
      de RF-CAL-16: `validar_objetos` sigue bloqueando G1a igual que antes, comprobado con
      su propio test y con el de `escritura` que lo ejercita de punta a punta. *(Test)*
- [ ] **CA-8** *(RF-CAL-17)* — Las cuatro invariantes de H-1 a H-4 viven en
      `features/calidad/tests/`, dentro de `testpaths`, y `uv run pytest` las recoge sin
      nombrar ningún fichero. Hoy la sonda está **fuera** a propósito, así que la suite no
      las ejercita: mientras sigan solo ahí, RF-CAL-17 no está cumplido y el arreglo no
      está protegido de volver a caer. *(Test)*

      Lo señaló la sesión **Mario** el 2026-09-23, repasando la cobertura RF→CA: RF-CAL-17
      era el único requisito sin criterio, y es justo el que evita que esto se repita.
- [ ] **CA-9** *(transversal, y fuera de la aprobación)* — *(Pendiente de umbral, y por eso no se puede marcar.)* «La tasa de
      defectos mal formados no empeora» no declara línea base, y `verification.md` §5 dice
      que lo que no se puede incumplir no verifica. Es el mismo reproche que D-3 le hace al
      comentario de `defectos.py`, y esta spec lo cometía a su vez: lo señaló la sesión
      **Mario** el 2026-09-23. La línea base no existe todavía: la corrida de un
      **capítulo completo de principio a fin** —el CA-1 de la 001 a día de hoy— no
      está registrada, y la 001 sigue en `en-revision`. Se nombra por lo que es y no
      solo por su número a propósito: la sesión **Mario** encontró el 2026-09-23 que la
      001 tiene **dos criterios distintos con el mismo `CA-14`**, así que citar sus
      criterios por número no es fiable ahora mismo—, así que este criterio
      **no entra en la aprobación**: se fija con el primer número real o se retira. Va el
      último a propósito: es el único que no se puede marcar. *(Demostración)*

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
- **CON-02 arrastrado por RF-CAL-16:** `validar_objetos` lee hoy el mismo campo que se
  parte, y **bloquea G1a**. El corte tiene que decir explícitamente cuál de los dos campos
  lo alimenta, y CA-7 lo protege de regresión. El coste de no haberlo declarado ya se vio:
  un test de `escritura` en rojo por un cambio de esquema de `calidad`.
- **Prompts:** RF-CAL-16 obliga a una **versión nueva** de `continuista.v1.md`, no a
  editarlo en sitio (`CLAUDE.md` §10).
- **Fronteras (§5):** el acoplamiento de H-5 es entre `calidad` y `canon` a través del
  estado en T. Hoy no es un import entre features y no debe convertirse en uno.
- **Dependencias:** ninguna nueva. `hypothesis` ya está en `pyproject.toml`.

## Vocabulario

Todos los términos usados —escena, canon, hecho de canon, estado en T, defecto, cita,
puerta de calidad, nivel de calor, ledger— existen en `docs/definitions.md`. Esta spec
**no introduce ninguno nuevo**.

## Decisiones

Las cinco las contestó **`maujimenez4`** el **2026-09-23**. Se conserva cada pregunta con
su porqué, como pide `CLAUDE.md` §3.2.

> **Firmadas por `maujimenez4` el 2026-09-23.** D-1 a D-5 llevan su firma, puesta por
> instrucción suya directa en la sesión **Hernán**. Con ella no queda ninguna pregunta
> abierta en esta spec.
>
> La firma alcanza **a las cinco decisiones, no al `estado:` de la spec**, que sigue en
> `borrador` con `aprobada_por` vacío. Cambiarlo es un acto distinto y va en un commit
> suyo que no contenga nada más (`CLAUDE.md` §3.2), para que la aprobación quede
> localizable en el historial. Ningún agente lo toca.

**Desviación que hay que declarar, y va la primera porque no se arregla contestándola.**
Las cinco se implementaron y se commitearon (`accb8e9`) con esta spec en `borrador`. Estas
decisiones **documentan** lo que el código ya hacía; no vuelven retroactivo el orden de
§3.4, que pide plan aprobado antes del código. Queda anotado aquí en vez de disimulado:
una desviación anotada es recuperable, una disimulada no.

| | Pregunta | Decisión |
| --- | --- | --- |
| **D-1** | Empate en `orden_discurso` (H-3) | **Desempatar en el validador.** `sorted(canon, key=(orden_discurso, hc_id, valor))` |
| **D-2** | Prosa vacía (H-1) | **Error de dominio.** `EntradaFueraDeDominio` con `not texto.strip()`, que cubre `""` y `"   "` igual |
| **D-3** | El contraste de CON-03 (H-5) | **Partir el campo, y medir antes de volver a bloquear.** Corrida real autorizada |
| **D-4** | Criterio de diálogo (H-6) | **Segmentos alternos separados por raya**, los de índice par son narración |
| **D-5** | Nivel de calor (H-2) | **Las dos cosas.** Enum en el esquema y el validador lanza |

### D-1 · El desempate vive en el validador, no en el esquema

La alternativa era prohibir el empate haciendo `orden_discurso` único por obra. Es más
fuerte, y por eso mismo se deja para cuando haga falta: el desempate en código ya hace
determinista el arbitraje sin coste de migración, y la unicidad en esquema puede añadirse
después sin deshacer nada. Lo que no podía seguir es que el `hecho_canon_id` que exige el
axioma 12 dependiera del orden de una lista.

### D-2 · Una prosa vacía no es una escena mal escrita

Es una llamada que no devolvió nada, y se dice en voz alta. El argumento decisivo es el
axioma 11: sin texto no hay pasaje que citar, y un EST-01 con una cita convencional sería
un defecto bien formado que no ancla nada.

**Consecuencia asumida:** esto escala a una persona sin gastar reintento, así que un fallo
del proveedor llega a la bandeja de alguien como trabajo humano. Es preferible a que se
lea como una escena defectuosa.

### D-3 · El umbral se mide, no se estima

El corte `objeto` / `informacion` se confirma, y con él el paso de igualdad exacta a
inclusión normalizada. Pero eso **baja** el falso positivo, no lo cierra: el contraste
sigue siendo léxico, y así lo dice el propio código.

Para devolver CAN-01 y CON-03 a `BLOQUEANTES_EN_G1A` hace falta un número, no una
condición. `maujimenez4` **autorizó la corrida real con el Continuista dentro** el
2026-09-23 para medir la tasa. Recuérdese por qué no basta con la de siempre:
`corrida.py --seco` pasa `AFIRMACIONES_FALSAS = "[]"`, el Continuista no afirma nada y los
validadores devuelven cero por construcción. Un cero que parece una buena noticia.

La forma de la respuesta la aportó la sesión **Jose**; la medición se registra en
[`umbral-can01-con03.md`](umbral-can01-con03.md).

### D-4 · El diálogo son segmentos alternos, y el límite se declara

En español la raya abre pero no cierra, y el inciso del narrador vuelve a abrirla. Los
segmentos separados por raya **alternan**: índice par es narración, impar es réplica.

**Límite conocido y aceptado:** la regla es correcta con diálogo bien puntuado y falla en
cuanto una escena use la raya como guion o como inciso suelto. No se persigue ese caso
aquí —la precisión léxica de VOZ-03 está fuera de alcance—, pero queda escrito para que
el próximo falso positivo no se investigue como si fuera una sorpresa.

### D-5 · Impedir y detectar no se sustituyen

`NivelDeCalor` es `StrEnum` en el esquema de la obra, así que un nivel inválido no debería
llegar nunca al validador; y el validador lanza igualmente si llega. La primera impide, la
segunda detecta, y ninguna sobra: la regla 5 de §8 es dura y `CLAUDE.md` §10 prohibe que
una regla de seguridad dependa de una sola capa.

## Trazabilidad

Cobertura requisito → criterio, para que no haya que repasarla a mano. La comprobó así la
sesión **Mario** el 2026-09-23 y encontró que RF-CAL-17 se había quedado sin ninguno:

| Requisito | Criterios | Hallazgo que cierra |
| --- | --- | --- |
| RF-CAL-13 | CA-2 | H-2 |
| RF-CAL-14 | CA-3 | H-1 |
| RF-CAL-15 | CA-4 | H-3, H-4 |
| RF-CAL-16 | CA-5, CA-7 | H-5, y CON-02 que arrastra |
| RF-CAL-17 | CA-8 | Ninguno: evita que los cinco anteriores vuelvan a caer |
| RF-CAL-18 | CA-6 | H-6 |

CA-1 es transversal —la sonda entera— y CA-9 queda fuera de la aprobación por no tener
umbral.

Cada criterio **nombra además su requisito en la propia línea**, no solo en esta tabla. Es
por lo mismo que existe RF-CAL-17: una cobertura que depende de que alguien cruce dos listas
a mano se rompe en silencio la primera vez que nadie las cruza. Así la comprueba una máquina.
*(Lo señaló la sesión **Hernán** el 2026-09-23, al corregir un validador de specs que hasta
entonces solo reconocía requisitos en negrita y daba por buena una cobertura que no había
leído.)*

**`RF-CAL-07` no es un requisito de esta spec.** Es de la 001, y aquí se cita solo al explicar
el arrastre de CON-02. Un comprobador que lo cuente como propio y sin criterio está dando un
falso positivo, no señalando un hueco.

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

### Cómo se hizo esta spec, que no fue en el orden de §3

**No hay `plan.md`, y no va a haberlo con sentido: el código ya existía cuando se firmaron
las decisiones.** §3.5 dice que el plan queda como registro de cómo se hizo el trabajo;
aquí no hay plan, así que el registro es este apartado. Lo escribe la sesión **Gustavo** a
petición de la sesión **Mario**, el 2026-09-23.

El orden real fue:

1. Se evaluaron quince lenguajes formales y se adoptaron tres técnicas (commit `1c7dbe1`).
2. Se sondeó `validadores.py` con esas técnicas y cayeron cuatro invariantes de cinco; una
   sexta la aportó la sesión **Nubia** leyendo el acoplamiento entre features.
3. Se escribió esta spec, en `borrador`, con cinco preguntas abiertas.
4. **Se implementó y se commiteó el código (`accb8e9`), con la spec todavía en
   `borrador`.** Eso incumple §3.3 y §3.4: no hay plan sin spec aprobada, ni código sin
   plan aprobado.
5. `maujimenez4` firmó las cinco decisiones **después**, el 2026-09-23.

De ahí se sigue una cosa que conviene leer con cuidado al revisar D-1 a D-5: **cuatro de
las cinco son confirmaciones de decisiones que el código ya había tomado**, no decisiones
tomadas antes de programar. La única que se planteó como pregunta de verdad, con su
límite delante, fue **D-4** —y es la que mejor salió—. No parece casualidad, y por eso se
deja escrito en vez de resumirlo como «cinco decisiones firmadas».

Esto no se disimula por la misma razón por la que `defectos.py` documenta RF-CAL-09
incumplido a propósito en lugar de callarlo: **aquella decisión se pudo revisar hoy porque
estaba escrita.** Una desviación anotada es recuperable; una disimulada deja un historial
que dice que hubo spec, decisiones e implementación en ese orden, y no fue ese el orden.

### Lo que la corrida de D-3 encontró, y por qué no cierra

La medición que autorizó D-3 **no se pudo hacer**: la corrida murió en la escena 1 porque
una cita inventada por el Continuista revienta el ciclo en vez de registrarse como defecto
mal formado. Es un séptimo hallazgo —**H-7**— y está documentado con su evidencia en
[`umbral-can01-con03.md`](umbral-can01-con03.md).

**No se ha añadido como requisito de esta spec a propósito.** Meter un `RF-CAL-19` por
decisión de un agente reabriría en `borrador` una spec cuyas preguntas acaban de cerrarse,
y §3.2 dice que una spec no se aprueba —ni se reabre— a medias. Quién lo recoge y dónde
lo decide `maujimenez4`. Lo que sí es un hecho: **D-3 no se puede cerrar hasta que H-7 esté
resuelto**, porque cualquier corrida nueva morirá igual en cuanto el Continuista
parafrasee.

### Lo que dice de la suite, y no lo dice ningún test verde

**Los seis hallazgos estaban cerrados en el código, con 444 tests en verde, y la primera
corrida real murió en la escena 1.** Conviene dejarlo escrito tal cual, porque es la
conclusión más útil de toda esta spec y no se deduce de ninguna casilla.

La sesión **Mario** encontró el 2026-09-23 a las 19:30 el porqué exacto, y es de manual.
`test_puerta.py:31` se llama `test_una_cita_que_no_coincide_con_el_texto_queda_mal_formada`
y su docstring dice cubrir «**la** categoría que esta comprobación elimina». Lo que hace es:

```python
defecto = _defecto(CodigoDeDefecto.CON_01, "cortaba la red").model_copy(
    update={"desplazamiento_inicio": 0, "desplazamiento_fin": 10}
)
```

`"cortaba la red"` **sí está** en el texto de prueba —comprobado—. El test construye un
defecto válido y luego le corrompe los **desplazamientos**. Prueba un anclaje corrompido,
no una cita inventada; y el `model_copy` rodea exactamente el punto donde el sistema
revienta con entrada real, porque construir el `Defecto` por la vía normal habría lanzado.

Es el párrafo de apertura de esta spec cumpliéndose sobre la propia spec: *los ejemplos se
escriben con la entrada que el autor tenía en la cabeza*. Esta vez el ejemplo estaba
escrito para pasar por encima del fallo.

**Y falsifica un criterio de la 001.** Su segundo `CA-14` (`specs/001-backend-v1/spec.md:362`)
dice que un defecto con la cita inventada «no bloquea la escena, no gasta intento y queda
contado como mal formado». Con una cita inventada la corrida **muere**: 0 de 10. Ese
criterio está sin cumplir, y la 001 no debería marcarse `implementada` sin declararlo.
—Con el agravante de que hay **dos criterios con el número `CA-14`** en esa spec, así que
ni siquiera se puede citar sin ambigüedad.—
