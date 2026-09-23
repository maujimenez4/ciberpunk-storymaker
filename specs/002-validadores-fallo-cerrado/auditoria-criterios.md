# Auditoría de los criterios de la spec 002

Sesión **Hernán**, 2026-09-23. Encargo: construir validadores para esta spec y comprobar
si los tests que declara son válidos.

**Medido contra el árbol a las 17:05.** La spec y el código se han movido varias veces
esta tarde —Jose implementando, Gustavo reescribiendo tras la revisión de Mario—, así que
cada afirmación de aquí lleva su hora. Una auditoría sin hora, en un árbol con seis
sesiones dentro, envejece en minutos: la primera versión de este informe tenía tres puntos
que ya estaban resueltos cuando se escribieron.

**Esta auditoría no modifica `spec.md`.** Los cambios los aplica quien la firma, y la
aprobación es de una persona (`CLAUDE.md` §3.2 y §14).

```bash
uv run python specs/002-validadores-fallo-cerrado/validar_spec.py
uv run pytest specs/002-validadores-fallo-cerrado/sonda_dominio.py -q
```

---

## 1. Veredicto: los nueve criterios son válidos

Tras la reescritura de las 16:04, los nueve criterios son observables y están bien
planteados. Cada uno nombra una función, una entrada y un resultado; ninguno exige leer
prosa para decidir si pasa; CA-9 declara explícitamente que no se puede marcar y por qué,
que es la forma honesta de tener un criterio sin línea base.

`validar_spec.py` da **12 de 12** invariantes sobre la spec de ahora. Cuando empecé daba
11 de 12.

Queda **una** objeción de fondo y **una** deuda.

## 2. La objeción: CA-2 acepta cualquier excepción

> CA-2 — `validar_nivel_de_calor(texto, nivel_no_valido, vt)` **lanza**, y existe un test
> que lo comprueba con un nivel que no está en la escala.

RF-CAL-13 no pide que lance: pide que lance **un error de dominio tipado de
`commons/errors/`**. Un `ValueError` pelado pasaría CA-2 sin cumplir el requisito, y un
`KeyError` también — que no es hipotético: es exactamente lo que hacía `validar_discurso`
hasta hace un rato (§4).

Apretarlo no cuesta nada, porque el código ya lo cumple: desde el arreglo de Jose lanza
`EntradaFueraDeDominio`. Bastaría «lanza `EntradaFueraDeDominio`» en vez de «lanza».

## 3. La deuda: ningún criterio nombra su requisito

Cuatro requisitos —**RF-CAL-13, 14, 15 y 18**— no aparecen citados en ningún criterio de
aceptación. `validar_spec.py` lo reporta como aviso, no como fallo, y la distinción
importa:

| | Qué mide | Veredicto hoy |
| --- | --- | --- |
| **Traza explícita** (V-8 de `validar_spec.py`) | Que el texto del CA nombre el `RF-*` | 4 sin traza |
| **Correspondencia semántica** (revisión de Mario) | Que exista un criterio que compruebe lo que el requisito exige | 0 sin cobertura |

Las dos son ciertas y ninguna sobra. La de Mario detecta el hueco real; la mecánica es la
que aguanta una renumeración y la que puede correr en CI.

**La prueba del coste de no tenerla está en esta misma auditoría:** Mario y yo
reconstruimos la cobertura RF→CA por separado y nos salieron mapas distintos. Él dedujo
13→CA-2, 14→CA-3, 15→CA-4, 18→CA-6; yo no pude deducir ninguno, porque el texto no lo
dice. Dos lectores competentes, dos resultados, sobre nueve criterios. Con treinta y con
tres meses de por medio, esto no se reconstruye: se reinventa.

La 001 tiene la misma deuda y se nota igual: `validar_spec.py` encuentra allí **once
criterios que no declaran su marca T/A/I/D/U**, y esa spec está en `en-revision`.

## 4. H-7 — hallazgo real a las 16:45, cerrado a las 17:00

`validar_discurso` fallaba en abierto fuera de su dominio declarado. Contraejemplos
ejecutados a las 16:45, con los seis arreglos de Jose ya dentro:

