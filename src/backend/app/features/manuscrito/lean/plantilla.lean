/-
  Los invariantes de la cronologia. Encargo §5c, `RF-FOR-02`.

  Este fichero es **la mitad fija**; la otra la genera `generar_lean` desde la
  vista `cronologia` y se pega debajo. Juntos forman un fichero autocontenido
  que compila con `lean` a secas: sin Mathlib, sin dependencias y sin proyecto.

  **Un invariante que se incumple impide compilar.** Esa es la puerta: no hay un
  informe que alguien tenga que leer, hay un `lake`/`lean` que devuelve error y
  una publicacion que no ocurre.

  ## Por que enteros y no cadenas

  Las pruebas se cierran con `decide`, que evalua por fuerza bruta. Comparar dos
  `Nat` es una instruccion; comparar dos `String` recorre caracteres, y
  `sinUbicuidad` compara `n²` pares. Los nombres viajan una vez, en sus tablas.

  Medido sobre esta plantilla: **2,4 s con 40 eventos**, que es una novela de
  diez capitulos con cuatro personajes por escena. El plan avisaba de que lo
  cuadratico podia morder pronto; a esta escala no muerde.

  ## Que NO prueba este fichero, y conviene leerlo antes de creer que si

  **No prueba que el tiempo de la historia avance.** El encargo §5c lo sugiere y
  el esquema no lo permite: `evento.tiempo_historia` es texto libre -- «una
  manana», «el verano del 98» --, no una fecha. El `momento` de aqui es un
  **indice por orden de aparicion**, que es orden de discurso; en un salto atras
  el discurso avanza mientras la historia retrocede. Sirve para preguntar si dos
  filas comparten momento, que es lo que «nadie en dos lugares a la vez»
  necesita, y **no** para preguntar si el tiempo avanza.

  **Y la regla de dominio 13 -- la edad concuerda con la fecha de nacimiento --
  no esta aqui, a proposito.** Es condicional: «cuando ambas existen». Hoy solo
  el destinatario tiene fecha de nacimiento y no es un `Personaje`, asi que el
  antecedente casi nunca se cumple. Escribirla como invariante daria un verde
  permanente que pareceria una garantia y seria una tautologia. Cuando los
  personajes tengan fecha, entra aqui con su test.
-/

/-- Una fila: **un participante** en un momento y un lugar.

Una fila por participante y no por evento: `sinUbicuidad` compara pares
preguntando «mismo personaje, mismo momento, distinto lugar», y un evento con
tres participantes metido en una sola fila no tendria pares que comparar. -/
structure Evento where
  momento   : Nat
  personaje : Nat
  lugar     : Nat
  deriving Repr, DecidableEq

/-- Desde `momento`, `personaje` ya no puede aparecer.

Sale de `evento.excluye[]`, que existe desde la Fase 2 y hasta hoy no lo
comprobaba nada: una muerte, una partida definitiva. -/
structure Exclusion where
  momento   : Nat
  personaje : Nat
  deriving Repr, DecidableEq

/-- **Invariante 1.** Nadie esta en dos lugares en el mismo momento.

Es literalmente lo que `CA-21` exige probar. -/
def sinUbicuidad (es : List Evento) : Bool :=
  es.all fun a => es.all fun b =>
    !((a.personaje == b.personaje) && (a.momento == b.momento)) || (a.lugar == b.lugar)

/-- **Invariante 2.** Nadie aparece despues de un evento que lo excluye.

Estricto (`>`), no `≥`: el evento que excluye a alguien **puede** tenerlo
presente. Quien muere esta en la escena de su muerte; lo que no puede es estar
en la siguiente. Con `≥` la propia muerte seria una violacion. -/
def sinReaparecidos (es : List Evento) (xs : List Exclusion) : Bool :=
  es.all fun e => xs.all fun x =>
    !((e.personaje == x.personaje) && (x.momento < e.momento))

-- La mitad generada se pega justo debajo de esta linea.
