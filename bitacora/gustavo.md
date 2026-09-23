# Gustavo

## 15:30 · Encargo: evaluar quince lenguajes de verificación formal

- **Qué:** el usuario me pasó quince lenguajes (TLA+, Lean 4, Alloy, Dafny, Quint, Verus, Kani, P, Rocq, Isabelle, SPARK, Event-B, F\*, Agda/Idris, Z/VDM/PVS) para decidir cuáles mejoran nuestros validadores, documentarlos para otros agentes y guardar los enlaces en el repositorio. **Mi encargo no era `calidad/`**, y de ahí salieron tres verificaciones a ciegas sobre mí.
- **Ficheros:** `.claude/skills/verification-methods/references/lenguajes-formales.md`, `SKILL.md`, `SOURCES.md`, `docs/verification.md`
- **Estado:** terminado — commiteado en `1c7dbe1`
- **Ojo:** ninguno de los quince se instala. `pyproject.toml` y `uv.lock` intactos: lo que se adopta de tres de ellos es la técnica, escrita con `hypothesis`, que ya era dependencia.

## 16:00 · Sonda de invariantes: seis defectos en `validadores.py`

- **Qué:** aplicar las tres técnicas adoptadas al código real. Cuatro invariantes de cinco cayeron a la primera. Con H-5 de Nubia, que reproduje antes de darlo por bueno, son seis: dos fallan en abierto (H-2 nivel fuera de escala, H-6 la narración tras la raya), dos no son deterministas ante empates (H-3, H-4), H-1 revienta con texto vacío.
- **Ficheros:** `specs/002-validadores-fallo-cerrado/spec.md` y `sonda_invariantes.py`. **Ninguno de `src/`.**
- **Estado:** terminado — la spec queda en `borrador` con cinco preguntas abiertas
- **Ojo:** la sonda está fuera de `testpaths`, así que `uv run pytest` no la recoge. Falla a propósito: es la evidencia, y sirve de rojo a quien implemente.

## 16:30 · Reparto: no toco `calidad/`

- **Qué:** Jose reclamó `calidad/` y `escritura/service.py`, que llevaba a medias. Se lo consulté a mi usuario y decidió que los seis defectos los lleve él entero.
- **Estado:** terminado
- **Ojo:** no voy a tocar `validadores.py` ni aunque me lo pidan sin avisar antes a quien lo esté implementando. Hoy es Hernan, según Nubia.

## 17:00 · Correcciones a la spec 002, de la revisión de Mario

- **Qué:** Mario revisó la 002 y encontró tres defectos bloqueantes y cuatro menores. Los acepto todos y los he corregido. El bueno de verdad es B-1: **RF-CAL-13 decía corregir H-6 y no podía**, porque un párrafo con diálogo y narración en la misma línea es entrada perfectamente de dominio y no hay nada que lanzar. H-6 pasa a **RF-CAL-18**, y no se implementa hasta que P-4 esté contestada: es la única de las cinco preguntas que exige criterio lingüístico y no se puede zanjar programando.
- **Ficheros:** `specs/002-validadores-fallo-cerrado/spec.md`
- **Estado:** terminado
- **Ojo para quien implemente:** dos cosas que la spec no decía y ahora sí. (1) **RF-CAL-16 arrastra CON-02**: `validar_objetos` lee el mismo `Afirmacion.objeto` que se parte, y CON-02 **sí bloquea G1a**; hay un CA-8 nuevo que lo protege de regresión. (2) **CA-1 estaba mal redactado**: exigía que la sonda pasara «sin relajar ninguna invariante», pero la sonda codificaba una respuesta a P-2 y el código eligió la otra. Ya no prejuzga.

## 17:05 · Estado del árbol cuando escribo esto

- **Qué:** `4 failed, 435 passed`; 23 errores de `ruff`. Los 23 están en ficheros de quien implementa —`validar_spec.py`, `sonda_dominio.py`, `test_invariantes.py`, `validadores.py`, `manejadores.py`—, ninguno en los míos. Trabajo a medias, no avería.
- **Estado:** terminado — solo lectura, no he tocado nada
- **Ojo:** **la spec 002 sigue en `borrador` y `aprobada_por` está vacío**, y en `validadores.py` ya hay `EntradaFueraDeDominio`, el corte `objeto`/`informacion` y los desempates. Eso responde a P-1, P-2, P-3 y P-5 sin que lo firme nadie. No es reproche a quien implementa —le habrán dicho que adelante—, pero §3.2 dice que una spec no se aprueba a medias, y desde fuera no se ve la autorización. Se lo he planteado a mi usuario.

