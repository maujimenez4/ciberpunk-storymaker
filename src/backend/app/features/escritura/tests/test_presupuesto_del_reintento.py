"""Juntura 3: **el prompt del reintento se vuelve a presupuestar.**

`CLAUDE.md` §4.1 dice que la reserva de 10.000 tokens existe, con esas palabras,
«para que el reintento con el defecto anadido siga cabiendo». Hasta hoy nadie lo
comprobaba, y la seccion de reparacion anade **el capitulo anterior integro**
mas una linea por defecto: la segunda vuelta manda un prompt mayor que el que se
conto, y su fila de `ejecucion` guardaba como `tokens_previstos` el total del
paquete, no el del prompt de verdad.

Es la union T5-T6-T8 y ninguna de las tres la tenia asignada. Lo que se
comprueba aqui son las dos mitades:

1. **Lo que crece se cuenta**, y la fila de esa vuelta lo dice.
2. **Si no cabe en la reserva, no se llama**: `ContextBudgetExceeded`, que es lo
   que RF-CTX-02 pide y lo que hace que la reserva sea un mecanismo y no una
   fila de una tabla.

Ninguna prueba llama al proveedor (CA-4).
"""

import pytest
from sqlalchemy import select

from app.commons.domain.errores import ContextBudgetExceeded
from app.commons.llm.doble import DobleDeterminista
from app.features.calidad import RangoDeExtension
from app.features.contexto import ensamblar_capitulo
from app.features.escena import RestriccionesDeDiscurso
from app.features.escritura.agents import MARCA_DE_PLANTILLA, MARCA_DE_REPARACION, Escritor
from app.features.escritura.modelos import Ejecucion
from app.features.escritura.service import escribir_capitulo
from app.features.obra.modelos import HechoCanon

BUENA = "Nadia cerro el invernadero y miro la carta que estaba sobre la mesa."
CORTA = "Nadia miro."

RANGO_ANCHO = RangoDeExtension(minimo=1, maximo=10_000)
RANGO_DE_CAPITULO = RangoDeExtension(minimo=800, maximo=1200)
"""La palanca de rechazo sin veto: `EST-02`, como en el resto de la suite."""


class ContadorDePalabras:
    """El mismo de `conftest.py`: exacto, reproducible y sin red."""

    def contar(self, texto: str) -> int:
        return len(texto.split())


class ContadorQueInflaLaReparacion:
    """Cuenta igual, salvo el bloque de reparacion, que cuenta **muy caro**.

    Es la unica forma de alcanzar la rama de «no cabe» sin construir un paquete
    de cien mil tokens en un test: lo que se prueba es que el **incremento** del
    prompt se compara contra la reserva libre, no cuanto pesa cada palabra.
    """

    def contar(self, texto: str) -> int:
        palabras = len(texto.split())
        if MARCA_DE_REPARACION in texto:
            return palabras + 100_000
        return palabras


async def _contexto(sesion, obra_con_outline):
    sesion.add(
        HechoCanon(
            obra_id=obra_con_outline.obra.id,
            entidad="Nadia",
            atributo="oficio",
            valor="botanica",
            origen="escena",
            escena_de_origen=str(obra_con_outline.escena.id),
        )
    )
    await sesion.flush()
    return await ensamblar_capitulo(sesion, obra_con_outline.capitulos[0].id, ContadorDePalabras())


async def _escribir(sesion, obra_con_outline, *, contador, rango=RANGO_ANCHO, respuestas=None):
    contexto = await _contexto(sesion, obra_con_outline)
    return await escribir_capitulo(
        sesion,
        Escritor(
            DobleDeterminista(
                respuestas
                if respuestas is not None
                else {MARCA_DE_REPARACION: BUENA, MARCA_DE_PLANTILLA: CORTA}
            )
        ),
        contexto=contexto,
        contador=contador,
        run_id="run-1",
        modelo="doble",
        restricciones=RestriccionesDeDiscurso(
            persona="3ª limitada", tiempo_verbal="pasado", nivel_de_calor=2
        ),
        rango_de_extension=rango,
    )


async def test_la_vuelta_del_reintento_cuenta_el_prompt_que_de_verdad_se_manda(
    sesion, obra_con_outline
):
    """La fila de la segunda vuelta guarda **mas** tokens que la de la primera.

    La diferencia es exactamente lo que anade la seccion de reparacion: el
    capitulo anterior integro y una linea por defecto. Si el ciclo siguiera
    guardando el total del paquete, las dos filas serian iguales.
    """
    escritura = await _escribir(
        sesion, obra_con_outline, contador=ContadorDePalabras(), rango=RANGO_DE_CAPITULO
    )

    assert len(escritura.intentos) >= 2
    previstos = (
        (await sesion.execute(select(Ejecucion.tokens_previstos).order_by(Ejecucion.id)))
        .scalars()
        .all()
    )
    assert previstos[1] > previstos[0]


async def test_si_la_reparacion_no_cabe_en_la_reserva_no_se_vuelve_a_llamar(
    sesion, obra_con_outline
):
    """RF-CTX-02: el paquete que no cabe **no llega a gastarse**.

    Se cuentan las llamadas del doble: la primera vuelta si se hizo, la segunda
    no. Sin esa comprobacion, «lanza antes de llamar» seria una afirmacion sobre
    el orden de dos lineas que nadie mira.
    """
    doble = DobleDeterminista({MARCA_DE_REPARACION: BUENA, MARCA_DE_PLANTILLA: CORTA})
    contexto = await _contexto(sesion, obra_con_outline)

    with pytest.raises(ContextBudgetExceeded) as fallo:
        await escribir_capitulo(
            sesion,
            Escritor(doble),
            contexto=contexto,
            contador=ContadorQueInflaLaReparacion(),
            run_id="run-1",
            modelo="doble",
            restricciones=RestriccionesDeDiscurso(
                persona="3ª limitada", tiempo_verbal="pasado", nivel_de_calor=2
            ),
            rango_de_extension=RANGO_DE_CAPITULO,
        )

    assert fallo.value.capa == "reserva"
    assert len(doble.llamadas) == 1
