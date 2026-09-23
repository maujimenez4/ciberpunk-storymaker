"""P-100, P-101 y P-103: las demostraciones que no necesitan proveedor.

CA-10, CA-11, RNF-OBS-01 y RNF-OBS-02. Son criterios marcados **D** en la spec:
no basta con que una función devuelva lo esperado, hay que **enseñar** que el
sistema hace lo que promete de punta a punta.

P-99 —el capítulo completo de CA-1— no está aquí: necesita el proveedor real y
gasta cuota, así que se corre aparte y con permiso.
"""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.commons.config import Metricas, cargar_ajustes
from app.commons.db import RegistroDeEjecucion, RepositorioDeEjecuciones
from app.commons.domain import RelojFijo
from app.commons.llm import CargadorDePrompts
from app.features.contexto import Capa, CapaEnsamblada, Pieza, ensamblar

PROMPTS = Path(__file__).resolve().parents[1] / "features"


class ContadorDePalabras:
    def contar(self, texto: str) -> int:
        return len(texto.split())


@pytest.fixture
def reloj() -> RelojFijo:
    return RelojFijo(datetime(2026, 9, 22, tzinfo=UTC))


@pytest.fixture
def obra(base_de_datos: Path) -> str:
    conexion = sqlite3.connect(base_de_datos)
    conexion.execute("INSERT INTO serie (serie_id, titulo) VALUES ('s1','S')")
    conexion.execute(
        "INSERT INTO obra (obra_id, serie_id, titulo, genero, subgenero,"
        " extension_objetivo, persona, tiempo_verbal, esquema_de_pov, nivel_de_calor)"
        " VALUES ('o1','s1','O','romance','contemporaneo',90000,'tercera','pasado',"
        "'dual','sensual')"
    )
    conexion.execute(
        "INSERT INTO version_obra (version_obra_id, obra_id, numero, biblia, creada_en)"
        " VALUES ('vo1','o1',1,'{}','2026-09-22')"
    )
    conexion.execute(
        "INSERT INTO parte (parte_id, obra_id, numero, funcion_estructural)"
        " VALUES ('pa1','o1',1,'planteamiento')"
    )
    conexion.execute(
        "INSERT INTO capitulo (capitulo_id, parte_id, numero) VALUES ('ca1','pa1',1)"
    )
    conexion.execute(
        "INSERT INTO escena (escena_id, capitulo_id, version_obra_id, orden_discurso,"
        " pov) VALUES ('es1','ca1','vo1',1,'pj-ada')"
    )
    conexion.commit()
    conexion.close()
    return "o1"


# --- P-100 (CA-10): desde una fila de `ejecucion` se audita lo que se envió --


def test_desde_una_ejecucion_se_reconstruye_que_se_envio(
    base_de_datos: Path, obra: str, reloj: RelojFijo
) -> None:
    """CA-10 tras D-02, y la matización importa.

    Ya **no** se promete reconstruir el mismo paquete: la ordenación semántica
    tiene varianza, así que un ensamblado nuevo del mismo estado puede devolver
    otro orden. Lo que sí se promete es **auditar** una ejecución concreta: con
    qué prompt exacto se llamó —identificado por su hash—, qué fragmentos
    entraron y cuántos tokens ocupó cada capa.
    """
    capas: dict[Capa, CapaEnsamblada] = {
        capa: CapaEnsamblada(
            capa=capa, piezas=[Pieza(f"contenido de {capa.value}", 0, "p0")]
        )
        for capa in Capa
        if capa is not Capa.RESERVA
    }
    paquete = ensamblar(capas, ContadorDePalabras())
    prompt = CargadorDePrompts(PROMPTS).cargar("arquitecto")

    repositorio = RepositorioDeEjecuciones(base_de_datos)
    ejecucion_id = repositorio.registrar(
        RegistroDeEjecucion(
            run_id="run-1",
            escena_id="es1",
            prompt_id=prompt.prompt_id,
            prompt_version=prompt.version,
            prompt_hash=prompt.hash,
            version_obra_id="vo1",
            ids_recuperados=["frag-1", "frag-2"],
            modelo="doble",
            parametros={"temperatura": 0.8},
            semilla=7,
            tokens_por_capa=paquete.desglose.por_capa,
            coste=0.02,
            veredicto="aprobada",
        ),
        reloj,
    )

    auditado = repositorio.leer(ejecucion_id)
    recargado = CargadorDePrompts(PROMPTS).cargar(
        auditado.prompt_id, auditado.prompt_version
    )

    # 1. El prompt exacto que se envió, recuperado por su hash.
    assert recargado.hash == auditado.prompt_hash
    # 2. Qué se recuperó, aunque otro ensamblado ordenara distinto.
    assert auditado.ids_recuperados == ["frag-1", "frag-2"]
    # 3. El desglose por capa, que suma lo que dice (RF-CTX-06).
    assert sum(auditado.tokens_por_capa.values()) == paquete.desglose.total


