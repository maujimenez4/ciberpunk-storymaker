"""Las tablas de la feature `obra`.

Las cinco primeras entraron juntas y en una sola migracion porque la spec lo
pide en Impacto tecnico —«Esquema: toda la base de datos. Es la migracion
inicial»— y porque `alembic revision --autogenerate` lee `Base.metadata`
**entera**: dos agentes generando a la vez producen dos *heads* y la cadena
deja de ser lineal.

`Entrevista` y `TextoAportado` entran despues, con la Tarea 9, y el plan no se
las habia dado a nadie: ver Desviaciones. No rompen la regla de arriba porque
T9 va sola en su ola, asi que no hay un segundo autor generando a la vez.
"""

from datetime import date
from typing import Any

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.commons.db.base import Base

AMBITOS_DE_VETO = ("global", "obra", "brief")
ORIGENES_DE_HECHO = ("escena", "brief", "edicion_humana")


class Serie(Base):
    """Conjunto de obras que comparten canon, personajes o mundo.

    Hoy no hace nada, y entra igual: RD-04 la exige desde la migracion
    inicial porque `definitions.md` §4.1 avisa de que anadirla despues
    **obliga a reescribir referencias** que ya apuntan a otro sitio. Es de
    las pocas tablas cuyo coste no esta en construirla sino en llegar tarde.

    `personajes_recurrentes` guarda nombres y no claves ajenas porque
    `Personaje` es de la Fase 2. Cuando exista, pasa a ser una relacion.
    """

    __tablename__ = "serie"

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String(200))
    canon_compartido: Mapped[bool] = mapped_column(default=True)
    orden_de_lectura: Mapped[list[int]] = mapped_column(JSON, default=list)
    personajes_recurrentes: Mapped[list[str]] = mapped_column(JSON, default=list)


class Destinatario(Base):
    """De quien es el regalo (`definitions.md` §9.1).

    **No es un `Personaje`** y no se le aplican las reglas de canon narrativo:
    es una persona real, y sus datos entran por el comprador.
    """

    __tablename__ = "destinatario"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    edad: Mapped[int]
    rasgos: Mapped[list[str]] = mapped_column(JSON, default=list)
    recuerdos_aportados: Mapped[list[str]] = mapped_column(JSON, default=list)
    fecha_de_nacimiento: Mapped[date | None]


