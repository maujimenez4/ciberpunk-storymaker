"""Los invariantes, contra el compilador de verdad. `RF-FOR-02`, R-3, R-5.

**Estos tests llaman a Lean.** No es un descuido de `CA-4`: `CA-4` prohibe la
red y las credenciales, no un binario local, y una puerta formal que se prueba
con un doble no prueba nada -- lo unico que hay que demostrar aqui es que el
compilador rechaza lo que tiene que rechazar.

Se saltan si no hay Lean en la maquina -- preguntando **lo mismo que pregunta la
puerta** --, y el test de R-7 comprueba que esa ausencia se explica.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.canon.modelos import Evento
from app.features.manuscrito.lean import correr_lean, ruta_de_lean
from app.features.obra.modelos import Obra

hay_lean = pytest.mark.skipif(
    ruta_de_lean() is None, reason="Lean 4 no esta instalado en esta maquina"
)
"""Pregunta **lo mismo que la puerta**, no `shutil.which` por su cuenta.

Preguntar otra cosa daria tests que se saltan en una maquina donde la puerta si
funciona -- y eso ya paso aqui: con `lean` instalado por elan y fuera del PATH,
seis tests se saltaban en silencio y la suite decia verde. Una puerta formal sin
probar que parece probada es peor que no tenerla.
"""


async def _evento(
    sesion: AsyncSession,
    obra_id: int,
    *,
    tiempo: str,
    lugar: str = "la cocina",
    participantes: list[str] | None = None,
    excluye: list[str] | None = None,
) -> None:
    sesion.add(
        Evento(
            obra_id=obra_id,
            descripcion="pasa algo",
            tiempo_historia=tiempo,
            lugar=lugar,
            participantes=participantes or [],
            excluye=excluye or [],
        )
    )
    await sesion.flush()


@hay_lean
async def test_una_cronologia_coherente_pasa(sesion: AsyncSession, obra: Obra) -> None:
    """Marta se mueve: dos momentos, dos lugares. Eso es una novela normal."""
    await _evento(sesion, obra.id, tiempo="la manana del 3", participantes=["Marta"])
    await _evento(
        sesion, obra.id, tiempo="la tarde del 3", lugar="la playa", participantes=["Marta"]
    )

    resultado = await correr_lean(sesion, obra.id)

    assert resultado.ok, resultado.mensaje
    assert resultado.eventos_comprobados == 2


@hay_lean
async def test_alguien_en_dos_sitios_a_la_vez_falla(sesion: AsyncSession, obra: Obra) -> None:
    """`CA-21`, primera mitad, con el caso literal del criterio.

    Y dice **quien**: «no se puede publicar» sin nombre obliga a abrir la base
    para encontrar el evento.
    """
    await _evento(
        sesion, obra.id, tiempo="la manana del 3", lugar="la cocina", participantes=["Marta"]
    )
    await _evento(
        sesion, obra.id, tiempo="la manana del 3", lugar="la playa", participantes=["Marta"]
    )

    resultado = await correr_lean(sesion, obra.id)

    assert not resultado.ok
    assert "Marta" in resultado.mensaje
    assert "la cocina" in resultado.mensaje and "la playa" in resultado.mensaje


@hay_lean
async def test_aparecer_despues_de_ser_excluido_falla(sesion: AsyncSession, obra: Obra) -> None:
    """`evento.excluye[]` existe desde la Fase 2 y hasta hoy no lo miraba nadie."""
    await _evento(sesion, obra.id, tiempo="el entierro", excluye=["Abuela"])
    await _evento(sesion, obra.id, tiempo="la semana siguiente", participantes=["Abuela"])

    resultado = await correr_lean(sesion, obra.id)

    assert not resultado.ok
    assert "Abuela" in resultado.mensaje


@hay_lean
async def test_estar_presente_en_el_evento_que_te_excluye_no_falla(
    sesion: AsyncSession, obra: Obra
) -> None:
    """Quien muere **esta** en la escena de su muerte.

    Es la diferencia entre `<` y `≤` en el invariante, y sin este test un `≤`
    pasaria los otros tres y rechazaria todas las novelas con una muerte
    dentro -- que en romance no son pocas.
    """
    await _evento(
        sesion, obra.id, tiempo="el naufragio", participantes=["Abuela"], excluye=["Abuela"]
    )

    resultado = await correr_lean(sesion, obra.id)

    assert resultado.ok, resultado.mensaje


@hay_lean
async def test_una_obra_vacia_pasa_y_el_resultado_lo_distingue(
    sesion: AsyncSession, obra: Obra
) -> None:
    """R-3. **Sin esto, `CA-21` se cumple con una obra sin eventos.**

    «Lean paso» sobre una obra vacia y «Lean paso» sobre una cronologia
    coherente son el mismo verde y significan cosas distintas.
    """
    resultado = await correr_lean(sesion, obra.id)

    assert resultado.ok
    assert resultado.eventos_comprobados == 0


@hay_lean
async def test_dos_personajes_en_el_mismo_momento_y_sitios_distintos_no_es_un_fallo(
    sesion: AsyncSession, obra: Obra
) -> None:
    """El invariante es por **personaje**, no por momento.

    Sin este test, un invariante que dijera «en un momento dado todos estan en
    el mismo sitio» pasaria los anteriores y rechazaria cualquier novela con dos
    escenas simultaneas, que es una tecnica narrativa corriente.
    """
    await _evento(sesion, obra.id, tiempo="esa noche", lugar="la cocina", participantes=["Marta"])
    await _evento(sesion, obra.id, tiempo="esa noche", lugar="la playa", participantes=["Noe"])

    resultado = await correr_lean(sesion, obra.id)

    assert resultado.ok, resultado.mensaje
    assert resultado.eventos_comprobados == 2


async def test_sin_lean_el_error_dice_que_falta_y_como_instalarlo(
    sesion: AsyncSession, obra: Obra, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R-7. **Lo primero que vera quien clone el repositorio.**

    Un `FileNotFoundError: 'lean'` no le dice a nadie que le falta Lean 4. Este
    test no necesita Lean instalado: comprueba justamente su ausencia.
    """
    from app.features.manuscrito.lean import HerramientaNoDisponible

    monkeypatch.setattr("app.features.manuscrito.lean.corredor.ruta_de_lean", lambda: None)

    with pytest.raises(HerramientaNoDisponible) as fallo:
        await correr_lean(sesion, obra.id)

    mensaje = str(fallo.value)
    assert "lean" in mensaje.lower()
    assert "elan" in mensaje.lower(), "no dice como instalarlo"
