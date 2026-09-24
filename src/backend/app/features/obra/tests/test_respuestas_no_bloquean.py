"""RI-02 no retiene la base mientras habla con el modelo.

Lo destapo la primera corrida desde el frontend: `responder_entrevista` hacia
el `UPDATE` de las respuestas, **luego** llamaba al Entrevistador y **solo
despues** commiteaba. La transaccion de escritura quedaba abierta durante toda
la llamada al modelo, y el segundo clic del comprador -- que llega porque el
primero tarda y la pantalla no dice nada -- esperaba `busy_timeout` y moria con
`database is locked`. Cuatro de seis peticiones acabaron en 500 por esto.
"""

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.commons.llm.doble import DobleDeterminista
from app.features.obra.agents import Entrevistador, Evaluacion
from app.features.obra.repository import obtener_entrevista
from app.features.obra.service import abrir_entrevista, responder_entrevista


class EntrevistadorQueMiraLaBase(Entrevistador):
    """Cuando lo llaman, abre **otra** sesion y lee la entrevista.

    En WAL una segunda conexion solo ve lo commiteado: si el servicio llama al
    modelo con la transaccion abierta, esta lectura devuelve las respuestas de
    antes, no las que acaba de guardar.
    """

    def __init__(self, motor: AsyncEngine, entrevista_id: int) -> None:
        super().__init__(DobleDeterminista({}))
        self._motor = motor
        self._entrevista_id = entrevista_id
        self.vio: dict[str, object] | None = None

    async def evaluar(self, respuestas: dict[str, object], texto: str) -> Evaluacion:
        async with AsyncSession(self._motor) as otra:
            fila = await obtener_entrevista(otra, self._entrevista_id)
            assert fila is not None
            self.vio = dict(fila.respuestas)
        return Evaluacion(faltantes=[], contradicciones=[])


async def test_las_respuestas_estan_commiteadas_antes_de_llamar_al_modelo(
    motor: AsyncEngine, sesion: AsyncSession
) -> None:
    entrevista = await abrir_entrevista(sesion)
    agente = EntrevistadorQueMiraLaBase(motor, entrevista.id)

    await responder_entrevista(sesion, agente, entrevista.id, {"nombre": "Marta"})

    assert agente.vio == {"nombre": "Marta"}
