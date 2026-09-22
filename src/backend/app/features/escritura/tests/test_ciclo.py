"""P-72, P-73, P-83, P-84 y P-86: el ciclo de escena y los permisos de agente.

RF-ORQ-02, RF-ORQ-07, RF-ORQ-08, RF-ORQ-15 a RF-ORQ-18.
"""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.commons.domain import RelojFijo
from app.commons.jobs import Estado, RepositorioDeTrabajos, Trabajo
from app.features.escritura import (
    DefectoParaReparar,
    ReintentoGenericoProhibido,
    aceptar_pese_al_defecto,
    preparar_reparacion,
    prompt_de_reparacion,
    reentrar_tras_edicion_humana,
)

DEFECTO = DefectoParaReparar(
    defecto_id="def-1",
    codigo="CON-03",
    cita="Noe menciona el incendio",
    detalle="Noe usa informacion sin sabe_desde anterior",
)


@pytest.fixture
def reloj() -> RelojFijo:
    return RelojFijo(datetime(2026, 9, 22, tzinfo=UTC))


@pytest.fixture
def repositorio(base_de_datos: Path) -> RepositorioDeTrabajos:
    conexion = sqlite3.connect(base_de_datos)
    conexion.execute("INSERT INTO serie (serie_id, titulo) VALUES ('s1','S')")
    conexion.execute(
        "INSERT INTO obra (obra_id, serie_id, titulo, genero, subgenero,"
        " extension_objetivo, persona, tiempo_verbal, esquema_de_pov, nivel_de_calor)"
        " VALUES ('o1','s1','O','romance','contemporaneo',90000,'tercera','pasado',"
        "'dual','sensual')"
    )
    conexion.execute(
        "INSERT INTO parte (parte_id, obra_id, numero, funcion_estructural)"
        " VALUES ('pa1','o1',1,'planteamiento')"
    )
    conexion.execute(
        "INSERT INTO capitulo (capitulo_id, parte_id, numero) VALUES ('ca1','pa1',1)"
    )
    conexion.execute(
        "INSERT INTO escena (escena_id, capitulo_id, orden_discurso, pov)"
        " VALUES ('es1','ca1',1,'pj-ada')"
    )
    conexion.commit()
    conexion.close()
    return RepositorioDeTrabajos(base_de_datos)


def _en_validando(repositorio: RepositorioDeTrabajos, reloj: RelojFijo) -> Trabajo:
    trabajo = repositorio.crear("o1", "es1", "escribir_escena", reloj)
    for estado in (Estado.ENSAMBLANDO, Estado.ESCRIBIENDO, Estado.VALIDANDO):
        repositorio.transitar(trabajo.trabajo_id, estado, reloj)
    return repositorio.leer(trabajo.trabajo_id)


# --- P-83: dos reparaciones y a la tercera, escalada ------------------------


def test_la_primera_reparacion_vuelve_a_escribir(
    repositorio: RepositorioDeTrabajos, reloj: RelojFijo
) -> None:
    trabajo = _en_validando(repositorio, reloj)

    resultado = preparar_reparacion(trabajo, [DEFECTO], repositorio, reloj)

    assert resultado.estado is Estado.ESCRIBIENDO
    assert resultado.intento == 1


def test_la_segunda_escala_a_humano(
    repositorio: RepositorioDeTrabajos, reloj: RelojFijo
) -> None:
    """RF-ORQ-07: máximo dos. El tercer intento raramente arregla lo que dos no
    arreglaron, y cada uno cuesta una llamada."""
    trabajo = _en_validando(repositorio, reloj)

    preparar_reparacion(trabajo, [DEFECTO], repositorio, reloj)
    repositorio.transitar(trabajo.trabajo_id, Estado.VALIDANDO, reloj)
    segunda = preparar_reparacion(
        repositorio.leer(trabajo.trabajo_id), [DEFECTO], repositorio, reloj
    )

    assert segunda.estado is Estado.ESCALADA
    assert segunda.intento == 2


def test_no_se_repara_sin_defecto_adjunto(
    repositorio: RepositorioDeTrabajos, reloj: RelojFijo
) -> None:
    """RF-ORQ-08. Un reintento genérico —«mejóralo»— degrada el texto casi
    siempre: el modelo no sabe qué arreglar y reescribe lo que ya estaba bien."""
    trabajo = _en_validando(repositorio, reloj)

    with pytest.raises(ReintentoGenericoProhibido):
        preparar_reparacion(trabajo, [], repositorio, reloj)

    assert repositorio.leer(trabajo.trabajo_id).estado is Estado.VALIDANDO


def test_no_se_repara_con_un_defecto_sin_cita(
    repositorio: RepositorioDeTrabajos, reloj: RelojFijo
) -> None:
    """RF-CAL-08: el prompt necesita el pasaje, no una descripción."""
    trabajo = _en_validando(repositorio, reloj)
    sin_cita = DEFECTO.model_copy(update={"cita": "   "})

    with pytest.raises(ReintentoGenericoProhibido):
        preparar_reparacion(trabajo, [sin_cita], repositorio, reloj)