## 17:25 · Segunda vuelta de Mario: RF-CAL-17 sin criterio

- **Qué:** Mario repasó la cobertura RF→CA y encontró que **RF-CAL-17 era el único requisito sin criterio de aceptación** — justo el que evita que los cinco arreglos vuelvan a caer dentro de tres meses. Añadido **CA-8**: las cuatro invariantes viven en `features/calidad/tests/`, dentro de `testpaths`, y `pytest` las recoge sin nombrar fichero. Hoy la sonda está fuera a propósito, así que la suite no las ejercita. Renumerado también el criterio del umbral, que iba antes que otro más nuevo.
- **Ficheros:** `specs/002-validadores-fallo-cerrado/spec.md`
- **Estado:** terminado — la spec sigue en `borrador`
- **Ojo para quien implemente:** mover las cuatro propiedades de la sonda a `features/calidad/tests/` es parte del trabajo, no un extra. Mientras solo estén en `specs/002-*/`, `uv run pytest` no las ve y el arreglo no está protegido.

## 17:30 · Cobertura RF→CA dentro de la spec

- **Qué:** añadida la tabla requisito → criterio en Trazabilidad, para que la cobertura no haya que repasarla a mano como hizo Mario. Seis requisitos, nueve criterios, ninguno huérfano.
- **Ficheros:** `specs/002-validadores-fallo-cerrado/spec.md`
- **Estado:** terminado
- **Ojo:** `estado: borrador` y `aprobada_por` vacío, comprobado ahora mismo. Nadie ha firmado nada, y yo no voy a firmar.

## 17:32 · Corrección: el CA del arrastre de CON-02 es el 7, no el 8

- **Qué:** en la entrada de las 17:00 escribí que CON-02 lo protegía «CA-8». Al añadir el criterio de RF-CAL-17 se renumeró y **ese criterio es ahora CA-7**; CA-8 es el de las invariantes en la suite. No reescribo la entrada anterior, que es el formato de esta bitácora: queda corregido aquí.
- **Estado:** terminado

## 17:50 · CA-2 exige el error tipado — y con esto cierro mi parte

- **Qué:** último punto vivo de la 002, de Hernán vía Mario. CA-2 decía que `validar_nivel_de_calor` «lanza», a secas, y RF-CAL-13 pide un error de dominio **tipado de `commons/errors/`**: un `ValueError` pelado habría pasado el criterio sin cumplir el requisito. CA-2 exige ahora que el test nombre el tipo en vez de `pytest.raises(Exception)`. La clase concreta la sigue fijando P-5; hoy es `EntradaFueraDeDominio`, subclase de `ErrorDeDominio`.
- **Ficheros:** `specs/002-validadores-fallo-cerrado/spec.md`
- **Estado:** terminado
- **Ojo:** el `noqa: B017` de `sonda_invariantes.py` está ahí porque el tipo estaba sin decidir; desaparece cuando se firme P-5. Verificado antes de escribir esto: 444 tests y `ruff` limpio, y `EntradaFueraDeDominio` se lanza en los cuatro puntos de dominio.

## 17:55 · Cierre de mi encargo

- **Qué:** terminadas las dos cosas que me pidió mi usuario: la evaluación de los quince lenguajes formales con veredicto (`1c7dbe1`) y la spec 002 con los seis hallazgos y sus correcciones (`82a1a49` más el CA-2 de arriba). No tengo nada más abierto.
- **Ficheros:** ninguno en curso. El único cambio mío sin commitear es el CA-2 de `spec.md`.
- **Estado:** terminado
- **Ojo:** queda **bloqueado por firma, no por trabajo**. La spec sigue en `borrador` con `aprobada_por` vacío y las cinco preguntas abiertas sin contestar, mientras el código de `accb8e9` ya responde de hecho a P-1, P-2, P-3 y P-5. **P-4 —qué cuenta como diálogo en español— sigue virgen y bloquea RF-CAL-18 (H-6)**, que es el único de los seis hallazgos sin arreglar. Y P-3 ya no es interna: el DEP-04 de la spec 003 depende de ella.

## 18:05 · La 002 se renumera, y dos de los catorce ficheros son míos

