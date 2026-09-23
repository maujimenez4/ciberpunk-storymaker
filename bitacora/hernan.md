# Hernán

## 15:20 · Skills de sistemas de specs, en MyFactory

- **Qué:** el usuario pidió descargar siete sistemas de desarrollo dirigido por specs, verificarlos y decidir cuáles sirven aquí. Clonados los siete; solo las skills de `obra/superpowers` son auto-contenidas (markdown puro, cero referencias fuera de su carpeta). Spec Kit necesita resolver `__SPECKIT_COMMAND_*__` con su CLI, gsd-core carga `@~/.claude/gsd-core/workflows/`, BMAD ejecuta `_bmad/scripts/` con uv y MUSUBI depende de su propio `steering/`. GSD además está archivado: redirige a `open-gsd/gsd-core`.
- **Ficheros:** ninguno del repositorio. Todo en `maujimenez4/MyFactory` (commits `7e3a607` y `9c74fb0`).
- **Estado:** terminado
- **Ojo:** la evaluación completa, con lo aprovechable de cada descarte, está en `MyFactory/catalogo-sdd.md`.

## 15:45 · Cuatro skills de proceso y `clarificar-spec`

- **Qué:** instaladas `brainstorming`, `writing-plans`, `test-driven-development` y `verification-before-completion`, que cubren las cuatro puertas de §3. Ninguna conoce nuestro formato de spec, así que escribí `clarificar-spec`: barrido de ambigüedad por once categorías, ≤5 preguntas por ronda, umbral como puerta y ningún `RF-*` sin su `CA-N`.
- **Ficheros:** `.claude/skills/` (cinco carpetas), `.claude/skills/SOURCES.md`, `CLAUDE.md` §12, `docs/architecture.md` §7.2
- **Estado:** terminado — lo commiteó otra sesión en `57e6c11`
- **Ojo:** `brainstorming` y `writing-plans` guardan por defecto dentro de `docs/`, que §3.1 reserva para lo que ya es verdad. Al invocarlas hay que darles `specs/NNN-slug/`. Está anotado en `SOURCES.md`.

## 16:45 · Validadores para la spec 002 y auditoría de sus criterios

- **Qué:** encargo del usuario — construir validadores que comprueben que la 002 se construye de acuerdo a lo que promete, y verificar si sus criterios son válidos. Dos artefactos ejecutables y un informe. Hallazgo nuevo **H-7**: `validar_discurso` con `tiempo_verbal` fuera de `{pasado, presente}` devuelve `[]` —falla en abierto, es H-2 otra vez— y con `persona` fuera de `{primera, tercera}` sube un `KeyError` pelado. Contraejemplos ejecutados.
- **Ficheros:** `specs/002-validadores-fallo-cerrado/validar_spec.py`, `sonda_dominio.py`, `auditoria-criterios.md`. **Nada más.** No he tocado `validadores.py`, `commons/errors/` ni ningún test de la suite.
- **Estado:** terminado, sin commitear
- **Ojo:** los cuatro requisitos `RF-CAL-13/14/15/17` no los cita ningún criterio de aceptación. Se pueden arreglar los seis hallazgos, poner los siete CA en verde y dejarlos incumplidos. Lo detecta `validar_spec.py` (invariante V-8), que también encuentra en la spec 001 once criterios sin marca T/A/I/D/U.

## 16:55 · Aclaración de atribución

- **Qué:** Nubia y Mario me han escrito dando por hecho que soy yo quien edita `validadores.py`, `commons/errors/` y `calidad/tests/`. **No lo soy.** Cuando empecé, `validar_nivel_de_calor` devolvía `[]` con un nivel fuera de escala; a mitad de mi trabajo pasó a lanzar `EntradaFueraDeDominio`, y no fui yo. Los rojos de `ruff` y `pytest` que ambos reportan no salen de mis ficheros: los míos pasan `ruff check` y `ruff format --check` limpios.
- **Estado:** terminado
- **Ojo:** quien esté implementando la 002 lo hace con la spec en `borrador` y sin `plan.md`, que es lo que §3.3 y §3.4 prohíben. No es asunto mío arreglarlo, pero conviene que esté escrito: mis dos sondas están **fuera de `testpaths`** justamente para no meter tests en la suite antes de que haya plan aprobado.

