# Herramientas de verificación formal

Las dos que pide el encargo: **Lean 4** para la cronología de la historia
(`examen-final.md` §5c) y **TLA+ / TLC** para la máquina de estados del harness
(§5d). Este fichero dice cómo se instalan y cómo se comprueba que funcionan.

**Las dos mitades no están igual de avanzadas, y conviene saberlo al entrar.**
La de TLA+ está **escrita y verificada**: `tla/Harness.tla` especifica la máquina
de `architecture.md` §3.9 con tres invariantes de seguridad y una propiedad de
*liveness*, y su correspondencia con el código la comprueba un test. La de Lean
sigue siendo **andamiaje**: el fichero mínimo prueba que la herramienta y la
puerta funcionan, pero el validador de §5c —generar el fichero desde la
cronología en SQLite— es de la Fase 4.

```
formal/
  lean/          proyecto Lake · fichero mínimo con dos invariantes probados
  tla/           tla2tools.jar · Juguete.tla (humo) · Harness.tla + su README
```

---

## Versiones verificadas

Instaladas y ejecutadas en Windows 11 (10.0.26200, AMD64) el 2026-09-24.

| Herramienta | Versión | De dónde |
| --- | --- | --- |
| elan | 4.2.4 (227caca13, 2026-08-25) | `elan-init.exe` del repositorio de `leanprover/elan` |
| Lean | **4.34.0** (x86_64-w64-windows-gnu, commit 293d5d0c) | la trae elan como *toolchain* `stable` |
| Lake | 5.0.0-src+293d5d0 | va dentro del *toolchain* de Lean |
| Java | OpenJDK **21.0.12.1+1 LTS** (Temurin, JRE) | winget · `EclipseAdoptium.Temurin.21.JRE` |
| TLC | **2.19** de 08-08-2024 (rev 5a47802) | `tla2tools.jar` de la última *release* de `tlaplus/tlaplus` |

`lean-toolchain` fija la versión de Lean dentro del proyecto, así que quien
clone obtiene **4.34.0** aunque su `stable` sea otro. Es deliberado: una prueba
que compila con una versión y no con otra no es una prueba reproducible.

---

## Instalación

### Lean 4 — por `elan`, no a mano

`elan` es el gestor de *toolchains* de Lean, equivalente a `rustup`. **No está
en winget**, así que va por su instalador:

```powershell
curl.exe -sSL -o "$env:TEMP\elan.zip" https://github.com/leanprover/elan/releases/latest/download/elan-x86_64-pc-windows-msvc.zip
Expand-Archive "$env:TEMP\elan.zip" -DestinationPath "$env:TEMP\elan" -Force
& "$env:TEMP\elan\elan-init.exe" -y --default-toolchain stable
```

Queda en `%USERPROFILE%\.elan\bin`, que el instalador añade al `PATH` del
usuario. **En la sesión donde se instala no está todavía**: o se abre una
terminal nueva, o se antepone a mano.

No hace falta administrador.

### TLA+ / TLC — Java más un `.jar`

TLC es Java. Basta el JRE:

```powershell
winget install --id EclipseAdoptium.Temurin.21.JRE --silent --accept-package-agreements --accept-source-agreements
```

**Sí pide administrador**, y `--scope user` no sirve: el instalador de Temurin
solo existe en ámbito de máquina y winget contesta `No applicable installer
found`. Si no se puede elevar, el *zip* portable de Adoptium vale igual.

Después, el `.jar`, que no se instala: se descarga y se invoca.

```powershell
curl.exe -sSL -o formal\tla\tla2tools.jar https://github.com/tlaplus/tlaplus/releases/latest/download/tla2tools.jar
```

`tla2tools.jar` pesa **2,27 MB** y está *commiteado* a propósito: son las
herramientas exactas con las que se comprobó la especificación, y bajar «la
última» dentro de seis meses puede traer otro TLC.

---

## Comprobar que funcionan

Las dos comprobaciones corren de verdad y su salida está abajo. **Un «ya está
instalado» sin ejecución no vale** (`CLAUDE.md` §16).

### Lean

```bash
cd formal/lean
lake build          # compila y comprueba las pruebas
lake exe cronologia # salida legible de los dos invariantes
```

`Cronologia/Basic.lean` define los dos invariantes de §5c —orden temporal y
que nadie esté en dos lugares en el mismo momento— y prueba **cuatro** cosas:
que se cumplen en una cronología coherente y que **fallan** en las dos que los
violan. Lo segundo es la mitad que prueba algo: un invariante que solo se ha
visto pasar no distingue una cronología buena de una función que devuelve
`true`.

