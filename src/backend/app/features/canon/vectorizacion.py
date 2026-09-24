"""Del `ClienteModelo` al indice: la unica traduccion, escrita una sola vez.

**Por que hace falta una traduccion.** `commons/llm/cliente.py` devuelve
`Vectorizacion` y `consolidar_escena` recibe `Vector`, y los dos tienen los
mismos tres campos a proposito: `commons/` **no puede importar de una feature**
(primer contrato de `import-linter`, `CLAUDE.md` §5.1), asi que el contrato del
cliente no puede hablar del tipo del canon. T1 lo dejo dicho al cerrar la deuda:
«`Vectorizacion` repite a proposito los tres campos de `canon.Vector` para que
la traduccion sea una».

**Por que vive aqui y no en quien orquesta.** El indice vectorial lo escribe el
Extractor y la tabla es de esta feature (`architecture.md` §4.3): esta es la
casa del tipo de destino. Repetida en cada sitio que ejecute un ciclo, la linea
acabaria escrita mal en alguno, y el sintoma seria un `embedding.modelo`
equivocado -- que no rompe nada hoy y hace incomparables los vectores manana,
que es la peor forma de fallo que tiene este sistema.

**Lo que esto NO hace: vectorizar.** No hay aqui ningun calculo: el vector es el
que produce el cliente, y el cliente real y `DobleDeterminista` comparten
implementacion (T1). Es lo que hace que lo que la suite indexa sea lo que
produccion indexara.
"""

from collections.abc import Callable

from app.commons.llm.cliente import ClienteModelo
from app.features.canon.schemas import Vector


def vectorizador_de(cliente: ClienteModelo) -> Callable[[str], Vector]:
    """El `vectorizar` que `consolidar_escena` espera, sacado del cliente.

    Se devuelve una funcion y no se pide el cliente en cada llamada porque asi
    es como `consolidar_escena` lo declara desde la Fase 2 -- `Callable[[str],
    Vector]`, inyectado --, y ese hueco existe para que consolidar una escena no
    dependa de que la extension vectorial cargue (R-6, RNF-FIA-02).
    """

    def vectorizar(texto: str) -> Vector:
        vectorizacion = cliente.vectorizar(texto)
        return Vector(
            datos=vectorizacion.datos,
            dimension=vectorizacion.dimension,
            modelo=vectorizacion.modelo,
        )

    return vectorizar
