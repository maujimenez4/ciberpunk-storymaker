# Mario — revisión de specs

Reviso lo que otras sesiones escriben en `specs/`, verifico sus afirmaciones
contra el árbol y devuelvo hallazgos. **No escribo código de producción ni
cambio ningún `estado:`** (§14: eso lo firma una persona en un commit suyo).

---

## 15:50 · Reviso la spec 002 de validadores

- **Qué:** verificar `specs/002-validadores-fallo-cerrado/spec.md` contra el código, no contra sí misma. Corrí su sonda antes de que nadie la tocara: los 7 tests fallaban, los seis hallazgos reproducen. La evidencia es buena.
- **Ficheros:** solo lectura — `specs/002-*/`, `features/calidad/`, `features/contexto/`
- **Estado:** terminado
- **Ojo:** la spec es de **Gustavo** (me lo confirmaron Julio y Nubia; la sonda además acredita a Jose el arreglo de H-1 y Nubia dice que Hernan implementa en vivo). Le pasé la revisión completa a Gustavo y a Jose.

## 15:58 · Tres bloqueantes en la spec 002

- **Qué:** los hallazgos, todos verificados:
  1. **RF-CAL-13 se atribuye H-6 y no puede corregirlo.** Exige lanzar «ante entrada fuera de dominio», pero un párrafo con diálogo e inciso en la misma línea es entrada *de dominio*: el fallo está en la regex `_DIALOGO`. Prueba: H-2 se arregló lanzando y H-6 sigue rojo. H-6 necesita requisito propio y P-4 contestada antes.
  2. **RF-CAL-16 toca CON-02 y la spec no lo declara.** `validar_objetos` leía el mismo `Afirmacion.objeto`, y CON-02 **sí bloquea** G1a. La factura se ve en `escritura/tests/test_continuidad_en_g1a.py` rojo: el cambio de esquema cruzó de feature.
  3. **CA-1 no puede ser criterio de aceptación.** Pide que la sonda pase «sin relajar ninguna invariante», pero se cumple editando el fichero al que apunta — que es lo que pasó con `test_h1`. Además prejuzgaba P-2, declarada abierta.
- **Ficheros:** ninguno tocado
- **Estado:** terminado
- **Ojo:** para quien implemente H-6: `linea.split("—")[::2]` es buena intuición, pero es justo la decisión que P-4 dice que se toma **antes** de escribir la regex, no mientras.

## 16:00 · Código de producción con la spec en `borrador`

- **Qué:** no hay `plan.md` en `specs/002-*/`, la spec sigue en `borrador` con `aprobada_por:` vacío, y `validadores.py` ya tiene el arreglo. CLAUDE.md §3.3, §3.4 y §14. Cuatro de las cinco preguntas abiertas (P-1, P-2, P-3, P-5) las ha contestado el código sin que las firme nadie; la única sin contestar es P-4, que era la que no se resolvía programando.
- **Ficheros:** ninguno tocado
- **Estado:** terminado
- **Ojo:** propuse no revertir nada: tratar la implementación como **propuesta de respuesta** a P-1/P-2/P-3/P-5, llevarlas a *Decisiones* y que las firme `maujimenez4`. Julio confirma que la 001 lleva todo el día igual, así que no es un descuido de una sesión.

## 16:05 · RF-CTX-07 incumplido: nadie hace el filtro estructural

- **Qué:** me lo señaló Julio y lo verifiqué por mi cuenta. **Tres docstrings prometen el filtro y cada uno apunta a otra capa:**
  - `contexto/recoleccion.py:153` — «1. Filtro estructural. **Lo hace el almacén**»
  - `contexto/repository.py:168` — «**Ya filtrados** por el filtro estructural», y en la línea siguiente llama a `self.canon.candidatos_para_ordenar(tope)` **descartando `escena_id`**
  - `canon/repository.py:514` — «**El filtro estructural va antes**», y el cuerpo es `SELECT ... FROM fragmento ORDER BY rowid DESC LIMIT ?`
- **Ficheros:** solo lectura — `features/contexto/repository.py`, `features/canon/repository.py`, `features/contexto/recoleccion.py`
- **Estado:** terminado
- **Ojo:** el `escena_id` **llega** a `fragmentos_candidatos` y se tira en la línea siguiente: la firma está, el filtro no. Rompe CLAUDE.md §4.2, donde el orden filtrar→ordenar→fusionar se declara no negociable, y hoy está clasificado **T** en `verification.md` con tests que solo comprueban el tope. No es mío; quien lleve `contexto` o `canon` que lo recoja.

## 16:10 · Corrijo mi entrada de las 16:05, y H-7 ya está cerrado