- **Qué:** el usuario ha decidido que la 002 es el frontend, así que la spec de validadores cambia de número. Me lo comunica Hernán. **No renumero por mi cuenta:** lo decide Ezequiel y se hace de una vez, porque con cinco sesiones sobre esa carpeta dos renombrando a la vez es peor que el número mal puesto.
- **Ficheros:** ninguno ahora. Cuando toque, me quedo `.claude/skills/verification-methods/references/lenguajes-formales.md` (§2.4 y §6 citan la ruta) y `.claude/skills/SOURCES.md`.
- **Estado:** bloqueado — por la decisión de Ezequiel sobre el número
- **Ojo:** esos dos son una **skill**, no una spec. Se cargan solos cuando alguien toca verificación, así que una ruta muerta ahí no es un enlace roto en un documento: es un agente siguiendo un camino que no existe. Que no se queden fuera del renombrado.

## 18:20 · No hay renumeración, y cada criterio nombra ya su requisito

- **Qué:** dos avisos de Hernán. (1) Ezequiel decidió que la 002 se queda como está, así que **no muevo nada** y los dos ficheros de skill que me había reservado siguen con rutas válidas. (2) Corrigió su propia cifra: el validador de specs solo reconocía requisitos en negrita y daba por buena una cobertura que no había leído —fallando en abierto, que es justo el pecado que persigue esta spec—. Con el validador arreglado se ve el hueco real: mis criterios no **nombraban** su requisito en la línea, solo en la tabla de Trazabilidad. Ya lo hacen los nueve.
- **Ficheros:** `specs/002-validadores-fallo-cerrado/spec.md`
- **Estado:** terminado
- **Ojo:** `RF-CAL-07` aparecerá en cualquier comprobador como requisito mío sin criterio, y **no lo es**: es de la 001 y aquí solo se cita al explicar el arrastre de CON-02. Queda dicho en la propia spec para que nadie lo persiga dos veces.

## 18:40 · Sí se renumera a la 005, y la hace Hernán entera

- **Qué:** el usuario revocó la decisión de Ezequiel. Hernán renumera, **incluidos mis dos ficheros de skill**, en contra de lo que él y yo habíamos acordado. Su razón es mejor que mi acuerdo: una renumeración tiene que ser **atómica**, y si él mueve la carpeta y yo actualizo la skill diez minutos después, en esa ventana hay una skill apuntando a una ruta muerta — que es justo el argumento que di yo para que esos dos ficheros importaran. No toco nada y reviso después.
- **Ficheros:** ninguno mío en curso.
- **Estado:** terminado por mi parte
- **Ojo:** comprobado a las 18:40, **la renumeración aún no está en el árbol**: la carpeta sigue siendo `specs/002-validadores-fallo-cerrado/` y mis dos ficheros siguen citando 002, o sea que ahora mismo todo es coherente. Si alguien «arregla» esas rutas antes de que Hernán mueva la carpeta, crea justo la inconsistencia que la atomicidad evita.

## 18:45 · CA-9 deja de citar la 001 solo por número

- **Qué:** Mario encontró que la 001 tiene **dos criterios distintos con el mismo `CA-14`**. Mi CA-9 citaba «la corrida de CA-1 de la spec 001»; ahora la nombra por lo que es —la corrida de un capítulo completo de principio a fin— y deja el número como apunte. Una referencia cruzada que solo es un número se rompe sin ruido cuando el documento citado se renumera o duplica.
- **Ficheros:** `specs/002-validadores-fallo-cerrado/spec.md`
- **Estado:** terminado

## 18:50 · Corrección: la renumeración sí estaba, entró mientras yo miraba

- **Qué:** en la entrada de las 18:40 escribí que la renumeración «aún no está en el árbol». Era cierto cuando lo comprobé y dejó de serlo segundos después: Hernán movió la carpeta mientras yo leía. **La spec es `specs/005-validadores-fallo-cerrado/`.** No reescribo la entrada anterior; se corrige aquí, que es el formato de esta bitácora.
- **Estado:** terminado
- **Ojo:** verificados mis dos ficheros de skill sobre el árbol, no sobre su palabra: `lenguajes-formales.md:87` y `SOURCES.md:228` apuntan ya a `005-`. La renumeración de Hernán fue atómica de verdad y mi reserva sobre esos dos ficheros no hacía falta.

## 19:05 · `verification.md` deja de citar la spec por número

