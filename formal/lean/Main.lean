import Cronologia

/-- Comprobación de humo: imprime el veredicto de los dos invariantes.
    La verificación de verdad la hace `lake build` al comprobar las pruebas
    de `Cronologia/Basic.lean`; esto solo da una salida legible. -/
def main : IO Unit := do
  IO.println s!"orden temporal (coherente) : {ordenTemporal coherente}"
  IO.println s!"sin ubicuidad  (coherente) : {sinUbicuidad coherente}"
  IO.println s!"orden temporal (desordenada): {ordenTemporal desordenada}"
  IO.println s!"sin ubicuidad  (ubicua)     : {sinUbicuidad ubicua}"