## 17:10 · H-7 cerrado por Jose, informe actualizado y recados dados

- **Qué:** verifiqué H-7 por mi cuenta contra HEAD y ya no reproduce: las cuatro entradas fuera de escala lanzan `EntradaFueraDeDominio`. Fue real a las 16:45 y Jose lo cerró hacia las 17:00. Reescribí `auditoria-criterios.md` contra el árbol de las 17:05, porque la spec se había reescrito a las 16:04 y tres de mis puntos ya estaban resueltos. `validar_spec.py` da ahora **12/12** en la 002 y 11/12 en la 001.
- **Ficheros:** `specs/002-validadores-fallo-cerrado/auditoria-criterios.md`, `sonda_dominio.py`, `validar_spec.py`
- **Estado:** terminado, sin commitear — el usuario encargó los commits a Ezequiel y a Mario
- **Ojo:** de mi auditoría solo sobrevive una objeción: **CA-2 dice «lanza» y RF-CAL-13 pide error tipado de `commons/errors/`**. Ahora es gratis apretarlo porque el código ya lanza `EntradaFueraDeDominio`. Lo demás es deuda de trazabilidad: cuatro requisitos que ningún CA nombra. Mario y yo reconstruimos la cobertura por separado y nos salieron mapas distintos — esa es la medida del coste, no una discrepancia entre nosotros.
- **Ojo 2:** las dos propiedades de H-7 se quedan en `sonda_dominio.py` aunque el defecto esté cerrado: ahora protegen el arreglo de una regresión. Las siete propiedades pasan.

## 17:35 · Numeración, y un fallo en abierto en mi propio validador

- **Qué:** el usuario encargó comunicar a todas las sesiones que **la 002 es el frontend**, con **Ezequiel con prioridad de decisiones**. Ezequiel decidió **no renumerar** y se lo planteó al usuario; comunicado a las seis sesiones alcanzables (la séptima, sin nombre, se cerró antes). Aparte: al pasar `validar_spec.py` sobre la 003 a petición de Nubia descubrí que **mi regex solo veía requisitos en negrita** y las specs los declaran en tablas — en la 001 veía 14 de 142. Mi validador fallaba en abierto, el mismo pecado que audita.
- **Ficheros:** `specs/002-validadores-fallo-cerrado/validar_spec.py`, `auditoria-criterios.md`
- **Estado:** terminado, sin commitear — los commits los lleva Nubia
- **Ojo:** las cifras que di antes (12/12 y 11/12) valían menos de lo que parecían y ya las he corregido con los cuatro que las recibieron. Buenas: **001 → 11/12, 002 → 12/12, 003 → 11/12**. V-8 baja de fallo a **aviso**, y no para que pase: la sección de requisitos cita identificadores de otras specs —`RF-CAL-07` en la 002 es de la 001— y mecánicamente no se distingue el propio del ajeno.

## 17:45 · Segundo falso positivo del validador, y cifras definitivas

- **Qué:** Mario encontró que V-9 reconocía `*(Test)*` pero no `*(T)*`, y acusaba a los veinte criterios de la 003 de no declarar marca. Mismo modo de fallo que el de V-8 de hace diez minutos: reconocer un formato y dar por ausente lo que viene en otro. Corregido con prueba de regresión. Aplicada también su regla para V-8: un requisito es propio si la sección lo declara en tabla o en negrita; si solo aparece en prosa es cita a otra spec.
- **Ficheros:** `specs/002-validadores-fallo-cerrado/validar_spec.py`, `auditoria-criterios.md`
- **Estado:** terminado, sin commitear — para Nubia
- **Ojo:** cifras definitivas a las 17:45: **001 → 11/12** (once criterios sin marca, real y comprobado a mano), **002 → 12/12**, **003 → 12/12**. Gustavo y Ezequiel etiquetaron sus criterios esta tarde. Ninguno de los dos defectos de mi validador lo delató el propio validador: al primero un número absurdo, al segundo un revisor leyendo a mano.

## 18:05 · Renumeración: la 002 pasa a 005, y V-13

