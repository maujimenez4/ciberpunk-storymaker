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


class RecursoDesconocido(ErrorDeDominio):
    """Se pidio algo que no existe. El manejador central lo baja a **404**.

    Es una marca, no una excepcion que se lance tal cual: cada feature declara
    la suya —`ObraDesconocida`, `CapituloDesconocido`— y hereda de esta. El
    manejador vive en `commons/` y por el primer contrato de `import-linter`
    **no puede importar de ninguna feature**, asi que preguntar por la clase
    concreta obligaba a que `commons` conociera a quien no debe conocer. Con la
    marca, la dependencia va en el sentido correcto.

    Antes de existir, cada feature que anadia la suya respondia 409 en silencio
    —«el estado actual no admite esta peticion»— y eso paso dos veces.
    """


class EntrevistaDesconocida(RecursoDesconocido):
    """El id que se pide no es de ninguna entrevista.

    No estaba en el plan y entra con la Tarea 9 (ver Desviaciones): sin ella,
    un id inventado revienta con un `AttributeError` sobre `None` y el
    comprador recibe un 500 por haber escrito mal una URL. Es la unica de las
    tres que no se traduce a 409.
    """

    def __init__(self, entrevista_id: int) -> None:
        self.entrevista_id = entrevista_id
        super().__init__(f"No existe la entrevista {entrevista_id}")


class ContextBudgetExceeded(ErrorDeDominio):
    """Una capa del paquete no cabe en su tope y no se puede recortar.

    El nombre esta en ingles a proposito y no por descuido: es el literal de
    `CLAUDE.md` §4.1 y de RF-CTX-03, y cambiarlo por una traduccion propia seria
    exactamente lo que §2 prohibe. Se lanza **antes de llamar al modelo**: el
    paquete que no cabe no llega a gastarse (RF-CTX-02).

    `capa` es `str` y no el `Capa` de `features/contexto/`: `commons/` no importa
    de ninguna feature (primer contrato de `import-linter`), y `Capa` es un
    `StrEnum`, asi que quien la lanza pasa el miembro y quien la captura lee su
    valor sin necesitar el enum para nombrarlo.
    """

    def __init__(self, capa: str, tokens: int, tope: int) -> None:
        self.capa = str(capa)
        self.tokens = tokens
        self.tope = tope
        super().__init__(f"La capa {self.capa} no cabe en su tope: {tokens} tokens sobre {tope}")


class TiempoAgotado(ErrorDeDominio):
    """Un paso supero su plazo, o la espera de turno vencio (`architecture.md` §3.6).

    El trabajo pasa a `FALLIDA` con el paso anotado. Cuando la vence la espera
    de turno del presupuesto concurrente (`commons/jobs/turnos.py`), **no se
    llego a llamar al modelo**: es relanzable sin coste, y por eso el paso viene
    nombrado y no se resume en «se agoto el tiempo».

    Es una regla de negocio y no un fallo tecnico: el techo concurrente del
    encargo §7 se hace cumplir **esperando**, asi que agotar la espera es el
    desenlace previsto de esa regla, no una averia.
    """

    def __init__(self, paso: str, segundos: float | None = None) -> None:
        self.paso = paso
        self.segundos = segundos
        plazo = "sin plazo" if segundos is None else f"su plazo de {segundos} s"
        super().__init__(f"«{paso}» agoto {plazo}")
