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
from app.commons.db import RegistroDeEjecucion, RepositorioDeEjecuciones  # noqa: E402
from app.commons.domain import RelojDelSistema  # noqa: E402
from app.commons.jobs import (  # noqa: E402
    CerrojoPorObra,
    Estado,
    RepositorioDeTrabajos,
    TurnoDeModelo,
)
from app.commons.llm import (  # noqa: E402
    CargadorDePrompts,
    ContadorBPE,
    DobleDeModelo,
    DobleDeOrdenador,
)
from app.features.calidad import (  # noqa: E402
    pasar_g1a,
    validar_discurso,
    validar_giro_de_valor,
    validar_nivel_de_calor,
)
from app.features.canon import RepositorioDeCanon, extraer_de_escena  # noqa: E402
from app.features.contexto import (  # noqa: E402
    Capa,
    CapaEnsamblada,
    Pieza,
    ensamblar,
)
from app.features.escena import RepositorioDeEscenas, planificar_escena  # noqa: E402
from app.features.manuscrito import RepositorioDeManuscrito  # noqa: E402

RAIZ = Path(__file__).parent
PROMPTS = RAIZ / "src" / "backend" / "app" / "features"
ESCENAS = 10

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
        "resumen": "Ada intenta cerrar el trato y Noe se niega: control pasa a amenaza.",
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
        " VALUES ('vo1','o1',1,'{}',?)",
        (datetime.now(UTC).isoformat(),),
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
            " orden_discurso, tiempo_historia, pov) VALUES (?,?,?,?,?,'pj-ada')",
            (f"es{i}", "ca1", "vo1", i, f"dia-{i}"),
        )
    conexion.commit()
    conexion.close()


def _capas(escena_id: str, prompt: str, anterior: str | None) -> dict:
    """Las siete con contenido. En la corrida real las surten los almacenes;
    aqui basta con que ninguna llegue vacia, que es lo que RF-CTX-14 exige."""
    contenido = {
        Capa.CONSTITUCIONAL: "Obra en tercera persona, pasado, nivel sensual.",
        Capa.ESTRUCTURAL: "Capitulo 1, La tregua. Beat: encuentro.",
        Capa.CANON_RELEVANTE: "Ada: protagonista. Noe: coprotagonista.",
        Capa.ESTADO_EN_T: "Ada sabe lo del contrato. Noe no.",
        Capa.CONTINUIDAD_LOCAL: anterior or "Primera escena del capitulo.",
        Capa.MEMORIA_RECUPERADA: "El taller aparece en la escena inicial.",
        Capa.INSTRUCCION: prompt,
    }
    return {
        capa: CapaEnsamblada(capa=capa, piezas=[Pieza(texto, 0, capa.value)])
        for capa, texto in contenido.items()
    }


