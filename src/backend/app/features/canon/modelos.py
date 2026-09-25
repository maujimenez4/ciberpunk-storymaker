"""Las tablas de `canon`: el ledger, lo que crece con la obra, y las dos vistas.

Esta feature es la que sostiene la memoria de largo plazo, y la columna que
importa de `architecture.md` §4.3 es la tercera: **solo el Extractor escribe
aqui**, y solo desde el paso `EXTRAYENDO`. Ningun otro agente deja rastro
permanente.

Dos cosas de este modulo no son tablas y conviene decirlo arriba:

- **El ledger es una pared, no un cartel.** `evento` rechaza `UPDATE` y `DELETE`
  con disparadores `RAISE(ABORT)`. La Fase 1 dejo el registro de auditoria con
  ese contrato sostenido por una funcion que se niega, lo anoto en Desviaciones,
  y aqui no se repite: una funcion que se niega solo protege de quien la llame.
- **`estado_en_t` y la cronologia son vistas.** No hay modelo que las mapee, no
  entran en `Base.metadata` y no hay repositorio que las escriba, porque no hay
  tabla sobre la que escribir (RF-MEM-03, RF-MEM-05, regla de dominio 3).
"""

from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    ForeignKey,
    LargeBinary,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapped, mapped_column

from app.commons.db.base import Base

# `definitions.md` §4.5. Conjuntos cerrados.
ESTADOS_DE_HILO = ("abierto", "pagado", "vencido")
IMPORTANCIAS_DE_PLANTADO = ("alta", "media", "decorativa")


class Evento(Base):
    """El ledger: log *append-only* de eventos confirmados (`definitions.md` §7).

    Es la fuente de la que se derivan el estado en T y la cronologia. Por eso
    no se actualiza ni se borra: un ledger del que se puede quitar una fila no
    acredita nada, porque lo que falta no se distingue de lo que nunca paso.

    `testigos[]` es la columna clave y no un adorno: de ella se deriva quien
    puede saber el hecho despues, que es el mecanismo que evita que un personaje
    use informacion que no deberia tener (regla de dominio 2).

    `excluye[]` son los personajes que dejan de poder aparecer -- una muerte, una
    partida definitiva --. Sin este campo, «que nadie reaparezca despues de
    morir» no es comprobable: es un juicio de lectura.

    `escena_id` es nulo a proposito: hay eventos que existen **antes** del
    texto, porque vienen del brief.
    """

    __tablename__ = "evento"

    id: Mapped[int] = mapped_column(primary_key=True)
    obra_id: Mapped[int] = mapped_column(ForeignKey("obra.id", name="fk_evento_obra_id"))
    escena_id: Mapped[int | None] = mapped_column(
        ForeignKey("escena.id", name="fk_evento_escena_id")
    )
    descripcion: Mapped[str] = mapped_column(Text)
    tiempo_historia: Mapped[str] = mapped_column(String(120))
    lugar: Mapped[str | None] = mapped_column(String(200))
    participantes: Mapped[list[str]] = mapped_column(JSON, default=list)
    testigos: Mapped[list[str]] = mapped_column(JSON, default=list)
    causa: Mapped[list[str]] = mapped_column(JSON, default=list)
    consecuencia: Mapped[list[str]] = mapped_column(JSON, default=list)
    excluye: Mapped[list[str]] = mapped_column(JSON, default=list)
    sustituye_a: Mapped[int | None] = mapped_column(
        ForeignKey("evento.id", name="fk_evento_sustituye_a")
    )
    """El evento que este corrige. **Corregir no edita** (`CLAUDE.md` §4.2): un
    evento mal extraido no se actualiza --el disparador lo impide--; se registra
    otro que lo cita, y las vistas solo ven el vigente. Corrida real, obra 3: el
    Extractor anoto «cruza el salon hacia la salida» como partida definitiva.
    """
    run_id: Mapped[str | None] = mapped_column(String(60), index=True)
    """Que corrida lo escribio (P-6).

    **Nulo a proposito:** las filas anteriores a esta migracion no tienen
    ninguno y no se les puede inventar, y un evento del brief no lo escribe
    ninguna corrida.
    """


