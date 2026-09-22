"""P-32, P-33, P-35, P-36, P-39 a P-42: el paso EXTRAYENDO completo.

RF-CAN-01 a RF-CAN-04, RF-CAN-07, RF-CAN-08, RF-CAN-10, RF-CAN-12 y RD-13.

La regla que gobierna el paso: **una escena rechazada no deja rastro**. Si un
borrador que nunca llego al manuscrito dejara hechos en canon, el canon se
contaminaria con afirmaciones de texto que no existe, y el sintoma apareceria
capitulos despues como una contradiccion imposible de explicar.
"""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.commons.db import DobleDeEmbeddings
from app.commons.domain import RelojFijo
from app.commons.llm import DobleDeModelo
from app.features.canon import (
    ExtraccionInvalida,
    RepositorioDeCanon,
    extraer_de_escena,
)

EXTRACCION = {
    "hechos": [
        {"entidad": "Ada", "atributo": "ojos", "valor": "verdes"},
        {"entidad": "taller", "atributo": "olor", "valor": "ozono"},
    ],
    "eventos": [
        {
            "descripcion": "Ada ve la grieta del muro",
            "testigos": ["pj-ada"],
            "participantes": ["pj-ada", "pj-noe"],
        }
    ],
    "resumen": "Ada descubre la grieta y calla.",
    "hilos": [
        {"pregunta": "Que hay detras del muro?", "estado": "abierto"},
    ],
    "plantados": [
        {"importancia": "alta", "descripcion": "la grieta"},
    ],
    "ngramas_gastados": ["la grieta del muro"],
}


@pytest.fixture
def reloj() -> RelojFijo:
    return RelojFijo(datetime(2026, 9, 22, tzinfo=UTC))


@pytest.fixture
def repositorio(base_de_datos: Path) -> RepositorioDeCanon:
    return RepositorioDeCanon(base_de_datos)


@pytest.fixture
def escena(base_de_datos: Path) -> str:
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
    conexion.execute(
        "INSERT INTO version_texto (version_texto_id, escena_id, texto, vigente,"
        " run_id, autoria, creada_en) VALUES ('vt1','es1','La grieta del muro.',1,"
        "'run-1','generado','2026-09-22')"
    )
    conexion.commit()
    conexion.close()
    return "es1"


def _extraer(
    repositorio: RepositorioDeCanon,
    escena: str,
    reloj: RelojFijo,
    salida: dict[str, object] | str = EXTRACCION,
) -> object:
    texto = salida if isinstance(salida, str) else json.dumps(salida)
    return extraer_de_escena(
        serie_id="s1",
        escena_id=escena,
        version_texto_id="vt1",
        cliente=DobleDeModelo([texto]),
        prompt="prompt del extractor",
        repositorio=repositorio,
        embeddings=DobleDeEmbeddings(8),
        reloj=reloj,
    )


def test_todo_hecho_cita_su_escena_de_origen(
    repositorio: RepositorioDeCanon, escena: str, reloj: RelojFijo
) -> None:
    """RF-CAN-04."""
    _extraer(repositorio, escena, reloj)

    hechos = repositorio.hechos_de_escena(escena)

    assert len(hechos) == 2
    assert all(h.escena_de_origen == escena for h in hechos)


def test_la_escritura_ocurre_en_el_orden_declarado(
    repositorio: RepositorioDeCanon, escena: str, reloj: RelojFijo
) -> None:
    """P-36, §4.4: canon -> ledger -> resumen -> hilos -> embeddings.

    El orden importa porque los hilos citan escenas y los embeddings citan
    versiones de texto: invertirlo dejaria referencias colgando dentro de la
    misma transaccion.
    """
    resultado = _extraer(repositorio, escena, reloj)

    assert resultado.orden_de_escritura == [  # type: ignore[attr-defined]
        "canon",
        "ledger",
        "resumen",
        "hilos",
        "embeddings",
    ]


class EmbeddingsQueFallan:
    """Revienta al incrustar: es el **ultimo** paso de la consolidacion.

    Es el unico doble que prueba de verdad RF-CAN-03. Un fallo de validacion no
    sirve: se detecta antes de abrir la transaccion, asi que el test pasaria sin
    que hubiera transaccion ninguna.
    """

    def incrustar(self, texto: str) -> object:
        raise RuntimeError("el proveedor de embeddings se cayo")