- **Qué:** dos correcciones a lo que escribí antes, ninguna de las dos mía por descubrimiento:
  1. **Me equivoqué en un detalle de RF-CTX-07.** Escribí que `escena_id` «se descarta en la línea siguiente». No se descarta: alimenta `_es_el_principio`, que decide si devolver el marcador de «todavía no hay memoria» en la primera escena. **Nunca filtra**, que era mi conclusión y esa sí se sostiene, pero el parámetro se usa. Me lo corrigió Julio y tiene razón: quien abra el fichero y vea que sí se usa dejará de creerse el resto del hallazgo.
  2. **H-7, propuesto por Hernán, ya no reproduce.** Lo medí: `validar_discurso` con `tiempo_verbal='PASADO'`, con `'preterito'` y con `persona='segunda'` lanza hoy `EntradaFueraDeDominio` con mensaje tipado, no `0 defectos` ni `KeyError`. Jose lo cerró en los minutos intermedios. El hallazgo era real cuando Hernán lo midió; está cerrado ahora.
- **Ficheros:** ninguno tocado; solo lectura de `features/contexto/repository.py` y `features/calidad/validadores.py`
- **Estado:** terminado
- **Ojo:** el árbol se mueve en minutos. Cualquier medición sobre `features/calidad/` lleva hora, o no vale. La mía de las 15:50 y la de Hernán de las 16:01 ya no describen el mismo código.

## 16:12 · Reparto de autoría, que tres sesiones hemos dado por distinto

- **Qué:** para que no se repita. **Gustavo** escribe `specs/002-*/spec.md` y no toca `src/`. **Jose** implementa `validadores.py` y es quien cerró H-1 a H-7. **Hernán** audita los criterios de la 002 (`auditoria-criterios.md`, `validar_spec.py`, `sonda_dominio.py`) y tampoco toca `src/`. **Julio** commitea y verifica. **Yo** reviso la spec y no escribo código de producción.
- **Ficheros:** ninguno
- **Estado:** terminado
- **Ojo:** yo le atribuí a Gustavo ediciones de Jose, y Nubia nos atribuyó a Hernán y a mí cosas que eran de Jose. Tres errores de atribución en media hora, todos por deducir del `git status`. Es justo lo que esta bitácora existe para evitar.

## 17:20 · Cerrada mi revisión de la 002 y de la 003

- **Qué:** las dos specs revisadas y sus autores han aceptado todo. En la **002** queda un punto vivo: CA-2 dice «lanza» y RF-CAL-13 pide error **tipado** de `commons/errors/` (hallazgo de Hernán). En la **003** quedan tres: que DEP-04 cite por su nombre la **P-3 de la 002** en vez del directorio, que incluya **CON-03** además de CAN-01, y una fila declarando que G1a es por escena y el **Auditor de manuscrito** no entra en el flujo de regeneración.
- **Ficheros:** ninguno de código; solo `bitacora/mario.md`
- **Estado:** terminado
- **Ojo:** **la P-3 de la 002 dejó de ser interna.** La DEP-04 de la 003 depende de ella: mientras `CAN-01` y `CON-03` no vuelvan a `BLOQUEANTES_EN_G1A`, la petición de cambio detecta una contradicción de canon entre capítulos y **publica igual**. Quien lleve la 002 debe saber que su pregunta abierta bloquea una entrega ajena.

## 17:22 · Decisiones del usuario

- **Qué:** dos, y las dejo escritas porque cambian premisas que otros están dando por ciertas.
  1. **P-1 a P-5 de la 002 las firma el usuario en persona.** Ni Gustavo ni yo redactamos las Decisiones. Se lo he puesto delante con las cinco.
  2. **Manda la escala nueva** —capítulo=escena, 1.000–1.500 palabras, diez capítulos—. `CLAUDE.md:11`, `domain-knowledge.md:78` y `definitions.md:75` están desfasados y hay que corregirlos; verificado línea a línea.
- **Ficheros:** ninguno
- **Estado:** terminado
- **Ojo:** **yo no corrijo los tres documentos.** El usuario eligió que se corrijan, no que los corrija yo, y `CLAUDE.md` es el manual del proyecto. Queda libre para quien tenga ese encargo. `definitions.md` es además la fuente de verdad de §2, así que al moverse mueve vocabulario.

## 17:40 · Revisión de la 002 cerrada por mi parte

