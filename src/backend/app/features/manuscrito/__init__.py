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
| `VersionPublicada`       | `schemas`       | **T1 → T9**   |
| `CapituloPublicado`      | `schemas`       | **T1 → T9**   |
| `FichaDeLectura`         | `schemas`       | **T9**        |
| `EntradaDeFicha`         | `schemas`       | **T1**        |
| `DefectoDelCuadro`       | `schemas`       | **T1**        |
| `DedicatoriaEntrada`     | `schemas`       | **T2**        |
| `nuevo_identificador_publico` | `modelos`  | **T1**        |
| `version_por_token`      | `repository`    | **T1**        |
| `ultima_version`         | `repository`    | **T1**        |
| `capitulos_de`           | `repository`    | **T1**        |
| `dedicatoria_de`         | `repository`    | **T1**        |
| `capitulos_cambiados`    | `repository`    | **T7**        |
| `texto_publicado`        | `repository`    | **T9**        |
| `guardar_dedicatoria`    | `repository`    | **T2 → T9**   |
| `ficha_de`               | `repository`    | **T9**        |
| `versiones_de`           | `repository`    | **T9**        |
| `publicar`               | `service`       | **T6**        |
| `ensamblar_manuscrito`   | `service`       | **T6**        |
| `dedicatoria_o_nada`     | `service`       | **T6**        |
| `CapituloSinPuerta`      | `service`       | **T6**        |
| `generar_lean`           | `lean.generador`| T4            |
| `router`                 | `router`        | **T9**        |

**Los modelos de base de datos ya no salen de aqui. Invertido el 2026-09-24,
en T9, y conviene el porque porque contradice lo que T1 decidio.** T1 exporto
`VersionPublicada`, `CapituloPublicado`, `FichaDeLectura`, `CuadroDeDefectos` y
`Dedicatoria` -- las cinco filas de SQLAlchemy -- y `CLAUDE.md` §6 dice que el
modelo de base de datos **no se expone nunca**.

Lo destapo el contrato con la spec 002: su cliente se genera del OpenAPI, y
FastAPI publica **el nombre de la clase Pydantic**. Para que el frontend derive
un tipo llamado `VersionPublicada` hacia falta que asi se llamara el esquema, y
ese nombre ya estaba ocupado por el modelo. Al resolverlo, el test que
bloqueaba resulto estar senalando el defecto de fondo.

Quien necesite las filas las importa **por su modulo** desde dentro de la
feature -- `from app.features.manuscrito import modelos`, y `modelos.Dedicatoria` --,
que ademas obliga a decir cual de las dos cosas se esta mirando.

**La regla al anadir: la linea de import y la entrada de `__all__` en el mismo
commit que el simbolo.** Un `__all__` que nombra algo que no existe rompe la
importacion de la feature entera, y con ella la de todo el que la use.
"""

from app.features.manuscrito.modelos import nuevo_identificador_publico
from app.features.manuscrito.repository import (
    capitulos_cambiados,
    capitulos_de,
    dedicatoria_de,
    ficha_de,
    guardar_dedicatoria,
    texto_publicado,
    ultima_version,
    version_por_token,
    versiones_de,
)
from app.features.manuscrito.router import router
from app.features.manuscrito.schemas import (
    CapituloPublicado,
    DedicatoriaEntrada,
    DefectoDelCuadro,
    EntradaDeFicha,
    FichaDeLectura,
    VersionPublicada,
)
from app.features.manuscrito.service import (
    CapituloSinPuerta,
    dedicatoria_o_nada,
    ensamblar_manuscrito,
    publicar,
)

__all__ = [
    "CapituloPublicado",
    "CapituloSinPuerta",
    "DedicatoriaEntrada",
    "DefectoDelCuadro",
    "EntradaDeFicha",
    "FichaDeLectura",
    "VersionPublicada",
    "capitulos_cambiados",
    "capitulos_de",
    "dedicatoria_de",
    "dedicatoria_o_nada",
    "ensamblar_manuscrito",
    "ficha_de",
    "guardar_dedicatoria",
    "nuevo_identificador_publico",
    "publicar",
    "router",
    "texto_publicado",
    "ultima_version",
    "version_por_token",
    "versiones_de",
]