def test_una_escena_rechazada_no_deja_rastro(
    repositorio: RepositorioDeCanon, escena: str, reloj: RelojFijo
) -> None:
    """RF-CAN-02 y RF-CAN-03: o entra todo, o no entra nada.

    El fallo se fuerza en el ultimo paso, cuando el canon, el ledger, el resumen
    y los hilos **ya estan escritos**. Es el caso peligroso: sin transaccion, la
    escena rechazada dejaria hechos en el canon y el sintoma apareceria capitulos
    despues como una contradiccion que nadie sabe explicar.
    """
    with pytest.raises(RuntimeError):
        extraer_de_escena(
            serie_id="s1",
            escena_id=escena,
            version_texto_id="vt1",
            cliente=DobleDeModelo([json.dumps(EXTRACCION)]),
            prompt="p",
            repositorio=repositorio,
            embeddings=EmbeddingsQueFallan(),  # type: ignore[arg-type]
            reloj=reloj,
        )

    assert repositorio.hechos_de_escena(escena) == []
    assert repositorio.eventos_de_escena(escena) == []
    assert repositorio.resumen_de("escena", escena) is None
    assert repositorio.hilos_abiertos() == []
    assert repositorio.fragmentos_de(escena) == []


def test_una_salida_que_no_valida_no_llega_a_tocar_la_base(
    repositorio: RepositorioDeCanon, escena: str, reloj: RelojFijo
) -> None:
    with pytest.raises(ExtraccionInvalida):
        _extraer(repositorio, escena, reloj, "no soy json")

    assert repositorio.hechos_de_escena(escena) == []


def test_el_resumen_de_escena_se_genera_al_integrarla(
    repositorio: RepositorioDeCanon, escena: str, reloj: RelojFijo
) -> None:
    """RF-CAN-08."""
    _extraer(repositorio, escena, reloj)

    assert repositorio.resumen_de("escena", escena) == "Ada descubre la grieta y calla."


def test_se_registran_plantados_e_hilos_pero_no_se_auditan(
    repositorio: RepositorioDeCanon, escena: str, reloj: RelojFijo
) -> None:
    """RF-CAN-10: la v1 los **registra**. Auditarlos es la fase 5."""
    _extraer(repositorio, escena, reloj)

    assert repositorio.hilos_abiertos() == ["Que hay detras del muro?"]
    assert not hasattr(repositorio, "auditar_plantados")


def test_el_extractor_escribe_la_lista_negra_de_ngramas(
    repositorio: RepositorioDeCanon, escena: str, reloj: RelojFijo
) -> None:
    """RD-13. Nadie la lee en la v1: su consumidor es el Editor de linea."""
    _extraer(repositorio, escena, reloj)

    assert "la grieta del muro" in repositorio.ngramas_vetados("o1")


def test_el_indice_vectorial_se_reconstruye_entero_desde_el_texto(
    repositorio: RepositorioDeCanon, escena: str, reloj: RelojFijo
) -> None:
    """RF-CAN-12. Es lo que hace barato cambiar de proveedor de embeddings: el
    coste es un reindexado, no una migracion rota."""
    _extraer(repositorio, escena, reloj)
    antes = repositorio.fragmentos_de(escena)

    repositorio.reconstruir_indice(DobleDeEmbeddings(8))

    assert repositorio.fragmentos_de(escena) == antes


def test_corregir_un_hecho_registra_uno_nuevo_y_cita_al_anterior(
    repositorio: RepositorioDeCanon, escena: str, reloj: RelojFijo
) -> None:
    """RF-CAN-07 y P-33: el hecho viejo sigue ahi, y por eso se puede encontrar
    la escena que se apoyo en el."""
    _extraer(repositorio, escena, reloj)
    viejo = repositorio.hechos_de_escena(escena)[0]

    nuevo = repositorio.sustituir_hecho(
        "s1", escena, viejo.hc_id, viejo.entidad, viejo.atributo, "grises"
    )

    assert nuevo.sustituye_a == viejo.hc_id
    assert repositorio.leer_hecho(viejo.hc_id).valor == "verdes"
