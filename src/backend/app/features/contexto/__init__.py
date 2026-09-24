"""La UNICA puerta de entrada a la feature `contexto` (`CLAUDE.md` §5.1).

Lo que no esta aqui no se importa desde fuera. Estan el presupuesto de la
llamada (T5), la recuperacion hibrida con sus dos almacenes (T7) y el
**Ensamblador** (T6), que es lo que une los tres.

Del Ensamblador se exporta lo que otras features necesitan y nada mas:

- `Paquete` y `ensamblar`: lo que recibe el Escritor y como se hace.
- `Surtido` y `CAPAS_CON_ORIGEN`: el contrato de quien surte una capa, con su
  censo, que es lo que hace comprobable RF-CTX-06.
- `ensamblar_capitulo`, `registrar_ejecucion` y `DatosDeLlamada`: el ciclo de
  un capitulo, para T8 y T11.
- `CapaVacia`: para que quien orqueste distinga un fallo del almacen de uno del
  modelo, que es de lo que depende que un defecto sea atribuible.
- `router`: RI-07, que monta `main.py`.

**No se exporta nada de `presupuestar` hacia dentro**: quien surte no decide
topes, y quien llama al modelo no ensambla.
"""

from app.features.contexto.almacenes import (
    AlmacenFuerzaBruta,
    AlmacenSqliteVec,
    Vecino,
    VectorStore,
    crear_almacen,
)
from app.features.contexto.capas import (
    CAPAS_CON_ORIGEN,
    CapaVacia,
    Paquete,
    Surtido,
    ensamblar,
)
from app.features.contexto.presupuesto import (
    TECHO_POR_LLAMADA,
    TOPES,
    Capa,
    Desglose,
    LineaDeCapa,
    Pieza,
    presupuestar,
)
from app.features.contexto.recuperacion import (
    LIMITE_POR_DEFECTO,
    PESO_RECENCIA_POR_DEFECTO,
    Candidato,
    FiltroEstructural,
    Recuperado,
    filtrar_estructuralmente,
    fusionar_con_recencia,
    recuperar,
)
from app.features.contexto.router import router
from app.features.contexto.service import (
    CapituloDesconocido,
    CapituloSinEscena,
    ContextoDelCapitulo,
    DatosDeLlamada,
    ensamblar_capitulo,
    registrar_ejecucion,
    surtir_capitulo,
)

__all__ = [
    "CAPAS_CON_ORIGEN",
    "LIMITE_POR_DEFECTO",
    "PESO_RECENCIA_POR_DEFECTO",
    "TECHO_POR_LLAMADA",
    "TOPES",
    "AlmacenFuerzaBruta",
    "AlmacenSqliteVec",
    "Candidato",
    "Capa",
    "CapaVacia",
    "CapituloDesconocido",
    "CapituloSinEscena",
    "ContextoDelCapitulo",
    "DatosDeLlamada",
    "Desglose",
    "FiltroEstructural",
    "LineaDeCapa",
    "Paquete",
    "Pieza",
    "Recuperado",
    "Surtido",
    "Vecino",
    "VectorStore",
    "crear_almacen",
    "ensamblar",
    "ensamblar_capitulo",
    "filtrar_estructuralmente",
    "fusionar_con_recencia",
    "presupuestar",
    "recuperar",
    "registrar_ejecucion",
    "router",
    "surtir_capitulo",
]