class ResumenCapitulo(Base):
    """Sintesis de un capitulo ya integrado, que alimenta el contexto (RF-MEM-04).

    **Se deriva del texto aprobado**, no se escribe aparte: `version_texto_id`
    dice de cual. Uno por capitulo -- dos serian dos verdades sobre lo mismo --.
    """

    __tablename__ = "resumen_capitulo"
    __table_args__ = (UniqueConstraint("capitulo_id", name="uq_resumen_capitulo_capitulo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    capitulo_id: Mapped[int] = mapped_column(
        ForeignKey("capitulo.id", name="fk_resumen_capitulo_capitulo_id")
    )
    version_texto_id: Mapped[int | None] = mapped_column(
        ForeignKey("version_texto.id", name="fk_resumen_capitulo_version_texto_id")
    )
    texto: Mapped[str] = mapped_column(Text)
    hechos_establecidos: Mapped[list[str]] = mapped_column(JSON, default=list)
    hilos_abiertos: Mapped[list[str]] = mapped_column(JSON, default=list)


class HiloNarrativo(Base):
    """Pregunta abierta que el lector arrastra: abierto, pagado o vencido.

    El segundo `CheckConstraint` es el que tiene contenido: un hilo «pagado»
    sin escena de cierre es una promesa dada por cumplida sin cumplirla, y el
    estado sirve justo para saber que queda por cerrar antes del final.
    """

    __tablename__ = "hilo_narrativo"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('abierto', 'pagado', 'vencido')", name="ck_hilo_narrativo_estado"
        ),
        CheckConstraint(
            "estado <> 'pagado' OR escena_de_cierre IS NOT NULL",
            name="ck_hilo_narrativo_pagado_con_cierre",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    obra_id: Mapped[int] = mapped_column(ForeignKey("obra.id", name="fk_hilo_narrativo_obra_id"))
    pregunta: Mapped[str] = mapped_column(String(500))
    estado: Mapped[str] = mapped_column(String(10), default="abierto")
    escena_de_apertura: Mapped[int | None] = mapped_column(
        ForeignKey("escena.id", name="fk_hilo_narrativo_escena_de_apertura")
    )
    escena_de_cierre: Mapped[int | None] = mapped_column(
        ForeignKey("escena.id", name="fk_hilo_narrativo_escena_de_cierre")
    )


class Plantado(Base):
    """Dato sembrado sin explicar, destinado a cobrarse mas adelante.

    `importancia` decide si el `Pago` es obligatorio: todo plantado de
    importancia alta necesita pago antes del final (`definitions.md` §11,
    axioma 2). Esa comprobacion es del Auditor y no de esta tabla, que solo
    garantiza que la importancia sea una de las tres.
    """

    __tablename__ = "plantado"
    __table_args__ = (
        CheckConstraint(
            "importancia IN ('alta', 'media', 'decorativa')", name="ck_plantado_importancia"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    obra_id: Mapped[int] = mapped_column(ForeignKey("obra.id", name="fk_plantado_obra_id"))
    descripcion: Mapped[str] = mapped_column(String(500))
    importancia: Mapped[str] = mapped_column(String(12))
    escena_de_origen: Mapped[int] = mapped_column(
        ForeignKey("escena.id", name="fk_plantado_escena_de_origen")
    )
    escena_de_pago_prevista: Mapped[int | None] = mapped_column(
        ForeignKey("escena.id", name="fk_plantado_escena_de_pago_prevista")
    )


class HechoUsadoEn(Base):
    """En que capitulos se apoya un hecho de canon (RF-MEM-02).

    Es la relacion **hacia adelante**, y por eso no se deriva de
    `escena_de_origen`: un hecho sabia de donde vino y no a donde fue. Sin esto,
    «el perro se llama Nala, no Luna» no se puede atender, porque no hay forma
    de saber que capitulos hay que rehacer.

    La clave primaria es el par: registrar dos veces el mismo uso
    sobre-reportaria que hay que regenerar. La escribe quien **integra** el
    capitulo, no quien crea el hecho.
    """

    __tablename__ = "hecho_usado_en"
    __table_args__ = (
        PrimaryKeyConstraint("hecho_canon_id", "capitulo_id", name="pk_hecho_usado_en"),
    )

    hecho_canon_id: Mapped[int] = mapped_column(
        ForeignKey("hecho_canon.id", name="fk_hecho_usado_en_hecho_canon_id")
    )
    capitulo_id: Mapped[int] = mapped_column(
        ForeignKey("capitulo.id", name="fk_hecho_usado_en_capitulo_id")
    )


class VarianteDeNombre(Base):
    """Como se le puede llamar a alguien ademas de por su forma canonica (RF-VAL-03).

    **Es lo que `CA-16` pedia y no existia.** El validador `nombres_literales`
    sabe distinguir la forma canonica de una variante declarada desde la Fase 2
    -- `NombreDeCanon` tiene el campo --, pero no habia donde declararlas, asi
    que llegaban siempre vacias: «Mari» por «María» no se rechazaba por
    incompatible, se rechazaba porque nadie la habia dado. La diferencia entre
    un error de grafia y un apodo tiene que estar **en el canon**, no en la
    astucia del validador.

    `forma_canonica` es texto y no una clave ajena: el canon no tiene tabla de
    entidades -- los nombres salen de `hecho_canon.entidad` --, y una clave
    ajena a una tabla que no existe no se puede escribir. Queda anotado.

    El `CheckConstraint` es R-2 de la Fase 1 otra vez: una variante en blanco
    es subcadena de cualquier cosa, y daria por declarado cualquier nombre.
    """

    __tablename__ = "variante_de_nombre"
    __table_args__ = (
        UniqueConstraint("obra_id", "forma_canonica", "variante", name="uq_variante_de_nombre"),
        CheckConstraint("length(trim(variante)) > 0", name="ck_variante_de_nombre_no_vacia"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    obra_id: Mapped[int] = mapped_column(
        ForeignKey("obra.id", name="fk_variante_de_nombre_obra_id")
    )
    forma_canonica: Mapped[str] = mapped_column(String(120))
    variante: Mapped[str] = mapped_column(String(120))


class Embedding(Base):
    """Un fragmento con su vector, detras de la interfaz `VectorStore`.

    `architecture.md` §5.5 admite dos implementaciones: `vec0` de `sqlite-vec`,
    o BLOB mas NumPy. Esta tabla es la segunda, que es la que hace que el
    sistema arranque en una maquina sin la extension (RNF-FIA-02, CA-28). El
    indice es **regenerable entero** desde el texto: si se pierde, no se pierde
    canon.
    """

    __tablename__ = "embedding"

    id: Mapped[int] = mapped_column(primary_key=True)
    obra_id: Mapped[int] = mapped_column(ForeignKey("obra.id", name="fk_embedding_obra_id"))
    escena_id: Mapped[int | None] = mapped_column(
        ForeignKey("escena.id", name="fk_embedding_escena_id")
    )
    fragmento: Mapped[str] = mapped_column(Text)
    vector: Mapped[bytes] = mapped_column(LargeBinary)
    dimension: Mapped[int]
    modelo: Mapped[str] = mapped_column(String(60))


# ---------------------------------------------------------------------------
# El ledger, en el esquema (RF-MEM-05)
# ---------------------------------------------------------------------------

SQL_EVENTO_SIN_UPDATE = """
CREATE TRIGGER IF NOT EXISTS trg_evento_sin_update
BEFORE UPDATE ON evento
BEGIN
    SELECT RAISE(ABORT, 'El ledger es append-only: un evento no se actualiza.');
END;
"""

SQL_EVENTO_SIN_DELETE = """
CREATE TRIGGER IF NOT EXISTS trg_evento_sin_delete
BEFORE DELETE ON evento
BEGIN
    SELECT RAISE(ABORT, 'El ledger es append-only: un evento no se borra.');
END;
"""

# ---------------------------------------------------------------------------
# Las dos vistas derivadas (RF-MEM-03, RF-MEM-05, regla de dominio 3)
# ---------------------------------------------------------------------------

# Son vistas y no tablas por una razon dura: escritas a mano serian una segunda
# verdad sobre quien sabe que y sobre cuando paso cada cosa, y divergirian del
# texto sin que nada lo detectara. Como vistas **no se pueden escribir**, asi
# que la imposibilidad no depende de que nadie escriba el repositorio.
#
# `json_each` expande `testigos[]` sin una tabla puente: es lo que permite que
# «quien sabe que» se derive del ledger en vez de mantenerse aparte.
SQL_VISTA_ESTADO_EN_T = """
CREATE VIEW IF NOT EXISTS estado_en_t AS
SELECT ev.obra_id      AS obra_id,
       t.value         AS personaje,
       ev.id           AS evento_id,
       ev.tiempo_historia AS tiempo_historia,
       esc.orden_discurso AS sabe_desde
FROM evento ev
JOIN json_each(ev.testigos) t
LEFT JOIN escena esc ON esc.id = ev.escena_id
WHERE NOT EXISTS (SELECT 1 FROM evento s WHERE s.sustituye_a = ev.id);
"""

# La cronologia es la entrada del validador formal (`definitions.md` §4.4), que
# necesita leerla entera y de una vez en lugar de recorrer el ledger. Sigue
# siendo una proyeccion: no anade ni un dato que el ledger no tenga.
SQL_VISTA_CRONOLOGIA = """
CREATE VIEW IF NOT EXISTS cronologia AS
SELECT ev.id            AS evento_id,
       ev.obra_id       AS obra_id,
       ev.tiempo_historia AS tiempo_historia,
       ev.lugar         AS lugar,
       ev.participantes AS participantes,
       ev.testigos      AS testigos,
       ev.excluye       AS excluye,
       esc.orden_discurso AS orden_discurso
FROM evento ev
LEFT JOIN escena esc ON esc.id = ev.escena_id
WHERE NOT EXISTS (SELECT 1 FROM evento s WHERE s.sustituye_a = ev.id);
"""

SENTENCIAS_DDL = (
    SQL_EVENTO_SIN_UPDATE,
    SQL_EVENTO_SIN_DELETE,
    SQL_VISTA_ESTADO_EN_T,
    SQL_VISTA_CRONOLOGIA,
)


def _emitir_ddl_de_canon(_objetivo: Any, conexion: Connection, **_resto: Any) -> None:
    """Crea disparadores y vistas justo despues de las tablas.

    Cuelga de `after_create` de **la metadata** y no de una tabla suelta porque
    las vistas leen `evento` y `escena`: enganchado a una tabla correria antes
    de que existiera la otra.

    Es una funcion y no un `DDL(...)` por `mypy --strict`, que marca `DDL` como
    llamada sin anotar. La alternativa era un `type: ignore`, y una funcion
    dice lo mismo sin apagar el comprobador.
    """
    for sentencia in SENTENCIAS_DDL:
        conexion.exec_driver_sql(sentencia)


# La migracion lleva el mismo SQL, y `tests/test_esquema_migrado.py` comprueba
# que los dos esquemas coinciden: son dos y solo uno existira.
event.listen(Base.metadata, "after_create", _emitir_ddl_de_canon)