def correr(real: bool) -> int:
    reloj = RelojDelSistema()
    contador = ContadorBPE()
    cargador = CargadorDePrompts(PROMPTS)
    metricas = Metricas()
    turno = TurnoDeModelo(simultaneas=1)
    cerrojo = CerrojoPorObra()

    if real:
        from app.commons.llm import ClienteDeClaudeCode, OrdenadorPorModelo

        cliente_planificador = ClienteDeClaudeCode(modelo="haiku")
        cliente_escritor = ClienteDeClaudeCode(modelo="haiku")
        cliente_extractor = ClienteDeClaudeCode(modelo="haiku")
        ordenador = OrdenadorPorModelo(
            ClienteDeClaudeCode(modelo="haiku"), cargador.cargar("ordenador").texto
        )
    else:
        cliente_planificador = DobleDeModelo([FICHA_FALSA] * ESCENAS)
        cliente_escritor = DobleDeModelo([PROSA_FALSA] * ESCENAS)
        cliente_extractor = DobleDeModelo([EXTRACCION_FALSA] * ESCENAS)
        ordenador = DobleDeOrdenador()

    carpeta = Path(tempfile.mkdtemp(prefix="corrida-"))
    base = carpeta / "obra.db"
    preparar_base(base)

    trabajos = RepositorioDeTrabajos(base)
    escenas = RepositorioDeEscenas(base)
    canon = RepositorioDeCanon(base)
    ejecuciones = RepositorioDeEjecuciones(base)

    from app.commons.domain import NivelDeCalor, ParametrosDeDiscurso

    parametros = ParametrosDeDiscurso(
        persona="tercera",
        tiempo_verbal="pasado",
        esquema_de_pov="dual",
        nivel_de_calor=NivelDeCalor.SENSUAL,
    )

    print(f"{'REAL' if real else 'SECO'} · {ESCENAS} escenas · base {base}\n")
    anterior: str | None = None
    coste_total = 0.0

    for numero in range(1, ESCENAS + 1):
        escena_id = f"es{numero}"
        with cerrojo.en_uso("o1", espera_s=5) as tomado:
            if not tomado:
                raise SystemExit("no se pudo tomar el cerrojo de la obra")
            trabajo = trabajos.crear("o1", escena_id, "escribir_escena", reloj)
            run_id = trabajo.run_id

            # PLANIFICANDO
            p_plan = cargador.cargar("planificador")
            with turno.en_uso(espera_s=300) as hay_turno:
                if not hay_turno:
                    raise SystemExit("sin turno")
                ficha = planificar_escena(
                    escena_id, parametros, cliente_planificador, p_plan.texto, reloj
                )
            trabajos.transitar(trabajo.trabajo_id, Estado.ENSAMBLANDO, reloj)

            # ENSAMBLANDO
            p_escritor = cargador.cargar("escritor")
            instruccion = p_escritor.texto.format(
                persona=ficha.persona,
                tiempo_verbal=ficha.tiempo_verbal,
                pov=ficha.pov,
                nivel_de_calor=ficha.nivel_de_calor.value,
                extension_objetivo=ficha.extension_objetivo,
            )
            paquete = ensamblar(_capas(escena_id, instruccion, anterior), contador)
            trabajos.transitar(trabajo.trabajo_id, Estado.ESCRIBIENDO, reloj)

            # ESCRIBIENDO
            with turno.en_uso(espera_s=300) as hay_turno:
                if not hay_turno:
                    raise SystemExit("sin turno")
                respuesta = cliente_escritor.generar(paquete.texto)
            prosa = respuesta.texto
            version = escenas.guardar_version(escena_id, prosa, run_id, reloj)
            coste = float(respuesta.parametros.get("coste_usd") or 0)
            coste_total += coste
            ejecuciones.registrar(
                RegistroDeEjecucion(
                    run_id=run_id,
                    escena_id=escena_id,
                    prompt_id=p_escritor.prompt_id,
                    prompt_version=p_escritor.version,
                    prompt_hash=p_escritor.hash,
                    version_obra_id="vo1",
                    ids_recuperados=["frag-memoria"],
                    modelo=respuesta.modelo or "doble",
                    parametros={"tokens_salida": respuesta.tokens_salida},
                    semilla=None,
                    tokens_por_capa=paquete.desglose.por_capa,
                    coste=coste,
                    veredicto=None,
                ),
                reloj,
            )
            trabajos.transitar(trabajo.trabajo_id, Estado.VALIDANDO, reloj)

            # VALIDANDO (G1a, mecanica)
            defectos = [
                *validar_giro_de_valor(
                    ficha.valor_entrada,
                    ficha.valor_salida,
                    prosa,
                    version.version_texto_id,
                ),
                *validar_nivel_de_calor(
                    prosa, ficha.nivel_de_calor.value, version.version_texto_id
                ),
                *validar_discurso(
                    prosa, ficha.persona, ficha.tiempo_verbal, version.version_texto_id
                ),
            ]
            veredicto = pasar_g1a(defectos, prosa, set())
            for defecto in [
                *veredicto.bloquean,
                *veredicto.no_bloquean,
                *veredicto.mal_formados,
            ]:
                metricas.anotar_defecto(defecto.codigo.value, defecto.bien_formado)

            if not veredicto.aprobada:
                print(
                    f"  es{numero}: G1a rechaza -> "
                    f"{[d.codigo.value for d in veredicto.bloquean]}"
                )
                trabajos.transitar(
                    trabajo.trabajo_id,
                    Estado.REPARANDO,
                    reloj,
                    causa_fallo="DefectoBloqueante",
                    incrementa_intento=True,
                )
                trabajos.transitar(trabajo.trabajo_id, Estado.ESCALADA, reloj)
                metricas.escalados += 1
                continue

            trabajos.transitar(trabajo.trabajo_id, Estado.EXTRAYENDO, reloj)

            # EXTRAYENDO
            with turno.en_uso(espera_s=300) as hay_turno:
                if not hay_turno:
                    raise SystemExit("sin turno")
                extraer_de_escena(
                    serie_id="s1",
                    escena_id=escena_id,
                    version_texto_id=version.version_texto_id,
                    cliente=cliente_extractor,
                    prompt=cargador.cargar("extractor").texto,
                    repositorio=canon,
                    reloj=reloj,
                )
            canon.crear_snapshot_si_toca(escena_id, 5, reloj)
            trabajos.transitar(trabajo.trabajo_id, Estado.INTEGRADA, reloj)

        metricas.anotar_escena(escena_id, coste, paquete.desglose.por_capa)
        anterior = prosa
        _ = ordenador  # se usará cuando la recuperación lea fragmentos reales
        print(
            traza(
                "escena_integrada",
                escena_id=escena_id,
                tokens=paquete.desglose.total,
                coste_usd=round(coste, 4),
            )
        )

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
    shutil.rmtree(carpeta, ignore_errors=True)

    return 0 if integradas == ESCENAS else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--seco", action="store_true")
    grupo.add_argument("--real", action="store_true")
    argumentos = parser.parse_args()
    raise SystemExit(correr(real=argumentos.real))
