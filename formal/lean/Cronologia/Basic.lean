/-
  Fichero **mínimo de humo**: existe para comprobar que Lean y `lake build`
  funcionan en esta máquina, y que un invariante falso detiene la compilación.

  **No es el validador de §5c.** Ese lo escribe la Fase 4, y se **genera**
  desde la cronología en SQLite. Aquí los identificadores son `Nat` en vez de
  `String` a propósito: mantiene las pruebas por `decide` triviales y rápidas,
  que es lo único que este fichero tiene que demostrar.
-/

structure Evento where
  momento   : Nat
  personaje : Nat
  lugar     : Nat
  deriving Repr, DecidableEq

/-- Invariante 1 (§5c): los eventos respetan el orden temporal declarado. -/
def ordenTemporal : List Evento → Bool
  | []      => true
  | [_]     => true
  | a :: b :: r => (a.momento ≤ b.momento) && ordenTemporal (b :: r)

/-- Invariante 2 (§5c): nadie está en dos lugares en el mismo momento. -/
def sinUbicuidad (es : List Evento) : Bool :=
  es.all fun a => es.all fun b =>
    !((a.personaje == b.personaje) && (a.momento == b.momento)) || (a.lugar == b.lugar)

/-- Cronología coherente: Mara pasa del lugar 0 al 1. -/
def coherente : List Evento :=
  [ { momento := 0, personaje := 0, lugar := 0 },
    { momento := 1, personaje := 0, lugar := 1 } ]

/-- Cronología con los momentos al revés. -/
def desordenada : List Evento :=
  [ { momento := 5, personaje := 0, lugar := 0 },
    { momento := 1, personaje := 0, lugar := 1 } ]

/-- Mara en dos lugares en el mismo momento. -/
def ubicua : List Evento :=
  [ { momento := 2, personaje := 0, lugar := 0 },
    { momento := 2, personaje := 0, lugar := 1 } ]

-- Los dos invariantes se cumplen donde deben...
theorem coherente_ordenada  : ordenTemporal coherente = true  := by decide
theorem coherente_sin_ubicuidad : sinUbicuidad coherente = true := by decide

-- ...y **fallan** donde deben, que es la mitad que de verdad prueba algo.
theorem desordenada_falla : ordenTemporal desordenada = false := by decide
theorem ubicua_falla      : sinUbicuidad ubicua = false      := by decide
