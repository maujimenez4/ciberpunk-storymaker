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

(* Solo se evalua con `Len(versiones) > 0` delante: TLC corta la conjuncion *)
(* por la izquierda.                                                        *)
Vigente == versiones[Len(versiones)]

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

(* R-3. La caida y su reanudacion, en una accion:                           *)
(*   - la prosa sin confirmar se retira      -> validado[actual] = FALSE    *)
(*   - el paso interrumpido se repite entero -> vuelve a ESCRIBIENDO        *)
(*   - las reparaciones gastadas SE HEREDAN  -> `intento` sin cambiar       *)
(* Esa tercera linea es `reanudacion.reanudar`, y es la unica que impide    *)
(* que matar el proceso sea una forma de conseguir reintentos.              *)
(*                                                                          *)
(* Una caida en ESCRIBIENDO_CAPITULO no cambia ninguna variable observable  *)
(* —la prosa no llego a confirmarse—, asi que es stuttering y no una accion.*)
Reanudar ==
  /\ estado = "VALIDANDO_CAPITULO"
  /\ actual \notin integrados
  /\ estado' = "ESCRIBIENDO_CAPITULO"
  /\ validado' = [validado EXCEPT ![actual] = FALSE]
  /\ UNCHANGED <<rondas, actual, integrados, intento,
                 versiones, peticiones, porRehacer>>

(* §3.9: VALIDANDO_CAPITULO --> VERIFICANDO, «ultimo capitulo aprobado».    *)
(* La condicion de `porRehacer` la usa T3; con la regeneracion sin escribir *)
(* es siempre cierta, y ponerla ya evita que T3 tenga que tocar esta linea. *)
Verificar ==
  /\ estado \in {"VALIDANDO_CAPITULO", "REGENERANDO"}
  /\ Pendientes = {}
  /\ porRehacer = {}
  /\ estado' = "VERIFICANDO"
  /\ UNCHANGED <<rondas, actual, integrados, validado, intento,
                 versiones, peticiones, porRehacer>>

TodosValidados == \A c \in Numeros : validado[c]

(* Publicar es AFIRMAR QUE PASO LAS PUERTAS, no que se escribio             *)
(* (`CLAUDE.md` §8, regla 14). La guarda es el invariante S1 escrito como   *)
(* precondicion; el invariante comprueba que no hay otro camino.            *)
Publicar ==
  /\ estado = "VERIFICANDO"
  /\ Pendientes = {}
  /\ TodosValidados
  /\ versiones' = Append(versiones,
                         [capitulos |-> integrados,
                          validados |-> {c \in Numeros : validado[c]}])
  /\ estado' = "PUBLICADA"
  /\ UNCHANGED <<rondas, actual, integrados, validado, intento,
                 peticiones, porRehacer>>

(* §5c: si Lean falla, la version NO se publica y el fallo vuelve al editor.*)
LeanFalla ==
  /\ estado = "VERIFICANDO"
  /\ estado' = "DETENIDA"
  /\ UNCHANGED <<rondas, actual, integrados, validado, intento,
                 versiones, peticiones, porRehacer>>

(* PUBLICADA --> REGENERANDO. Los capitulos que la peticion toca salen de   *)
(* `integrados` y pierden su validacion: hay que volver a ganarlas. La      *)
(* version publicada NO se toca, y por eso `versiones` no aparece aqui.     *)
PeticionDelLector ==
  /\ estado = "PUBLICADA"
  /\ peticiones < MaxPeticiones
  /\ \E S \in (SUBSET Numeros) \ {{}} :
       /\ porRehacer' = S
       /\ integrados' = integrados \ S
       /\ validado' = [c \in Numeros |-> IF c \in S THEN FALSE ELSE validado[c]]
  /\ peticiones' = peticiones + 1
  /\ estado' = "REGENERANDO"
  /\ UNCHANGED <<rondas, actual, intento, versiones>>

(* Un capitulo rehecho y aprobado. El ciclo de escritura de arriba NO se    *)
(* reutiliza a proposito: §3.9 dibuja `REGENERANDO` como un estado, no como *)
(* una vuelta por ESCRIBIENDO_CAPITULO, y lo que este modelo tiene que      *)
(* decidir es que pasa con la version vigente, no como se reescribe un      *)
(* capitulo — eso ya esta modelado.                                         *)
RehacerCapitulo ==
  /\ estado = "REGENERANDO"
  /\ porRehacer # {}
  /\ LET c == Primero(porRehacer) IN
       /\ actual' = c
       /\ validado' = [validado EXCEPT ![c] = TRUE]
       /\ integrados' = integrados \cup {c}
       /\ porRehacer' = porRehacer \ {c}
  /\ UNCHANGED <<estado, rondas, intento, versiones, peticiones>>

