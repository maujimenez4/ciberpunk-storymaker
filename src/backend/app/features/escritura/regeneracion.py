"""Escribir encima de un capitulo que ya forma parte del manuscrito (plan 5, T3).

**No pasa por `checkpoint.empezar_capitulo`, a proposito.** Aquella puerta es
de la escritura de la novela y lanza `CapituloYaIntegrado`; regenerar es, por
definicion, escribir un capitulo ya integrado. Relajarla con un parametro es la
forma de que una reanudacion acabe reescribiendo un capitulo sano. Aqui hay una
puerta **inversa**: se exige que el capitulo **si** este integrado.

**La regeneracion no consolida** (decision previa del plan 5): corre el ciclo
con `consolidar=False`, y quien decide si la peticion prospera llama despues a
`consolidar_la_regeneracion` o a `retirar_prosa_de_la_corrida`.

**El contador de reparaciones se cuenta aparte.** `reparaciones_del_capitulo`
devuelve el maximo de **todos** los trabajos del capitulo: una regeneracion
empezaria con las reparaciones que costo escribirlo. Los trabajos de
regeneracion se reconocen por el prefijo `reg-` de su `run_id` y no por
`trabajo.tipo`, como decia el plan: `ck_trabajo_tipo` es un conjunto cerrado y
ampliarlo seria una migracion de `trabajo` (modo batch, tres restricciones)
que no hace falta para distinguirlos. Anotado como desviacion.

**Las tablas de otras features se leen por SQL con su nombre** (`CLAUDE.md` §5.1).
"""

from collections.abc import Callable
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.domain.errores import ErrorDeDominio, OperacionNoPermitida
from app.features.canon import Consolidacion, Vector, consolidar_escena, registrar_uso_de_hechos
from app.features.escritura.ciclo import ResultadoDelCiclo, _retirar_lo_descartado, abrir_trabajo
from app.features.escritura.maquina import Estado
from app.features.escritura.modelos import Trabajo

PREFIJO_DE_REGENERACION = "reg-"
"""Lo que distingue el `run_id` de un trabajo de regeneracion."""


class Ejecutar(Protocol):
    """El ciclo ya compuesto con sus dependencias; la regeneracion solo decide
    **que no consolide**. Se le pasa `consolidar` en vez de confiar en que quien
    lo compuso se acordara: un olvido consolidaria una prosa que puede acabar
    descartada, y el ledger no se borra."""

    async def __call__(self, trabajo: Trabajo, *, consolidar: bool) -> ResultadoDelCiclo: ...


class CapituloNoIntegrado(ErrorDeDominio):
    """Se pidio regenerar un capitulo que todavia no forma parte del manuscrito.

    Se escribe con `escribir_novela`, no con una peticion del lector.
    """

    def __init__(self, obra_id: int, capitulo_id: int) -> None:
        self.obra_id = obra_id
        self.capitulo_id = capitulo_id
        super().__init__(
            f"El capitulo {capitulo_id} de la obra {obra_id} no esta integrado: "
            "no hay nada que regenerar"
        )


async def regenerar_capitulo(
    sesion: AsyncSession, *, obra_id: int, capitulo_id: int, ejecutar: Ejecutar
) -> ResultadoDelCiclo:
    """Abre un trabajo de regeneracion y corre el ciclo **sin consolidar**.

    El resultado lleva `run_id` (para retirar), `escritura`, `extraccion` e
    `ids_de_canon` (para consolidar). La escena es la unica del capitulo (P-C):
    quien necesite su id lo lee de `leer_trabajo(resultado.trabajo_id).escena_id`.
    """
    integrado = (
        await sesion.execute(
            text(
                "SELECT COUNT(*) FROM trabajo "
                "WHERE obra_id = :obra AND capitulo_id = :cap AND estado = :integrada"
            ),
            {"obra": obra_id, "cap": capitulo_id, "integrada": Estado.INTEGRADA.value},
        )
    ).scalar_one()
    if int(integrado) == 0:
        raise CapituloNoIntegrado(obra_id, capitulo_id)

    trabajo = await abrir_trabajo(sesion, capitulo_id=capitulo_id)
    trabajo.run_id = f"{PREFIJO_DE_REGENERACION}{trabajo.run_id}"
    await sesion.flush()
    return await ejecutar(trabajo, consolidar=False)


async def reparaciones_de_la_regeneracion(
    sesion: AsyncSession, *, obra_id: int, capitulo_id: int
) -> int:
    """Las reparaciones gastadas **por regeneraciones** de este capitulo, y nada mas."""
    gastadas = (
        await sesion.execute(
            text(
                "SELECT COALESCE(MAX(intento), 0) FROM trabajo "
                "WHERE obra_id = :obra AND capitulo_id = :cap AND run_id LIKE :prefijo"
            ),
            {"obra": obra_id, "cap": capitulo_id, "prefijo": f"{PREFIJO_DE_REGENERACION}%"},
        )
    ).scalar_one()
    return int(gastadas)


async def retirar_prosa_de_la_corrida(sesion: AsyncSession, *, escena_id: int, run_id: str) -> None:
    """RF-PET-07, la parte del manuscrito (J-4): borra las `version_texto` de esta
    corrida y vuelve a encender la anterior, que es la entregada.

    **Se reexporta en vez de copiarse**: apagar la vigente sin volver a encender
    una deja la escena sin manuscrito, y esa sutileza es lo que una copia pierde.
    """
    await _retirar_lo_descartado(sesion, escena_id, run_id)


async def consolidar_la_regeneracion(
    sesion: AsyncSession,
    *,
    resultado: ResultadoDelCiclo,
    obra_id: int,
    escena_id: int,
    capitulo_id: int,
    vectorizar: Callable[[str], Vector] | None = None,
) -> Consolidacion:
    """La memoria de largo plazo, **despues** de saber que la peticion prospera.

    Depende de las dos deudas que pago T1: el `run_id` de los rastros (P-6) y el
    resumen que se sobrescribe (P-7). Registra ademas el uso de los hechos que
    entraron en el paquete (RF-MEM-02), que el ciclo aplazo con la consolidacion.
    """
    if resultado.extraccion is None or resultado.escritura is None:
        raise OperacionNoPermitida(
            "no hay extraccion que consolidar: el ciclo corrio con consolidar=True "
            "o no llego a aprobar la prosa"
        )
    consolidacion = await consolidar_escena(
        sesion,
        obra_id=obra_id,
        escena_id=escena_id,
        capitulo_id=capitulo_id,
        extraccion=resultado.extraccion,
        prosa=resultado.escritura.texto,
        version_texto_id=resultado.escritura.version_texto_id,
        vectorizar=vectorizar,
        run_id=resultado.run_id,
    )
    if resultado.ids_de_canon:
        await registrar_uso_de_hechos(
            sesion, capitulo_id=capitulo_id, hecho_canon_ids=resultado.ids_de_canon
        )
    return consolidacion