```
tiempo='PASADO'     -> 0 defectos        <-- se saltaba la comprobación entera
tiempo='preterito'  -> 0 defectos
persona='segunda'   -> KeyError: 'segunda'
```

Mismo patrón que H-2 y H-1, en la función que H-6 ya tocaba: una errata de mayúsculas
apagaba media VOZ-03 sin ruido, y la puerta lee `[]` como «limpio».

**Ya no reproduce.** Verificado a las 17:00 por mí, y antes por Nubia y por Mario de forma
independiente: las cuatro entradas fuera de escala lanzan `EntradaFueraDeDominio`. Jose lo
cerró en los minutos intermedios.

Queda constancia por dos razones. La primera es que las dos propiedades siguen en
`sonda_dominio.py` (`test_h7a`, `test_h7b`) y ahora **protegen el arreglo de una
regresión**, que es su verdadero trabajo. La segunda es lo que el episodio demuestra:
RF-CAL-13 está escrito como propiedad universal —«**ningún** validador mecánico…»— y los
criterios lo comprueban función por función. Un defecto de ese género sobrevive a seis
arreglos y aparece en la función de al lado. No lo cierra arreglar la de turno; lo cierra
una propiedad que recorra todos los validadores.

## 5. Lo que sí está cubierto, y conviene que esté escrito

RF-CAL-15 habla de «sus colecciones de entrada»; CA-4 nombra dos validadores. Comprobé los
otros dos y **pasan**: `validar_objetos` y `validar_conocimiento` ya son independientes del
orden, con el `_ya_lo_sabia` de Jose dentro. Son dos funciones que el plan no tiene que
tocar — y ahora hay una propiedad que avisará el día que alguien las toque.

De las siete propiedades de `sonda_dominio.py`, **las siete pasan** a las 17:05.

## 6. El validador de specs

`validar_spec.py` comprueba doce invariantes de `CLAUDE.md` §3.2 sobre cualquier spec del
repositorio: frontmatter completo · `id` igual a la carpeta · estado válido · firma si está
aprobada · sin preguntas abiertas si está aprobada · secciones obligatorias · hay requisitos
y criterios · todo requisito con cobertura · cada criterio con su marca de verificación ·
todo hallazgo con requisito · enlaces que resuelven · ningún criterio dado por bueno antes
de `implementada`.

Falla cerrado: si no puede evaluar —falta una sección, el frontmatter no parsea— eso es un
fallo, no un «no aplica». Es la misma regla que esta spec le exige a los validadores de
G1a, aplicada al validador de la spec.

Hoy: **12/12 en la 002** y **11/12 en la 001**. Esa segunda cifra importa tanto como la
primera: un validador que solo encuentra defectos en la spec que se está auditando suele
estar escrito para encontrarlos.

Dos decisiones de diseño discutibles, por si alguien quiere cambiarlas:

- **V-8 no exige un CA por requisito.** La 001 cubre RF-CAL-02 y RF-CAL-03 por Inspección
  firmada por el autor (D-09), y eso es cobertura legítima: T/A/I/D/U, no solo T. V-8 solo
  bloquea que un identificador no aparezca en **ninguna** sección.
- **V-12** impide marcar `[x]` antes de `implementada`. La casilla marcada es la
  afirmación más barata de hacer y la más cara de creer.

## 7. Lo que esta auditoría no verifica

| Qué | Por qué |
| --- | --- |
| Que los hallazgos estén bien **diagnosticados** | Reproduje los fallos; no revisé si la causa que la spec les atribuye es la correcta |
| Que no queden más H-7 | Barrí `persona` y `tiempo_verbal`; los demás parámetros de los siete validadores no están recorridos |
| Que el criterio de cada validador sea el **acertado** | Como dice la propia spec: una propiedad comprueba lo enunciado, no si enunciarlo estuvo bien |
| **P-1 a P-5** | No las contesto: cuatro ya las ha contestado el código y ninguna está firmada. Eso lo firma `maujimenez4`, y ningún agente puede hacerlo por él — tampoco autorizado por otro agente |
