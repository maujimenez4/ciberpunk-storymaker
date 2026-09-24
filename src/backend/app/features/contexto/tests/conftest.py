"""El corpus de la Tarea 7: cinco escenas donde **lo parecido y lo pertinente difieren**.

Es la fixture que hace ejecutable R-5, y esta construida al reves de como sale
solo: la escena mas parecida al vector de consulta es justo la que **no** viene
a cuento, y ademas es **mas reciente** que la pertinente. Asi ni el parecido ni
la recencia pueden rescatarla: solo la descarta el filtro estructural.

Un corpus donde lo parecido coincidiera con lo pertinente pasaria el test sin
filtro ninguno, que es exactamente el fallo que la version anterior de la spec
escondio detras de un requisito «probado» (`CA-8`).

La dimension es 3 a proposito: un vector que se puede leer a ojo hace que el
test diga por que falla, y `vec_distance_cosine` no pide mas.
"""

from dataclasses import dataclass

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.db.vectores import empaquetar_vector, extension_disponible
from app.conftest import ObraConOutline
from app.features.canon import Embedding
from app.features.canon.modelos import HiloNarrativo
from app.features.escena.modelos import Escena


@pytest.fixture(autouse=True)
def _deteccion_sin_memoria():
    """La deteccion se cachea por proceso, y eso cruzaria tests entre si.

    Sin esto, el primer test que mire un modo deja decidido el de todos los
    demas, y peor: un test que falle a mitad se lleva por delante a los
    siguientes. Se limpia antes y despues, no solo despues.
    """
    extension_disponible.cache_clear()
    yield
    extension_disponible.cache_clear()


MODELO_DE_PRUEBA = "doble"

# El vector de consulta. Lo calcula el proveedor que genera y por eso llega
# desde fuera (ver Desviaciones); aqui se fija para que el test sea legible.
CONSULTA = [1.0, 0.0, 0.0]


@dataclass(frozen=True)
class Corpus:
    """Las cinco escenas del corpus, con nombre y no por indice."""

    obra_id: int
    fuera_de_rango: Escena
    pertinente: Escena
    parecida_e_impertinente: Escena
    pertinente_por_presentes: Escena
    pertinente_por_hilo: Escena
    hilo_abierto_id: int
    hilo_pagado_id: int


def _escena(base: ObraConOutline, capitulo_id: int, orden: int, **campos: object) -> Escena:
    """Una escena valida con lo minimo: los `CheckConstraint` de `escena` mandan."""
    valores: dict[str, object] = {
        "capitulo_id": capitulo_id,
        "version_obra_id": base.version_obra.id,
        "orden_discurso": orden,
        "tiempo_historia": f"dia {orden}",
        "pov": "Nadia",
        "lugar": "El invernadero",
        "presentes": ["Nadia", "Teo"],
        "objetivo_del_pov": "Que Teo confiese",
        "obstaculo": "Teo no habla",
        "resultado": "si-pero",
        "valor_entrada": "confianza",
        "valor_salida": "sospecha",
        "extension_objetivo": 1200,
        "densidad_de_dialogo_objetivo": 0.4,
        "distancia_psiquica": 3,
    }
    valores.update(campos)
    return Escena(**valores)


@pytest.fixture
async def corpus(sesion: AsyncSession, obra_con_outline: ObraConOutline) -> Corpus:
    capitulos = obra_con_outline.capitulos

    pertinente = _escena(obra_con_outline, capitulos[1].id, 2)
    parecida = _escena(
        obra_con_outline,
        capitulos[2].id,
        3,
        lugar="La azotea",
        pov="Bruno",
        presentes=["Bruno"],
    )
    por_presentes = _escena(
        obra_con_outline,
        capitulos[3].id,
        4,
        lugar="El muelle",
        presentes=["Nadia"],
    )
    por_hilo = _escena(
        obra_con_outline,
        capitulos[4].id,
        5,
        lugar="El sotano",
        pov="Ines",
        presentes=["Ines"],
    )
    sesion.add_all([pertinente, parecida, por_presentes, por_hilo])
    await sesion.flush()

    # `por_hilo` no comparte lugar ni presentes: entra **solo** por el hilo.
    hilo_abierto = HiloNarrativo(
        obra_id=obra_con_outline.obra.id,
        pregunta="Quien apago la luz del sotano",
        estado="abierto",
        escena_de_apertura=por_hilo.id,
    )
    # `parecida` tambien abre un hilo, pero **pagado**: un hilo cerrado no
    # vuelve a traer su escena, o el filtro crece con la obra en vez de acotarla.
    hilo_pagado = HiloNarrativo(
        obra_id=obra_con_outline.obra.id,
        pregunta="De quien era la azotea",
        estado="pagado",
        escena_de_apertura=parecida.id,
        escena_de_cierre=por_presentes.id,
    )
    sesion.add_all([hilo_abierto, hilo_pagado])
    await sesion.flush()

    vectores = {
        # Pertinente **y lejana** del vector de consulta: es la que tiene que
        # salir, y no por parecerse.
        obra_con_outline.escena.id: [1.0, 0.0, 0.0],
        pertinente.id: [0.0, 1.0, 0.0],
        # Identica a la consulta. Ordenar por parecido la pone la primera.
        parecida.id: [1.0, 0.0, 0.0],
        por_presentes.id: [0.6, 0.8, 0.0],
        por_hilo.id: [0.1, 0.0, 0.99],
    }
    sesion.add_all(
        [
            Embedding(
                obra_id=obra_con_outline.obra.id,
                escena_id=escena_id,
                fragmento=f"fragmento de la escena {escena_id}",
                vector=empaquetar_vector(vector),
                dimension=len(vector),
                modelo=MODELO_DE_PRUEBA,
            )
            for escena_id, vector in vectores.items()
        ]
    )
    await sesion.flush()

    return Corpus(
        obra_id=obra_con_outline.obra.id,
        fuera_de_rango=obra_con_outline.escena,
        pertinente=pertinente,
        parecida_e_impertinente=parecida,
        pertinente_por_presentes=por_presentes,
        pertinente_por_hilo=por_hilo,
        hilo_abierto_id=hilo_abierto.id,
        hilo_pagado_id=hilo_pagado.id,
    )
