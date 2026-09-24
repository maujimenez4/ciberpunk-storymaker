"""La puerta G1a mecanica. Sin algo que rechace de verdad, R-7 no se prueba."""

from app.features.calidad import (
    CATALOGO,
    CapituloAValidar,
    Defecto,
    MotivoMalFormado,
    NombreDeCanon,
    ParametrosDeDiscurso,
    Persona,
    PuntoDeEjecucion,
    RangoDeExtension,
    TiempoVerbal,
    comprobar_forma,
    cruzar_g1a,
)

LIMPIO = "Marta cerró la puerta. Estaba cansada y no dijo nada más aquella tarde de octubre."
HECHOS = frozenset({"hc-1"})


def capitulo(texto: str = LIMPIO, minimo: int = 5, maximo: int = 100) -> CapituloAValidar:
    return CapituloAValidar(
        version_texto_id="vt-1",
        texto=texto,
        rango_de_extension=RangoDeExtension(minimo=minimo, maximo=maximo),
        discurso=ParametrosDeDiscurso(
            persona=Persona.TERCERA_LIMITADA, tiempo_verbal=TiempoVerbal.PASADO
        ),
        nombres_del_canon=(NombreDeCanon(forma_canonica="Marta"),),
    )


def test_un_capitulo_limpio_cruza_la_puerta():
    resultado = cruzar_g1a(capitulo(), HECHOS)

    assert resultado.aprobado
    assert resultado.bloqueantes == ()


def test_un_capitulo_corto_no_cruza_la_puerta():
    """Lo que hace probable R-7: algo que rechaza de verdad."""
    resultado = cruzar_g1a(capitulo(minimo=500, maximo=600), HECHOS)

    assert not resultado.aprobado
    assert [d.codigo for d in resultado.bloqueantes] == ["EST-02"]


def test_un_defecto_con_cita_inventada_no_bloquea_y_se_cuenta_aparte():
    """CA-17, entero: no bloquea, no gasta reintento y se cuenta aparte."""
    inventado = Defecto(
        codigo="CON-01",
        version_texto_id="vt-1",
        cita="abrio la ventana",
        desplazamiento_inicio=0,
        desplazamiento_fin=16,
    )

    resultado = cruzar_g1a(capitulo(), HECHOS, defectos_recibidos=[inventado])

    assert resultado.aprobado
    assert resultado.bloqueantes == ()
    assert not resultado.gasta_reintento
    assert [m.motivo for m in resultado.mal_formados] == [
        MotivoMalFormado.CITA_FUERA_DE_SU_DESPLAZAMIENTO
    ]


def test_un_defecto_recibido_bien_formado_si_bloquea_y_gasta_reintento():
    real = Defecto(
        codigo="CON-01",
        version_texto_id="vt-1",
        cita="cerró la puerta",
        desplazamiento_inicio=LIMPIO.index("cerró la puerta"),
        desplazamiento_fin=LIMPIO.index("cerró la puerta") + len("cerró la puerta"),
    )

    resultado = cruzar_g1a(capitulo(), HECHOS, defectos_recibidos=[real])

    assert not resultado.aprobado
    assert resultado.gasta_reintento
    assert resultado.bloqueantes == (real,)


def test_los_defectos_que_producen_los_validadores_pasan_su_propia_comprobacion_de_forma():
    """Si un validador propio produjera un defecto mal formado, la puerta lo
    descartaria en silencio y el capitulo pasaria. Es el modo de fallo que esta
    comprobacion existe para impedir."""
    capi = capitulo(texto="Yo cerré la puerta. Maria no dijo nada.", minimo=500, maximo=600)
    capi = CapituloAValidar(
        version_texto_id=capi.version_texto_id,
        texto=capi.texto,
        rango_de_extension=capi.rango_de_extension,
        discurso=capi.discurso,
        nombres_del_canon=(NombreDeCanon(forma_canonica="María"),),
    )

    resultado = cruzar_g1a(capi, HECHOS)

    assert {d.codigo for d in resultado.bloqueantes} == {"EST-02", "PER-02", "VOZ-03"}
    assert resultado.mal_formados == ()
    for defecto in resultado.bloqueantes:
        assert comprobar_forma(defecto, capi.texto, HECHOS) is None


def test_la_puerta_declara_que_validadores_ejecuto():
    resultado = cruzar_g1a(capitulo(), HECHOS)

    assert resultado.validadores_ejecutados == tuple(v.nombre for v in CATALOGO)


def test_cada_validador_tiene_nombre_y_punto_de_ejecucion_declarado():
    """RF-VAL-01. Lo que no se puede nombrar no se puede contar.

    Los nombres no son libres: son los de `verification.md` §8.1, que es el
    catalogo que la spec cita y no duplica. Renombrar uno aqui rompe el enlace
    entre el documento y el codigo sin que falle nada mas.

    Se afirma la **lista exacta y ordenada**, y no una inclusion: un
    `set(...) <= {...}` pasa con el catalogo vacio, que es justo el test que no
    puede caer del que este proyecto lleva cuatro.
    """
    nombres = [v.nombre for v in CATALOGO]

    assert nombres == ["extension_de_capitulo", "nombres_literales", "discurso"]
    assert len(set(nombres)) == len(nombres)
    for validador in CATALOGO:
        assert validador.punto is PuntoDeEjecucion.HOOK_DE_CAPITULO
