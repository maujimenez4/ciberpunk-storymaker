# Lenguajes de especificación y verificación — catálogo con veredicto

Quince lenguajes de métodos formales, evaluados **contra este repositorio** el
2026-09-23. Cada fila lleva enlace oficial, tendencia y un veredicto. Un catálogo sin
veredictos no es una decisión; es una lista de deseos (`SKILL.md`, punto 4).

> **Regla de lectura, y es la que evita el error caro.** Ninguno de los quince se
> instala. Lo que se adopta de tres de ellos es la **técnica**, escrita en Python con las
> herramientas que ya están en `pyproject.toml`. Un modelo formal que nadie ejecuta en CI
> es peor que no tenerlo: afirma una garantía que no se está comprobando, que es justo lo
> que `verification.md` §5 advierte de los «Previsto» sin umbral.
>
> La razón de fondo es el **hueco de refinamiento**: demostrar un modelo no demuestra el
> código. El validador que corre en producción es `validadores.py`, y una prueba en Lean
> sobre una reescritura del mismo algoritmo deja sin verificar exactamente lo que se
> quería verificar. Se paga el coste entero de la especificación y se compra confianza
> sobre otro artefacto.

## 1. Las quince filas

| Lenguaje | Qué es | Dónde se usa fuera | Tendencia | Veredicto aquí |
| --- | --- | --- | --- | --- |
| [TLA+](https://foundation.tlapl.us) | Especificación y comprobación de modelos sobre estados y transiciones | AWS, Microsoft, Oracle, Intel, bases de datos distribuidas | ↑ moderada | **Técnica adoptada** — §2.2 |
| [Quint](https://quint-lang.org) ([repo](https://github.com/informalsystems/quint)) | TLA+ con sintaxis moderna y tipos | Blockchain, protocolos de consenso | ↑↑ rápida, base pequeña | **Técnica adoptada** — §2.2. Es el que se usaría si algún día se modela |
| [Alloy](https://alloytools.org) | Especificación ligera sobre relaciones, con contraejemplos en alcance pequeño | Academia, diseño de modelos de datos | → estable | **Técnica adoptada** — §2.1. La que más ha rendido |
| [Dafny](https://dafny.org) | Lenguaje verificable con precondiciones y postcondiciones | AWS, *benchmarks* de IA | ↑ creciendo | **Técnica adoptada** — §2.3 |
| [SPARK (Ada)](https://www.adacore.com/about-spark) | Subconjunto verificable de Ada | Aeroespacial, defensa, ferroviario | → nicho regulado | **Descartado** — §3.1. Su idea de contrato entra por Dafny |
| [Lean 4](https://lean-lang.org) | Asistente de pruebas y lenguaje de programación | Matemáticas, AWS, DeepMind, Harmonic | ↑↑ el que más crece | **Descartado** — §3.2 |
| [Rocq](https://rocq-prover.org) (antes Coq) | Asistente de pruebas | CompCert, academia, criptografía | → estable | **Descartado** — §3.2 |
| [Isabelle/HOL](https://isabelle.in.tum.de) | Asistente de pruebas | seL4, academia | → estable | **Descartado** — §3.2 |
| [Agda](https://agda.readthedocs.io) / [Idris 2](https://www.idris-lang.org) | Tipos dependientes | Investigación en teoría de tipos | → académico | **Descartado** — §3.2 |
| [F\*](https://www.fstar-lang.org) | Tipos dependientes y efectos | Criptografía: HACL\*, presente en Firefox, Linux y Windows | → nicho | **Descartado** — §3.2 |
| [Verus](https://github.com/verus-lang/verus) | Verificación de código Rust | Sistemas en Rust, Microsoft Research | ↑↑ rápida, base pequeña | **Descartado** — §3.3. No hay Rust en el *stack* |
| [Kani](https://github.com/model-checking/kani) | Comprobador de modelos para Rust | AWS, librería estándar de Rust | ↑ creciendo | **Descartado** — §3.3. No hay Rust en el *stack* |
| [P](https://p-org.github.io/P/) | Modelado de máquinas de estados que se comunican | AWS (S3, DynamoDB) | ↑ creciendo | **Descartado** — §3.4 |
| [B-Method / Event-B](https://www.atelierb.eu/en/) ([Event-B](http://www.event-b.org)) | Especificación por refinamiento | Metro y ferrocarril: Alstom, Siemens | → / ↓ legado | **Descartado** — §3.1 |
| [VDM](https://www.overturetool.org) · [PVS](https://pvs.csl.sri.com) · Z (ISO/IEC 13568) | Especificación clásica | NASA (PVS), sistemas industriales heredados | ↓ en declive | **Descartado** — §3.1 |

Las tendencias son las que aportó el equipo el 2026-09-23 (§6). No se han medido aquí y
no deciden nada por sí solas: un lenguaje que crece rápido sigue siendo inaplicable si no
toca Python.

## 2. Lo que sí se adopta, y qué produjo

Los tres seleccionados aportan **tres maneras distintas de enunciar una invariante**. Las
tres se escriben con `hypothesis`, que ya es dependencia y ya corre en CI.

### 2.1 De Alloy: alcance pequeño y contraejemplo

La *small scope hypothesis* de Jackson: casi todo fallo de un modelo relacional se
manifiesta ya en un alcance diminuto. No hacen falta cien hechos de canon; con **dos
hechos, dos valores y dos órdenes de discurso** basta.

Traducción aquí: generar conjuntos minúsculos y comprobar una invariante sobre la
relación, no sobre un ejemplo. La que rinde es la **independencia del orden**: si el
resultado de un validador cambia al barajar su entrada, hay un desempate sin declarar.

### 2.2 De TLA+ y Quint: separar seguridad de vivacidad, y nombrar el invariante de estado

Una propiedad de **seguridad** dice que nunca ocurre algo malo; una de **vivacidad**, que
acaba ocurriendo algo bueno. Confundirlas es el error habitual. Aquí:

- Seguridad: el ledger es *append-only*; ninguna llamada supera los 100.000 tokens;
  ninguna escena excede el nivel de calor declarado.
- Vivacidad: toda escena termina aprobada o escalada a una persona tras dos reintentos.

`verification.md` §3 ya declara la comprobación de modelos **«No aplicable, por ahora»**,
y esta evaluación no lo cambia: diez estados con transiciones cerradas y una escena en
vuelo por obra siguen cabiendo en tests. Lo que cambia es que ahora está escrito **cuál**
sería la herramienta si se levanta esa restricción: **Quint**, por sintaxis y tipos, no
TLA+ en su notación original.

### 2.3 De Dafny y SPARK: la precondición se declara, y el fallo es cerrado

Un validador es una función con un dominio de entrada. Dafny obliga a escribirlo
(`requires`); Python no. Si el dominio no se declara, una entrada fuera de él no produce
error: produce **silencio**, y en un validador de seguridad el silencio se lee como
«aprobado».

Traducción aquí, y es la regla que vale igual para el código y para los prompts: **un
validador que no entiende su entrada lanza; nunca devuelve lista vacía.**

### 2.4 Qué encontró esto de verdad

Cinco invariantes sondeadas sobre `features/calidad/validadores.py`. **Cuatro cayeron**,
con contraejemplo reproducible. Los hallazgos y sus criterios de aceptación viven en
`specs/002-validadores-fallo-cerrado/spec.md`, no aquí: un validador nuevo o corregido es
un requisito, y los requisitos viven en una spec (`CLAUDE.md` §3.2, `verification.md`
§6.4).

## 3. Por qué se descartan los doce restantes

Agrupados por la razón, no repetida fila a fila. Saber **qué se escapa de un método que
no se usa** es lo que impide volver a proponerlo dentro de seis meses.

### 3.1 Nicho regulado o legado sin obligación normativa aquí

**SPARK (Ada), B-Method/Event-B, Z, VDM, PVS.** Su valor está donde un regulador exige la
evidencia: certificación aeroespacial, señalización ferroviaria, defensa. Aquí no hay
regulador, y el coste de la especificación por refinamiento no lo paga nadie. Su idea
útil —el contrato explícito— entra por §2.3 sin traer el lenguaje.

### 3.2 Asistentes de pruebas: el coste está en la especificación, y el hueco de refinamiento no se cierra

**Lean 4, Rocq, Isabelle/HOL, Agda, Idris 2, F\*.** Son los más capaces de la lista y por
eso conviene ser preciso al descartarlos:

1. Ninguno tiene puente con Python. Habría que reimplementar el validador, y el que corre
   en producción seguiría sin demostrarse.
2. Las invariantes que merecerían demostración aquí —el estado en T deriva del ledger,
   ningún paquete supera los 100.000 tokens— están garantizadas **por construcción**:
   vista derivada, ledger *append-only*, `ContextBudgetExceeded`. Construirlas sale más
   barato que demostrarlas, y así lo recoge `verification.md` §2.
3. El punto ciego que ya declara `verification.md` §2.1 sigue en pie: una demostración
   correcta de la especificación equivocada es una demostración correcta.

Y el argumento decisivo, que es de dominio y no de coste: **el riesgo dominante de este
sistema no es aritmético ni estructural, es semántico.** Los riesgos descubiertos de
`verification.md` §7 —un hecho inventado que entra al canon, un dato que le faltó al
paquete— no se dejan enunciar como teorema. Ninguno de estos seis los tocaría.

### 3.3 Atados a Rust

**Verus, Kani.** Verifican código Rust. El *stack* de `CLAUDE.md` §4 es Python 3.12 y
TypeScript, y no hay ningún componente candidato a reescribirse en Rust. Se reabren el día
que lo haya, no antes.

### 3.4 Resuelven un problema que aquí no existe

**P.** Modela máquinas de estados que se comunican y descubre entrelazados imposibles de
alcanzar con tests. Aquí hay **una escena en vuelo por obra** (`architecture.md` §3.8) y
**una llamada al modelo por proceso** (`CLAUDE.md` §4.1): la concurrencia está acotada por
diseño, así que no hay entrelazado que explorar. Es el mismo razonamiento que deja la
comprobación de modelos en «No aplicable, por ahora», y se reconsidera con la misma
condición.

## 4. Lo que esta evaluación **no** compra

- No añade cobertura a ninguna casilla de `verification.md` §7 por sí sola. Lo que la
  mueve son las correcciones de la spec 002, no el hecho de haber evaluado quince
  lenguajes.
- Las propiedades buscan violaciones de la invariante **enunciada**. La que nadie enunció
  no se busca: que un validador sea determinista y falle cerrado no dice que su criterio
  sea el correcto.
- Sigue sin tocar el punto ciego central de `verification.md` §6.2: la puerta G1a es
  mecánica en el **contraste**, no en la **extracción**. Una afirmación que el Continuista
  no extraiga no llega nunca al validador, por bien especificado que esté.

## 5. Cuándo se reabre esto

Tres condiciones concretas, para que la revisión no dependa de que alguien se acuerde:

1. Se levanta la restricción de una escena en vuelo por obra → vuelven **Quint** y **P**.
2. Aparece un componente en Rust → vuelven **Verus** y **Kani**.
3. Un regulador o un cliente exige evidencia de certificación → vuelve **SPARK** o
   **Event-B**, según el sector.

## 6. Procedencia

- La lista de quince lenguajes, con sus enlaces y tendencias, la aportó el equipo
  (`maujimenez4`) el **2026-09-23**. Las tendencias se reproducen tal como se recibieron.
- Los enlaces son los sitios oficiales de cada proyecto, no páginas de producto ni de
  proveedor, igual que en [`methodologies.md`](methodologies.md).
- Z no tiene sitio oficial único: es el estándar **ISO/IEC 13568:2002**.
- Las skills de este repositorio y su origen se registran en
  [`SOURCES.md`](../../SOURCES.md). El repositorio del que se traen las skills propias del
  equipo es <https://github.com/maujimenez4/MyFactory>.
