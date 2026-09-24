"""Excepciones de dominio. Aqui no entra FastAPI ni SQLAlchemy.

Es lo que permite que un servicio diga *que* salio mal sin decidir con que
codigo HTTP se cuenta: esa traduccion la hace el handler central de
`commons/errors/` y la hace en un solo sitio (`CLAUDE.md` §6). Un
`HTTPException` dentro de un servicio ata el dominio al transporte y deja el
caso de uso sin poder probarse fuera de una peticion.

`commons/domain/` se prueba sin base de datos y sin framework, y el segundo
contrato de `import-linter` lo impone: cualquier import de `fastapi`,
`sqlalchemy` o `httpx` en este arbol rompe la build.

De `ErrorDeDominio` cuelgan las excepciones que anaden las tareas siguientes:
`OperacionNoPermitida` (T10), `BriefIncompleto` y `BriefContradictorio` (T9).
Tener la raiz desde el principio es lo que permite que el handler central
registre **una** regla de traduccion en vez de una por excepcion.
"""


class ErrorDeDominio(Exception):
    """Raiz de todo error que el dominio sabe nombrar.

    Un fallo que no hereda de aqui es un fallo del sistema, no una regla de
    negocio que se haya incumplido, y no se traduce a una respuesta: se
    propaga.
    """


class OperacionNoPermitida(ErrorDeDominio):
    """La operacion existe, se entiende, y el dominio la prohibe.

    No es un fallo de permisos ni de validacion de entrada: es una regla de
    negocio que dice que **eso no se hace**, con los datos correctos y quien
    sea que lo pida. Hoy la lanza `borrar_auditoria` (`commons/db/auditoria.py`),
    porque el registro de auditoria es *append-only* (RF-GUA-05): borrar una
    fila es exactamente lo que ese registro existe para impedir.

    Vive aqui, y no junto a la tabla, porque `commons/domain/` se prueba sin
    base de datos: quien captura la excepcion no tiene por que importar
    SQLAlchemy para nombrarla.
    """