def test_el_prompt_de_reparacion_lleva_codigo_cita_y_limite() -> None:
    texto = prompt_de_reparacion("Eres el Escritor.", [DEFECTO])

    assert "CON-03" in texto
    assert "Noe menciona el incendio" in texto
    assert "No reescribas lo que no se cita" in texto


# --- P-84: reentrada tras la edición humana ---------------------------------


def test_un_escalado_editado_reentra_por_validando(
    repositorio: RepositorioDeTrabajos, reloj: RelojFijo
) -> None:
    """RF-ORQ-17 y D-08. Entrar por `EXTRAYENDO` escribiría en canon un error
    introducido a mano, y deshacerlo cuesta un hecho sustitutorio más la
    invalidación de *snapshots*. Revalidar es barato; deshacer no."""
    trabajo = _en_validando(repositorio, reloj)
    preparar_reparacion(trabajo, [DEFECTO], repositorio, reloj)
    repositorio.transitar(trabajo.trabajo_id, Estado.VALIDANDO, reloj)
    escalado = preparar_reparacion(
        repositorio.leer(trabajo.trabajo_id), [DEFECTO], repositorio, reloj
    )

    reentrado = reentrar_tras_edicion_humana(escalado, repositorio, reloj)

    assert reentrado.estado is Estado.VALIDANDO


def test_la_revalidacion_humana_no_consume_intentos(
    repositorio: RepositorioDeTrabajos, reloj: RelojFijo
) -> None:
    """Los dos intentos de RF-ORQ-07 son de reparación **por el modelo**; aquí
    ha escrito una persona."""
    trabajo = _en_validando(repositorio, reloj)
    preparar_reparacion(trabajo, [DEFECTO], repositorio, reloj)
    repositorio.transitar(trabajo.trabajo_id, Estado.VALIDANDO, reloj)
    escalado = preparar_reparacion(
        repositorio.leer(trabajo.trabajo_id), [DEFECTO], repositorio, reloj
    )

    reentrado = reentrar_tras_edicion_humana(escalado, repositorio, reloj)

    assert reentrado.intento == escalado.intento


def test_aceptar_pese_al_defecto_avanza_y_deja_constancia(
    repositorio: RepositorioDeTrabajos, reloj: RelojFijo
) -> None:
    """RF-ORQ-18. Existe porque un validador puede equivocarse: sin esta salida,
    la postcondición de CU-04 no se puede prometer."""
    trabajo = _en_validando(repositorio, reloj)
    preparar_reparacion(trabajo, [DEFECTO], repositorio, reloj)
    repositorio.transitar(trabajo.trabajo_id, Estado.VALIDANDO, reloj)
    escalado = preparar_reparacion(
        repositorio.leer(trabajo.trabajo_id), [DEFECTO], repositorio, reloj
    )

    aceptado = aceptar_pese_al_defecto(
        escalado, "def-1", "maujimenez4", repositorio, reloj
    )

    assert aceptado.estado is Estado.EXTRAYENDO
    assert aceptado.defecto_anulado_id == "def-1"
    assert aceptado.anulado_por == "maujimenez4"


def test_no_se_acepta_sin_decir_quien(
    repositorio: RepositorioDeTrabajos, reloj: RelojFijo
) -> None:
    """El registro es la condición, no un adorno: sin él no se avanza."""
    trabajo = _en_validando(repositorio, reloj)

    with pytest.raises(ValueError):
        aceptar_pese_al_defecto(trabajo, "def-1", "", repositorio, reloj)


# --- P-72 y P-73: topología en estrella y agentes sin herramientas ----------


AGENTES = ("obra", "outline", "escena", "escritura", "calidad", "canon")
RAIZ = Path(__file__).resolve().parents[3]


def test_ningun_agente_invoca_a_otro() -> None:
    """RF-ORQ-02, §3.1 punto 1. Una cadena de agentes que se invocan entre sí
    hace imposible saber quién introdujo un defecto. El orquestador es el único
    que decide el orden, y vive en `escritura` y `commons/jobs`."""
    for feature in AGENTES:
        if feature == "escritura":
            continue
        for fichero in (RAIZ / "features" / feature).rglob("*.py"):
            if "tests" in fichero.parts:
                continue
            texto = fichero.read_text(encoding="utf-8")
            assert "app.features.escritura" not in texto, (
                f"{fichero.name} invoca al orquestador: la estrella se rompe"
            )


def test_ningun_agente_lee_ni_escribe_ficheros() -> None:
    """RF-ORQ-16. Los prompts los carga el orquestador (`commons/llm`), no el
    agente: así la invariante es cierta por construcción y no por instrucción en
    el prompt, que es lo que `verification.md` §3 llama supresión de alcance."""
    prohibidos = ("open(", "Path(", "read_text", "write_text", "requests.", "httpx.")
    for feature in AGENTES:
        for fichero in (RAIZ / "features" / feature).rglob("*.py"):
            if "tests" in fichero.parts or fichero.name == "repository.py":
                continue
            texto = fichero.read_text(encoding="utf-8")
            for prohibido in prohibidos:
                assert prohibido not in texto, (
                    f"{fichero.relative_to(RAIZ)} usa {prohibido}: los agentes no "
                    f"tocan ficheros ni red (RF-ORQ-16)"
                )
