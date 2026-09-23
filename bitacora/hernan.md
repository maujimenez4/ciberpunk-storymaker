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
