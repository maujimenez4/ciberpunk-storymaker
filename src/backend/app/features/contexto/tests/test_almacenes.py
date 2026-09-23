"""P-108 y P-109: las capas salen de los almacenes (§4.8, RF-CTX-02).

`Almacenes` era un `Protocol` **que no implementaba nadie**. El ensamblador
estaba escrito y probado contra dobles, y `corrida.py` se fabricaba las siete
capas a mano con cadenas fijas. De ahi el sintoma que el Cierre de la spec 001
anoto sin explicar: el canon aportaba 36 tokens de media al paquete.

El caso que de verdad importa es el del canon de la escena N en el paquete de
la N+1.
Sin el, la memoria de largo plazo se escribe correctamente, se consolida en una
transaccion, se versiona, se resume... y no la lee nadie. Un bucle abierto que
pasa todos los tests de sus dos mitades.
"""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.commons.domain import RelojFijo, RolNarrativo
from app.commons.llm import ContadorBPE, DobleDeOrdenador
from app.features.canon import (
    EventoExtraido,
    Extraccion,
    HechoExtraido,
    RepositorioDeCanon,
)
from app.features.contexto import AlmacenesDeLaObra, ensamblar, recolectar
from app.features.escena import RepositorioDeEscenas
from app.features.obra import (
    Biblia,
    DistanciaDeBiblia,
    LugarDeBiblia,
    PersonajeDeBiblia,
)

BIBLIA = Biblia(
    tropo="enemigos a amantes",
    promesa_de_apertura="Una relojera y un contrabandista, obligados a pactar.",
    personajes=[
        PersonajeDeBiblia(
            pj_id="pj-ada",
            nombre="Ada",
            edad=31,
            rol_narrativo=RolNarrativo.PROTAGONISTA,
        ),
        PersonajeDeBiblia(
            pj_id="pj-noe",
            nombre="Noe",
            edad=34,
            rol_narrativo=RolNarrativo.COPROTAGONISTA,
        ),
    ],
    lugares=[LugarDeBiblia(lug_id="lug-taller", nombre="El taller")],
    distancias=[
        DistanciaDeBiblia(
            origen_id="lug-taller",
            destino_id="lug-muelle",
            tiempo_de_viaje="veinte minutos",
        )
    ],
)

RELOJ = RelojFijo(datetime(2026, 9, 22, tzinfo=UTC))


@pytest.fixture
def obra_con_dos_escenas_escritas(base_de_datos: Path) -> Path:
    """Tres escenas: dos ya integradas y la tercera por escribir."""
    conexion = sqlite3.connect(base_de_datos)
    conexion.execute("INSERT INTO serie (serie_id, titulo) VALUES ('s1','Serie')")
    conexion.execute(
        "INSERT INTO obra (obra_id, serie_id, titulo, genero, subgenero,"
        " extension_objetivo, persona, tiempo_verbal, esquema_de_pov, nivel_de_calor)"
        " VALUES ('o1','s1','Ceniza y neon','romance','romantasy',90000,'tercera',"
        "'pasado','dual','sensual')"
    )
    conexion.execute(
        "INSERT INTO version_obra (version_obra_id, obra_id, numero, biblia, creada_en)"
        " VALUES ('vo1','o1',1,?,?)",
        (BIBLIA.model_dump_json(), RELOJ.ahora().isoformat()),
    )
    conexion.execute(
        "INSERT INTO parte (parte_id, obra_id, numero, funcion_estructural)"
        " VALUES ('pa1','o1',1,'planteamiento')"
    )
    conexion.execute(
        "INSERT INTO capitulo (capitulo_id, parte_id, numero, titulo)"
        " VALUES ('ca1','pa1',1,'La tregua')"
    )
    for i, beat in ((1, "encuentro"), (2, "chispa")):
        conexion.execute(
            "INSERT INTO escena (escena_id, capitulo_id, version_obra_id,"
            " orden_discurso, tiempo_historia, pov, lugar, beat_de_genero)"
            " VALUES (?,?, 'vo1', ?, ?, 'pj-ada','el taller', ?)",
            (f"es{i}", "ca1", i, f"dia-{i}", beat),
        )
    conexion.execute(
        "INSERT INTO escena (escena_id, capitulo_id, version_obra_id, orden_discurso,"
        " tiempo_historia, pov, lugar, presentes, mencionados, objetivo_del_pov,"
        " obstaculo, valor_entrada, valor_salida, beat_de_genero)"
        " VALUES ('es3','ca1','vo1',3,'dia-3','pj-ada','el muelle',?,?,"
        "'recuperar el contrato','la puerta esta sellada','esperanza','miedo',"
        "'primera grieta')",
        (json.dumps(["pj-ada", "pj-noe"]), json.dumps(["pj-vera"])),
    )
    conexion.commit()
    conexion.close()

    escenas = RepositorioDeEscenas(base_de_datos)
    canon = RepositorioDeCanon(base_de_datos)

    v1 = escenas.guardar_version(
        "es1", "Ada abrio el taller al amanecer.", "run-1", RELOJ
    )
    canon.consolidar(
        serie_id="s1",
        escena_id="es1",
        version_texto_id=v1.version_texto_id,
        extraccion=Extraccion(
            hechos=[
                HechoExtraido(
                    entidad="pj-noe", atributo="oficio", valor="contrabandista"
                ),
                HechoExtraido(entidad="pj-vera", atributo="cargo", valor="inspectora"),
            ],
            eventos=[
                EventoExtraido(
                    descripcion="Ada descubre el contrato falsificado",
                    testigos=["pj-ada"],
                )
            ],
            resumen="Ada abre el taller y encuentra el contrato.",
        ),
        reloj=RELOJ,
    )

    v2 = escenas.guardar_version(
        "es2", "Noe cruzo el umbral sin llamar.", "run-2", RELOJ
    )
    canon.consolidar(
        serie_id="s1",
        escena_id="es2",
        version_texto_id=v2.version_texto_id,
        extraccion=Extraccion(resumen="Noe aparece y niega el encargo."),
        reloj=RELOJ,
    )
    return base_de_datos


