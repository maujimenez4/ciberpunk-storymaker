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
