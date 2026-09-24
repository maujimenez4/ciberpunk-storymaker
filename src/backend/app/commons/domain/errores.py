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


class BriefIncompleto(ErrorDeDominio):
    """Falta un dato obligatorio, y se dice **cual** (RF-ENT-03, CA-2).

    Los faltantes vienen nombrados a proposito: «falta algo» no deja volver a
    preguntar. Llegan de dos sitios distintos y se cuentan igual: los que
    nombra el Entrevistador —que ve datos que el esquema no exige, como los
    recuerdos_aportados— y los campos que `BriefEntrada` marca como `missing`.
    """

    def __init__(self, faltantes: list[str]) -> None:
        self.faltantes = list(faltantes)
        super().__init__(f"Faltan datos obligatorios del brief: {', '.join(self.faltantes)}")


class BriefContradictorio(ErrorDeDominio):
    """Dos respuestas validas por separado que no pueden ser ciertas a la vez.

    **El esquema no la ve** (RF-ENT-04): edad 8 y tono erotico validan los
    tipos. Quien la detecta es el Entrevistador; y tambien los validadores de
    `BriefEntrada` que no son de tipo sino de coherencia —la edad contra la
    fecha de nacimiento (R-7), el veto que choca con el nombre (R-8)—.

    `contradicciones` es una lista de diccionarios y no de objetos por una
    frontera: `Contradiccion` es el modelo de salida del Entrevistador y vive
    en `features/obra/agents.py`, de donde `commons/` no puede importar
    (primer contrato de `import-linter`). Duplicar la clase aqui seria tener
    dos formas del mismo concepto que pueden divergir; se lleva el dato plano,
    con las mismas dos claves: `campos` y `explicacion`.
    """

    def __init__(self, contradicciones: list[dict[str, object]]) -> None:
        self.contradicciones = list(contradicciones)
        super().__init__(f"El brief se contradice en {len(self.contradicciones)} punto(s)")


class EntrevistaDesconocida(ErrorDeDominio):
    """El id que se pide no es de ninguna entrevista.

    No estaba en el plan y entra con la Tarea 9 (ver Desviaciones): sin ella,
    un id inventado revienta con un `AttributeError` sobre `None` y el
    comprador recibe un 500 por haber escrito mal una URL. Es la unica de las
    tres que no se traduce a 409.
    """

    def __init__(self, entrevista_id: int) -> None:
        self.entrevista_id = entrevista_id
        super().__init__(f"No existe la entrevista {entrevista_id}")