- **Qué:** verificados sobre el fichero en disco los cuatro puntos que quedaban, todos resueltos por Gustavo. `RF-CAL-18` separado de `RF-CAL-13` con su condición de P-4; CON-02 declarado en `RF-CAL-16` con `CA-7`; `CA-1` reformulado a «actualizada con las respuestas firmadas»; `RF-CAL-17` con `CA-8` sobre `testpaths`; y `CA-2` pidiendo ya el error **tipado** por su clase y no `Exception`. La tabla requisito→criterio está en Trazabilidad.
- **Ficheros:** ninguno; solo lectura de `specs/002-validadores-fallo-cerrado/spec.md`
- **Estado:** terminado
- **Ojo:** **la spec sigue sin poder aprobarse, y no por nada técnico.** `estado: borrador`, `aprobada_por` vacío y P-1 a P-5 sin firmar, con cuatro ya contestadas de hecho por el código. El usuario ha dicho que las firma él. Hasta entonces no pasa a `en-revision`, y `RF-CAL-18` no se implementa porque depende de P-4.

## 17:42 · Revisión de la 003 cerrada salvo repaso final

- **Qué:** Ezequiel aplicó las tres últimas. Verificado en disco: DEP-04 cita la **P-3 de la 002** por su nombre, incluye **CON-03** además de CAN-01, y hay fila nueva declarando que G1a es por escena y que el **Auditor de manuscrito no entra en el flujo**.
- **Ficheros:** ninguno; solo lectura de `specs/003-lectura-web/spec.md`
- **Estado:** en curso — falta mi repaso entero antes de `en-revision`
- **Ojo:** la 003 está bloqueada por su **P-03** (qué ve el lector mientras su petición tarda el peor caso), que es del usuario. No la deis por cerrada sin mi repaso: me comprometí con Ezequiel a hacerlo cuando P-03 esté contestada.

## 17:55 · El validador de criterios da falsos positivos; y la numeración

- **Qué:** dos avisos.
  1. **`validar_spec.py` acusa de más.** Hernán corrigió su V-8 —buscaba requisitos en negrita y las specs los declaran en tablas— pero su **V-9 sigue igual**: dice «003, 20 criterios sin marca» y lo medí, **los 20 llevan su `(T)`/`(A)`/`(D)`**. Mismo defecto en la invariante de al lado, y falla en la misma dirección. Sus cifras sobre la 001 pueden tener el mismo problema.
  2. **Numeración en duda.** Al usuario se le ha atribuido que «la 002 es el frontend». En disco y commiteado: `002-validadores-fallo-cerrado` (`82a1a49`) y `003-lectura-web` (`ce2b810`), con **33 referencias cruzadas en 16 ficheros**, incluidas `docs/definitions.md`, `.claude/skills/`, un test de `src/` y las seis bitácoras.
- **Ficheros:** ninguno; solo lectura y medición
- **Estado:** terminado
- **Ojo:** **no renumeréis por iniciativa propia.** Las bitácoras son *append-only* por su propio README: renumerar obliga a reescribir seis registros que dicen no reescribirse, o a dejarlos apuntando a rutas muertas. Si el usuario decide renumerar, que sea un commit que solo haga eso y con las bitácoras corregidas por **entrada nueva**. Y que nadie use las cifras de `validar_spec.py` sin comprobar una a mano: hoy no son fiables.

## 18:05 · La spec 001 tiene dos criterios llamados CA-14

- **Qué:** medido sobre `specs/001-backend-v1/spec.md`: 15 líneas de criterio, 14 identificadores únicos, **`CA-14` declarado dos veces** (líneas 361 y 362) sobre dos cosas distintas —VOZ-03 más capa vacía, y el defecto con cita inventada—. Además solo 3 de las 15 llevan marca T/A/I/D/U, no 11 sin marca como decían las cifras que circulaban: el duplicado desplazaba el recuento.
- **Ficheros:** ninguno; solo lectura y medición
- **Estado:** terminado
- **Ojo:** **no es cosmético.** La spec 002 ya cita «la corrida de CA-1 de la spec 001», así que las referencias cruzadas a los criterios de la 001 están en uso: hoy «CA-14 de la 001» no identifica nada. Y la 001 es la que está en `en-revision` **con código de producción encima**. Le propuse a Hernán una invariante nueva para `validar_spec.py` —ningún identificador declarado dos veces—, que es decidible sin heurística de formato y no puede dar falso positivo, al revés que sus V-8 y V-9.

## 18:20 · Acepto validador de proceso del frontend, y paro el paso de la 001 a `implementada`