Salida de `lake exe cronologia`:

```
orden temporal (coherente)  : true
sin ubicuidad  (coherente)  : true
orden temporal (desordenada): false
sin ubicuidad  (ubicua)     : false
```

**Y lo que de verdad exige §5c —que un fallo detenga la publicación— está
comprobado.** Cambiando a propósito `ordenTemporal desordenada = false` por
`= true`, `lake build` se niega:

```
error: Cronologia/Basic.lean:48:67: Tactic `decide` proved that the proposition
error: build failed
```

Ese es el mecanismo entero: si el fichero generado desde SQLite contiene una
cronología incoherente, la prueba no cierra y el *build* falla.

### TLA+

```bash
cd formal/tla
java -cp tla2tools.jar tlc2.TLC -config Juguete.cfg Juguete.tla
```

```
Model checking completed. No error has been found.
7 states generated, 6 distinct states found, 0 states left on queue.
The depth of the complete state graph search is 6.
```

**`Juguete.tla` es el humo; la especificacion del harness y su tabla de correspondencia estan en [`tla/README.md`](tla/README.md).**

`Juguete.tla` es un contador acotado con un invariante de seguridad
(`EnRango`) y una propiedad de *liveness* (`Termina`). No modela nada del
sistema: comprueba que TLC parsea, explora y verifica las dos clases de
propiedad que §5d va a necesitar.

---

## Lo que cuesta

| Paso | Tiempo real |
| --- | --- |
| `winget install` del JRE | ~40 s, con descarga |
| Descargar `tla2tools.jar` | ~2 s |
| `elan-init.exe` | **10,4 s** |
| Primera descarga del *toolchain* de Lean (4.34.0) | ~60 s, la dispara el primer `lean --version` o `lake build` |
| `lake build` en frío | **13,1 s** |
| `lake build` incremental | 3,4 s |
| TLC sobre el modelo de juguete | **1,7 s** |

**Lean no tarda «minutos» en este proyecto**, que era el riesgo que había que
descartar. Tarda porque descarga 4.34.0 una vez; a partir de ahí el ciclo es de
segundos. El dato que importa para la Fase 4 es el **incremental**: 3,4 s con
un fichero trivial. Un fichero generado con cientos de eventos subirá, y eso
todavía **no está medido**.

---

## Lo que me preocupa, y conviene que esté escrito

- **El tiempo de Lean con una cronología real no se conoce.** Los 3,4 s son de
  cuatro pruebas por `decide` sobre listas de dos elementos. `decide` evalúa
  por fuerza bruta: con una cronología de diez capítulos y un invariante
  cuadrático —«nadie en dos lugares a la vez» compara todos contra todos— puede
  crecer deprisa. Si la Fase 4 lo nota, la salida no es bajar el invariante:
  es cambiar `decide` por una prueba estructurada. Conviene medirlo pronto.
- **`decide` sobre `String` no es gratis.** El fichero mínimo usa `Nat` para
  personaje y lugar a propósito. El generador de la Fase 4 saldrá de SQLite,
  donde son cadenas; mapearlas a índices al generar es más barato que probar
  igualdades de cadenas dentro de Lean.
- **La máquina de estados no es una función de (estado, señal).**
  `maquina.py:172` tiene la tabla explícita, pero su propia cabecera avisa de
  que **el destino de `REPARANDO` no sale de la tabla**: depende del contador de
  reparaciones contra `INTENTOS_MAXIMOS`. Así que la especificación de §5d **no
  puede** ser una relación de transición sobre los diez estados: el contador es
  parte del estado. Es justo lo que exige el invariante «el número de reintentos
  nunca supera el límite», así que sale gratis si se ve venir, y obliga a
  rehacer la especificación si no.
- **Y §5d pide más de lo que `maquina.py` contiene.** Dos de sus invariantes
  —que la reanudación desde *checkpoint* no duplique ni pierda capítulos, y que
  la versión anterior se conserve tras una regeneración— hablan de estado que
  vive en `checkpoint.py` y en las versiones publicadas, no en la máquina del
  ciclo de escena. La especificación abarca las dos, y el README que pide §5d
  —«qué estado o transición del código implementa cada acción»— tendrá que
  citar los dos ficheros.
- **`tla2tools.jar` va commiteado**, y es un binario de 2,27 MB en el
  repositorio. Es a propósito —reproducibilidad— pero es una decisión, no un
  descuido: quien prefiera bajarlo en CI puede, y entonces hay que fijar la
  versión, porque `latest` no es una versión.