def test_un_prompt_editado_en_sitio_rompe_la_auditoria_y_se_nota(
    base_de_datos: Path, obra: str, reloj: RelojFijo
) -> None:
    """Es el modo de fallo que el hash existe para detectar: si alguien edita el
    fichero sin subir versión, la ejecución guardada deja de ser auditable y
    `coincide_el_hash` lo dice en vez de reconstruir algo que nunca se envió."""
    cargador = CargadorDePrompts(PROMPTS)
    prompt = cargador.cargar("arquitecto")
    falsificado = prompt.__class__(
        prompt_id=prompt.prompt_id,
        version=prompt.version,
        hash="hash-que-no-es",
        texto=prompt.texto,
    )

    assert cargador.coincide_el_hash(prompt) is True
    assert cargador.coincide_el_hash(falsificado) is False


# --- P-101 (CA-11): arranca con una sola credencial -------------------------


def test_el_proceso_arranca_sin_ninguna_credencial(
    monkeypatch: pytest.MonkeyPatch, base_de_datos: Path
) -> None:
    """CA-11 tras D-02 y la decisión (a) de 2026-09-22.

    Decía demostrar que «una sola credencial basta» y en su propio cuerpo
    exportaba `STORYMAKER_PROVEEDOR_EMBEDDINGS_CLAVE: "no-se-usa"`. Demostraba
    lo contrario de lo que afirmaba, y el Cierre de la spec se apoyaba en él.

    Lo que se demuestra ahora es lo que de verdad ocurre: el proveedor es el CLI
    de Claude Code, la credencial es su sesión, y el proceso arranca **sin
    ninguna** variable de credencial."""
    for nombre, valor in {
        "STORYMAKER_MODELO": "modelo",
        "STORYMAKER_RUTA_BASE_DE_DATOS": str(base_de_datos),
    }.items():
        monkeypatch.setenv(nombre, valor)

    ajustes = cargar_ajustes()

    from app.main import crear_app

    app = crear_app(ajustes.ruta_base_de_datos)

    assert "/trabajos/{trabajo_id}" in app.openapi()["paths"]


def test_no_queda_ninguna_dependencia_de_la_extension_vectorial() -> None:
    """D-02: si algo volviera a cargar `sqlite_vec`, el sistema dejaría de
    arrancar en una máquina limpia y nadie lo sabría hasta desplegarlo."""
    import importlib.util

    raiz = Path(__file__).resolve().parents[1]
    for fichero in raiz.rglob("*.py"):
        if "tests" in fichero.parts:
            continue
        assert "sqlite_vec" not in fichero.read_text(encoding="utf-8")
    assert importlib.util.find_spec("sqlite_vec") is None


# --- P-103 (RNF-OBS-01, 02): las métricas de una corrida --------------------


def test_las_metricas_de_una_corrida_estan_completas() -> None:
    """RNF-OBS-01 y RNF-OBS-02: las ocho de §9, sobre una corrida simulada."""
    metricas = Metricas()
    for i in range(10):
        metricas.anotar_escena(
            f"es{i}",
            coste=0.03,
            por_capa={"constitucional": 400, "canon_relevante": 1600},
        )
        metricas.anotar_espera_de_turno(1.5, vencida=False)
    metricas.anotar_defecto("CON-03", bien_formado=True)
    metricas.anotar_defecto("CAN-01", bien_formado=False)
    metricas.escalados = 1
    metricas.reintentos = 3

    assert sum(metricas.coste_por_escena.values()) == pytest.approx(0.3)
    assert metricas.porcentaje_por_capa()["canon_relevante"] == pytest.approx(80.0)
    assert metricas.tasa_de_defectos_mal_formados == 0.5
    assert metricas.escalados_por_cien_escenas == 10.0
    assert metricas.espera_media_de_turno_s == pytest.approx(1.5)
    assert metricas.esperas_vencidas == 0
