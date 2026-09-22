"""Esquema inicial del backend v1.

Revision ID: 0001_inicial
Revises:

RD-01 y RD-02: los nombres de tablas y columnas son los de `definitions.md`, sin
traducir ni abreviar. RD-11: `serie_id` existe desde aqui aunque la v1 maneje una
sola obra, porque anadirlo despues obliga a reescribir el canon entero.

Se construye en tres entregas (desviacion anotada en el plan): obra y manuscrito,
canon, y orquestacion con trazas. La revision es una sola.
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_inicial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- obra y manuscrito -------------------------------------------------
    op.create_table(
        "serie",
        sa.Column("serie_id", sa.String, primary_key=True),
        sa.Column("titulo", sa.String, nullable=False),
        sa.Column("orden_de_lectura", sa.Integer),
        sa.Column("canon_compartido", sa.Boolean, nullable=False, default=True),
    )
    op.create_table(
        "obra",
        sa.Column("obra_id", sa.String, primary_key=True),
        # RD-11: el canon cuelga de la serie desde el primer dia.
        sa.Column("serie_id", sa.String, sa.ForeignKey("serie.serie_id"), nullable=False),
        sa.Column("titulo", sa.String, nullable=False),
        sa.Column("logline", sa.String),
        sa.Column("premisa", sa.String),
        sa.Column("tema", sa.String),
        sa.Column("genero", sa.String, nullable=False),
        sa.Column("subgenero", sa.String, nullable=False),
        sa.Column("extension_objetivo", sa.Integer, nullable=False),
        sa.Column("publico_objetivo", sa.String),
        sa.Column("promesa_de_apertura", sa.String),
        sa.Column("tipo_de_final", sa.String),
        # Parametros de discurso, heredados por toda escena (RF-OBR-01).
        sa.Column("persona", sa.String, nullable=False),
        sa.Column("tiempo_verbal", sa.String, nullable=False),
        sa.Column("esquema_de_pov", sa.String, nullable=False),
        sa.Column("nivel_de_calor", sa.String, nullable=False),
    )
    op.create_table(
        "version_obra",
        sa.Column("version_obra_id", sa.String, primary_key=True),
        sa.Column("obra_id", sa.String, sa.ForeignKey("obra.obra_id"), nullable=False),
        sa.Column("numero", sa.Integer, nullable=False),
        sa.Column("biblia", sa.JSON, nullable=False),
        sa.Column("creada_en", sa.DateTime, nullable=False),
        sa.UniqueConstraint("obra_id", "numero"),
    )
    op.create_table(
        "parte",
        sa.Column("parte_id", sa.String, primary_key=True),
        sa.Column("obra_id", sa.String, sa.ForeignKey("obra.obra_id"), nullable=False),
        sa.Column("numero", sa.Integer, nullable=False),
        sa.Column("funcion_estructural", sa.String, nullable=False),
        sa.Column("giro_que_la_cierra", sa.String),
        sa.Column("porcentaje_del_manuscrito", sa.Float),
        sa.UniqueConstraint("obra_id", "numero"),
    )
    op.create_table(
        "capitulo",
        sa.Column("capitulo_id", sa.String, primary_key=True),
        sa.Column("parte_id", sa.String, sa.ForeignKey("parte.parte_id"), nullable=False),
        sa.Column("numero", sa.Integer, nullable=False),
        sa.Column("titulo", sa.String),
        sa.Column("pov_dominante", sa.String),
        sa.Column("gancho_de_apertura", sa.String),
        sa.Column("tipo_de_corte_final", sa.String),
        sa.Column("extension_objetivo", sa.Integer),
        sa.UniqueConstraint("parte_id", "numero"),
    )
    op.create_table(
        "escena",
        sa.Column("escena_id", sa.String, primary_key=True),
        sa.Column(
            "capitulo_id", sa.String, sa.ForeignKey("capitulo.capitulo_id"), nullable=False
        ),
        # RF-ESC-06: con que version de biblia se escribio.
        sa.Column(
            "version_obra_id",
            sa.String,
            sa.ForeignKey("version_obra.version_obra_id"),
        ),
        # RD-04: los dos relojes son campos distintos.
        sa.Column("orden_discurso", sa.Integer, nullable=False),
        sa.Column("tiempo_historia", sa.String),
        sa.Column("elapsed_desde_anterior", sa.String),
        sa.Column("pov", sa.String, nullable=False),
        sa.Column("lugar", sa.String),
        sa.Column("presentes", sa.JSON),
        sa.Column("mencionados", sa.JSON),
        sa.Column("objetivo_del_pov", sa.String),
        sa.Column("obstaculo", sa.String),
        sa.Column("resultado", sa.String),
        # RG-08: el giro de valor. La no nulidad la impone el dominio, no la
        # tabla: una escena nace en el outline antes de tener prosa.
        sa.Column("valor_entrada", sa.String),
        sa.Column("valor_salida", sa.String),
        sa.Column("extension_objetivo", sa.Integer),
        sa.Column("densidad_de_dialogo_objetivo", sa.Float),
        sa.Column("distancia_psiquica", sa.String),
        sa.Column("beat_de_genero", sa.String),
        sa.UniqueConstraint("capitulo_id", "orden_discurso"),
    )
    op.create_table(
        "version_texto",
        sa.Column("version_texto_id", sa.String, primary_key=True),
        sa.Column(
            "escena_id", sa.String, sa.ForeignKey("escena.escena_id"), nullable=False
        ),
        # RF-ESC-03: inmutable. No hay UPDATE sobre `texto` en ninguna ruta.
        sa.Column("texto", sa.Text, nullable=False),
        sa.Column("vigente", sa.Boolean, nullable=False, default=False),
        sa.Column("run_id", sa.String, nullable=False),
        # RF-MAN-02: generado, editado o humano.
        sa.Column("autoria", sa.String, nullable=False),
        sa.Column("creada_en", sa.DateTime, nullable=False),
    )
    # Una sola version vigente por escena (RF-ESC-03).
    op.create_index(
        "ix_version_texto_una_vigente_por_escena",
        "version_texto",
        ["escena_id"],
        unique=True,
        sqlite_where=sa.text("vigente = 1"),
    )


def downgrade() -> None:
    op.drop_index("ix_version_texto_una_vigente_por_escena", "version_texto")
    for tabla in (
        "version_texto",
        "escena",
        "capitulo",
        "parte",
        "version_obra",
        "obra",
        "serie",
    ):
        op.drop_table(tabla)
