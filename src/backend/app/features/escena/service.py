"""Casos de uso de la feature `escena`: planificar la escena de un capitulo.

Es la parte de CU-03 anterior al ensamblado. Lo que sale de aqui es la **ficha
de escena**, que es la entrada del Ensamblador y, a traves del paquete, del
Escritor.

**Ningun `HTTPException` entra en este fichero** (`CLAUDE.md` §6).
"""

from collections.abc import Mapping
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.escena.agents import Planificador
from app.features.escena.repository import guardar_ficha
from app.features.escena.schemas import FichaDeEscena, RestriccionesDeDiscurso


async def planificar_escena(
    sesion: AsyncSession,
    planificador: Planificador,
    *,
    capitulo_id: int,
    version_obra_id: int,
    orden_discurso: int,
    capitulo: Mapping[str, Any],
    estado_en_t: Mapping[str, Any],
    biblia: Mapping[str, Any],
    nivel_de_calor: int,
) -> FichaDeEscena:
    """La ficha del capitulo, validada y escrita. En este orden y no en otro.

    **Las restricciones se resuelven primero**, antes de llamar al modelo: si la
    biblia no declara el discurso, el prompt no se puede construir sin
    inventarselo, y una llamada que no puede salir bien no se hace (el mismo
    criterio que RF-CTX-02 aplica al presupuesto).

    Despues se planifica, y **solo lo que pasa el esquema se guarda**: una
    salida mal formada sale por `SalidaMalFormada` sin haber escrito fila, que
    es lo que R-7 pide del ciclo entero —lo que se descarta no contamina lo que
    viene despues—.

    El capitulo, el estado en T y la biblia llegan como datos y no como filas:
    `Capitulo`, `Obra` y `VersionObra` son de otras features, y una feature no
    importa de los ficheros internos de otra (`CLAUDE.md` §5.1). Quien orqueste
    el ciclo los trae.

    No hace `commit`: la escena es un paso del ciclo de un capitulo, y quien lo
    orqueste decide cuando se cierra la transaccion. Si hiciera `commit` aqui,
    una ficha escrita sobreviviria al fallo del paso siguiente.
    """
    restricciones = RestriccionesDeDiscurso.de_la_obra(biblia, nivel_de_calor)
    salida = await planificador.planificar(capitulo, estado_en_t, restricciones)
    ficha = FichaDeEscena(
        **salida.model_dump(),
        capitulo_id=capitulo_id,
        version_obra_id=version_obra_id,
        orden_discurso=orden_discurso,
        restricciones=restricciones,
    )
    await guardar_ficha(sesion, ficha)
    return ficha
