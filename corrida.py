#!/usr/bin/env python
"""CA-1: escribe un capítulo completo, de principio a fin.

    uv run python corrida.py --seco          # con dobles, sin gastar cuota
    uv run python corrida.py --real          # con el CLI de Claude, gasta

**El modo seco existe porque es el que prueba la integración.** Recorre el ciclo
entero con dobles: si las siete features encajan y la máquina de estados llega a
`INTEGRADA` diez veces, la corrida real solo pone a prueba la calidad del texto,
no el cableado. Verificar en seco antes de gastar es más barato que descubrir un
`AttributeError` en la escena siete después de pagar seis.

Lo que **no** hace: no es un test. Los 347 tests comprueban las piezas; esto
comprueba que juntas escriben un capítulo, que es lo que CA-1 pide demostrar.
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src" / "backend"))

from app.commons.config import Metricas, traza  # noqa: E402
from app.commons.db import RepositorioDeEjecuciones  # noqa: E402
from app.commons.domain import RelojDelSistema  # noqa: E402
from app.commons.jobs import (  # noqa: E402
    CerrojoPorObra,
    RepositorioDeTrabajos,
    TurnoDeModelo,
)
from app.commons.llm import (  # noqa: E402
    CargadorDePrompts,
    ContadorBPE,
    DobleDeModelo,
    DobleDeOrdenador,
)
from app.features.canon import RepositorioDeCanon  # noqa: E402
from app.features.contexto import AlmacenesDeLaObra  # noqa: E402
from app.features.escena import RepositorioDeEscenas  # noqa: E402
from app.features.escritura import Dependencias, ciclo_de_escena  # noqa: E402
from app.features.manuscrito import RepositorioDeManuscrito  # noqa: E402
from app.features.obra import RepositorioDeObras  # noqa: E402

RAIZ = Path(__file__).parent
PROMPTS = RAIZ / "src" / "backend" / "app" / "features"
ESCENAS = 10

# La biblia tiene que validar contra `Biblia`: desde P-111c la capa
# constitucional del paquete sale de `version_obra`, asi que un `{}` como el que
# habia aqui rompe la corrida en la primera escena. Es la misma leccion de
# siempre: lo que no se lee, no se sabe que esta mal.
BIBLIA_FALSA = json.dumps(
    {
        "tropo": "enemigos a amantes",
        "promesa_de_apertura": "Una relojera y un contrabandista, obligados a pactar.",
        "personajes": [
            {
                "pj_id": "pj-ada",
                "nombre": "Ada",
                "edad": 31,
                "rol_narrativo": "protagonista",
            },
            {
                "pj_id": "pj-noe",
                "nombre": "Noe",
                "edad": 34,
                "rol_narrativo": "coprotagonista",
            },
        ],
        "lugares": [{"lug_id": "lug-taller", "nombre": "El taller"}],
        "distancias": [
            {
                "origen_id": "lug-taller",
                "destino_id": "lug-muelle",
                "tiempo_de_viaje": "veinte minutos",
            }
        ],
    }
)

FICHA_FALSA = json.dumps(
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
PROSA_FALSA = (
    "Ada cruzo el taller con la carpeta apretada contra el pecho. La lluvia "
    "golpeaba el techo de chapa y el olor a ozono se le metia en la garganta. "
    "Noe la esperaba junto a la mesa, sin levantar la vista de los planos.\n\n"
    "—No voy a firmar eso —dijo el.\n\n"
    "Ella dejo la carpeta sobre la mesa y no la solto."
)
EXTRACCION_FALSA = json.dumps(
    {
        "hechos": [
            {"entidad": "Ada", "atributo": "gesto", "valor": "aprieta la carpeta"}
        ],
        "eventos": [
            {
                "descripcion": "Noe se niega a firmar",
                "testigos": ["pj-ada", "pj-noe"],
                "participantes": ["pj-ada", "pj-noe"],
            }
        ],
        "resumen": "Ada intenta cerrar el trato y Noe se niega.",
        "hilos": [{"pregunta": "Por que Noe no firma?", "estado": "abierto"}],
        "plantados": [{"importancia": "alta", "descripcion": "los planos"}],
        "ngramas_gastados": ["el olor a ozono"],
    }
)


def preparar_base(ruta: Path) -> None:
    resultado = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-x",
            f"url=sqlite:///{ruta}",
            "upgrade",
            "head",
        ],
        cwd=RAIZ,
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
        raise SystemExit(resultado.stdout + resultado.stderr)

    import sqlite3

    conexion = sqlite3.connect(ruta)
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
        (BIBLIA_FALSA, datetime.now(UTC).isoformat()),
    )
    conexion.execute(
        "INSERT INTO parte (parte_id, obra_id, numero, funcion_estructural)"
        " VALUES ('pa1','o1',1,'planteamiento')"
    )
    conexion.execute(
        "INSERT INTO capitulo (capitulo_id, parte_id, numero, titulo)"
        " VALUES ('ca1','pa1',1,'La tregua')"
    )
    for i in range(1, ESCENAS + 1):
        conexion.execute(
            "INSERT INTO escena (escena_id, capitulo_id, version_obra_id,"
            " orden_discurso, tiempo_historia, pov, lugar, beat_de_genero)"
            " VALUES (?,?,?,?,?,'pj-ada','lug-taller',?)",
            (
                f"es{i}",
                "ca1",
                "vo1",
                i,
                f"dia-{i}",
                "encuentro" if i == 1 else "chispa",
            ),
        )
    conexion.commit()
    conexion.close()


def correr(real: bool, destino: Path | None = None) -> int:
    """Escribe ESCENAS escenas llamando al **mismo** ciclo que usara la API.

    Hasta P-111c este guion tenia el bucle dentro, 200 lineas que duplicaban lo
    que `features/escritura/service.py` deberia hacer. Dos copias del
    orquestador se desincronizan en cuanto alguien toca una: la real pasaba por
    el ensamblador de verdad y esta se fabricaba las capas a mano.
    """
    reloj = RelojDelSistema()
    cargador = CargadorDePrompts(PROMPTS)
    metricas = Metricas()

    if real:
        from app.commons.llm import ClienteDeClaudeCode, OrdenadorPorModelo

        planificador = ClienteDeClaudeCode(modelo="haiku")
        escritor = ClienteDeClaudeCode(modelo="haiku")
        extractor = ClienteDeClaudeCode(modelo="haiku")
        ordenador = OrdenadorPorModelo(
            ClienteDeClaudeCode(modelo="haiku"), cargador.cargar("ordenador").texto
        )
    else:
        planificador = DobleDeModelo([FICHA_FALSA] * ESCENAS)
        escritor = DobleDeModelo([PROSA_FALSA] * ESCENAS)
        extractor = DobleDeModelo([EXTRACCION_FALSA] * ESCENAS)
        ordenador = DobleDeOrdenador()

    # Con `--base` la base sobrevive a la corrida y se puede abrir con sqlite3
    # para mirar `hecho_canon`, `version_texto` y `ejecucion`. Sin ella va a un
    # temporal que se borra: es una demostracion, no un almacen.
    efimera = destino is None
    carpeta = Path(tempfile.mkdtemp(prefix="corrida-")) if efimera else destino.parent
    base = carpeta / "obra.db" if efimera else destino
    base.parent.mkdir(parents=True, exist_ok=True)
    if base.exists():
        base.unlink()
    preparar_base(base)

    dep = Dependencias(
        reloj=reloj,
        contador=ContadorBPE(),
        cargador=cargador,
        turno=TurnoDeModelo(simultaneas=1),
        cerrojo=CerrojoPorObra(),
        ordenador=ordenador,
        planificador=planificador,
        escritor=escritor,
        extractor=extractor,
        trabajos=RepositorioDeTrabajos(base),
        escenas=RepositorioDeEscenas(base),
        canon=RepositorioDeCanon(base),
        ejecuciones=RepositorioDeEjecuciones(base),
        obras=RepositorioDeObras(base),
        almacenes=AlmacenesDeLaObra(base),
    )

    print(
        f"{'REAL' if real else 'SECO'} · {ESCENAS} escenas · base {base}\n", flush=True
    )
    coste_total = 0.0

    for numero in range(1, ESCENAS + 1):
        escena_id = f"es{numero}"
        resultado = ciclo_de_escena(
            escena_id=escena_id, obra_id="o1", serie_id="s1", dep=dep
        )
        coste_total += resultado.coste
        metricas.anotar_escena(escena_id, resultado.coste, resultado.tokens_por_capa)
        if resultado.estado != "INTEGRADA":
            metricas.escalados += 1
            print(f"  {escena_id}: {resultado.estado} -> {resultado.defectos}")
            continue
        print(
            traza(
                "escena_integrada",
                escena_id=escena_id,
                tokens=sum(resultado.tokens_por_capa.values()),
                coste_usd=round(resultado.coste, 4),
            ),
            flush=True,
        )

    trabajos = dep.trabajos

    # --- resultado -----------------------------------------------------------
    manuscrito = RepositorioDeManuscrito(base).ensamblar("o1")
    integradas = sum(
        1 for t in [trabajos.leer(t.trabajo_id) for t in trabajos.vivos()] if False
    )
    import sqlite3

    with sqlite3.connect(base) as c:
        integradas = c.execute(
            "SELECT COUNT(*) FROM trabajo WHERE estado = 'INTEGRADA'"
        ).fetchone()[0]

    print(f"\nescenas INTEGRADA: {integradas}/{ESCENAS}")
    print(f"fragmentos en el manuscrito: {len(manuscrito.fragmentos)}")
    print(f"palabras: {len(manuscrito.texto.split())}")
    print(
        f"tokens medios por capa: "
        f"{ {k: round(sum(v) / len(v)) for k, v in metricas.tokens_por_capa.items()} }"
    )
    print(
        f"defectos: {metricas.defectos_por_codigo} · "
        f"mal formados: {metricas.tasa_de_defectos_mal_formados:.0%}"
    )
    print(f"escalados por cien escenas: {metricas.escalados_por_cien_escenas:.0f}")
    print(f"coste total: {coste_total:.4f} USD")

    salida = RAIZ / ("manuscrito-real.txt" if real else "manuscrito-seco.txt")
    salida.write_text(manuscrito.texto, encoding="utf-8")
    print(f"manuscrito escrito en {salida.name}")
    if efimera:
        shutil.rmtree(carpeta, ignore_errors=True)
    else:
        print(f"base conservada en {base} · abrela con: sqlite3 {base}")

    return 0 if integradas == ESCENAS else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--seco", action="store_true")
    grupo.add_argument("--real", action="store_true")
    parser.add_argument(
        "--base",
        type=Path,
        default=None,
        help="donde conservar la base; por defecto, un temporal que se borra",
    )
    argumentos = parser.parse_args()
    raise SystemExit(correr(real=argumentos.real, destino=argumentos.base))
