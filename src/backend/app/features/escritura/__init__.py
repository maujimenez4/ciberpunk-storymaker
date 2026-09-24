"""La UNICA puerta de entrada a la feature `escritura` (`CLAUDE.md` §5.1).

Detras de ella vive el **Escritor**: el unico rol de `CLAUDE.md` §9 que escribe
prosa, y el unico del que `architecture.md` §3.5 dice que su lectura es «solo el
paquete recibido».

**Lo que se exporta y por que:**

- `Escritor`, `Reparacion` y `ProsaVacia`: el agente, el defecto concreto que
  vuelve en un reintento, y lo que se lanza cuando lo devuelto no es una escena.
- `escribir_capitulo`, `Escritura` e `IntentoDeEscritura`: la escritura de un
  capitulo con su resultado, para quien lo orqueste.
- `Agentes`, `abrir_trabajo`, `ejecutar_ciclo`, `leer_trabajo` y
  `ResultadoDelCiclo`: **el ciclo de punta a punta** (T11), que es lo que monta
  `main.py` con `router` y lo que un test sustituye por
  `obtener_sesion_de_fondo`.
- `localizar_veto`: la palabra prohibida **con su desplazamiento**, que es lo
  que la hace citable.
- `PROMPT_ID`, `PROMPT_VERSION` y `HASH_DE_PLANTILLA_V1`: lo que ata una fila de
  `ejecucion` al fichero de la plantilla (regla de dominio 7).

Las tablas **no cruzan**: `VersionTexto`, `Ejecucion` y `Trabajo` se quedan
dentro, y las claves ajenas se declaran por nombre. Quien necesite el texto
recibe el texto, no la fila.

**Se exporta desde el cierre de la ola 1 de la Fase 3**, y va dicho por que:
la maquina de estados (T2) y el guardia de idempotencia (T3) nacieron sin
exportar **a proposito**. El `__init__.py` de una feature no tiene dueno en la
tabla del reparto —lo tienen `modelos.py` y `alembic/env.py`, no este— y tres
agentes de la misma ola tocandolo habria repetido el conflicto de codigo que la
regla 8 describe. Los tres hicieron lo correcto dejandolo al integrador.
"""

from app.features.escritura.agents import (
    HASH_DE_PLANTILLA_V1,
    PROMPT_ID,
    PROMPT_VERSION,
    Escritor,
    ProsaVacia,
    Reparacion,
)
from app.features.escritura.ciclo import (
    Agentes,
    ResultadoDelCiclo,
    TrabajoDesconocido,
    abrir_trabajo,
    ejecutar_ciclo,
    leer_trabajo,
)
from app.features.escritura.idempotencia import (
    Paso,
    RastroCompuesto,
    RastroEnEjecucion,
    RastroEnEvento,
    RastroEnHechoCanon,
    RastroEnVersionTexto,
    ResultadoDelPaso,
    una_sola_vez,
)
from app.features.escritura.maquina import (
    DETIENEN_LA_NOVELA,
    ESTADOS_TERMINALES,
    Estado,
    NovelaDetenida,
    Senal,
    TransicionInexistente,
    avanzar,
    detiene_la_novela,
    estado_de,
    exigir_que_la_novela_siga,
    transitar,
)
from app.features.escritura.router import obtener_sesion_de_fondo, router
from app.features.escritura.service import (
    CODIGO_DE_PALABRA_PROHIBIDA,
    Escritura,
    IntentoDeEscritura,
    escribir_capitulo,
    localizar_veto,
)

__all__ = [
    "CODIGO_DE_PALABRA_PROHIBIDA",
    "DETIENEN_LA_NOVELA",
    "ESTADOS_TERMINALES",
    "HASH_DE_PLANTILLA_V1",
    "PROMPT_ID",
    "PROMPT_VERSION",
    "Agentes",
    "Escritor",
    "Escritura",
    "Estado",
    "IntentoDeEscritura",
    "NovelaDetenida",
    "Paso",
    "ProsaVacia",
    "RastroCompuesto",
    "RastroEnEjecucion",
    "RastroEnEvento",
    "RastroEnHechoCanon",
    "RastroEnVersionTexto",
    "Reparacion",
    "ResultadoDelCiclo",
    "ResultadoDelPaso",
    "Senal",
    "TrabajoDesconocido",
    "TransicionInexistente",
    "abrir_trabajo",
    "avanzar",
    "detiene_la_novela",
    "ejecutar_ciclo",
    "escribir_capitulo",
    "estado_de",
    "exigir_que_la_novela_siga",
    "leer_trabajo",
    "localizar_veto",
    "obtener_sesion_de_fondo",
    "router",
    "transitar",
    "una_sola_vez",
]
