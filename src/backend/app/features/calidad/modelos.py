"""Las tablas del juicio: quien puntua, con que rubrica y por que.

**Lo que decide la forma de este modulo es una sola pregunta: que se puede
comparar con que.** Un numero suelto no dice nada; lo que se mide en esta fase
es la **distancia** entre lo que puntua el juez y lo que puntua el Autor, y esa
resta solo tiene sentido si las dos puntuaciones hablan del mismo criterio de la
misma version de la rubrica.

De ahi las tres decisiones que gobiernan el esquema:

1. **La rubrica se versiona** (`definitions.md` §8). Cambiar la definicion de un
   criterio invalida la comparacion con todo lo puntuado antes, y sin version no
   habria forma de saber que dos cuatros no son el mismo cuatro.
2. **Una sola tabla para todas las puntuaciones**, con `origen` para separarlas.
   Los *scores* mecanicos y los de juicio se leen del mismo sitio -es lo que
   permite que la tabla de los cinco briefs salga de una consulta- y `origen` es
   lo que impide que la distancia del juez sume por error un `extension_de_capitulo`.
3. **La aceptacion del Comprador NO es una puntuacion** (`R-7`, P-05). Vive en su
   propia tabla porque de un si o un no **no sale una distancia**: el Comprador
   acepta o rechaza y el Autor revisa con rubrica, y son dos actos distintos.
   Estando separada, ninguna consulta de distancia puede alcanzarla por
   accidente; con una columna `aceptada` dentro de `puntuacion`, evitarlo seria
   una promesa en cada `WHERE`.

**Las restricciones llevan nombre, todas.** SQLite no altera tablas: `alembic`
trabaja en modo *batch* recreandolas, y una restriccion anonima muere ahi con
«Constraint must have a name». A `hecho_canon` ya le paso en la Fase 1.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime

from app.commons.db.base import Base
from app.commons.domain.reloj import RelojDelSistema

ORIGENES = ("juez", "humana", "programatico", "formal")
"""Los cuatro tipos de puntuacion que el sistema sabe distinguir.

