"""El Escritor: la frontera con el modelo, y el único sitio donde vive.

`CLAUDE.md` §9.3. A diferencia del Arquitecto o el Extractor, **el Escritor no
devuelve JSON**: devuelve prosa, y no hay esquema contra el que validarla. Lo
que lo hace comprobable es lo de después —los validadores de `calidad`—, no un
contrato de forma.

Lo que sí se sostiene aquí es la invariante que importa (§9.1): **el Escritor
solo ve el paquete**. No recibe repositorios, ni la base de datos, ni la ficha:
recibe un texto. Si le falta un dato, el fallo es del ensamblado y no suyo, y
eso es lo que hace que un defecto sea atribuible.
"""

from app.commons.llm import ClienteDeModelo, RespuestaDeModelo


def invocar_escritor(cliente: ClienteDeModelo, paquete: str) -> RespuestaDeModelo:
    """RF-ORQ-16: el paquete entero y nada más."""
    return cliente.generar(paquete)
