"""Cada validador emite su *score* (RF-VAL-01, RF-OBS-04, media `CA-18`, R-2).

Dos cosas distintas se prueban aqui y conviene no confundirlas:

1. **Que `validadores_ejecutados` diga la verdad.** Hoy no la dice: se rellena con
   el catalogo entero, corriera o no, asi que el campo que existe para distinguir
   «ninguno encontro nada» de «ninguno corrio» no puede distinguirlo. Es R-2.
2. **Que de ahi salga una puntuacion por validador**, con el nombre de
   `verification.md` §8.1 y sin traducir.

Y una tercera que es regla de la fase y no de este modulo: **nada de lo que emite
el observador puede romper una generacion** (regla 11). `emitir` corre dentro de
un camino de produccion, asi que el test que lo ata vive aqui.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from app.commons.observabilidad import Puntuacion, SpanEnMemoria
from app.features.calidad import (
    CATALOGO,
    CapituloAValidar,
    NombreDeCanon,
    ParametrosDeDiscurso,
    Persona,
    PuntoDeEjecucion,
    RangoDeExtension,
    TiempoVerbal,
    Validador,
    cruzar_g1a,
)
from app.features.calidad.cobertura import HechoUsado
from app.features.calidad.scores import (
    emitir,
    puntuaciones_de_g1a,
    puntuaciones_de_g4,
    puntuaciones_del_juez,
)
from app.features.calidad.validadores import (
    CATALOGO_DE_MANUSCRITO,
    ManuscritoAValidar,
    ValidadorDeManuscrito,
    cerrar_manuscrito,
)

LIMPIO = "Marta cerró la puerta. Estaba cansada y no dijo nada más aquella tarde de octubre."
HECHOS = frozenset({"hc-1"})


def capitulo() -> CapituloAValidar:
    return CapituloAValidar(
        version_texto_id="vt-1",
        texto=LIMPIO,
        rango_de_extension=RangoDeExtension(minimo=5, maximo=100),
        discurso=ParametrosDeDiscurso(
            persona=Persona.TERCERA_LIMITADA, tiempo_verbal=TiempoVerbal.PASADO
        ),
        nombres_del_canon=(NombreDeCanon(forma_canonica="Marta"),),
    )


def manuscrito() -> ManuscritoAValidar:
    return ManuscritoAValidar(
        elementos_obligatorios=("Luna",),
        hechos=(HechoUsado(entidad="Luna", atributo="especie", valor="perro", usado_en=(1,)),),
    )


# --- R-2: el censo dice quien corrio, no quien estaba apuntado ---------------


def test_validadores_ejecutados_nombra_a_los_que_corrieron_de_verdad() -> None:
    def revienta(_capitulo: CapituloAValidar) -> list[object]:
        raise RuntimeError("boom")

    catalogo = (
        *CATALOGO,
        Validador("roto", PuntoDeEjecucion.HOOK_DE_CAPITULO, revienta),  # type: ignore[arg-type]
    )

    resultado = cruzar_g1a(capitulo(), HECHOS, catalogo=catalogo)

    assert "roto" not in resultado.validadores_ejecutados
    assert resultado.validadores_rotos == ("roto",)
    assert not resultado.aprobado


def test_un_validador_roto_no_se_lleva_un_reintento() -> None:
    """Mismo criterio que el defecto mal formado: lo que falla de forma distinta
    no se mezcla en el mismo monton. Un fallo del *harness* no es culpa del
    capitulo, asi que no puede gastar uno de los dos intentos de `CLAUDE.md` §9.1."""

    def revienta(_capitulo: CapituloAValidar) -> list[object]:
        raise RuntimeError("boom")

    catalogo = (
        Validador("roto", PuntoDeEjecucion.HOOK_DE_CAPITULO, revienta),  # type: ignore[arg-type]
    )

    resultado = cruzar_g1a(capitulo(), HECHOS, catalogo=catalogo)

    assert not resultado.gasta_reintento


def test_los_que_si_corren_se_cuentan_aunque_otro_reviente() -> None:
    """Un validador roto no puede llevarse por delante el censo de los demas: la
    tabla de los cinco briefs quedaria con casillas vacias sin saber por que."""

    def revienta(_capitulo: CapituloAValidar) -> list[object]:
        raise RuntimeError("boom")

    catalogo = (
        Validador("roto", PuntoDeEjecucion.HOOK_DE_CAPITULO, revienta),  # type: ignore[arg-type]
        *CATALOGO,
    )

    resultado = cruzar_g1a(capitulo(), HECHOS, catalogo=catalogo)

    assert resultado.validadores_ejecutados == tuple(v.nombre for v in CATALOGO)


def test_en_g4_tambien() -> None:
    def revienta(_manuscrito: ManuscritoAValidar) -> object:
        raise RuntimeError("boom")

    catalogo = (
        *CATALOGO_DE_MANUSCRITO,
        ValidadorDeManuscrito("roto", PuntoDeEjecucion.PUERTA_G4, revienta),  # type: ignore[arg-type]
    )

    cierre = cerrar_manuscrito(manuscrito(), catalogo=catalogo)

    assert "roto" not in cierre.validadores_ejecutados
    assert cierre.validadores_rotos == ("roto",)


# --- RF-OBS-04: una puntuacion por validador ejecutado -----------------------


def test_cada_validador_ejecutado_produce_exactamente_una_puntuacion() -> None:
    resultado = cruzar_g1a(capitulo(), HECHOS)

    nombres = [p.nombre for p in puntuaciones_de_g1a(resultado)]

    assert sorted(nombres) == sorted(resultado.validadores_ejecutados)


def test_cada_validador_de_g4_produce_exactamente_una_puntuacion() -> None:
    cierre = cerrar_manuscrito(manuscrito())

    nombres = [p.nombre for p in puntuaciones_de_g4(cierre)]

    assert sorted(nombres) == sorted(cierre.validadores_ejecutados)


def test_un_validador_roto_no_produce_puntuacion() -> None:
    """Ni cero ni dos para los que corrieron; **ninguna** para el que no llego a
    correr. Una puntuacion de un validador roto seria un numero inventado."""

    def revienta(_capitulo: CapituloAValidar) -> list[object]:
        raise RuntimeError("boom")

    catalogo = (
        *CATALOGO,
        Validador("roto", PuntoDeEjecucion.HOOK_DE_CAPITULO, revienta),  # type: ignore[arg-type]
    )
    resultado = cruzar_g1a(capitulo(), HECHOS, catalogo=catalogo)

    assert "roto" not in [p.nombre for p in puntuaciones_de_g1a(resultado)]


def test_el_capitulo_limpio_puntua_distinto_que_el_que_tiene_defectos() -> None:
    """Un *score* que no se mueve con el resultado es telemetria muda."""
    limpio = puntuaciones_de_g1a(cruzar_g1a(capitulo(), HECHOS))

    corto = CapituloAValidar(
        version_texto_id="vt-2",
        texto="Marta cerró.",
        rango_de_extension=RangoDeExtension(minimo=50, maximo=100),
        discurso=ParametrosDeDiscurso(
            persona=Persona.TERCERA_LIMITADA, tiempo_verbal=TiempoVerbal.PASADO
        ),
        nombres_del_canon=(NombreDeCanon(forma_canonica="Marta"),),
    )
    con_defecto = puntuaciones_de_g1a(cruzar_g1a(corto, HECHOS))

    de = {p.nombre: p.valor for p in limpio}
    con = {p.nombre: p.valor for p in con_defecto}

    assert de["extension_de_capitulo"] != con["extension_de_capitulo"]


# --- El juez: un score por criterio, con su justificacion --------------------


@dataclass(frozen=True)
class _PuntuacionDelCritico:
    criterio: str
    valor: int
    justificacion: str


@dataclass(frozen=True)
class _Juicio:
    puntuaciones: tuple[_PuntuacionDelCritico, ...]


def test_el_juez_produce_una_puntuacion_por_criterio() -> None:
    juicio = _Juicio(
        puntuaciones=(
            _PuntuacionDelCritico("tono", 4, "registro sostenido"),
            _PuntuacionDelCritico("arco", 2, "termina donde empezo"),
        )
    )

    puntuaciones = puntuaciones_del_juez(juicio)

    assert [p.criterio for p in puntuaciones] == ["tono", "arco"]
    assert [p.valor for p in puntuaciones] == [4.0, 2.0]
    assert all(p.nombre == "juez_con_rubrica" for p in puntuaciones)
    assert [p.justificacion for p in puntuaciones] == [
        "registro sostenido",
        "termina donde empezo",
    ]


# --- Los nombres son los de `verification.md` §8.1, sin traducir -------------


def nombres_de_verification() -> set[str]:
    documento = Path(__file__).parents[6] / "docs" / "verification.md"
    texto = documento.read_text(encoding="utf-8")
    seccion = texto[texto.index("## 8. Los validadores") : texto.index("## 9.")]
    return set(re.findall(r"^\| `([a-z0-9_]+)`", seccion, re.MULTILINE))


def test_todo_validador_que_puntua_esta_en_la_tabla_de_verification() -> None:
    """`CLAUDE.md` §16. Renombrar uno aqui romperia el enlace entre el documento y
    el panel **sin que fallara nada**, y este test es lo que lo impide."""
    emitidos = {p.nombre for p in puntuaciones_de_g1a(cruzar_g1a(capitulo(), HECHOS))}
    emitidos |= {p.nombre for p in puntuaciones_de_g4(cerrar_manuscrito(manuscrito()))}
    emitidos.add("juez_con_rubrica")

    assert emitidos <= nombres_de_verification(), emitidos - nombres_de_verification()


def test_spec_tla_no_emite_puntuacion() -> None:
    """La unica excepcion del encargo §6: TLC corre en desarrollo, no en cada
    generacion. Se comprueba **por ausencia**, que es como se comprueba que algo
    no ocurre."""
    assert "spec_tla" in nombres_de_verification()

    emitidos = {p.nombre for p in puntuaciones_de_g1a(cruzar_g1a(capitulo(), HECHOS))}
    emitidos |= {p.nombre for p in puntuaciones_de_g4(cerrar_manuscrito(manuscrito()))}

    assert "spec_tla" not in emitidos


# --- Regla 11: emitir no puede romper una generacion -------------------------


def test_emitir_manda_cada_puntuacion_al_span() -> None:
    span = SpanEnMemoria(nombre="g1a")
    puntuaciones = puntuaciones_de_g1a(cruzar_g1a(capitulo(), HECHOS))

    emitir(span, puntuaciones)

    assert span.puntuaciones == list(puntuaciones)


def test_emitir_no_rompe_una_generacion_si_el_span_revienta() -> None:
    """Regla 11 de la fase. Corre dentro de un camino de produccion: una
    telemetria que tumba la novela que mide es peor que no tenerla."""

    class SpanRoto:
        def puntuar(self, puntuacion: Puntuacion) -> None:
            raise RuntimeError("langfuse caido")

    emitir(SpanRoto(), [Puntuacion(nombre="discurso", valor=1.0)])  # type: ignore[arg-type]


def test_emitir_sigue_con_las_demas_si_una_revienta() -> None:
    """Que no rompa no puede significar que se rinda a la primera: perder nueve
    *scores* por uno malo produce el panel vacio que R-1 describe."""
    fallados: list[str] = []

    class SpanQueFallaUnaVez:
        def __init__(self) -> None:
            self.recibidas: list[Puntuacion] = []

        def puntuar(self, puntuacion: Puntuacion) -> None:
            if puntuacion.nombre == "discurso":
                fallados.append(puntuacion.nombre)
                raise RuntimeError("boom")
            self.recibidas.append(puntuacion)

    span = SpanQueFallaUnaVez()
    emitir(
        span,  # type: ignore[arg-type]
        [
            Puntuacion(nombre="discurso", valor=1.0),
            Puntuacion(nombre="nombres_literales", valor=1.0),
        ],
    )

    assert fallados == ["discurso"]
    assert [p.nombre for p in span.recibidas] == ["nombres_literales"]