- **Qué:** Mario encontró que `docs/verification.md:345` decía «de ese catálogo salió **la spec 002**» significando validadores. Hoy no apunta a nada; cuando Ezequiel mueva la suya al 002, apuntará a una spec que **sí existe** y que no tiene nada que ver. Arreglado con el criterio de Hernán, que es mejor que cambiar el número: **quitarlo**. Ahora dice «la spec de los validadores mecánicos», inmune a la próxima renumeración y no solo a esta.
- **Ficheros:** `docs/verification.md`
- **Estado:** terminado
- **Ojo:** una ruta muerta falla a gritos; una referencia válida y falsa no falla nunca —se lee, se cree y se propaga—. Y esta estaba en el documento que más se cita para justificar decisiones.

## 19:10 · H-6 está arreglado, y conviene que no se repita lo contrario

- **Qué:** Mario me dijo a la vez que la sonda pasa 7/7 y que `RF-CAL-18` sigue sin implementar, que son incompatibles. Comprobado: la sonda pasa **7 de 7** desde `specs/005-`, y sobre `—Yo no fui —dijo ella. Yo camine hasta la puerta y yo espere.` la narración ya es `' dijo ella. Yo camine hasta la puerta y yo espere.'` y VOZ-03 emite dos defectos. **Los seis hallazgos están corregidos en el código.**
- **Estado:** terminado
- **Ojo:** eso cambia lo que hay que pedirle al usuario. P-4 **no** está sin respuesta: el código la contestó —los segmentos separados por raya alternan, y los de índice par son narración—. Lo que falta es **confirmarla**, no decidirla en blanco. Que se pida como pregunta virgen invita a responder deprisa algo que ya está funcionando.

## 16:45 · Corrida real autorizada: muere en la escena 1, y compra un hallazgo

- **Qué:** `maujimenez4` firmó las cinco decisiones (D-1 a D-5) y autorizó la corrida real con el Continuista dentro para medir el umbral de D-3. **La corrida murió en la escena 1**: `citar()` lanza `ValueError` porque el Continuista devolvió una cita que no es subcadena literal de la prosa. 0 de 10 escenas, 0 defectos registrados, **0,0517 USD**.
- **Ficheros:** `specs/005-validadores-fallo-cerrado/umbral-can01-con03.md` (nuevo), `spec.md` (Decisiones y Cierre). Evidencia fuera del repositorio, en `Documents/evidencia-corridas/corrida-continuista-2026-09-23/`, porque contiene prosa generada (§15).
- **Estado:** bloqueado — D-3 no se puede medir hasta que se cierre H-7
- **Ojo para quien lleve `calidad/` y `escritura/`:** **H-7.** Los cuatro validadores de continuidad llaman a `citar(texto, a.cita, …)` con la cita **que devuelve el modelo**, y `citar` lanza si no la encuentra. Toda la defensa contra la cita inventada —`comprobar_forma`, axiomas 11 y 12, la tasa de mal formados de `verification.md` §6.3— vive en `puerta.py`, **aguas abajo**: para que un defecto mal formado se registre, primero tiene que construirse, y aquí revienta antes. **No lo he arreglado**: no es mi área y añadir un requisito reabriría una spec cuyas preguntas acaban de cerrarse.

## 19:35 · H-7 falsifica un criterio de la spec 001

- **Qué:** Mario rastreó H-7 hasta su causa y la verifiqué yo: `test_puerta.py:31` dice cubrir «la categoría que esta comprobación elimina» —la cita inventada— y lo que prueba es **otra cosa**. Usa `"cortaba la red"`, que **sí está** en el texto, y luego corrompe los desplazamientos con `model_copy`. Prueba un anclaje corrompido, no una cita inventada, y el `model_copy` rodea justo el punto donde el sistema revienta con entrada real.
- **Ficheros:** `specs/005-validadores-fallo-cerrado/spec.md` (Cierre ampliado)
- **Estado:** terminado
- **Ojo:** el segundo `CA-14` de la 001 (`spec.md:362`) dice que un defecto con cita inventada «no bloquea, no gasta intento y queda contado como mal formado». **Mi corrida lo falsifica:** con cita inventada la corrida muere, 0 de 10. Si la 001 va a marcarse `implementada`, eso hay que declararlo. Y esa spec tiene **dos criterios con el número `CA-14`**, así que ni se puede citar sin ambigüedad.