def test_el_canon_de_la_escena_n_aparece_en_el_de_la_n_mas_1(
    obra_con_dos_escenas_escritas: Path,
) -> None:
    """P-109. El bucle de memoria, cerrado: lo que el Extractor escribio en la
    escena 1 tiene que llegar al paquete de la 3."""
    almacenes = AlmacenesDeLaObra(obra_con_dos_escenas_escritas)

    canon = almacenes.canon_relevante("es3")
    textos = [texto for texto, _ in canon]

    assert any("contrabandista" in t for t in textos), (
        f"el canon de es1 no llego al contexto de es3: {textos}"
    )


def test_el_canon_separa_a_los_presentes_de_los_mencionados(
    obra_con_dos_escenas_escritas: Path,
) -> None:
    """§2.1: la capa de canon cede primero a los personajes mencionados y no
    presentes, asi que el recolector necesita la marca, no solo el texto."""
    canon = dict(
        (texto, presente)
        for texto, presente in AlmacenesDeLaObra(
            obra_con_dos_escenas_escritas
        ).canon_relevante("es3")
    )

    presencia = {
        "pj-noe" in t: p for t, p in canon.items()
    }  # noe esta presente, vera solo mencionada
    assert presencia[True] is True
    assert any(p is False for t, p in canon.items() if "pj-vera" in t)


def test_la_continuidad_local_trae_el_texto_anterior_y_el_resumen_previo(
    obra_con_dos_escenas_escritas: Path,
) -> None:
    """§4.2: la N-1 integra y la N-2 resumida."""
    almacenes = AlmacenesDeLaObra(obra_con_dos_escenas_escritas)

    assert almacenes.escena_anterior_integra("es3") == "Noe cruzo el umbral sin llamar."
    assert almacenes.resumen_de_la_penultima("es3") == (
        "Ada abre el taller y encuentra el contrato."
    )


def test_la_primera_escena_no_tiene_continuidad_y_lo_dice_con_none(
    obra_con_dos_escenas_escritas: Path,
) -> None:
    """Que la capa quede vacia es asunto de RF-CTX-14. Inventarse un texto para
    que no lo este seria mucho peor: el Escritor creeria que hubo una escena."""
    almacenes = AlmacenesDeLaObra(obra_con_dos_escenas_escritas)

    assert almacenes.escena_anterior_integra("es1") is None
    assert almacenes.resumen_de_la_penultima("es1") is None


def test_cada_capa_restante_sale_de_su_almacen(
    obra_con_dos_escenas_escritas: Path,
) -> None:
    """§4.8: una capa, un almacen. Ninguna se queda sin origen."""
    almacenes = AlmacenesDeLaObra(obra_con_dos_escenas_escritas)

    constitucional = " ".join(almacenes.biblia_y_discurso("es3"))
    assert "tercera" in constitucional and "sensual" in constitucional
    assert "relojera" in constitucional  # la biblia de la version vigente

    estructural = " ".join(almacenes.outline_del_capitulo("es3"))
    assert "La tregua" in estructural and "primera grieta" in estructural

    estado = [texto for texto, _ in almacenes.estado_en_t("es3")]
    assert any("contrato falsificado" in t for t in estado)

    assert almacenes.fragmentos_candidatos("es3", 50)
    assert almacenes.muestras_ancla("es3", 2)

    instruccion = " ".join(almacenes.instruccion("es3"))
    assert "recuperar el contrato" in instruccion
    assert "la puerta esta sellada" in instruccion


def test_el_paquete_se_monta_entero_desde_la_base_de_datos(
    obra_con_dos_escenas_escritas: Path,
) -> None:
    """P-110, RF-CTX-14 contra el disco y no contra dobles.

    Es la unica forma de saber que las nueve lecturas encajan de verdad: un
    doble que devuelve cadenas siempre llena todas las capas, asi que un almacen
    que no supiera leer la suya pasaria inadvertido hasta la primera corrida.
    """
    capas = recolectar(
        escena_id="es3",
        almacenes=AlmacenesDeLaObra(obra_con_dos_escenas_escritas),
        ordenador=DobleDeOrdenador(),
        consulta="el contrato del taller",
    )

    vacias = [capa.value for capa, contenido in capas.items() if contenido.esta_vacia]
    assert not vacias, f"capas sin contenido desde los almacenes reales: {vacias}"

    paquete = ensamblar(capas, ContadorBPE())

    assert paquete.desglose.total > 0
    assert "contrabandista" in paquete.texto, "el canon no llego al paquete montado"
    assert "recuperar el contrato" in paquete.texto
