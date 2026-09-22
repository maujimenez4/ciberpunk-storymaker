"""Esquema inicial del backend v1.

Revision ID: 0001_inicial
Revises:

RD-01 y RD-02: los nombres de tablas y columnas son los de `definitions.md`, sin
traducir ni abreviar. RD-11: `serie_id` existe desde aqui aunque la v1 maneje una
sola obra, porque anadirlo despues obliga a reescribir el canon entero.

Construida en cuatro entregas (desviacion anotada en el plan): obra y
manuscrito, biblia y mundo, canon, y orquestacion con trazas. La revision es
una sola: veintiseis tablas y dos disparadores.
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
        sa.Column(
            "canon_compartido", sa.Boolean, nullable=False, server_default=sa.text("1")
        ),
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
        sa.Column("vigente", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("run_id", sa.String, nullable=False),
        # RF-MAN-02: generado, editado o humano.
        sa.Column("autoria", sa.String, nullable=False),
        sa.Column("creada_en", sa.DateTime, nullable=False),
    )

    # --- biblia y mundo ----------------------------------------------------
    # RD-03: del Personaje vive aqui **solo la parte fija**. La movil
    # -ubicacion, estado emocional, que sabe y desde cuando- se deriva del
    # ledger (RF-CAN-06) y no tiene tabla propia: tenerla la desincronizaria
    # del texto ya escrito, que es justo lo que definitions.md §4.5 previene.
    op.create_table(
        "personaje",
        sa.Column("pj_id", sa.String, primary_key=True),
        sa.Column("obra_id", sa.String, sa.ForeignKey("obra.obra_id"), nullable=False),
        sa.Column("nombre", sa.String, nullable=False),
        sa.Column("apodos", sa.JSON),
        sa.Column("edad", sa.Integer, nullable=False),
        sa.Column("fisico_invariable", sa.String),
        sa.Column("profesion", sa.String),
        sa.Column("familia", sa.String),
        sa.Column("historia_previa", sa.String),
        sa.Column("herida_original", sa.String),
        sa.Column("mentira_que_se_cree", sa.String),
        sa.Column("deseo_consciente", sa.String),
        sa.Column("necesidad_inconsciente", sa.String),
        sa.Column("miedo_central", sa.String),
        sa.Column("competencias", sa.JSON),
        sa.Column("limitaciones", sa.JSON),
        sa.Column("rol_narrativo", sa.String, nullable=False),
        # RG-09 por esquema: ningun personaje menor entra en contenido
        # romantico. El validador de RF-CAL-03 se apoya en esta columna.
        sa.CheckConstraint("edad >= 0", name="ck_personaje_edad_no_negativa"),
    )
    op.create_table(
        "perfil_de_voz",
        sa.Column("perfil_de_voz_id", sa.String, primary_key=True),
        sa.Column("pj_id", sa.String, sa.ForeignKey("personaje.pj_id"), nullable=False),
        sa.Column("lexico_propio", sa.JSON),
        sa.Column("muletillas", sa.JSON),
        sa.Column("longitud_media_de_frase", sa.Float),
        sa.Column("registro", sa.String),
        sa.Column("uso_de_tacos", sa.String),
        sa.Column("temas_que_evita", sa.JSON),
        sa.Column("modo_de_mentir", sa.String),
        sa.Column("humor", sa.String),
        sa.Column("ritmo_de_pensamiento", sa.String),
        sa.UniqueConstraint("pj_id"),
    )
    op.create_table(
        "relacion",
        sa.Column("rel_id", sa.String, primary_key=True),
        sa.Column("personaje_a", sa.String, sa.ForeignKey("personaje.pj_id"), nullable=False),
        sa.Column("personaje_b", sa.String, sa.ForeignKey("personaje.pj_id"), nullable=False),
        sa.Column("tipo", sa.String, nullable=False),
        sa.Column("conflicto_central", sa.String),
        sa.Column("deuda_emocional", sa.String),
        sa.Column("historia_compartida", sa.String),
        # `temperatura` es [movil]: se deriva del ledger, no se guarda aqui.
    )
    op.create_table(
        "lugar",
        sa.Column("lug_id", sa.String, primary_key=True),
        sa.Column("obra_id", sa.String, sa.ForeignKey("obra.obra_id"), nullable=False),
        sa.Column("nombre", sa.String, nullable=False),
        sa.Column("tipo", sa.String),
        sa.Column("sensorialidad_fija", sa.JSON),
        sa.Column("accesos", sa.JSON),
    )
    # `distancias_a[]` con `tiempo_de_viaje` es una relacion entre lugares, no
    # un atributo: es lo que hace comprobable RG-04 (RF-CAL-04, teletransporte).
    op.create_table(
        "distancia_entre_lugares",
        sa.Column("origen_id", sa.String, sa.ForeignKey("lugar.lug_id"), primary_key=True),
        sa.Column("destino_id", sa.String, sa.ForeignKey("lugar.lug_id"), primary_key=True),
        sa.Column("tiempo_de_viaje", sa.String, nullable=False),
    )
    op.create_table(
        "objeto",
        sa.Column("obj_id", sa.String, primary_key=True),
        sa.Column("obra_id", sa.String, sa.ForeignKey("obra.obra_id"), nullable=False),
        sa.Column("nombre", sa.String, nullable=False),
        sa.Column("carga_simbolica", sa.String),
        sa.Column("escena_de_plantado", sa.String, sa.ForeignKey("escena.escena_id")),
        sa.Column("escena_de_pago", sa.String, sa.ForeignKey("escena.escena_id")),
        # `dueno_actual`, `ubicacion_actual` y `estado` son [movil]: ledger.
    )
    op.create_table(
        "regla_de_mundo",
        sa.Column("regla_id", sa.String, primary_key=True),
        sa.Column("obra_id", sa.String, sa.ForeignKey("obra.obra_id"), nullable=False),
        sa.Column("enunciado", sa.String, nullable=False),
        sa.Column("alcance", sa.String),
        sa.Column("excepciones", sa.JSON),
        sa.Column("escena_en_que_se_establece", sa.String, sa.ForeignKey("escena.escena_id")),
    )


    # --- canon, ledger, estado derivado e indice ---------------------------
    op.create_table(
        "entidad",
        sa.Column("entidad_id", sa.String, primary_key=True),
        sa.Column("obra_id", sa.String, sa.ForeignKey("obra.obra_id"), nullable=False),
        sa.Column("tipo", sa.String, nullable=False),
        sa.Column("nombre", sa.String, nullable=False),
    )
    # RD-11: el canon cuelga de `serie_id`, no de `obra_id`. Es lo unico de
    # todo el esquema cuya clave ajena apunta a la serie a proposito.
    op.create_table(
        "hecho_canon",
        sa.Column("hc_id", sa.String, primary_key=True),
        sa.Column("serie_id", sa.String, sa.ForeignKey("serie.serie_id"), nullable=False),
        sa.Column("entidad", sa.String, nullable=False),
        sa.Column("atributo", sa.String, nullable=False),
        sa.Column("valor", sa.String, nullable=False),
        # RF-CAN-04: todo hecho cita la escena que lo establecio.
        sa.Column(
            "escena_de_origen", sa.String, sa.ForeignKey("escena.escena_id"), nullable=False
        ),
        sa.Column("confianza", sa.Float),
        # RF-CAN-07: corregir no edita. El hecho nuevo cita al que sustituye.
        sa.Column("sustituye_a", sa.String, sa.ForeignKey("hecho_canon.hc_id")),
    )
    op.create_table(
        "evento",
        sa.Column("evt_id", sa.String, primary_key=True),
        sa.Column("serie_id", sa.String, sa.ForeignKey("serie.serie_id"), nullable=False),
        sa.Column("descripcion", sa.String, nullable=False),
        sa.Column("tiempo_historia", sa.String),
        sa.Column("lugar", sa.String),
        sa.Column("participantes", sa.JSON),
        # RF-CAN-11: de aqui se deriva quien puede saber que, y desde cuando.
        sa.Column("testigos", sa.JSON),
        sa.Column("causa", sa.JSON),
        sa.Column("consecuencia", sa.JSON),
        sa.Column("escena_de_origen", sa.String, sa.ForeignKey("escena.escena_id")),
    )
    # RF-CAN-05: append-only impuesto por el motor, no por el repositorio. Si
    # solo lo impidiera el codigo, una consulta suelta o una migracion futura
    # podrian romperlo sin que nada avisara.
    op.execute(
        "CREATE TRIGGER evento_sin_update BEFORE UPDATE ON evento BEGIN "
        "SELECT RAISE(ABORT, 'el ledger es append-only'); END"
    )
    op.execute(
        "CREATE TRIGGER evento_sin_delete BEFORE DELETE ON evento BEGIN "
        "SELECT RAISE(ABORT, 'el ledger es append-only'); END"
    )
    op.create_table(
        "plantado",
        sa.Column("plantado_id", sa.String, primary_key=True),
        sa.Column(
            "escena_de_origen", sa.String, sa.ForeignKey("escena.escena_id"), nullable=False
        ),
        sa.Column("importancia", sa.String, nullable=False),
        sa.Column("escena_de_pago_prevista", sa.String, sa.ForeignKey("escena.escena_id")),
        sa.Column("escena_de_pago", sa.String, sa.ForeignKey("escena.escena_id")),
    )
    op.create_table(
        "hilo_narrativo",
        sa.Column("hilo_id", sa.String, primary_key=True),
        sa.Column("pregunta", sa.String, nullable=False),
        sa.Column(
            "escena_de_apertura", sa.String, sa.ForeignKey("escena.escena_id"), nullable=False
        ),
        sa.Column("escena_de_cierre", sa.String, sa.ForeignKey("escena.escena_id")),
        sa.Column("estado", sa.String, nullable=False),
    )
    # RF-CAN-08: cascada escena -> capitulo -> acto -> obra. `referencia_id`
    # apunta a la unidad resumida; que tabla sea depende de `nivel`, asi que no
    # lleva clave ajena.
    op.create_table(
        "resumen",
        sa.Column("resumen_id", sa.String, primary_key=True),
        sa.Column("nivel", sa.String, nullable=False),
        sa.Column("referencia_id", sa.String, nullable=False),
        sa.Column("texto", sa.Text, nullable=False),
        sa.UniqueConstraint("nivel", "referencia_id"),
    )
    # RF-CAN-06 y RF-CAN-13: el estado en T es derivado; esto es solo cache.
    # `valido` es lo que permite invalidar los posteriores a un hecho sustituido
    # sin borrarlos, y recalcular desde el ultimo valido.
    op.create_table(
        "snapshot_estado_en_t",
        sa.Column("snapshot_id", sa.String, primary_key=True),
        sa.Column(
            "escena_id", sa.String, sa.ForeignKey("escena.escena_id"), nullable=False
        ),
        sa.Column("estado", sa.JSON, nullable=False),
        sa.Column("valido", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("creado_en", sa.DateTime, nullable=False),
        sa.UniqueConstraint("escena_id"),
    )
    # RD-07, desde D-02: `fragmento` guarda **solo texto**. No hay vectores
    # porque no hay proveedor de vectores; la ordenacion semantica la resuelve
    # el proveedor de modelo sobre estos textos (architecture.md §4.6).
    op.create_table(
        "fragmento",
        sa.Column("fragmento_id", sa.String, primary_key=True),
        sa.Column(
            "version_texto_id",
            sa.String,
            sa.ForeignKey("version_texto.version_texto_id"),
            nullable=False,
        ),
        sa.Column("texto", sa.Text, nullable=False),
    )


    # --- orquestacion y trazas ---------------------------------------------
    # RD-05: los campos de architecture.md §3.2. `estado` es uno de los diez
    # de §3.3 y `intento` el contador de reparacion dirigida (maximo 2).
    op.create_table(
        "trabajo",
        sa.Column("trabajo_id", sa.String, primary_key=True),
        sa.Column("obra_id", sa.String, sa.ForeignKey("obra.obra_id"), nullable=False),
        # Nulo en trabajos de manuscrito, que no son de una escena.
        sa.Column("escena_id", sa.String, sa.ForeignKey("escena.escena_id")),
        sa.Column("tipo", sa.String, nullable=False),
        sa.Column("estado", sa.String, nullable=False),
        sa.Column("intento", sa.Integer, nullable=False, server_default=sa.text("0")),
        # Clave de idempotencia: repetir un paso con el mismo run_id no duplica
        # escrituras (RF-ORQ-06).
        sa.Column("run_id", sa.String, nullable=False),
        sa.Column("causa_fallo", sa.String),
        # RF-ORQ-18: que defecto se anulo al aceptar, y quien lo anulo.
        sa.Column("defecto_anulado_id", sa.String),
        sa.Column("anulado_por", sa.String),
        sa.Column("creado_en", sa.DateTime, nullable=False),
        sa.Column("actualizado_en", sa.DateTime, nullable=False),
        sa.CheckConstraint("intento <= 2", name="ck_trabajo_maximo_dos_reparaciones"),
    )
    op.create_index("ix_trabajo_estado", "trabajo", ["estado"])
    # RD-06 y RI-14. `Prompt` no es tabla (RD-01): es un fichero del repositorio
    # del que aqui se guardan identificador, version y hash. Con eso se
    # reconstruye el paquete (RF-CTX-13) sin un segundo sistema de versionado.
    op.create_table(
        "ejecucion",
        sa.Column("ejecucion_id", sa.String, primary_key=True),
        sa.Column("run_id", sa.String, nullable=False),
        sa.Column("escena_id", sa.String, sa.ForeignKey("escena.escena_id")),
        sa.Column("prompt_id", sa.String, nullable=False),
        sa.Column("prompt_version", sa.String, nullable=False),
        sa.Column("prompt_hash", sa.String, nullable=False),
        sa.Column(
            "version_obra_id", sa.String, sa.ForeignKey("version_obra.version_obra_id")
        ),
        sa.Column("ids_recuperados", sa.JSON, nullable=False),
        sa.Column("modelo", sa.String, nullable=False),
        sa.Column("parametros", sa.JSON, nullable=False),
        sa.Column("semilla", sa.Integer),
        # RF-CTX-06: el desglose por capa se persiste aqui, no solo se devuelve.
        sa.Column("tokens_por_capa", sa.JSON, nullable=False),
        sa.Column("coste", sa.Float),
        sa.Column("veredicto", sa.String),
        sa.Column("creada_en", sa.DateTime, nullable=False),
    )
    op.create_index("ix_ejecucion_run_id", "ejecucion", ["run_id"])
    # RD-14 y D-06: la cita se ancla por desplazamiento sobre una version de
    # texto inmutable, y va con su literal para que sea legible sin la base.
    op.create_table(
        "defecto",
        sa.Column("defecto_id", sa.String, primary_key=True),
        sa.Column("codigo", sa.String, nullable=False),
        sa.Column(
            "version_texto_id",
            sa.String,
            sa.ForeignKey("version_texto.version_texto_id"),
            nullable=False,
        ),
        sa.Column("cita", sa.Text, nullable=False),
        sa.Column("desplazamiento_inicio", sa.Integer, nullable=False),
        sa.Column("desplazamiento_fin", sa.Integer, nullable=False),
        # Axioma 12: obligatorio cuando el codigo es CAN-01. Lo comprueba
        # RF-CAL-11 en codigo, porque SQLite no valida condicionales por columna.
        sa.Column("hecho_canon_id", sa.String, sa.ForeignKey("hecho_canon.hc_id")),
        # architecture.md §8.3: un defecto mal formado no bloquea ni consume
        # reintento, pero se registra: es la unica senal que mide al Continuista.
        sa.Column(
            "bien_formado", sa.Boolean, nullable=False, server_default=sa.text("1")
        ),
        sa.CheckConstraint(
            "desplazamiento_fin > desplazamiento_inicio",
            name="ck_defecto_cita_no_vacia",
        ),
    )
    # RD-13. La escribe el Extractor; en la v1 no la lee nadie, porque su unico
    # consumidor es el Editor de linea, que esta fuera de alcance.
    op.create_table(
        "ngrama_vetado",
        sa.Column("ngrama", sa.String, primary_key=True),
        sa.Column("obra_id", sa.String, sa.ForeignKey("obra.obra_id"), primary_key=True),
        sa.Column("veces", sa.Integer, nullable=False, server_default=sa.text("1")),
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
    op.execute("DROP TRIGGER IF EXISTS evento_sin_update")
    op.execute("DROP TRIGGER IF EXISTS evento_sin_delete")
    for tabla in (
        "ngrama_vetado",
        "defecto",
        "ejecucion",
        "trabajo",
        "fragmento",
        "snapshot_estado_en_t",
        "resumen",
        "hilo_narrativo",
        "plantado",
        "evento",
        "hecho_canon",
        "entidad",
        "regla_de_mundo",
        "objeto",
        "distancia_entre_lugares",
        "lugar",
        "relacion",
        "perfil_de_voz",
        "personaje",
        "version_texto",
        "escena",
        "capitulo",
        "parte",
        "version_obra",
        "obra",
        "serie",
    ):
        op.drop_table(tabla)
