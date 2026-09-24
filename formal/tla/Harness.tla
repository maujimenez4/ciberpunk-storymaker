-------------------------------- MODULE Harness --------------------------------
(***************************************************************************)
(* La maquina de estados de la NOVELA: `docs/architecture.md` §3.9.         *)
(*                                                                         *)
(* No es la del ciclo de escena (§3.3), que es la de `maquina.py`: esta la  *)
(* contiene. Y NO es una relacion de transicion sobre los diez estados: el  *)
(* destino de `REPARANDO` depende del contador de reparaciones —lo dice la  *)
(* cabecera de `maquina.py`—, asi que el contador es parte del estado.      *)
(*                                                                         *)
(* La correspondencia, accion a accion, vive en `correspondencia.toml` y la *)
(* comprueba un test junto a la maquina.                                   *)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS Capitulos, MaxReintentos, MaxRondas, MaxPeticiones

ASSUME Capitulos \in Nat \ {0}
ASSUME MaxReintentos \in Nat
ASSUME MaxRondas \in Nat
ASSUME MaxPeticiones \in Nat

Numeros == 1..Capitulos

VARIABLES estado, rondas, actual, integrados, validado, intento,
          versiones, peticiones, porRehacer

vars == <<estado, rondas, actual, integrados, validado, intento,
          versiones, peticiones, porRehacer>>

Estados == {"CONFIGURANDO", "PLANIFICADA", "ESCRIBIENDO_CAPITULO",
            "VALIDANDO_CAPITULO", "VERIFICANDO", "PUBLICADA",
            "REGENERANDO", "DETENIDA"}

(* Una version publicada lleva SU PROPIA foto de que capitulos la componen y *)
(* cuales habian pasado su puerta. Guardarla es lo que permite preguntar por *)
(* una version antigua despues de que el estado vivo haya cambiado.          *)
Version == [capitulos: SUBSET Numeros, validados: SUBSET Numeros]

(* `intento` indexado POR CAPITULO, como `checkpoint.reparaciones_del_capitulo`:
   ni por trabajo —un relanzamiento daria reparaciones infinitas— ni por obra
   —avanzar de capitulo consumiria reintentos, R-1—. Y su rango es el cuarto
   ejemplo del encargo §5d comprobado como tipo: el contador nunca se pasa. *)
TypeOK ==
  /\ estado \in Estados
  /\ rondas \in 0..MaxRondas
  /\ actual \in 0..Capitulos
  /\ integrados \subseteq Numeros
  /\ validado \in [Numeros -> BOOLEAN]
  /\ intento \in [Numeros -> 0..MaxReintentos]
  /\ versiones \in Seq(Version)
  /\ peticiones \in 0..MaxPeticiones
  /\ porRehacer \subseteq Numeros

Pendientes == Numeros \ integrados
Primero(S) == CHOOSE c \in S : \A d \in S : c =< d

Init ==
  /\ estado = "CONFIGURANDO"
  /\ rondas = 0
  /\ actual = 0
  /\ integrados = {}
  /\ validado = [c \in Numeros |-> FALSE]
  /\ intento = [c \in Numeros |-> 0]
  /\ versiones = << >>
  /\ peticiones = 0
  /\ porRehacer = {}

(* CONFIGURANDO --> CONFIGURANDO: falta un dato o hay contradiccion.        *)
(* Se acota con MaxRondas, y la razon se escribe porque no es inocente: un  *)
(* bucle sin cota hace imposible cualquier propiedad de liveness, y quien   *)
(* cierra la entrevista de verdad es el Comprador, que no es el harness.    *)
FaltaUnDato ==
  /\ estado = "CONFIGURANDO"
  /\ rondas < MaxRondas
  /\ rondas' = rondas + 1
  /\ UNCHANGED <<estado, actual, integrados, validado, intento,
                 versiones, peticiones, porRehacer>>

Planificar ==
  /\ estado = "CONFIGURANDO"
  /\ estado' = "PLANIFICADA"
  /\ UNCHANGED <<rondas, actual, integrados, validado, intento,
                 versiones, peticiones, porRehacer>>

(* R-1. NO toca `intento`, y esa ausencia es el requisito: avanzar de       *)
(* capitulo no consume reintentos (§3.9, `CA-9`). La guarda del medio es    *)
(* `checkpoint.empezar_capitulo`: no se empieza el siguiente con el actual  *)
(* sin integrar.                                                            *)
SiguienteCapitulo ==
  /\ estado \in {"PLANIFICADA", "VALIDANDO_CAPITULO"}
  /\ (estado = "VALIDANDO_CAPITULO") => (actual \in integrados)
  /\ Pendientes # {}
  /\ actual' = Primero(Pendientes)
  /\ estado' = "ESCRIBIENDO_CAPITULO"
  /\ UNCHANGED <<rondas, integrados, validado, intento,
                 versiones, peticiones, porRehacer>>

(* Prosa nueva: sin validar, aunque la anterior lo estuviera.               *)
Escribir ==
  /\ estado = "ESCRIBIENDO_CAPITULO"
  /\ estado' = "VALIDANDO_CAPITULO"
  /\ validado' = [validado EXCEPT ![actual] = FALSE]
  /\ UNCHANGED <<rondas, actual, integrados, intento,
                 versiones, peticiones, porRehacer>>

(* Las puertas aprueban. `EXTRAYENDO` e `INTEGRADA` de §3.3 se abstraen en  *)
(* esta accion: la maquina de la novela no las distingue, y el modelo no    *)
(* inventa estados que su documento no tiene.                               *)
Aprobar ==
  /\ estado = "VALIDANDO_CAPITULO"
  /\ ~validado[actual]
  /\ validado' = [validado EXCEPT ![actual] = TRUE]
  /\ integrados' = integrados \cup {actual}
  /\ UNCHANGED <<estado, rondas, actual, intento,
                 versiones, peticiones, porRehacer>>

(* R-1, el otro lado: `Reparar` SI incrementa el contador. Y el destino     *)
(* depende de el, que es la decision previa 1 de este plan.                 *)
Reparar ==
  /\ estado = "VALIDANDO_CAPITULO"
  /\ ~validado[actual]
  /\ intento[actual] < MaxReintentos
  /\ intento' = [intento EXCEPT ![actual] = @ + 1]
  /\ estado' = "ESCRIBIENDO_CAPITULO"
  /\ UNCHANGED <<rondas, actual, integrados, validado,
                 versiones, peticiones, porRehacer>>

Escalar ==
  /\ estado = "VALIDANDO_CAPITULO"
  /\ ~validado[actual]
  /\ intento[actual] = MaxReintentos
  /\ estado' = "DETENIDA"
  /\ UNCHANGED <<rondas, actual, integrados, validado, intento,
                 versiones, peticiones, porRehacer>>

(* Sin esto, TLC informa de `deadlock` en los estados terminales de §3.9,   *)
(* que son finales y no averias.                                            *)
Fin ==
  /\ estado = "DETENIDA"
  /\ UNCHANGED vars

Next ==
  \/ FaltaUnDato
  \/ Planificar
  \/ SiguienteCapitulo
  \/ Escribir
  \/ Aprobar
  \/ Reparar
  \/ Escalar
  \/ Fin

Spec == Init /\ [][Next]_vars
=============================================================================
