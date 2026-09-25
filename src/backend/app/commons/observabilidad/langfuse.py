"""El cliente real. Traduce `obra_id` a `session_id` y **nada mas**.

Cuanto menos haga este adaptador, menos hay que volver a pensar el dia que el
proveedor cambie de forma. Todo lo que no sea traducir vive en `trazas.py`
(el contrato) o en `blindaje.py` (que no rompa nada).

**Las credenciales no se escriben en ningun sitio.** Ni en un `repr`, ni en un
mensaje de error, ni en un log: un `repr` con la clave dentro acaba en un
traceback y un traceback acaba en un fichero. Se leen del entorno (RF-OBS-07),
se usan y no se vuelven a nombrar.

El `import` de `langfuse` es **perezoso**: construir el observador no puede
exigir que la dependencia este instalada, porque la suite corre sin ella y sin
red (`CA-4`). Se importa al abrir la primera traza, y si no esta, el blindaje lo
cuenta como un fallo mas y la novela sigue.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Any

from app.commons.observabilidad.trazas import Puntuacion, sesion_de


class _SpanLangfuse:
    """Un span del proveedor, con las operaciones del contrato."""

    def __init__(self, interno: Any) -> None:
        self._interno = interno

    def entrada(self, texto: str) -> None:
        self._interno.update(input=texto)

    def salida(self, texto: str) -> None:
        self._interno.update(output=texto)

    def consumo(
        self,
        *,
        modelo: str,
        tokens_entrada: int,
        tokens_salida: int,
        coste_usd: Decimal,
    ) -> None:
        # El coste va como `float` porque es lo que el proveedor acepta. El
        # `Decimal` es el que se guarda en `ejecucion`: aqui es una cifra para
        # mirar en un panel, alli es la que se suma (RF-OBS-03).
        self._interno.update(
            model=modelo,
            usage_details={"input": tokens_entrada, "output": tokens_salida},
            cost_details={"total": float(coste_usd)},
        )

    def puntuar(self, puntuacion: Puntuacion) -> None:
        # P-22.1. Los criterios del juez comparten `nombre` (`juez_con_rubrica`),
        # y el proveedor agrupa por `name`: sin el criterio dentro, las seis
        # series salen mezcladas en una y el *tuning* no ve cual se movio.
        nombre = (
            f"{puntuacion.nombre}.{puntuacion.criterio}"
            if puntuacion.criterio
            else puntuacion.nombre
        )
        self._interno.score(
            name=nombre,
            value=puntuacion.valor,
            comment=puntuacion.justificacion,
        )

    def prompt(self, prompt_id: str, prompt_version: str, prompt_hash: str) -> None:
        # Como metadatos del span y no con el objeto `prompt` del SDK: ese exige
        # que la plantilla este registrada en el gestor de prompts de Langfuse, y
        # aqui la plantilla vive versionada en el repositorio (`CLAUDE.md` §10).
        # Los nombres son los de la fila de `ejecucion`, para cruzar sin traducir.
        self._interno.update(
            metadata={
                "prompt_id": prompt_id,
                "prompt_version": prompt_version,
                "prompt_hash": prompt_hash,
            }
        )


class _TrazaLangfuse:
    def __init__(self, cliente: Any, traza: Any) -> None:
        self._cliente = cliente
        self._traza = traza

    @asynccontextmanager
    async def span(self, nombre: str) -> AsyncIterator[_SpanLangfuse]:
        # SDK v4: `start_as_current_observation` (la v3 lo llamaba
        # `start_as_current_span`; con la v4 instalada no llegaba ninguna traza
        # y el blindaje se tragaba el AttributeError — corrida real 2026-09-24).
        with self._traza.start_as_current_observation(name=nombre, as_type="span") as interno:
            yield _SpanLangfuse(interno)


class ObservadorLangfuse:
    """El observador de produccion. **Se usa siempre blindado** (`blindar`).

    No se blinda a si mismo a proposito: el blindaje es una decision de quien lo
    monta -- `obtener_observador` -- y meterlo aqui haria imposible probar que
    este cliente falla cuando debe.
    """

    def __init__(
        self, *, clave_publica: str, clave_secreta: str, host: str, cliente: Any | None = None
    ) -> None:
        """`cliente` es la costura de las pruebas: un `Langfuse` falso, para ver
        lo que el adaptador le pide sin red ni dependencia (`CA-4`). En
        produccion no se pasa y el real se construye al abrir la primera traza."""
        self._clave_publica = clave_publica
        self._clave_secreta = clave_secreta
        self._host = host
        self._cliente: Any | None = cliente

    @staticmethod
    def sesion_de(obra_id: int) -> str:
        """RF-OBS-01: la sesion se deriva del `obra_id`. La misma funcion que
        usa el doble, para que las pruebas midan lo que corre en produccion."""
        return sesion_de(obra_id)

    def __repr__(self) -> str:
        """Sin la clave secreta, y **sin la publica tampoco**.

        La publica no es un secreto, pero identifica el proyecto; y el habito de
        no imprimir credenciales vale mas que la excepcion razonada.
        """
        return f"ObservadorLangfuse(host={self._host!r})"

    def _abrir(self) -> Any:
        """El cliente, construido la primera vez que hace falta.

        Perezoso porque importar `langfuse` al cargar el modulo obligaria a
        tener la dependencia para correr la suite, y `CA-4` dice lo contrario.
        """
        if self._cliente is None:
            from langfuse import Langfuse

            self._cliente = Langfuse(
                public_key=self._clave_publica,
                secret_key=self._clave_secreta,
                host=self._host,
            )
        return self._cliente

    def cerrar(self) -> None:
        """P-22.2: vacia la cola del SDK, que manda por lotes y en segundo plano.

        Solo si el cliente llego a construirse: un proceso que no trazo nada no
        tiene cola, y construirlo aqui abriria una conexion para cerrarla. Si el
        `flush` lanza, lanza: quien lo protege es el blindaje, que lo cuenta.
        """
        if self._cliente is not None:
            self._cliente.flush()

    @asynccontextmanager
    async def traza(self, *, obra_id: int, nombre: str) -> AsyncIterator[_TrazaLangfuse]:
        cliente = self._abrir()
        from langfuse import propagate_attributes

        # SDK v4: la sesion se propaga con `propagate_attributes`, no con
        # `update_trace` (que la v4 ya no tiene).
        with (
            cliente.start_as_current_observation(name=nombre, as_type="span") as traza,
            propagate_attributes(session_id=self.sesion_de(obra_id), trace_name=nombre),
        ):
            yield _TrazaLangfuse(cliente, traza)
