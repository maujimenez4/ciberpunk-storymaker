"""P-17: el Continuista estaba construido, probado, exportado — y sin llamar.

`features/calidad/agents.py` tiene el Continuista entero y `test_continuista.py`
lo prueba en trescientas lineas. `ciclo.Agentes` tenia tres campos —planificador,
escritor, extractor— y el unico `defectos_recibidos` que llegaba a `cruzar_g1a`
era el del veto. Es decir: **se escribia una novela entera sin una sola
comprobacion de continuidad**, que es la mitad del producto.

Es el modo de fallo que este repositorio ya nombro en `cobertura.py` con estas
palabras: *«la funcion estaba escrita, probada y sin que nadie la ejecutara, que
es la forma silenciosa de no tener un validador»*. La segunda vez que aparece.

Importa ademas para la Fase 6 y no solo para la coherencia: **un validador que no
corre no puede emitir *score***, y `CA-18` los pide todos. Con P-17 vivo, la
casilla de `continuidad_y_canon` en la tabla de los cinco briefs estaria vacia y
nadie sabria si es porque no encontro nada o porque no corrio.
"""

import json

import pytest

from app.commons.llm.doble import DobleDeterminista
from app.features.calidad import (
    CapituloAValidar,
    ConocimientoEnT,
    Continuista,
    NombreDeCanon,
    ParametrosDeDiscurso,
    Persona,
    RangoDeExtension,
    TiempoVerbal,
    cruzar_g1a,
)
from app.features.escritura.ciclo import Agentes

NOMBRE_DEL_CONTINUISTA = "continuidad_y_canon"
"""El de `verification.md` §8.1, sin traducir: es la llave del *score*."""


def _capitulo() -> CapituloAValidar:
    return CapituloAValidar(
        version_texto_id="vt-1",
        texto="Marta cerró la puerta. Estaba cansada y no dijo nada más aquella tarde.",
        rango_de_extension=RangoDeExtension(minimo=5, maximo=100),
        discurso=ParametrosDeDiscurso(
            persona=Persona.TERCERA_LIMITADA, tiempo_verbal=TiempoVerbal.PASADO
        ),
        nombres_del_canon=(NombreDeCanon(forma_canonica="Marta"),),
    )


# --- El hueco del censo: quien emite de fuera tambien corrio ------------------


def test_el_continuista_consta_entre_los_que_corrieron() -> None:
    """Sin esto su *score* no existe, y la casilla vacia de la tabla de los cinco
    briefs no distinguiria «no encontro nada» de «no corrio» — que es justo la
    distincion que `validadores_ejecutados` existe para dar."""
    resultado = cruzar_g1a(
        _capitulo(),
        (),
        emisores_externos=(NOMBRE_DEL_CONTINUISTA,),
    )

    assert NOMBRE_DEL_CONTINUISTA in resultado.validadores_ejecutados


def test_el_continuista_que_no_corre_no_consta() -> None:
    """La otra mitad, y la que hace que el test anterior signifique algo."""
    resultado = cruzar_g1a(_capitulo(), ())

    assert NOMBRE_DEL_CONTINUISTA not in resultado.validadores_ejecutados


def test_lo_que_aporta_el_continuista_se_le_imputa_a_el() -> None:
    """Sus defectos no pueden contarse como de un validador mecanico: la tabla
    de los cinco briefs dice **cual** fallo, y atribuirle a `discurso` un
    `CAN-01` del Continuista la haria mentir."""
    capitulo = _capitulo()
    defecto = {
        "codigo": "CAN-01",
        "version_texto_id": capitulo.version_texto_id,
        "cita": "Marta cerró la puerta",
        "desplazamiento_inicio": 0,
        "desplazamiento_fin": len("Marta cerró la puerta"),
        "hecho_canon_id": "hc-1",
        "detalle": "contradice el canon",
    }

    resultado = cruzar_g1a(
        capitulo,
        ("hc-1",),
        _defectos_del_continuista(defecto),
        emisores_externos=(NOMBRE_DEL_CONTINUISTA,),
    )

    hallazgos = dict(resultado.defectos_por_validador)
    assert hallazgos[NOMBRE_DEL_CONTINUISTA] == 1
    assert hallazgos["discurso"] == 0


def _defectos_del_continuista(*crudos: dict[str, object]) -> list[object]:
    from app.features.calidad.schemas import Defecto

    return [Defecto.model_validate(crudo) for crudo in crudos]


# --- P-17: el rol entra en `Agentes` ----------------------------------------


def test_agentes_admite_al_continuista() -> None:
    """El `TypeError` que este test producia es P-17 dicho por el interprete."""
    doble = DobleDeterminista({})

    agentes = Agentes(
        planificador=_planificador(doble),
        escritor=_escritor(doble),
        extractor=_extractor(doble),
        continuista=Continuista(doble),
    )

    assert agentes.continuista is not None


