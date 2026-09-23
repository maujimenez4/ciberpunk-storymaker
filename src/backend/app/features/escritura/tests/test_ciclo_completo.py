"""P-111c: el ciclo de una escena vive en la feature, no en un guion (§3.9).

El bucle entero -planificar, ensamblar, escribir, validar, extraer- estaba en
`corrida.py`, 431 lineas en la raiz del repositorio. Mientras estuviera ahi, la
API no podia conducirlo: el endpoint creaba la fila de `trabajo` y nadie la
ejecutaba.

Este test es el que lo fija. Corre el ciclo **desde la base de datos**, con las
capas saliendo de los almacenes reales, y comprueba las cuatro huellas que un
ciclo completo deja: el trabajo termina en `INTEGRADA`, hay una version de texto
vigente, el canon ha crecido y la ficha del Planificador esta escrita.
"""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.commons.db import RepositorioDeEjecuciones
from app.commons.domain import RelojFijo, RolNarrativo
from app.commons.jobs import CerrojoPorObra, RepositorioDeTrabajos, TurnoDeModelo
from app.commons.llm import (
    CargadorDePrompts,
    ContadorBPE,
    DobleDeModelo,
    DobleDeOrdenador,
)
from app.features.canon import RepositorioDeCanon
from app.features.contexto import AlmacenesDeLaObra
from app.features.escena import RepositorioDeEscenas
from app.features.escritura import Dependencias, ciclo_de_escena
from app.features.obra import (
    Biblia,
    DistanciaDeBiblia,
    LugarDeBiblia,
    PersonajeDeBiblia,
    RepositorioDeObras,
)
from app.features.outline import RepositorioDeOutline

RAIZ = Path(__file__).resolve().parents[4]
PROMPTS = RAIZ / "app" / "features"
RELOJ = RelojFijo(datetime(2026, 9, 22, tzinfo=UTC))

FICHA = json.dumps(
    {
        "pov": "pj-ada",
        "presentes": ["pj-ada", "pj-noe"],
        "lugar": "lug-taller",
        "objetivo_del_pov": "cerrar el trato antes del amanecer",
        "obstaculo": "el otro se niega a firmar",
        "valor_entrada": "control",
        "valor_salida": "amenaza",
        "distancia_psiquica": "cercana",
        "densidad_de_dialogo_objetivo": 0.4,
        "extension_objetivo": 1500,
    }
)
PROSA = (
    "Ada cruzo el taller con la carpeta apretada contra el pecho. Noe la "
    "esperaba junto a la mesa, sin levantar la vista de los planos.\n\n"
    "—No voy a firmar eso —dijo el.\n\n"
    "Ella dejo la carpeta sobre la mesa y no la solto."
)
EXTRACCION = json.dumps(
    {
        "hechos": [
            {"entidad": "pj-noe", "atributo": "postura", "valor": "se niega a firmar"}
        ],
        "eventos": [
            {
                "descripcion": "Noe se niega a firmar",
                "testigos": ["pj-ada", "pj-noe"],
                "participantes": ["pj-ada", "pj-noe"],
            }
        ],
        "resumen": "Ada intenta cerrar el trato y Noe se niega.",
    }
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
            tiempo_de_viaje="20 minutos",
        )
    ],
)


@pytest.fixture
def obra_lista(base_de_datos: Path) -> Path:
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
    conexion.execute(
        "INSERT INTO escena (escena_id, capitulo_id, version_obra_id, orden_discurso,"
        " tiempo_historia, pov, lugar, beat_de_genero)"
        " VALUES ('es1','ca1','vo1',1,'dia-1','pj-ada','lug-taller','encuentro')"
    )
    conexion.commit()
    conexion.close()
    return base_de_datos


def dependencias(ruta: Path) -> Dependencias:
    return Dependencias(
        reloj=RELOJ,
        contador=ContadorBPE(),
        cargador=CargadorDePrompts(PROMPTS),
        turno=TurnoDeModelo(simultaneas=1),
        cerrojo=CerrojoPorObra(),
        ordenador=DobleDeOrdenador(),
        arquitecto=DobleDeModelo([BIBLIA.model_dump_json()]),
        planificador=DobleDeModelo([FICHA]),
        escritor=DobleDeModelo([PROSA]),
        extractor=DobleDeModelo([EXTRACCION]),
        trabajos=RepositorioDeTrabajos(ruta),
        escenas=RepositorioDeEscenas(ruta),
        canon=RepositorioDeCanon(ruta),
        ejecuciones=RepositorioDeEjecuciones(ruta),
        obras=RepositorioDeObras(ruta),
        outline=RepositorioDeOutline(ruta),
        almacenes=AlmacenesDeLaObra(ruta),
    )


def test_el_ciclo_de_escena_vive_en_la_feature(obra_lista: Path) -> None:
    resultado = ciclo_de_escena(
        escena_id="es1", obra_id="o1", serie_id="s1", dep=dependencias(obra_lista)
    )

    assert resultado.estado == "INTEGRADA"

    # 1. Hay texto vigente.
    vigente = RepositorioDeEscenas(obra_lista).vigente_de("es1")
    assert "carpeta" in vigente.texto

    # 2. El canon crecio, y con su escena de origen.
    hechos = RepositorioDeCanon(obra_lista).hechos_de_escena("es1")
    assert [h.entidad for h in hechos] == ["pj-noe"]

    # 3. La ficha del Planificador quedo escrita (P-111b).
    ficha = RepositorioDeEscenas(obra_lista).ficha_de("es1")
    assert ficha.objetivo_del_pov == "cerrar el trato antes del amanecer"
    assert ficha.presentes == ["pj-ada", "pj-noe"]


def test_el_paquete_sale_de_los_almacenes_y_no_de_cadenas_fijas(
    obra_lista: Path,
) -> None:
    """La diferencia con `corrida.py`: las capas se recolectan, no se inventan.

    Se comprueba por el desglose, que es lo que `ejecucion` persiste y lo que
    hace auditable una llamada (RI-14): las siete capas con contenido tienen que
    haber aportado tokens.
    """
    resultado = ciclo_de_escena(
        escena_id="es1", obra_id="o1", serie_id="s1", dep=dependencias(obra_lista)
    )

    por_capa = resultado.tokens_por_capa
    vacias = [
        capa for capa, tokens in por_capa.items() if capa != "reserva" and not tokens
    ]

    assert not vacias, f"capas sin tokens: {vacias}"
    assert por_capa["constitucional"] > 0  # la biblia, leida de version_obra
    assert por_capa["instruccion"] > 0  # la ficha recien escrita
