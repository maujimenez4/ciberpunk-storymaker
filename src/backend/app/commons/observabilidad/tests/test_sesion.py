"""La sesion **se deriva** del `obra_id`, no se pasa. RF-OBS-01.

La diferencia no es de estilo. Si el identificador de sesion fuera un parametro,
una regeneracion pedida dentro de un mes caeria en la sesion correcta **solo si
quien la pide se acuerda de pasar el mismo valor**; y el dia que alguien no se
acuerde, esa peticion aparece en Langfuse como una novela distinta, sin la
entrevista ni la generacion que la explican. Derivandolo, el caso imposible es
equivocarse.
"""

from app.commons.observabilidad import ObservadorEnMemoria


async def test_tres_trazas_de_la_misma_obra_comparten_sesion() -> None:
    """La entrevista, la generacion y una regeneracion, una sola sesion."""
    observador = ObservadorEnMemoria()

    async with observador.traza(obra_id=7, nombre="entrevista"):
        pass
    async with observador.traza(obra_id=7, nombre="generacion"):
        pass
    async with observador.traza(obra_id=7, nombre="regeneracion"):
        pass

    assert {t.sesion_id for t in observador.trazas} == {"obra-7"}
    assert [t.nombre for t in observador.trazas] == [
        "entrevista",
        "generacion",
        "regeneracion",
    ]


async def test_dos_obras_no_comparten_sesion() -> None:
    """La otra mitad del requisito, y la que de verdad puede fallar.

    Un `sesion_id` constante tambien haria pasar el test de arriba, y juntaria
    en un solo hilo las novelas de dos compradores distintos.
    """
    observador = ObservadorEnMemoria()

    async with observador.traza(obra_id=7, nombre="generacion"):
        pass
    async with observador.traza(obra_id=8, nombre="generacion"):
        pass

    assert {t.sesion_id for t in observador.trazas} == {"obra-7", "obra-8"}


async def test_los_spans_cuelgan_de_su_traza_y_llevan_nombre() -> None:
    """RF-OBS-02: cada rol y cada tool, un span con nombre identificable."""
    observador = ObservadorEnMemoria()

    # Anidados y no combinados: son **dos** spans hermanos dentro de la misma
    # traza, que es justo lo que este test comprueba. Juntarlos en un solo
    # `async with` cambiaria el arbol que se esta afirmando.
    async with observador.traza(obra_id=1, nombre="generacion") as traza:
        async with traza.span("escritor") as span:
            span.entrada("el paquete")
            span.salida("la prosa")
        async with traza.span("ensamblador"):
            pass

    (registro,) = observador.trazas
    assert [s.nombre for s in registro.spans] == ["escritor", "ensamblador"]
    assert registro.spans[0].entradas == ["el paquete"]
    assert registro.spans[0].salidas == ["la prosa"]
