"""La UNICA puerta de entrada a la feature `manuscrito` (`CLAUDE.md` §5.1).

Lo que no esta aqui no se importa desde fuera: ni `router.py`, ni `service.py`,
ni `modelos.py`. `main.py` monta `router` y nada mas.

---

**Esta es la juntura de la Fase 4, y tiene dueno: T1.** `problemas-abiertos.md`
§P-16 cuenta lo que pasa cuando una juntura no lo tiene -- cinco olas de agentes
y el integrador cerrandolas al final, cuando ya nadie recuerda que exportaba
quien. Asi que el contrato se escribe entero aqui **antes** de que exista lo que
promete, y cada tarea anade su linea al llegar:

| Simbolo                  | Modulo          | Quien lo trae |
| ------------------------ | --------------- | ------------- |
| `VersionPublicada`       | `modelos`       | **T1**        |
| `CapituloPublicado`      | `modelos`       | **T1**        |
| `FichaDeLectura`         | `modelos`       | **T1**        |
| `CuadroDeDefectos`       | `modelos`       | **T1**        |
| `Dedicatoria`            | `modelos`       | **T1**        |
| `nuevo_identificador_publico` | `modelos`  | **T1**        |
| `version_por_token`      | `repository`    | **T1**        |
| `ultima_version`         | `repository`    | **T1**        |
| `capitulos_de`           | `repository`    | **T1**        |
| `dedicatoria_de`         | `repository`    | **T1**        |
| `CapituloDelIndice`      | `schemas`       | **T1**        |
| `EntradaDeFicha`         | `schemas`       | **T1**        |
| `DefectoDelCuadro`       | `schemas`       | **T1**        |
| `VersionPublicadaSalida` | `schemas`       | **T1**        |
| `DedicatoriaEntrada`     | `schemas`       | **T2**        |
| `publicar`               | `service`       | T6            |
| `diferencia_de_texto`    | `service`       | T7            |
| `generar_lean`           | `lean.generador`| T4            |
| `router`                 | `router`        | T9            |

**La regla al anadir: la linea de import y la entrada de `__all__` en el mismo
commit que el simbolo.** Un `__all__` que nombra algo que no existe rompe la
importacion de la feature entera, y con ella la de todo el que la use.
"""

from app.features.manuscrito.modelos import (
    CapituloPublicado,
    CuadroDeDefectos,
    Dedicatoria,
    FichaDeLectura,
    VersionPublicada,
    nuevo_identificador_publico,
)
from app.features.manuscrito.repository import (
    capitulos_de,
    dedicatoria_de,
    ultima_version,
    version_por_token,
)
from app.features.manuscrito.schemas import (
    CapituloDelIndice,
    DedicatoriaEntrada,
    DefectoDelCuadro,
    EntradaDeFicha,
    VersionPublicadaSalida,
)

__all__ = [
    "CapituloDelIndice",
    "CapituloPublicado",
    "CuadroDeDefectos",
    "Dedicatoria",
    "DedicatoriaEntrada",
    "DefectoDelCuadro",
    "EntradaDeFicha",
    "FichaDeLectura",
    "VersionPublicada",
    "VersionPublicadaSalida",
    "capitulos_de",
    "dedicatoria_de",
    "nuevo_identificador_publico",
    "ultima_version",
    "version_por_token",
]
