"""La tabla de la feature `escena`: la ficha, que es el contrato de generacion.

La escena es la **unidad atomica de generacion** (`CLAUDE.md` §1): el mayor
fragmento que cabe comodamente en una llamada y el menor que tiene sentido
narrativo completo. Sus columnas son las de `definitions.md` §4.1, una a una.

La regla de dominio 1 -- «exactamente un POV y un giro de valor no nulo» -- vive
aqui como dos `CheckConstraint` y no como una validacion de servicio, porque una
escena que entrara por otra ruta no tendria quien la parase.
"""

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.commons.db.base import Base

# `definitions.md` §4.1. El conjunto es cerrado.
RESULTADOS = ("si", "no", "si-pero", "no-y-ademas")


class Escena(Base):
    """El contrato de generacion de una escena: POV unico, lugar y tiempo continuos.

    `capitulo_id` es **unico**: hoy un capitulo contiene exactamente una escena
    (`definitions.md` §4.1, decision **P-C** del plan 2). Cuando la extension
    crezca, quitar esta restriccion es la unica linea que hay que tocar.

    `version_obra_id` es RF-PLA-01: la escena apunta a la biblia vigente cuando
    se escribio, no a la de hoy.

    `pov`, `lugar` y los demas se guardan por **nombre** y no por clave ajena
    porque `Personaje` y `Lugar` son tablas que todavia no existen: cuando
    entren, pasan a ser relaciones. Queda anotado en Desviaciones.
    """

    __tablename__ = "escena"
    __table_args__ = (
        UniqueConstraint("capitulo_id", name="uq_escena_capitulo"),
        # Regla de dominio 1, primera mitad: exactamente un POV. La columna es
        # escalar -- eso da el «exactamente uno» --, y el check impide el
        # blanco, que es la forma de tener cero teniendo columna.
        CheckConstraint("trim(pov) <> ''", name="ck_escena_pov_unico"),
        # Regla de dominio 1, segunda mitad: el giro de valor no es nulo. Una
        # escena que entra y sale del mismo valor es relleno (`definitions.md`
        # §4.1), y esa es «la primera validacion automatica que conviene
        # implementar» que el documento pide.
        CheckConstraint("valor_entrada <> valor_salida", name="ck_escena_giro_de_valor"),
        CheckConstraint(
            "resultado IN ('si', 'no', 'si-pero', 'no-y-ademas')",
            name="ck_escena_resultado",
        ),
        # `definitions.md` §5: 1 (lejana) a 5 (flujo interior).
        CheckConstraint("distancia_psiquica BETWEEN 1 AND 5", name="ck_escena_distancia_psiquica"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    capitulo_id: Mapped[int] = mapped_column(
        ForeignKey("capitulo.id", name="fk_escena_capitulo_id")
    )
    version_obra_id: Mapped[int] = mapped_column(
        ForeignKey("version_obra.id", name="fk_escena_version_obra_id")
    )

    orden_discurso: Mapped[int]
    tiempo_historia: Mapped[str] = mapped_column(String(120))
    elapsed_desde_anterior: Mapped[str | None] = mapped_column(String(120))

    pov: Mapped[str] = mapped_column(String(120))
    lugar: Mapped[str] = mapped_column(String(200))
    presentes: Mapped[list[str]] = mapped_column(JSON, default=list)
    mencionados: Mapped[list[str]] = mapped_column(JSON, default=list)

    objetivo_del_pov: Mapped[str] = mapped_column(String(500))
    obstaculo: Mapped[str] = mapped_column(String(500))
    resultado: Mapped[str] = mapped_column(String(20))

    valor_entrada: Mapped[str] = mapped_column(String(120))
    valor_salida: Mapped[str] = mapped_column(String(120))

    extension_objetivo: Mapped[int]
    densidad_de_dialogo_objetivo: Mapped[float]
    distancia_psiquica: Mapped[int]

    beat_de_genero: Mapped[str | None] = mapped_column(String(120))
    planta: Mapped[list[str]] = mapped_column(JSON, default=list)
    paga: Mapped[list[str]] = mapped_column(JSON, default=list)
    revela: Mapped[list[str]] = mapped_column(JSON, default=list)
