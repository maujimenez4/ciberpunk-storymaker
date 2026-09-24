---- MODULE Juguete ----
(* Modelo minimo, solo para comprobar que TLC corre en esta maquina.
   NO es la especificacion del harness: esa la escribe la Fase 7 contra
   `features/escritura/maquina.py`. *)
EXTENDS Naturals

CONSTANT Tope
VARIABLE n

Init == n = 0

Avanza == n < Tope /\ n' = n + 1
Quieto == n = Tope /\ UNCHANGED n
Next   == Avanza \/ Quieto

Spec == Init /\ [][Next]_n /\ WF_n(Avanza)

\* Seguridad: el contador nunca se sale del rango declarado.
EnRango == n \in 0..Tope

\* Liveness: siempre se acaba llegando al tope.
Termina == <>(n = Tope)
====
