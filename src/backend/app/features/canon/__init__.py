"""La UNICA puerta de entrada a la feature `canon` (`CLAUDE.md` §5.1).

Lo que no esta aqui no se importa desde fuera: ni `service.py`, ni
`repository.py`, ni `modelos.py`. Detras de esta puerta vive el **Extractor**,
que es el unico rol que escribe memoria de largo plazo (`architecture.md` §4.3,
RF-MEM-06).

**Lo que se exporta y por que:**

- `Extractor` y `Extraccion`: el agente y su salida, para quien orqueste el
  ciclo de un capitulo.
- `consolidar_escena`, `Consolidacion`, `registrar_uso_de_hechos` y
  `corregir_hecho`: los cuatro casos de uso.
- `Vector`: la forma con la que un fragmento ya vectorizado entra al indice.
  Quien lo calcula es el `ClienteModelo` (T1 de la Fase 3), y `vectorizador_de`
  es la **unica** traduccion de su `Vectorizacion` a este tipo: se exporta para
  que quien orqueste un ciclo no la escriba a mano en cada sitio.
- `Embedding`: la fila del indice, para quien **lee** recuperando. Leer se
  exporta; escribir no: no hay aqui ninguna funcion de escritura, y por esa
  ausencia pasa RF-MEM-06.
- `leer_resumenes_anteriores`, `contar_capitulos_con_texto_aprobado` y
  `ResumenDeCapitulo`: la segunda mitad de RF-MEM-04. El resumen se **escribe**
  aqui, detras de `consolidar_escena`, y quien lo **lee** es la capa de memoria
  recuperada de `contexto` (`architecture.md` §4.8: «indice vectorial **+
  resumenes**»). Exportarlo por esta puerta es lo unico que evita que `contexto`
  entre a un fichero interno de esta feature, igual que con `Embedding`.
- `declarar_variantes` y `leer_nombres_del_canon`: RF-VAL-03. El canon dice
  como se puede llamar a alguien ademas de por su forma canonica, y el
  validador de `calidad` lo **lee**; no lo adivina y no se reescribe. La
  escritura la hace el Extractor, que es esta feature.
`Embedding` cruza la frontera a proposito, y va dicho por que: el indice
vectorial lo **escribe** el Extractor (`architecture.md` §4.3) y por eso la
tabla vive aqui, pero quien lo **lee** es la recuperacion de `contexto` (T7).
Exportarlo por esta puerta es lo unico que evita que `contexto` importe un
fichero interno de otra feature, que es lo que §5.1 prohibe de verdad.

"""

from app.features.canon.agents import Extractor, SalidaMalFormada
from app.features.canon.modelos import Embedding
from app.features.canon.repository import declarar_variantes, leer_nombres_del_canon
from app.features.canon.resumenes import (
    ResumenDeCapitulo,
    contar_capitulos_con_texto_aprobado,
    leer_resumenes_anteriores,
)
from app.features.canon.schemas import Extraccion, Vector
from app.features.canon.service import (
    Consolidacion,
    consolidar_escena,
    corregir_hecho,
    registrar_uso_de_hechos,
)
from app.features.canon.vectorizacion import vectorizador_de

__all__ = [
    "Consolidacion",
    "Embedding",
    "Extraccion",
    "Extractor",
    "ResumenDeCapitulo",
    "SalidaMalFormada",
    "Vector",
    "consolidar_escena",
    "contar_capitulos_con_texto_aprobado",
    "corregir_hecho",
    "declarar_variantes",
    "leer_nombres_del_canon",
    "leer_resumenes_anteriores",
    "registrar_uso_de_hechos",
    "vectorizador_de",
]
