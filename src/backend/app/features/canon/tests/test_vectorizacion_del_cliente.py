"""La juntura que T1 dejo abierta: del `ClienteModelo` al indice, sin adivinar.

T1 cerro la deuda -- `ClienteModelo.vectorizar` existe y lo implementan el real
y el doble con **la misma funcion** -- y dejo escrito en Desviaciones que nadie
se lo pasaba a `consolidar_escena`, asi que el indice seguia vacio. La
traduccion que faltaba es de una linea: `Vectorizacion` repite a proposito los
tres campos de `canon.Vector`, porque `commons/` no puede importar de una
feature (primer contrato de `import-linter`).

**Esa linea vive aqui y no en quien orquesta**, y es una decision: escrita en
cada sitio donde se llame al ciclo, se escribiria mal en alguno, y el error
seria un indice lleno de vectores con el `modelo` equivocado -- que no rompe
nada hoy y hace incomparables los vectores manana. Escrita una vez, tiene test.
"""

from app.commons.llm.cliente import DIMENSION_DEL_VECTOR, MODELO_DEL_VECTOR, vectorizar_texto
from app.commons.llm.doble import DobleDeterminista
from app.features.canon import Vector, vectorizador_de


def test_el_vectorizador_traduce_los_tres_campos_sin_recalcular_nada() -> None:
    """Traduce, no vectoriza: el vector es **el mismo** que el del cliente.

    Si esto recalculara por su cuenta habria dos vectorizadores en el sistema y
    el dia que uno cambiara, el indice tendria vectores de dos familias sin que
    nada fallara.
    """
    cliente = DobleDeterminista({})

    vector = vectorizador_de(cliente)("Nadia abrio la puerta del invernadero")

    esperado = cliente.vectorizar("Nadia abrio la puerta del invernadero")
    assert isinstance(vector, Vector)
    assert vector.datos == esperado.datos
    assert vector.dimension == esperado.dimension
    assert vector.modelo == esperado.modelo


def test_lo_que_indexa_la_suite_es_lo_que_indexara_produccion() -> None:
    """El doble y el cliente real comparten implementacion (T1), y esto lo usa.

    Por eso el test puede afirmar la dimension y el **modelo** literales: no son
    los del doble, son los del sistema, y van a `embedding.modelo`, que es lo
    unico que permitira saber que vectores son comparables entre si.
    """
    vector = vectorizador_de(DobleDeterminista({}))("Nadia abrio la puerta")

    assert vector.dimension == DIMENSION_DEL_VECTOR
    assert vector.modelo == MODELO_DEL_VECTOR
    assert vector.datos == vectorizar_texto("Nadia abrio la puerta").datos