- **Qué:** Ezequiel, orquestando, me designa validador de proceso del desarrollo del frontend: comprobar que no hay código sin plan aprobado, que el ciclo rojo→verde→refactor se ve fallar, que el test entra con su código, que ningún import cruza §5.2 y que ningún término entra sin `definitions.md`. Aceptado, **sin autoridad de aprobar nada**: puedo parar y medir, no puedo firmar un `estado:` ni autorizar que se salte un paso.
- **Ficheros:** ninguno
- **Estado:** en curso
- **Ojo:** **la 001 no debería pasar a `implementada` tal como está.** `RF-CTX-07` es `M` y está marcado `T` en `spec.md:188`, y **no está implementado**: `canon/repository.py:514` hace `ORDER BY rowid DESC LIMIT ?` sin filtro estructural, y los únicos tests comprueban el tope. Marcarla es dejar escrito que un requisito imprescindible está probado cuando no existe. Tres salidas legítimas —implementarlo, marcarla con la desviación declarada como hizo `defectos.py` con RF-CAL-09, o bajarlo de `M` a `S`—; la decisión es del usuario. Lo que no vale es marcarla y callarlo. Va con ello el `CA-14` duplicado y que solo 3 de sus 15 criterios llevan marca.

## 18:40 · Verificada la primera mitad de la renumeración, y el riesgo real de la segunda

- **Qué:** corridas las puertas sobre el estado actual (`005-validadores-fallo-cerrado` ya movida, `003-lectura-web` todavía sin mover):
  - `pytest` **444 passed** · `ruff check` **limpio** · `lint-imports` **10 kept, 0 broken** · `mypy commons/domain` **sin incidencias**
  - `sonda_invariantes.py` desde su ruta nueva: **7 passed** — los seis hallazgos de la spec están corregidos
  - `validar_spec.py` sobre la 005: **13/13**
  - Rutas muertas a `002-validadores-fallo-cerrado`: **ninguna**
- **Ficheros:** ninguno tocado; solo medición
- **Estado:** terminado la primera mitad; **en curso** la verificación final, que va después de que Ezequiel mueva `003` → `002`
- **Ojo:** **el riesgo de la segunda mitad no es que queden rutas muertas, es lo contrario.** Quedan ocho menciones en prosa que dicen «la 002» o «spec 002» significando *validadores*: `docs/verification.md:345`, `specs/003-lectura-web/spec.md` en las líneas **15, 347 y 360**, `sonda_invariantes.py:1` y `validar_spec.py` en **68, 182 y 217**. Hoy son referencias muertas y se notan. En cuanto la lectura web sea la 002, pasan a ser referencias **vivas y equivocadas**: apuntarán a una spec que existe y que no es la que quieren decir. Una ruta muerta falla a gritos; una referencia válida y falsa no falla nunca. La de `spec.md:15` ya es una frase sin sentido: dice que esta spec no es la 002 «porque `specs/005-...` ya ocupa ese número».

## 19:05 · Verificación final de la renumeración: pasa

- **Qué:** las dos mitades hechas. `001-backend-v1`, `002-lectura-web`, `005-validadores-fallo-cerrado`, con `id:` == carpeta en las tres.
  - `pytest` **444 passed** · `ruff` **limpio** · `lint-imports` **10 kept, 0 broken** · `mypy commons/domain` **sin incidencias**
  - Las dos sondas desde su ruta nueva: **14 passed**
  - **Barrido en prosa hecho**, que era lo que no me quería saltar: cada mención a un número de spec significa lo que dice. Las de `auditoria-criterios.md` que citan «la 003» son relato histórico y están etiquetadas («antes 003», «medido a las 17:45»).
- **Ficheros:** ninguno tocado; solo medición
- **Estado:** terminado
- **Ojo:** verificado que no quedan referencias **vivas y falsas**, que era el riesgo real. Nubia puede soltar los commits retenidos por mi parte.

## 19:10 · Me equivoqué con H-6, y lo repetí varias veces

- **Qué:** dije que `RF-CAL-18` seguía sin implementar y que P-4 era «la única pregunta sin respuesta de ningún tipo». **Es falso**, y lo cazó Gustavo señalando que no podía ser cierto a la vez que la sonda pasaba 7/7 — la séptima es justo `test_h6`. Verificado por mí: `solo_narracion` está reescrita (los segmentos separados por raya alternan, los de índice par son narración), la narración sobrevive al inciso y VOZ-03 emite dos defectos donde antes callaba. **Los seis hallazgos están cerrados en el código.**
- **Ficheros:** ninguno
- **Estado:** terminado
- **Ojo:** mi error venía de una lectura de las 16:05 que no volví a comprobar antes de repetirla. Es el mismo fallo que llevo señalando todo el día: una medición vieja presentada como estado actual. **P-4 no es una pregunta virgen:** el código la contestó y lo que falta es confirmarla, con su límite a la vista —la regla de segmentos alternos es correcta con diálogo bien puntuado y falla si una escena usa la raya como guion o inciso suelto—.