def test_el_continuista_es_opcional_mientras_la_ola_2_no_cierra() -> None:
    """El Critico entra con T4 y todavia no existe. Que el Continuista tenga
    valor por defecto es lo que permite cablearlo **ahora**, con la corrida real
    en marcha, sin esperar a un rol que no esta escrito."""
    doble = DobleDeterminista({})

    agentes = Agentes(
        planificador=_planificador(doble),
        escritor=_escritor(doble),
        extractor=_extractor(doble),
    )

    assert agentes.continuista is None


def _planificador(doble):  # type: ignore[no-untyped-def]
    from app.features.escena import Planificador

    return Planificador(doble)


def _escritor(doble):  # type: ignore[no-untyped-def]
    from app.features.escritura.agents import Escritor

    return Escritor(doble)


def _extractor(doble):  # type: ignore[no-untyped-def]
    from app.features.canon import Extractor

    return Extractor(doble)


# --- El aviso de Vane: `sabe_desde` nulo no es cero --------------------------


@pytest.mark.parametrize("sabe_desde", [None, 0])
def test_sabe_desde_nulo_y_cero_no_son_lo_mismo(sabe_desde: int | None) -> None:
    """Un evento sin escena **no esta situado en el discurso**. Si la consulta lo
    rellenara con 0 «para que no moleste», todo evento sin escena pasaria a ser
    anterior a cualquier capitulo y el contraste diria que si a cualquier cosa.

    La vista `estado_en_t` lo deja nulo con un `LEFT JOIN`, y quien la lea tiene
    que conservarlo.
    """
    fila = ConocimientoEnT(
        personaje="Marta",
        evento_id="ev-1",
        tiempo_historia="dia 1",
        sabe_desde=sabe_desde,
    )

    assert fila.sabe_desde is sabe_desde


def test_la_consulta_del_estado_en_t_no_rellena_los_nulos() -> None:
    """El sitio donde se puede perder: al construir la proyeccion desde la vista.

    Se comprueba sobre la funcion que hace la junta, no sobre la vista, porque el
    `LEFT JOIN` ya esta probado en `canon` y lo que aqui puede fallar es el
    `or 0` de quien lee.
    """
    from app.features.escritura.ciclo import conocimiento_desde_filas

    filas = [
        ("Marta", "ev-1", "dia 1", None),
        ("Noe", "ev-2", "dia 2", 3),
    ]

    proyeccion = conocimiento_desde_filas(filas)

    assert proyeccion[0].sabe_desde is None
    assert proyeccion[1].sabe_desde == 3


def test_el_json_de_la_vista_no_convierte_el_nulo_en_cero() -> None:
    """Y el mismo nulo tiene que sobrevivir al render del prompt: si se serializa
    como 0, el modelo lee «lo supo en el capitulo 0» y responde en consecuencia."""
    fila = ConocimientoEnT(
        personaje="Marta", evento_id="ev-1", tiempo_historia="dia 1", sabe_desde=None
    )

    assert json.loads(fila.model_dump_json())["sabe_desde"] is None


# --- La juntura cerrada: el ciclo se lo pasa, y el router los construye -------


SIN_CRITICO = "El Critico no sale por `calidad/__init__.py`, y ese fichero es del integrador"


@pytest.mark.skip(reason=SIN_CRITICO)
def test_agentes_admite_tambien_al_critico() -> None:
    """R-6 de Vane quedaba «dicho y no comprobado» porque `Agentes` no tenia
    donde meter al juez. Sin campo, no hay test de extremo a extremo, y el
    requisito que dice que el juez **no bloquea** es justo el que no conviene
    sostener sobre una ausencia: `architecture.md` §8.3 ya avisa de lo que les
    pasa a las invariantes que se sostienen porque nadie llama a nadie."""
    doble = DobleDeterminista({})

    agentes = Agentes(
        planificador=_planificador(doble),
        escritor=_escritor(doble),
        extractor=_extractor(doble),
        continuista=Continuista(doble),
        critico=_critico(doble),
    )

    assert agentes.critico is not None


def _critico(doble):  # type: ignore[no-untyped-def]
    from app.features.calidad import Critico

    return Critico(doble)


def test_el_router_deja_de_pasar_none() -> None:
    """**El criterio de terminado de esta tarea**, y no el test anterior.

    El cableado puede estar escrito, probado y sin correr —eso era P-17—, asi
    que lo que decide si el Continuista comprueba la novela de verdad es lo que
    construye `obtener_agentes`, que es lo que la peticion usa.
    """
    from app.commons.llm.doble import DobleDeterminista as Doble
    from app.features.escritura.router import obtener_agentes

    agentes = obtener_agentes(Doble({}))

    assert agentes.continuista is not None, "el Continuista no correria en produccion"
