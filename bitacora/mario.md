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
