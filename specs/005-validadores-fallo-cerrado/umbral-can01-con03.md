# Umbral de CAN-01 y CON-03 — registro de la medición

Lo que D-3 autorizó medir, y qué pasó al medirlo. Medido el **2026-09-23 a las 16:40**,
contra el árbol de ese momento (444 tests en verde, `ruff` limpio).

## Resultado: **no hay umbral. La corrida murió en la escena 1.**

    REAL · 10 escenas · base …/corrida-umbral/obra.db

    ValueError: el fragmento citado no aparece en la version vtexto-a70c65bb02c7:
    'conozco a todos los clientes de este barrio en un radio de tres manzanas'

    escenas completadas ....... 0 de 10
    ejecuciones registradas ... 1 (el Escritor de es1)
    defectos registrados ...... 0
    coste ..................... 0,0517 USD

Evidencia conservada fuera del repositorio, porque contiene prosa generada
(`CLAUDE.md` §15): `C:\Users\student\Documents\evidencia-corridas\corrida-continuista-2026-09-23\`,
con `obra.db` y `salida.log`.

## H-7 · Una cita inventada por el Continuista **mata el proceso**

No es un fallo de la corrida: es el séptimo defecto de los validadores, y no estaba en la
spec porque solo aparece con el Continuista real dentro.

`validar_conocimiento` —y con él `validar_canon`, `validar_continuidad_fisica` y
`validar_objetos`— llama a `citar(texto, a.cita, …)` con la `cita` **que devuelve el
modelo**. Y `citar` está escrito así a propósito:

```python
inicio = texto.find(fragmento)
if inicio < 0:
    raise ValueError(...)
```

La cabecera de `defectos.py` lo llama garantía *por construcción*: «un validador no puede
emitir una cita que no esté en el texto». Y es cierto — pero la forma de esa garantía es
una **excepción que nadie captura**, y sube por `ciclo_de_escena` hasta matar la corrida.

**La ironía es exacta y conviene no perderla.** Toda la defensa contra la cita inventada
—`comprobar_forma`, los axiomas 11 y 12, `architecture.md` §8.3, la tasa de defectos mal
formados que `verification.md` §6.3 celebra como «la primera señal que mide al
Continuista»— vive en `puerta.py`, **aguas abajo** de los validadores. Para que un defecto
mal formado se registre en vez de bloquear, primero tiene que **existir**; y aquí no llega
a construirse, porque `citar` revienta antes.

Dicho de otro modo: el sistema tiene un mecanismo cuidadoso para tratar el caso «el
Continuista se inventó la cita», y ese caso no llega nunca al mecanismo.

### Por qué era previsible y aun así nadie lo vio

Que un modelo parafrasee al citar es su comportamiento más predecible. Aquí citó
`'conozco a todos los clientes de este barrio en un radio de tres manzanas'` sobre una
prosa que casi seguro decía lo mismo con otras palabras —o en tercera persona—.

No lo vio nadie porque **nada lo podía ver**:

- `corrida.py --seco` pasa `AFIRMACIONES_FALSAS = "[]"`: el doble no afirma nada, así que
  ningún `citar` se ejecuta con entrada del modelo. Es el mismo punto ciego que ya está
  escrito en el plan de la 001.
- Los tests de `calidad` construyen las `Afirmacion` a mano, con citas que **sí** están en
  el texto. Codifican el camino feliz por construcción.
- La sonda de invariantes tampoco: sus `Afirmacion` las escribo yo, no un modelo.

Es el mismo patrón de H-2 y H-6 —un camino que devuelve algo aceptable porque nunca se
recorrió con entrada real— y la tercera vez hoy que aparece la misma forma de fallo.

## Qué hacer con esto, y qué no decidir aquí

**No lo he arreglado ni lo he metido como requisito.** Dos razones:

1. `features/calidad/` y `features/escritura/service.py` los lleva otra sesión, y hay
   trabajo sin commitear que no se ve en `git`.
2. Esta spec acaba de cerrar sus cinco preguntas. Añadirle un `RF-CAL-19` por decisión de
   un agente la devolvería a `borrador` sin que nadie lo haya firmado, y §3.2 dice que una
   spec no se aprueba —ni se reabre— a medias.

Lo que sí está decidido por los hechos: **el umbral de D-3 no se puede medir hasta que
H-7 esté cerrado.** Una corrida nueva sin arreglarlo volverá a morir en cuanto el
Continuista parafrasee, que es en cualquier escena.

Preguntas que hay que contestar antes de repetirla, y que no son mías:

- ¿Una cita que no ancla es un **defecto mal formado** —lo que ya contempla
  `comprobar_forma`, y entonces `citar` debe devolver el defecto marcado en vez de
  lanzar— o un **fallo del paso** del Continuista, como RF-ORQ-15 trata al código fuera de
  taxonomía?
- Si es lo primero, la tasa de defectos mal formados de `verification.md` §6.3 pasa a
  medir algo real por primera vez, y conviene decirlo ahí.
- ¿Se aprovecha para que `--seco` deje de pasar `[]` y el doble devuelva afirmaciones con
  citas inventadas? Mientras no lo haga, la corrida en seco seguirá sin poder ver esta
  clase de fallo.

## Coste

0,0517 USD. La corrida completa estaba presupuestada en 1,5–2 USD según la estimación de
la sesión **Julio**, que midió 0,93 USD sin Continuista. Lo gastado no se pierde: compró
H-7, que es más de lo que habría dado el umbral.