class Obra(Base):
    """La novela individual, raiz de casi todo el grafo.

    `destinatario_id` es 0..1 a proposito: una obra sin destinatario es
    legitima; una obra **personalizada** sin el, no.
    """

    __tablename__ = "obra"
    __table_args__ = (
        CheckConstraint(
            "json_array_length(elementos_obligatorios) > 0",
            name="ck_obra_elementos_obligatorios_no_vacios",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String(200))
    genero: Mapped[str] = mapped_column(String(60))
    tono: Mapped[str] = mapped_column(String(60))
    nivel_de_calor: Mapped[int]

    elementos_obligatorios: Mapped[list[str]] = mapped_column(JSON, default=list)
    """Lo que el comprador pidio que apareciera, **en columna y no en el brief**.

    Cierra P-2. Hasta ahora se validaban al cerrar la entrevista y no se
    persistian: la cobertura los leia de `entrevista.respuestas`, asi que una
    obra creada por cualquier otra ruta no tenia elementos que cubrir y
    `cobertura_de_personalizacion` **aprobaba sin comprobar nada**.

    El `CheckConstraint` esta aqui y no solo en `BriefEntrada` por el mismo
    motivo que el de `palabra_prohibida.ambito`: una obra escrita por otra ruta
    —un script, una migracion de datos, un test— no tendria quien la parase, y
    una lista vacia es justo la que hace que el validador diga que si de balde.
    """
    destinatario_id: Mapped[int | None] = mapped_column(ForeignKey("destinatario.id"))
    serie_id: Mapped[int | None] = mapped_column(ForeignKey("serie.id"))


class PalabraProhibida(Base):
    """Un veto, en uno de los tres ambitos de RF-GUA-01.

    El `CheckConstraint` sobre `ambito` vive aqui y no solo en el servicio por
    el mismo motivo que el de `hecho_canon`: un cuarto ambito escrito por otra
    ruta no tendria quien lo parase.

    `obra_id` es nulo para el ambito `global`, que no pertenece a ninguna obra.
    """

    __tablename__ = "palabra_prohibida"
    __table_args__ = (
        CheckConstraint(
            "ambito IN ('global', 'obra', 'brief')",
            name="ck_palabra_prohibida_ambito",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ambito: Mapped[str] = mapped_column(String(10))
    termino: Mapped[str] = mapped_column(String(200))
    obra_id: Mapped[int | None] = mapped_column(ForeignKey("obra.id"))
    motivo: Mapped[str | None] = mapped_column(String(500))


class HechoCanon(Base):
    """Una afirmacion declarada verdadera.

    `escena_de_origen` es texto y **no** una clave ajena: la tabla `escena` es
    de la Fase 2, y una clave ajena a una tabla que no existe rompe el
    `upgrade head` con `foreign_keys=ON`.

    Nace incompleta a proposito: el `usado_en` por capitulos (RF-MEM-02) entra
    cuando haya capitulos que lo usen.

    **`sustituye_a` cierra RF-MEM-08, que hasta la Fase 3 estaba a medias.**
    Corregir un hecho no lo edita: escribe otro. Lo que faltaba era la **cita**
    al corregido, y sin ella el vinculo se deducia por entidad y atributo --
    una heuristica que dos correcciones seguidas sobre el mismo atributo dejan
    de sostener --. Es lo que se usa cuando el capitulo 7 contradice al 4: sin
    la cadena no se puede llegar desde el valor de hoy hasta la escena que se
    apoyo en el de ayer.
    """

    __tablename__ = "hecho_canon"
    __table_args__ = (
        CheckConstraint(
            "(origen = 'escena' AND escena_de_origen IS NOT NULL) OR "
            "(origen <> 'escena' AND escena_de_origen IS NULL)",
            name="ck_hecho_origen_coherente",
        ),
        CheckConstraint(
            "origen IN ('escena', 'brief', 'edicion_humana')",
            name="ck_hecho_origen_valido",
        ),
        # Un ciclo de un solo paso rompe la cadena: quien la recorra para
        # encontrar el valor original no llegaria nunca. Los ciclos mas largos
        # no los para el esquema, y eso queda dicho en Desviaciones.
        CheckConstraint(
            "sustituye_a IS NULL OR sustituye_a <> id",
            name="ck_hecho_no_se_sustituye_a_si_mismo",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    obra_id: Mapped[int] = mapped_column(ForeignKey("obra.id"))
    entidad: Mapped[str] = mapped_column(String(120))
    atributo: Mapped[str] = mapped_column(String(120))
    valor: Mapped[str] = mapped_column(Text)
    confianza: Mapped[float] = mapped_column(default=1.0)
    origen: Mapped[str] = mapped_column(String(20))
    escena_de_origen: Mapped[str | None] = mapped_column(String(60))
    sustituye_a: Mapped[int | None] = mapped_column(
        ForeignKey("hecho_canon.id", name="fk_hecho_canon_sustituye_a")
    )


class Entrevista(Base):
    """La conversacion con el comprador mientras aun no hay obra (RI-01 a RI-03).

    **No es una clase de `definitions.md` §9**, y eso esta anotado en
    Desviaciones: el documento nombra al `Entrevistador` (el rol) y describe la
    entrevista como proceso, pero no como entidad persistida. La tabla existe
    porque los tres endpoints la necesitan: el comprador responde en varias
    llamadas y lo respondido tiene que sobrevivir entre una y otra.

    `obra_id` es nulo hasta que la entrevista se cierra, y **es la clave de
    R-5**: si ya lo tiene, cerrar otra vez devuelve esa obra en vez de crear
    una segunda. La idempotencia vive en el dato, no en la memoria del proceso,
    porque el doble clic puede llegar a otro trabajador.

    `respuestas` se reasigna entera al actualizarla, nunca se muta en sitio:
    SQLAlchemy no vigila el interior de una columna `JSON` y una mutacion
    dentro del `dict` no llegaria a la base.
    """

    __tablename__ = "entrevista"

    id: Mapped[int] = mapped_column(primary_key=True)
    respuestas: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    obra_id: Mapped[int | None] = mapped_column(ForeignKey("obra.id", name="fk_entrevista_obra_id"))


class TextoAportado(Base):
    """La carta o la anecdota que el comprador pega (`definitions.md` §9.1).

    RF-ENT-05 dice que el texto libre **se guarda**, y hasta ahora solo se
    marcaba como dato dentro del prompt (Tarea 6): nadie lo persistia. Que sea
    contenido no confiable no lo exime de guardarse; al reves, guardarlo aparte
    y en su propia tabla es lo que permite que se lea siempre como dato.

    `hechos_extraidos` **no esta**, y no es olvido: producir enunciados a partir
    de prosa es del Extractor, que es de la Fase 2 («Lo que esta fase NO hace»).
    Los hechos que hoy entran al canon los pone quien llame a
    `registrar_hechos_del_brief`.

    El `CheckConstraint` es R-2 escrito donde no se puede rodear: un texto en
    blanco no es un texto aportado, y si entrara crearia mas adelante un hecho
    de canon vacio.
    """

    __tablename__ = "texto_aportado"
    __table_args__ = (CheckConstraint("trim(contenido) <> ''", name="ck_texto_aportado_no_vacio"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    entrevista_id: Mapped[int] = mapped_column(
        ForeignKey("entrevista.id", name="fk_texto_aportado_entrevista_id")
    )
    contenido: Mapped[str] = mapped_column(Text)
    procedencia: Mapped[str] = mapped_column(String(60), default="entrevista")