- **Qué:** el usuario revocó la decisión de Ezequiel y sí se renumera. Ezequiel me asignó la primera mitad: `git mv` de `002-validadores-fallo-cerrado` a `005-validadores-fallo-cerrado`, el `id:` del frontmatter y **13 referencias en 9 ficheros**, incluidos `test_invariantes.py` —dentro de los 444 verdes— y la skill `lenguajes-formales.md`. Después, las menciones en prosa a «la spec 002», que tras el movimiento significan otra cosa. Añadida **V-13** al validador, propuesta de Mario: ningún criterio declarado dos veces, tras encontrar él **dos `CA-14` distintos** en la 001.
- **Ficheros:** `specs/005-validadores-fallo-cerrado/*`, `.claude/skills/SOURCES.md`, `.claude/skills/verification-methods/references/lenguajes-formales.md`, `specs/003-lectura-web/spec.md`, `src/backend/app/features/calidad/tests/test_invariantes.py`
- **Estado:** terminado, sin commitear — para Nubia
- **Ojo:** **las dos mitades van en el mismo commit.** Ezequiel mueve ahora 003 → 002; subir solo una deja dos specs con el mismo número o una citando rutas muertas. Verificado antes de avisar: 444 tests, `ruff` limpio, 10 contratos, `mypy` sin incidencias, cero rutas muertas. Specs con las trece invariantes: **001 → 11/13** (los dos `CA-14` y once criterios sin marca), **003 → 13/13**, **005 → 13/13**.
- **Ojo 2:** rompí un acuerdo con Gustavo —él iba a tocar sus dos ficheros de skill— porque una renumeración tiene que ser atómica: esperarle alargaba la ventana de ruta muerta. Se lo dije con el motivo y estuvo de acuerdo; de hecho su `grep` cazó el árbol a medias entre mis dos comandos.
- **Ojo 3:** quedan dos menciones en prosa a «la spec 002» en ficheros de otros —`docs/verification.md:345` y `specs/003-lectura-web/spec.md:360`—, más una en `sonda_invariantes.py`, que es de Gustavo. No las toco: avisados sus dueños.

## 18:20 · Las referencias en prosa, que iban a pasar de muertas a falsas

- **Qué:** Mario matizó, con razón, mi «no rompen nada mecánicamente»: hoy «la spec 002» es una referencia muerta y se ve; en cuanto Ezequiel mueva la 003 al 002 pasa a ser una referencia **viva y equivocada**, que apunta a una spec que existe y no es la que se quiere decir. Corregidas las cuatro de mi lado, quitando el número en vez de cambiarlo: los tres comentarios de `validar_spec.py` nombran ahora «esta misma spec» y «la de validadores», y `sonda_invariantes.py` dice 005.
- **Ficheros:** `specs/005-validadores-fallo-cerrado/validar_spec.py`, `sonda_invariantes.py`
- **Estado:** terminado, sin commitear — retenido por Nubia hasta que Ezequiel cierre su mitad
- **Ojo:** la lección no es una invariante nueva, es **no citar números de spec en prosa**. Descarté la V-14 que proponía Mario —detectar menciones a specs inexistentes— porque caza el fallo que ya se ve y deja pasar el que no falla nunca, y porque daría falsos positivos con specs planificadas como la 004 de Ezequiel. Un comentario que nombra la spec por lo que es no caduca al renumerar.
- **Ojo 2:** verificado tras los retoques: 444 tests, `ruff` y `ruff format` limpios, las dos sondas 14 passed desde la ruta nueva, `validar_spec.py` 13/13. La verificación final la hace Mario cuando Ezequiel termine.

## 18:35 · Renumeración completa y verificada

- **Qué:** Ezequiel cerró su mitad (`002-lectura-web`), así que la renumeración está entera. Verificado el conjunto: `id` == carpeta en las tres, cero rutas muertas, 444 tests, `ruff` limpio, 10 contratos, `mypy` sin incidencias. Corregida una referencia mía que había quedado obsoleta —la tabla de la auditoría seguía diciendo `003-lectura-web`— y actualizadas sus cifras con V-13 dentro.
- **Ficheros:** `specs/005-validadores-fallo-cerrado/auditoria-criterios.md`
- **Estado:** terminado. Avisados Mario (verificación final) y Nubia (commit de las dos mitades juntas)
- **Ojo:** tres menciones a los números viejos que quedan y **no son errores**: `specs/002-lectura-web/spec.md:15`, donde Ezequiel explica a propósito el cambio; `docs/definitions.md:21`, fila de registro de cambios; y las seis bitácoras, que son registro histórico.
- **Ojo 2:** queda propuesta, sin aplicar, una convención que sale de todo esto: **una spec se nombra por lo que es, no por su número, salvo cuando el número es el dato.** Su sitio natural es `CLAUDE.md` §3.2, y ahí no la mete un agente: §3.1 dice que los documentos de autoridad describen el presente y §14 que no se firma en nombre de la persona. Propuesta a `maujimenez4`; la sugerencia original es de Mario.

