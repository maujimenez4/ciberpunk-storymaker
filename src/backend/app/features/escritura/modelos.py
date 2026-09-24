"""Las tablas de `escritura`: el texto inmutable, la ejecucion y el trabajo.

Las tres responden a la misma pregunta desde tres sitios: **que se entrego, con
que se produjo y en que punto iba**. Sin `ejecucion` una escena no se puede
auditar; sin `trabajo` no se puede reanudar; sin la inmutabilidad de
`version_texto`, lo entregado deja de ser recuperable en cuanto alguien edita.

El disparador de `version_texto` no es una comodidad: `CLAUDE.md` §15 dice «no
editar escenas en sitio: siempre version nueva», y la Fase 1 dejo el registro
de auditoria con esa regla sostenida por una funcion que se niega -- una puerta
con cartel, no una pared. Aqui la pared es un `BEFORE UPDATE ... RAISE(ABORT)`.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    event,
    text,
)
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime

from app.commons.db.base import Base
from app.commons.domain.reloj import RelojDelSistema

# `architecture.md` §3.2 y §3.3. Los dos conjuntos son cerrados: un estado que
# no esta aqui no es un estado, es una errata que nadie veria hasta que el
# orquestador buscara trabajos no terminales y no encontrara este.
TIPOS_DE_TRABAJO = ("escribir_escena", "auditar_manuscrito", "replanificar_capitulo")
ESTADOS_DE_TRABAJO = (
    "PLANIFICANDO",
    "ENSAMBLANDO",
    "ESCRIBIENDO",
    "VALIDANDO",
    "REPARANDO",
    "EXTRAYENDO",
    "INTEGRADA",
    "ESCALADA",
    "FALLIDA",
    "CANCELADA",
)
# `CLAUDE.md` §9.1: maximo dos reparaciones dirigidas; despues, escalado.
INTENTOS_MAXIMOS = 2

_EN_LISTA = ", ".join(f"'{v}'" for v in TIPOS_DE_TRABAJO)
_ESTADOS_EN_LISTA = ", ".join(f"'{v}'" for v in ESTADOS_DE_TRABAJO)


class VersionTexto(Base):
    """Texto **inmutable** de una escena (RF-ESC-02).

    Editar no modifica: crea otra version y marca la vigente. Lo unico mutable
    de una fila es `vigente`, y el disparador de abajo lo dice en el esquema.

    `run_id` es obligatorio porque `CLAUDE.md` §15 prohibe guardar prosa
    generada sin el: sin `run_id` no hay forma de llegar desde el texto hasta
    el prompt, el modelo y la semilla que lo produjeron.
    """

    __tablename__ = "version_texto"
    __table_args__ = (
        UniqueConstraint("escena_id", "numero", name="uq_version_texto_escena_numero"),
        # Indice **parcial**: una sola vigente por escena, y las no vigentes
        # sin limite. Dos vigentes es no tener ninguna, porque entonces nadie
        # sabe cual es el manuscrito.
        Index(
            "uq_version_texto_vigente",
            "escena_id",
            unique=True,
            sqlite_where=text("vigente = 1"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    escena_id: Mapped[int] = mapped_column(
        ForeignKey("escena.id", name="fk_version_texto_escena_id")
    )
    numero: Mapped[int]
    texto: Mapped[str] = mapped_column(Text)
    vigente: Mapped[bool] = mapped_column(default=False)
    run_id: Mapped[str] = mapped_column(String(60))
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: RelojDelSistema().ahora()
    )


class Ejecucion(Base):
    """Una llamada al modelo, con todo lo que la hace reproducible y auditable.

    Regla de dominio 7 y RF-OBS-06, campo a campo: plantilla de prompt **con su
    hash**, version de biblia, IDs recuperados -- de memoria **y de canon** --,
    modelo, semilla, tokens por capa, coste y veredicto.

    **Los dos recuentos de tokens son la decision P-A del plan 2.**
    `tokens_previstos` lo da el contador local antes de llamar, que es lo que
    hace cumplir RF-CTX-02 sin gastar cuota; `tokens_reales` lo devuelve el
    proveedor despues. Guardar solo uno dejaria la deriva del tokenizador local
    como riesgo declarado; guardar los dos la convierte en una cifra que se
    puede medir.

    `prompt_hash` y no el texto del prompt: la plantilla vive versionada en el
    repositorio (`architecture.md` §5.5), y el hash es lo que ata la fila al
    fichero sin duplicar el fichero en cada llamada.
    """

    __tablename__ = "ejecucion"
    __table_args__ = (
        # RF-CTX-02: nunca se llama sin haber contado. Una ejecucion sin
        # recuento previo describiria una llamada que no debio hacerse.
        CheckConstraint("tokens_previstos >= 0", name="ck_ejecucion_tokens_previstos"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(String(60), index=True)
    obra_id: Mapped[int] = mapped_column(ForeignKey("obra.id", name="fk_ejecucion_obra_id"))
    escena_id: Mapped[int | None] = mapped_column(
        ForeignKey("escena.id", name="fk_ejecucion_escena_id")
    )
    version_obra_id: Mapped[int | None] = mapped_column(
        ForeignKey("version_obra.id", name="fk_ejecucion_version_obra_id")
    )

    prompt_id: Mapped[str] = mapped_column(String(60))
    prompt_version: Mapped[str] = mapped_column(String(20))
    prompt_hash: Mapped[str] = mapped_column(String(64))

    modelo: Mapped[str] = mapped_column(String(60))
    semilla: Mapped[int]
    parametros: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    tokens_por_capa: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    tokens_previstos: Mapped[int] = mapped_column(default=0)
    tokens_reales: Mapped[int | None] = mapped_column(default=None)
    coste: Mapped[float | None] = mapped_column(default=None)

    ids_recuperados: Mapped[list[int]] = mapped_column(JSON, default=list)
    ids_canon: Mapped[list[int]] = mapped_column(JSON, default=list)

    # RF-CTX-09 entero, y **en columna propia desde la Fase 3**. El requisito
    # pide los identificadores de *todas* las capas que los tienen, con su capa;
    # las dos de arriba guardan solo canon y memoria, y el mapa completo vivia
    # dentro de `parametros`, que es donde van los parametros de la llamada.
    # Las dos columnas se conservan: son las que las consultas de CU-07 ya
    # saben mirar, y quitarlas seria una migracion de datos por comodidad.
    ids_por_capa: Mapped[dict[str, list[str]]] = mapped_column(JSON, default=dict)

    veredicto: Mapped[str | None] = mapped_column(String(30))

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: RelojDelSistema().ahora()
    )


class Trabajo(Base):
    """La unidad de trabajo de `architecture.md` §3.2.

    Todo lo que dura mas que una peticion HTTP vive aqui: el endpoint crea el
    trabajo y devuelve su identificador, y el frontend consulta su estado. Es
    tambien lo que hace posible reanudar tras una caida, porque el ultimo
    estado persistido dice desde donde repetir.

    `escena_id` es nulo en los trabajos de manuscrito, que no son de ninguna
    escena. `run_id` correlaciona todas las ejecuciones del trabajo y es su
    clave de idempotencia.

    **`capitulo_id` entra en la Fase 3 y no duplica a `escena_id`.** Un trabajo
    recien abierto **no tiene escena todavia** -- la crea el Planificador -- y
    sin embargo ya sabe de que capitulo es: sin esta columna, el estado que
    RI-06 pide leer **por capitulo** no se podia leer hasta despues de
    planificar. Es nulo por lo mismo que `escena_id`: auditar el manuscrito no
    es trabajo de ningun capitulo.
    """

    __tablename__ = "trabajo"
    __table_args__ = (
        CheckConstraint(f"tipo IN ({_EN_LISTA})", name="ck_trabajo_tipo"),
        CheckConstraint(f"estado IN ({_ESTADOS_EN_LISTA})", name="ck_trabajo_estado"),
        CheckConstraint(f"intento BETWEEN 0 AND {INTENTOS_MAXIMOS}", name="ck_trabajo_intento"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    obra_id: Mapped[int] = mapped_column(ForeignKey("obra.id", name="fk_trabajo_obra_id"))
    escena_id: Mapped[int | None] = mapped_column(
        ForeignKey("escena.id", name="fk_trabajo_escena_id")
    )
    capitulo_id: Mapped[int | None] = mapped_column(
        ForeignKey("capitulo.id", name="fk_trabajo_capitulo_id")
    )
    tipo: Mapped[str] = mapped_column(String(30))
    estado: Mapped[str] = mapped_column(String(20))
    intento: Mapped[int] = mapped_column(default=0)
    run_id: Mapped[str] = mapped_column(String(60), index=True)
    causa_fallo: Mapped[str | None] = mapped_column(String(60))
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: RelojDelSistema().ahora()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: RelojDelSistema().ahora(),
        onupdate=lambda: RelojDelSistema().ahora(),
    )


# ---------------------------------------------------------------------------
# La pared de RF-ESC-02
# ---------------------------------------------------------------------------

# `BEFORE UPDATE OF ...`: el disparador vigila las columnas que forman el texto
# entregado y deja libre `vigente`, que es justo lo que la regla manda cambiar
# al editar. Un disparador sobre la tabla entera prohibiria tambien la forma
# legitima de editar, y entonces nadie podria marcar la version nueva.
#
# `IF NOT EXISTS` porque `Base.metadata.create_all` es idempotente y este DDL
# cuelga de el: sin eso, crear dos veces el esquema fallaria.
SQL_VERSION_TEXTO_INMUTABLE = """
CREATE TRIGGER IF NOT EXISTS trg_version_texto_inmutable
BEFORE UPDATE OF texto, numero, escena_id, run_id ON version_texto
BEGIN
    SELECT RAISE(ABORT,
        'Una version de texto es inmutable: editar crea otra y marca la vigente.');
END;
"""


def _emitir_ddl_de_escritura(_objetivo: Any, conexion: Connection, **_resto: Any) -> None:
    """Crea el disparador justo despues de las tablas.

    Cuelga de `after_create` de **la metadata** y no de la tabla suelta: un
    disparador que se crea antes que su tabla no se puede crear.

    Es una funcion y no un `DDL(...)` por `mypy --strict`, que marca `DDL` como
    llamada sin anotar.
    """
    conexion.exec_driver_sql(SQL_VERSION_TEXTO_INMUTABLE)


# La migracion lleva el mismo SQL, y `features/canon/tests/test_esquema_migrado.py`
# comprueba que los dos esquemas coinciden: son dos y solo uno existira.
event.listen(Base.metadata, "after_create", _emitir_ddl_de_escritura)
