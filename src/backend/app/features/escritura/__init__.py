"""La UNICA puerta de entrada a la feature `escritura` (`CLAUDE.md` §5.1).

Detras de ella vive el **Escritor**: el unico rol de `CLAUDE.md` §9 que escribe
prosa, y el unico del que `architecture.md` §3.5 dice que su lectura es «solo el
paquete recibido».

**Lo que se exporta y por que:**

- `Escritor`, `Reparacion` y `ProsaVacia`: el agente, el defecto concreto que
  vuelve en un reintento, y lo que se lanza cuando lo devuelto no es una escena.
- `escribir_capitulo`, `Escritura` e `IntentoDeEscritura`: el ciclo de un
  capitulo con su resultado, para quien lo orqueste (T11).
- `localizar_veto`: la palabra prohibida **con su desplazamiento**, que es lo
  que la hace citable.
- `PROMPT_ID`, `PROMPT_VERSION` y `HASH_DE_PLANTILLA_V1`: lo que ata una fila de
  `ejecucion` al fichero de la plantilla (regla de dominio 7).

Las tablas **no cruzan**: `VersionTexto`, `Ejecucion` y `Trabajo` se quedan
dentro, y las claves ajenas se declaran por nombre. Quien necesite el texto
recibe el texto, no la fila.
"""

from app.features.escritura.agents import (
    HASH_DE_PLANTILLA_V1,
    PROMPT_ID,
    PROMPT_VERSION,
    Escritor,
    ProsaVacia,
    Reparacion,
)
from app.features.escritura.service import (
    CODIGO_DE_PALABRA_PROHIBIDA,
    Escritura,
    IntentoDeEscritura,
    escribir_capitulo,
    localizar_veto,
)

__all__ = [
    "CODIGO_DE_PALABRA_PROHIBIDA",
    "HASH_DE_PLANTILLA_V1",
    "PROMPT_ID",
    "PROMPT_VERSION",
    "Escritor",
    "Escritura",
    "IntentoDeEscritura",
    "ProsaVacia",
    "Reparacion",
    "escribir_capitulo",
    "localizar_veto",
]