## Cierre de la sesión

- **Qué:** entregado en esta sesión — las cinco skills de MyFactory y `clarificar-spec`; `validar_spec.py` con trece invariantes; `sonda_dominio.py` con siete propiedades universales; `auditoria-criterios.md`; y la primera mitad de la renumeración.
- **Estado:** terminado, todo sin commitear salvo lo que Nubia ya subió
- **Ojo:** lo que **no** se ha resuelto y no puede resolver ningún agente: la 005 tiene código de producción commiteado con la spec en `borrador`, sin `plan.md` y con `aprobada_por` vacío (§3.3 y §3.4); P-1 a P-5 siguen sin firmar y cuatro ya las ha contestado el código; y hay doce commits locales sin subir. Todo eso espera a `maujimenez4`.

## 18:55 · Verificada la 005 y firmadas sus decisiones

- **Qué:** verificación de la 005 a petición del usuario: `validar_spec.py` da **13/13**, incluido V-11, que hace un rato fallaba por un enlace a `umbral-can01-con03.md` que no existía y que Jose ya ha creado. Puesta la firma de `maujimenez4` en las decisiones D-1 a D-5, por instrucción directa suya.
- **Ficheros:** `specs/005-validadores-fallo-cerrado/spec.md`
- **Estado:** terminado, sin commitear
- **Ojo:** la firma alcanza a las cinco decisiones, **no** al `estado:` ni a `aprobada_por`, que siguen en `borrador` y vacío. Eso es un acto distinto y §3.2 pide commit propio de la persona; no lo toca ningún agente.
- **Ojo 2:** **el árbol está roto ahora mismo** y no es de la renumeración: `validadores.py:302`, `SyntaxError: unmatched ")"`, 12 errores de colección y 0 tests ejecutados. Es el ciclo en curso de Jose. Avisados él y Nubia, que iba a commitear. Las cifras de `pytest` que doy al usuario son de hace veinte minutos, cuando había 444 verdes.

## 19:15 · La 001 a 13/13, y dos mejoras del validador

- **Qué:** encargo de Ezequiel. Separados los dos `CA-14` de la 001 —el segundo, la cita inventada, pasa a **CA-15**— y puestas las marcas de verificación a los once criterios que no la declaraban: diez `*(Test)*` y **CA-9 `*(Análisis)*`**, porque lo que comprueba es que pasan `ruff`, `mypy` y `lint-imports`. Además, `CU-` sale de los prefijos de requisito de V-8, y V-5 gana un aviso para el caso contrario al que ya vigilaba.
- **Ficheros:** `specs/001-backend-v1/spec.md`, `src/backend/app/features/escritura/tests/test_continuidad_en_g1a.py`, `specs/005-validadores-fallo-cerrado/validar_spec.py`
- **Estado:** terminado, sin commitear
- **Ojo:** había una referencia al **segundo** CA-14 que no estaba en ninguna lista: `test_continuidad_en_g1a.py`, en su encabezado de sección y en su docstring. Actualizada a CA-15 con nota de su nombre anterior. Ese fichero pasa (8 passed).
- **Ojo 2:** la marca de **CA-9** es la única discutible. La puse `*(Análisis)*` y no `*(Test)*` aunque `pytest` esté en su lista, porque la marca declara **cómo** se comprueba y ahí lo dominante son las herramientas de análisis estático. Si Mario o Ezequiel discrepan, se cambia.
- **Ojo 3:** las tres specs en **13/13**, `ruff` limpio, **447 tests**. El árbol estuvo roto un rato por un `SyntaxError` en `validadores.py:302` del ciclo de Jose; ya no.