Se declara aqui y se repite en el `CheckConstraint` **a proposito**: un `Enum`
de SQLAlchemy sobre SQLite acaba siendo igualmente un `CHECK`, y tenerlo escrito
deja ver en la tabla lo que la columna admite. Que la lista viva en una
constante es lo que permite que un test la recorra entera en vez de nombrar
cuatro cadenas a mano.
"""

_ORIGEN_VALIDO = ", ".join(f"'{o}'" for o in ORIGENES)


class Rubrica(Base):
    """Una version de la rubrica con la que se juzga.

    `escala_minimo` y `escala_maximo` viajan con ella y no se clavan en el
    codigo: una rubrica de 1 a 5 y otra de 0 a 10 dan numeros que no se pueden
    comparar, y sin la escala guardada no habria forma de normalizarlos despues.
    """

    __tablename__ = "rubrica"
    __table_args__ = (
        UniqueConstraint("version", name="uq_rubrica_version"),
        CheckConstraint("escala_maximo > escala_minimo", name="ck_rubrica_escala"),
    )

    rubrica_id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(32))
    escala_minimo: Mapped[int]
    escala_maximo: Mapped[int]


class CriterioDeRubrica(Base):
    """Un criterio, con su definicion y **sus dos anclajes**.

    Los anclajes son `NOT NULL` y esa es la decision del plan: «una rubrica sin
    anclajes descritos no es una rubrica, es una escala». Sin saber que es un 1 y
    que es un 5, dos jueces -o el mismo dos veces- puntuan cosas distintas con el
    mismo numero, y la correlacion que `RF-JUZ-06` exige medir no significaria
    nada.
    """

    __tablename__ = "criterio_de_rubrica"
    __table_args__ = (UniqueConstraint("rubrica_id", "nombre", name="uq_criterio_rubrica_nombre"),)

    criterio_id: Mapped[int] = mapped_column(primary_key=True)
    rubrica_id: Mapped[int] = mapped_column(
        ForeignKey("rubrica.rubrica_id", name="fk_criterio_de_rubrica_rubrica_id")
    )
    nombre: Mapped[str] = mapped_column(String(64))
    definicion: Mapped[str] = mapped_column(Text)
    ancla_minimo: Mapped[str] = mapped_column(Text)
    ancla_maximo: Mapped[str] = mapped_column(Text)


class Puntuacion(Base):
    """Un numero sobre algo, con quien lo puso y por que.

    `unidad` y `unidad_id` son deliberadamente genericos -un capitulo, una
    novela, una version- porque los validadores no puntuan todos lo mismo y una
    clave ajena por tipo obligaria a una tabla por unidad.

    **`justificacion` es obligatoria cuando hay `criterio_id`**, y eso es `R-4`
    escrito donde no se puede incumplir. Pedirselo al juez en la plantilla lo
    deja en un deseo; lo que lo hace cierto es que la fila no entre. Un *score*
    mecanico no lleva criterio y no justifica nada: `extension_de_capitulo`
    cuenta palabras.
    """

    __tablename__ = "puntuacion"
    __table_args__ = (
        CheckConstraint(
            "criterio_id IS NULL OR (justificacion IS NOT NULL AND trim(justificacion) <> '')",
            name="ck_puntuacion_justificacion",
        ),
        CheckConstraint(f"origen IN ({_ORIGEN_VALIDO})", name="ck_puntuacion_origen"),
    )

    puntuacion_id: Mapped[int] = mapped_column(primary_key=True)
    validador: Mapped[str] = mapped_column(String(64))
    unidad: Mapped[str] = mapped_column(String(32))
    unidad_id: Mapped[str] = mapped_column(String(64))
    valor: Mapped[float]
    criterio_id: Mapped[int | None] = mapped_column(
        ForeignKey("criterio_de_rubrica.criterio_id", name="fk_puntuacion_criterio_id"),
        default=None,
    )
    justificacion: Mapped[str | None] = mapped_column(Text, default=None)
    origen: Mapped[str] = mapped_column(String(16))


class RevisionHumana(Base):
    """La pasada del **Autor** sobre una obra con una rubrica (P-05).

    `revisor` y `fecha` no son metadatos de cortesia: la correlacion de
    `RF-JUZ-06` se mide entre estas puntuaciones y las del juez, y una
    correlacion que nadie puede fechar ni atribuir no se puede auditar cuando
    alguien pregunte de donde salio el numero que dejo de bloquear al juez.
    """

    __tablename__ = "revision_humana"

    revision_id: Mapped[int] = mapped_column(primary_key=True)
    obra_id: Mapped[int]
    rubrica_id: Mapped[int] = mapped_column(
        ForeignKey("rubrica.rubrica_id", name="fk_revision_humana_rubrica_id")
    )
    revisor: Mapped[str] = mapped_column(String(64))
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: RelojDelSistema().ahora()
    )


class AceptacionDeEntrega(Base):
    """El Comprador acepta o rechaza el regalo. `RF-JUZ-07`.

    **No hay `valor` y no hay escala**, y esa ausencia es el contenido de `R-7`:
    de un si o un no no sale una distancia. Si esto fuera una `Puntuacion` con
    `origen='humana'`, cualquier consulta de correlacion la recogeria sin querer
    y el numero saldria contaminado sin que nada fallara.
    """

    __tablename__ = "aceptacion_de_entrega"

    aceptacion_id: Mapped[int] = mapped_column(primary_key=True)
    version_publicada_id: Mapped[int] = mapped_column(
        ForeignKey("version_publicada.id", name="fk_aceptacion_version_publicada_id")
    )
    aceptada: Mapped[bool]
    momento: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: RelojDelSistema().ahora()
    )
    comentario: Mapped[str | None] = mapped_column(Text, default=None)
