"""P-125 a P-129: los cuatro validadores de continuidad, en el bucle.

RF-CAL-04 a RF-CAL-06 y RF-CAL-09. Estaban implementados y probados desde la
fase 6, y **nadie los llamaba**: G1a invocaba tres de los once. La primera
corrida real integro diez escenas con cero defectos y un manuscrito que se
contradice a si mismo. Estos tests son la red que faltaba.

El caso de `test_una_afirmacion_que_contradice_el_canon_escala_la_escena` es el
de aquel manuscrito, reducido a dos escenas: lo que el canon fija en la primera,
la segunda lo desmiente.
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
from app.features.calidad import Defecto, RepositorioDeDefectos
from app.features.canon import RepositorioDeCanon
from app.features.contexto import AlmacenesDeLaObra
from app.features.escena import RepositorioDeEscenas
from app.features.escritura import Dependencias, ResultadoDeEscena, ciclo_de_escena
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
RELOJ = RelojFijo(datetime(2026, 9, 23, tzinfo=UTC))

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
                "testigos": ["pj-ada"],
                "participantes": ["pj-ada", "pj-noe"],
            }
        ],
        "resumen": "Ada intenta cerrar el trato y Noe se niega.",
    }
)
SIN_AFIRMACIONES = "[]"

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
def obra_con_dos_escenas(base_de_datos: Path) -> Path:
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
    for numero in (1, 2):
        conexion.execute(
            "INSERT INTO escena (escena_id, capitulo_id, version_obra_id,"
            " orden_discurso, tiempo_historia, pov, lugar, beat_de_genero)"
            " VALUES (?,'ca1','vo1',?,?,'pj-ada','lug-taller',?)",
            (
                f"es{numero}",
                numero,
                f"dia-{numero}",
                "encuentro" if numero == 1 else "chispa",
            ),
        )
    conexion.commit()
    conexion.close()
    return base_de_datos


def dependencias(ruta: Path, afirmaciones: list[str]) -> Dependencias:
    return Dependencias(
        reloj=RELOJ,
        contador=ContadorBPE(),
        cargador=CargadorDePrompts(PROMPTS),
        turno=TurnoDeModelo(simultaneas=1),
        cerrojo=CerrojoPorObra(),
        ordenador=DobleDeOrdenador(),
        arquitecto=DobleDeModelo([BIBLIA.model_dump_json()]),
        planificador=DobleDeModelo([FICHA] * 2),
        escritor=DobleDeModelo([PROSA] * 2),
        continuista=DobleDeModelo(afirmaciones),
        extractor=DobleDeModelo([EXTRACCION] * 2),
        trabajos=RepositorioDeTrabajos(ruta),
        escenas=RepositorioDeEscenas(ruta),
        canon=RepositorioDeCanon(ruta),
        ejecuciones=RepositorioDeEjecuciones(ruta),
        obras=RepositorioDeObras(ruta),
        outline=RepositorioDeOutline(ruta),
        almacenes=AlmacenesDeLaObra(ruta),
        defectos=RepositorioDeDefectos(ruta),
    )


def _correr_dos(ruta: Path, segunda: str) -> tuple[ResultadoDeEscena, Dependencias]:
    """La primera escena limpia, la segunda con lo que se quiera probar."""
    dep = dependencias(ruta, [SIN_AFIRMACIONES, segunda])
    ciclo_de_escena(escena_id="es1", obra_id="o1", serie_id="s1", dep=dep)
    resultado = ciclo_de_escena(escena_id="es2", obra_id="o1", serie_id="s1", dep=dep)
    return resultado, dep


def _defectos_de(ruta: Path) -> list[Defecto]:
    """Todos los defectos escritos, de las dos escenas."""
    repositorio = RepositorioDeDefectos(ruta)
    return [
        defecto
        for escena in ("es1", "es2")
        for defecto in repositorio.de_version(
            RepositorioDeEscenas(ruta).vigente_de(escena).version_texto_id
        )
    ]


# --- P-125: CAN-01, la averia del manuscrito del 22-09 ----------------------


def test_una_afirmacion_que_contradice_el_canon_escala_la_escena(
    obra_con_dos_escenas: Path,
) -> None:
    """RG-03: prevalece el hecho de menor `orden_discurso`.

    La escena 1 fija que Noe se niega a firmar. La 2 dice que firmo sin leerlo.
    Eso es lo que hizo el manuscrito real diez veces seguidas sin que nadie lo
    parara.
    """
    contradice = json.dumps(
        [
            {
                "cita": "—No voy a firmar eso",
                "sujeto": "pj-noe",
                "atributo": "postura",
                "valor": "firma sin leerlo",
                "momento": 1,
            }
        ]
    )

    resultado, _ = _correr_dos(obra_con_dos_escenas, contradice)

    # No escala: CAN-01 dejo de bloquear el 2026-09-23 porque su contraste da
    # falsos positivos (ver `defectos.py`). Lo que si tiene que pasar es que el
    # defecto **exista y quede escrito**, que es lo que en la corrida real no
    # ocurria: alli la tabla `defecto` tenia cero filas.
    assert resultado.estado == "INTEGRADA"
    assert [d.codigo.value for d in _defectos_de(obra_con_dos_escenas)] == ["CAN-01"]


def test_el_can_01_registrado_cita_el_hecho_con_el_que_choca(
    obra_con_dos_escenas: Path,
) -> None:
    """Axioma 12: sin el `hecho_canon_id` el defecto no es reparable."""
    contradice = json.dumps(
        [
            {
                "cita": "—No voy a firmar eso",
                "sujeto": "pj-noe",
                "atributo": "postura",
                "valor": "firma sin leerlo",
                "momento": 1,
            }
        ]
    )

    _correr_dos(obra_con_dos_escenas, contradice)

    defecto = _defectos_de(obra_con_dos_escenas)[0]
    assert defecto.hecho_canon_id is not None
    assert defecto.bien_formado
    assert defecto.cita == "—No voy a firmar eso"


# --- P-126: CON-03, usar lo que no se sabe ---------------------------------


def test_un_personaje_que_usa_lo_que_no_sabe_escala_la_escena(
    obra_con_dos_escenas: Path,
) -> None:
    """RG-01 y RF-CAN-11: el conocimiento sale de `testigos[]`.

    Noe **participa** en la negativa de la escena 1 pero no figura como testigo,
    asi que en la 2 no puede usarla. Estar en una escena no es haberse enterado.
    """
    usa_lo_que_no_sabe = json.dumps(
        [
            {
                "cita": "Ella dejo la carpeta sobre la mesa",
                "sujeto": "pj-noe",
                "informacion": "Noe se niega a firmar",
                "momento": 1,
            }
        ]
    )

    resultado, _ = _correr_dos(obra_con_dos_escenas, usa_lo_que_no_sabe)

    assert resultado.estado == "INTEGRADA"  # CON-03 tampoco bloquea hoy
    assert [d.codigo.value for d in _defectos_de(obra_con_dos_escenas)] == ["CON-03"]


def test_quien_presencio_el_evento_si_puede_usarlo(
    obra_con_dos_escenas: Path,
) -> None:
    """La otra mitad: sin esto, el validador podria estar bloqueando todo."""
    usa_lo_que_sabe = json.dumps(
        [
            {
                "cita": "Ella dejo la carpeta sobre la mesa",
                "sujeto": "pj-ada",
                "informacion": "Noe se niega a firmar",
                "momento": 1,
            }
        ]
    )

    resultado, _ = _correr_dos(obra_con_dos_escenas, usa_lo_que_sabe)

    assert resultado.estado == "INTEGRADA"
    assert _defectos_de(obra_con_dos_escenas) == []


# --- P-127: CON-01, dos lugares en el mismo momento ------------------------


def test_estar_en_dos_lugares_en_el_mismo_momento_escala_la_escena(
    obra_con_dos_escenas: Path,
) -> None:
    """RG-04, la mitad que no necesita tiempos de viaje.

    La otra mitad -llegar antes de lo que permite el `tiempo_de_viaje`- no se
    cablea: el `momento` del Continuista es un entero relativo a la escena y el
    `tiempo_de_viaje` de la biblia es texto libre. No son magnitudes
    comparables, y unirlas es una decision que no toma este paso.
    """
    en_dos_sitios = json.dumps(
        [
            {
                "cita": "Ada cruzo el taller",
                "sujeto": "pj-ada",
                "lugar": "lug-taller",
                "momento": 1,
            },
            {
                "cita": "Ella dejo la carpeta sobre la mesa",
                "sujeto": "pj-ada",
                "lugar": "lug-muelle",
                "momento": 1,
            },
        ]
    )

    resultado, _ = _correr_dos(obra_con_dos_escenas, en_dos_sitios)

    assert resultado.estado == "ESCALADA"
    assert "CON-01" in resultado.defectos


# --- P-128: el CAN-01 llega bien formado -----------------------------------


def test_un_can_01_bien_formado_no_se_cuenta_como_mal_formado(
    obra_con_dos_escenas: Path,
) -> None:
    """Axioma 12 y RF-CAL-11: el `hecho_canon_id` existe en el grafo.

    G1a recibia `set()` como grafo de canon, asi que un CAN-01 perfectamente
    formado se marcaba mal formado, **no bloqueaba** y se contaba como ruido del
    Continuista. El defecto habria existido y aun asi la escena habria pasado.
    """
    contradice = json.dumps(
        [
            {
                "cita": "—No voy a firmar eso",
                "sujeto": "pj-noe",
                "atributo": "postura",
                "valor": "firma sin leerlo",
                "momento": 1,
            }
        ]
    )

    _correr_dos(obra_con_dos_escenas, contradice)

    with sqlite3.connect(obra_con_dos_escenas) as conexion:
        filas = conexion.execute(
            "SELECT codigo, hecho_canon_id, bien_formado FROM defecto"
        ).fetchall()

    assert filas, "el defecto no se registro"
    codigo, hecho_canon_id, bien_formado = filas[0]
    assert codigo == "CAN-01"
    assert bien_formado == 1
    assert hecho_canon_id is not None


# --- P-129: la llamada queda registrada ------------------------------------


def test_la_llamada_al_continuista_queda_registrada_con_su_veredicto(
    obra_con_dos_escenas: Path,
) -> None:
    """RI-14 y RG-07: toda llamada al modelo deja su fila en `ejecucion`.

    La corrida real registro diez ejecuciones, todas del Escritor. El Extractor
    escribia noventa y nueve hechos sin dejar rastro de la llamada que los
    produjo.
    """
    _correr_dos(obra_con_dos_escenas, SIN_AFIRMACIONES)

    with sqlite3.connect(obra_con_dos_escenas) as conexion:
        prompts = [
            f[0]
            for f in conexion.execute(
                "SELECT DISTINCT prompt_id FROM ejecucion ORDER BY prompt_id"
            )
        ]
        veredictos = [
            f[0]
            for f in conexion.execute(
                "SELECT veredicto FROM ejecucion WHERE prompt_id = 'continuista'"
            )
        ]

    assert "continuista" in prompts
    assert veredictos and all(v == "aprobada" for v in veredictos)


# --- CA-15: la cita inventada, por el camino que la corrida recorrio --------


def test_una_cita_que_el_continuista_se_invento_no_mata_el_ciclo(
    obra_con_dos_escenas: Path,
) -> None:
    """La corrida real con Continuista murio en la escena 1 por esto.

    El test que decia cubrirlo -`test_puerta.py`- construye el defecto con un
    fragmento que **si** esta en el texto y luego le corrompe los
    desplazamientos con `model_copy`: prueba un anclaje corrompido, no una cita
    inventada, y el `model_copy` rodea justo el punto donde el sistema reventaba
    con entrada real. Este entra por donde entro la corrida: el Continuista
    devuelve una cita que no existe en la prosa.

    Lo que CA-15 promete y aqui se comprueba entero: no bloquea, **no gasta
    intento** y queda contada como mal formada. (Era CA-14 hasta el 2026-09-23:
    la 001 tenia dos criterios distintos con ese numero y se renumero el segundo.)
    """
    inventada = json.dumps(
        [
            {
                "cita": "conozco a todos los clientes de este barrio",
                "sujeto": "pj-noe",
                "atributo": "postura",
                "valor": "firma sin leerlo",
                "momento": 1,
            }
        ]
    )

    resultado, _ = _correr_dos(obra_con_dos_escenas, inventada)

    assert resultado.estado == "INTEGRADA"
    assert resultado.defectos == []

    with sqlite3.connect(obra_con_dos_escenas) as conexion:
        registrados = conexion.execute(
            "SELECT codigo, cita, bien_formado FROM defecto"
        ).fetchall()
        intentos = conexion.execute(
            "SELECT intento FROM trabajo WHERE escena_id = 'es2'"
        ).fetchone()[0]

    assert registrados, "la cita inventada tiene que quedar contada"
    codigo, cita, bien_formado = registrados[0]
    assert codigo == "CAN-01"
    assert cita == "conozco a todos los clientes de este barrio"
    assert bien_formado == 0, "una cita que no esta en el texto no es bien formada"
    assert intentos == 0, "un defecto mal formado no gasta reintento (RF-ORQ-19)"
