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
- El veto de palabras **ya no vive aqui**: es una regla del hook de policy y
  entra por `features.calidad` (`aplicar_policy`, `localizar_veto`,
  `CODIGO_DE_PALABRA_PROHIBIDA`). RF-GUA-07, Fase 7.
- `Checkpoint`, `Arranque`, `CapituloPendiente`, `empezar_capitulo`,
  `registrar_checkpoint`, `ultimo_capitulo_completado`, `siguiente_capitulo`,
  `reparaciones_del_capitulo` y sus cuatro errores: **el
  avance por capitulo** (T5 de la Fase 3), que es de lo que vive la reanudacion.
  Sale por la puerta porque quien lo consume —el orquestador de la novela— no
  esta dentro de esta feature.
- `ESTADOS_VIVOS`, `Reanudacion`, `Retomada`, `TrabajoTerminal`, `descartar`,
  `planificar_reanudacion`, `reanudar` y `trabajos_en_vuelo`: **la reanudacion
  tras la caida** (T8 de la Fase 3), por el mismo motivo que el avance — quien
  arranca el proceso y decide por donde sigue la novela es `novela.py`, que
  desde T9 si existe, y el router de operacion.
- `Novela`, `CapituloDeLaNovela`, `escribir_novela`, `ciclo_de_la_novela`,
  `numero_de_capitulo`, `hechos_usados`, `elementos_obligatorios_de` y
  `cobertura_de_la_novela`: **la novela entera** (T9 de la Fase 3), que es lo
  que cierra `CA-1`. Sale por la puerta porque quien la arranca de verdad no es
  solo el router de esta feature: la cobertura la consumira la publicacion
  (Fase 4), que vive en `manuscrito`.
- `CapituloNoIntegrado`, `Ejecutar`, `PREFIJO_DE_REGENERACION`,
  `regenerar_capitulo`, `reparaciones_de_la_regeneracion`,
  `retirar_prosa_de_la_corrida` y `consolidar_la_regeneracion`: **regenerar un
  capitulo ya integrado** (plan 5, T3). Las consume `manuscrito` al atender una
  peticion de cambio.
- `ResultadoDeLaPeticion`, `Revalidar`, `atender_peticion`, `registrar_peticion`,
  `avance_de_la_peticion`, `ciclo_de_la_peticion`, `revalidar_mecanicamente`,
  `lectura` y `obtener_atencion`: **la peticion de cambio de punta a punta**
  (plan 5, T7-T8). Viven aqui y no en `manuscrito` porque componen el ciclo, y
  `manuscrito -> escritura` cerraria un ciclo entre features.
- `PROMPT_ID`, `PROMPT_VERSION` y `HASH_DE_PLANTILLA_V2`: lo que ata una fila de
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
    HASH_DE_PLANTILLA_V2,
    PROMPT_ID,
    PROMPT_VERSION,
    Escritor,
    ProsaVacia,
    Reparacion,
)
from app.features.escritura.checkpoint import (
    Arranque,
    CapituloAnteriorSinIntegrar,
    CapituloPendiente,
    CapituloYaIntegrado,
    Checkpoint,
    CheckpointPrematuro,
    TrabajoSinCapitulo,
    empezar_capitulo,
    registrar_checkpoint,
    reparaciones_del_capitulo,
    siguiente_capitulo,
    ultimo_capitulo_completado,
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
from app.features.escritura.novela import (
    CapituloDeLaNovela,
    Novela,
    ciclo_de_la_novela,
    cobertura_de_la_novela,
    elementos_obligatorios_de,
    escribir_novela,
    hechos_usados,
    numero_de_capitulo,
)
from app.features.escritura.peticion import (
    ResultadoDeLaPeticion,
    Revalidar,
    atender_peticion,
    avance_de_la_peticion,
    ciclo_de_la_peticion,
    registrar_peticion,
    revalidar_mecanicamente,
)
from app.features.escritura.reanudacion import (
    ESTADOS_VIVOS,
    Reanudacion,
    Retomada,
    TrabajoTerminal,
    descartar,
    planificar_reanudacion,
    reanudar,
    trabajos_en_vuelo,
)
from app.features.escritura.regeneracion import (
    PREFIJO_DE_REGENERACION,
    CapituloNoIntegrado,
    Ejecutar,
    consolidar_la_regeneracion,
    regenerar_capitulo,
    reparaciones_de_la_regeneracion,
    retirar_prosa_de_la_corrida,
)
from app.features.escritura.router import (
    lectura,
    obtener_atencion,
    obtener_sesion_de_fondo,
    router,
)
from app.features.escritura.service import (
    Escritura,
    IntentoDeEscritura,
    escribir_capitulo,
)

__all__ = [
    "DETIENEN_LA_NOVELA",
    "ESTADOS_TERMINALES",
    "ESTADOS_VIVOS",
    "HASH_DE_PLANTILLA_V2",
    "PREFIJO_DE_REGENERACION",
    "PROMPT_ID",
    "PROMPT_VERSION",
    "Agentes",
    "Arranque",
    "CapituloAnteriorSinIntegrar",
    "CapituloDeLaNovela",
    "CapituloNoIntegrado",
    "CapituloPendiente",
    "CapituloYaIntegrado",
    "Checkpoint",
    "CheckpointPrematuro",
    "Ejecutar",
    "Escritor",
    "Escritura",
    "Estado",
    "IntentoDeEscritura",
    "Novela",
    "NovelaDetenida",
    "Paso",
    "ProsaVacia",
    "RastroCompuesto",
    "RastroEnEjecucion",
    "RastroEnEvento",
    "RastroEnHechoCanon",
    "RastroEnVersionTexto",
    "Reanudacion",
    "Reparacion",
    "ResultadoDeLaPeticion",
    "ResultadoDelCiclo",
    "ResultadoDelPaso",
    "Retomada",
    "Revalidar",
    "Senal",
    "TrabajoDesconocido",
    "TrabajoSinCapitulo",
    "TrabajoTerminal",
    "TransicionInexistente",
    "abrir_trabajo",
    "atender_peticion",
    "avance_de_la_peticion",
    "avanzar",
    "ciclo_de_la_novela",
    "ciclo_de_la_peticion",
    "cobertura_de_la_novela",
    "consolidar_la_regeneracion",
    "descartar",
    "detiene_la_novela",
    "ejecutar_ciclo",
    "elementos_obligatorios_de",
    "empezar_capitulo",
    "escribir_capitulo",
    "escribir_novela",
    "estado_de",
    "exigir_que_la_novela_siga",
    "hechos_usados",
    "lectura",
    "leer_trabajo",
    "numero_de_capitulo",
    "obtener_atencion",
    "obtener_sesion_de_fondo",
    "planificar_reanudacion",
    "reanudar",
    "regenerar_capitulo",
    "registrar_checkpoint",
    "registrar_peticion",
    "reparaciones_de_la_regeneracion",
    "reparaciones_del_capitulo",
    "retirar_prosa_de_la_corrida",
    "revalidar_mecanicamente",
    "router",
    "siguiente_capitulo",
    "trabajos_en_vuelo",
    "transitar",
    "ultimo_capitulo_completado",
    "una_sola_vez",
]