(* R-2. «No es una publicacion: es un regreso» (§3.9). No crea version y no *)
(* toca la vigente: DEVUELVE la lectura al estado de la vigente. Puede      *)
(* ocurrir con capitulos ya rehechos, y ese es justo el caso que S3 vigila. *)
DescartarPeticion ==
  /\ estado = "REGENERANDO"
  /\ Len(versiones) > 0
  /\ estado' = "PUBLICADA"
  /\ integrados' = Vigente.capitulos
  /\ validado' = [c \in Numeros |-> c \in Vigente.validados]
  /\ porRehacer' = {}
  /\ UNCHANGED <<rondas, actual, intento, versiones, peticiones>>

(* Sin esto, TLC informa de `deadlock` en los estados terminales de §3.9,   *)
(* que son finales y no averias.                                            *)
Fin ==
  /\ \/ estado = "DETENIDA"
     \/ /\ estado = "PUBLICADA"
        /\ peticiones = MaxPeticiones
  /\ UNCHANGED vars

Next ==
  \/ FaltaUnDato
  \/ Planificar
  \/ SiguienteCapitulo
  \/ Escribir
  \/ Aprobar
  \/ Reparar
  \/ Escalar
  \/ Reanudar
  \/ Verificar
  \/ Publicar
  \/ LeanFalla
  \/ PeticionDelLector
  \/ RehacerCapitulo
  \/ DescartarPeticion
  \/ Fin

(* ---------------------------------------------------------------------- *)
(* S1. Ninguna version publicada contiene un capitulo que no paso su       *)
(* puerta. Enunciada sobre la CREACION de la version y no sobre el estado  *)
(* de destino: `DescartarPeticion` llega a PUBLICADA sin crear nada, y una *)
(* invariante escrita sobre el estado seria falsa en el primer paso        *)
(* (§3.9, invariante 1). `CLAUDE.md` §8, regla 14.                         *)
PublicadaSoloConPuertas ==
  \A i \in 1..Len(versiones) :
    /\ versiones[i].capitulos = Numeros
    /\ versiones[i].capitulos \subseteq versiones[i].validados

(* S2. La reanudacion no duplica ni pierde capitulos.                      *)
(*   - no duplica: no se escribe un capitulo que ya esta integrado         *)
(*                 (`checkpoint.CapituloYaIntegrado`)                      *)
(*   - no pierde:  no se verifica con un hueco detras                      *)
(*                 (`checkpoint.CapituloAnteriorSinIntegrar`)              *)
ReanudacionIntegra ==
  /\ (estado = "ESCRIBIENDO_CAPITULO") => (actual \notin integrados)
  /\ (estado = "VERIFICANDO") => (integrados = Numeros)

(* S3. En PUBLICADA, lo que se sirve es exactamente la ultima version       *)
(* publicada. Es «la version anterior se conserva siempre» dicho por el     *)
(* lado que se puede romper: una peticion descartada a medias.             *)
LecturaIgualALaVigente ==
  (estado = "PUBLICADA") =>
    /\ Len(versiones) > 0
    /\ integrados = Vigente.capitulos
    /\ \A c \in integrados : validado[c]

(* Companera de S3, y es una propiedad de accion y no de estado: ninguna    *)
(* version ya publicada cambia ni desaparece.                              *)
VersionesAppendOnly ==
  [][ \A i \in 1..Len(versiones) :
        /\ i =< Len(versiones')
        /\ versiones'[i] = versiones[i] ]_vars

(* Liveness. NO es `<>[]`: `PUBLICADA --> REGENERANDO` existe, asi que      *)
(* «acaba y se queda» es falso en esta maquina. Lo que el encargo pide es   *)
(* que toda generacion termine, y eso es un leads-to.                       *)
TodaGeneracionTermina ==
  (estado = "CONFIGURANDO") ~> (estado \in {"PUBLICADA", "DETENIDA"})

(* Equidad FUERTE sobre `Aprobar`, y el motivo es el que decide:            *)
(* entre dos habilitaciones de `Aprobar` hay una vuelta por                 *)
(* ESCRIBIENDO_CAPITULO, asi que no esta CONTINUAMENTE habilitada y la      *)
(* equidad debil no la forzaria. Es lo que cierra los dos bucles que        *)
(* pueden no terminar: el de reparacion y el de caida.                      *)
Equidad ==
  /\ WF_vars(Planificar)
  /\ WF_vars(SiguienteCapitulo)
  /\ WF_vars(Escribir)
  /\ SF_vars(Aprobar)
  /\ WF_vars(Escalar)
  /\ WF_vars(Verificar)
  /\ WF_vars(Publicar)
  /\ WF_vars(RehacerCapitulo)

Spec == Init /\ [][Next]_vars /\ Equidad
=============================================================================
