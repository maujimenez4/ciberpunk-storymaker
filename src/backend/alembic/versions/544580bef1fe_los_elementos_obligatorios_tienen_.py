"""Los elementos obligatorios tienen columna, y una obra sin ellos no existe

P-2. `BriefEntrada.elementos_obligatorios` se validaba al cerrar la entrevista y
**no se persistia**: la cobertura los leia del brief en bruto, dentro de
`entrevista.respuestas`. De ahi salia la forma de aprobar de balde — una obra
creada por cualquier ruta que no fuera la entrevista no tenia elementos que
cubrir, y `cobertura_de_personalizacion` **decia que todo estaba bien sin haber
comprobado nada**.

**La premisa que esta revision quita:** que una obra pueda existir sin nada que
cubrir. Por eso la columna es `NOT NULL` y lleva ademas un `CheckConstraint` que
prohibe la lista vacia.

**Y el `CheckConstraint` va en la base, no solo en `BriefEntrada`.** El esquema
Pydantic solo protege el camino de la entrevista; una obra escrita por un script,
por una migracion de datos o por un test entraria sin pasar por el. Es el mismo
motivo por el que `palabra_prohibida.ambito` tiene el suyo: la restriccion que
solo vive en el borde se salta yendo por otro lado.

**`autogenerate` no emitio el constraint** —solo vio la columna— y tampoco habria
funcionado sobre una tabla con filas, porque anadia `NOT NULL` sin valor para las
que ya existen. Las dos cosas van escritas a mano aqui, y la segunda es la que
explica los tres pasos de `upgrade`.

**Las obras que ya existen.** Se rellenan desde `entrevista.respuestas`, que es
donde vivian. La que no tenga entrevista **no se puede rellenar**, y esta
revision **falla en vez de inventarle un valor**: rellenar con una lista de
relleno crearia exactamente la fila que P-2 viene a eliminar —una obra cuya
cobertura pasa sin comprobar nada—, y encima con la apariencia de estar bien.
Fallar deja el problema a la vista; rellenar lo esconde para siempre.

Revision ID: 544580bef1fe
Revises: 8bc0aee00b81
Create Date: 2026-09-24 16:50:14.714174

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "544580bef1fe"
down_revision: str | Sequence[str] | None = "8bc0aee00b81"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NOMBRE_DEL_CHECK = "ck_obra_elementos_obligatorios_no_vacios"


def upgrade() -> None:
    """Columna, relleno desde la entrevista, y entonces las dos restricciones."""
    # `batch_alter_table` en SQLite **recrea la tabla**: copia a una temporal y
    # hace `DROP TABLE obra`. Con `foreign_keys=ON` y una sola fila en
    # `entrevista` apuntando a una obra, ese DROP falla con «FOREIGN KEY
    # constraint failed».
    #
    # Se descubrio probandola **con datos**: sobre una base vacia pasa entera,
    # que es justo el caso que no se parece a la de nadie. Por eso el ciclo de
    # `RD-02` sobre una base recien creada no basta para dar una migracion por
    # buena — comprueba que corre, no que corra donde hay algo que migrar.
    op.execute(sa.text("PRAGMA foreign_keys=OFF"))

    # 1. Nullable primero: una tabla con filas no admite `NOT NULL` sin valor.
    with op.batch_alter_table("obra", schema=None) as batch_op:
        batch_op.add_column(sa.Column("elementos_obligatorios", sa.JSON(), nullable=True))

    # 2. Lo que habia, de donde estaba. Se toma la primera entrevista de la obra
    #    que traiga la clave, que es el mismo criterio que usaba la lectura
    #    anterior en `escritura/novela.py`.
    op.execute(
        sa.text(
            "UPDATE obra SET elementos_obligatorios = ("
            "  SELECT json_extract(e.respuestas, '$.elementos_obligatorios')"
            "  FROM entrevista e"
            "  WHERE e.obra_id = obra.id"
            "    AND json_extract(e.respuestas, '$.elementos_obligatorios') IS NOT NULL"
            "  ORDER BY e.id LIMIT 1"
            ") WHERE elementos_obligatorios IS NULL"
        )
    )

    # 3. Y si alguna se queda sin nada, se para. Es la fila que P-2 describe, y
    #    darle un valor inventado seria dejarla pasar con mejor aspecto.
    huerfanas = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT COUNT(*) FROM obra "
                "WHERE elementos_obligatorios IS NULL "
                "   OR json_array_length(elementos_obligatorios) = 0"
            )
        )
        .scalar_one()
    )
    if huerfanas:
        raise RuntimeError(
            f"{huerfanas} obra(s) sin elementos obligatorios y sin entrevista de la que "
            "sacarlos. Son exactamente las que P-2 describe: su cobertura aprueba sin "
            "comprobar nada. Hay que decidir que llevan antes de migrar, y esta revision "
            "no lo inventa."
        )

    with op.batch_alter_table("obra", schema=None) as batch_op:
        batch_op.alter_column("elementos_obligatorios", existing_type=sa.JSON(), nullable=False)
        batch_op.create_check_constraint(
            NOMBRE_DEL_CHECK, "json_array_length(elementos_obligatorios) > 0"
        )

    op.execute(sa.text("PRAGMA foreign_keys=ON"))


def downgrade() -> None:
    """Se va la columna y con ella el constraint: SQLite recrea la tabla."""
    op.execute(sa.text("PRAGMA foreign_keys=OFF"))
    with op.batch_alter_table("obra", schema=None) as batch_op:
        batch_op.drop_constraint(NOMBRE_DEL_CHECK, type_="check")
        batch_op.drop_column("elementos_obligatorios")
    op.execute(sa.text("PRAGMA foreign_keys=ON"))
