"""El registro de auditoria, que **no es un log de errores** (RF-GUA-04, RF-GUA-05).

Un log de errores dice que fallo. Este dice **que se permitio, que se bloqueo y
por que** (`definitions.md` §9.3). La diferencia no es de matiz: un registro que
solo guarda los bloqueos responde «que salio mal», y la pregunta que se le hace
meses despues es «por que aquella novela salio como salio». Esa no la puede
contestar si lo que se dejo pasar no esta escrito.

Vive en `commons/db/` y no en una feature porque lo escriben los guardarrailes,
que son transversales: el veto de `brief` lo comprueba la entrevista y el de
`obra` lo comprobara el ciclo de capitulo, y ninguna de las dos es dueña del
registro. `commons/` no importa de ninguna feature (primer contrato de
`import-linter`), asi que la clave ajena a `obra` se declara por **nombre de
tabla** y no importando `features/obra/modelos.py`.
"""

from datetime import datetime
from typing import Any, NoReturn

from sqlalchemy import CheckConstraint, ForeignKey, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, DateTime

from app.commons.db.base import Base
from app.commons.domain.errores import OperacionNoPermitida
from app.commons.domain.reloj import RelojDelSistema


class RegistroDeAuditoria(Base):
    """Que decidio el sistema sobre una unidad, cuando y por que. **Append-only.**

    Se llama como en `definitions.md` §9.3, igual que las cinco tablas de la
    Tarea 4 se llaman como su entrada del documento. El plan lo llamaba
    `FilaAuditoria`, que no existe en el vocabulario (`CLAUDE.md` §2: gana el
    documento); queda anotado en Desviaciones.

    `obra_id` hace hoy de `sujeto`: en esta fase la unica unidad sobre la que
    se decide es la obra, porque no hay capitulos todavia. Cuando los haya,
    `sujeto` tendra que nombrar cual, y `obra_id` pasara a ser solo el ambito.

    La clave ajena va **nombrada**. SQLite no altera tablas: cualquier
    migracion futura que toque esta la recrea en modo batch, y una restriccion
    sin nombre muere ahi con «Constraint must have a name». A `hecho_canon` le
    paso en la Tarea 4 y hubo que rescatarla con un `naming_convention`;
    ponerle el nombre al crearla cuesta una linea.
    """

    __tablename__ = "registro_auditoria"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('permitido', 'bloqueado')",
            name="ck_registro_auditoria_decision",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    obra_id: Mapped[int] = mapped_column(
        ForeignKey("obra.id", name="fk_registro_auditoria_obra_id")
    )
    momento: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decision: Mapped[str] = mapped_column(String(10))
    motivo: Mapped[str] = mapped_column(String(500))
    evidencia: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


async def registrar(
    sesion: AsyncSession,
    obra_id: int,
    decision: str,
    motivo: str,
    evidencia: dict[str, Any],
) -> None:
    """Anota una decision. `decision` es `permitido` o `bloqueado`, las dos.

    Hace `flush` y **no** `commit`: quien decide que una unidad de trabajo
    termino bien es el servicio, no esto (`commons/db/sesion.py`). El `flush`
    si hace falta, porque es lo que hace que la fila exista para el `select`
    de `leer_auditoria` dentro de la misma transaccion, y lo que da el `id`
    que fija el orden de insercion.
    """
    sesion.add(
        RegistroDeAuditoria(
            obra_id=obra_id,
            momento=RelojDelSistema().ahora(),
            decision=decision,
            motivo=motivo,
            evidencia=evidencia,
        )
    )
    await sesion.flush()


async def leer_auditoria(sesion: AsyncSession, obra_id: int) -> list[RegistroDeAuditoria]:
    """Lo anotado para una obra, en orden de insercion.

    Ordena por `id` y no por `momento` a proposito: dos decisiones de la misma
    rafaga pueden compartir instante, y entonces el orden de lectura dejaria de
    ser el de los hechos. La clave autoincremental si es un orden total.
    """
    filas = await sesion.execute(
        select(RegistroDeAuditoria)
        .where(RegistroDeAuditoria.obra_id == obra_id)
        .order_by(RegistroDeAuditoria.id)
    )
    return list(filas.scalars().all())


async def borrar_auditoria(sesion: AsyncSession, fila_id: int) -> NoReturn:
    """No borra. Existe para que quien lo intente se lleve un error con nombre.

    El registro es *append-only* (RF-GUA-05): una auditoria de la que se puede
    quitar una fila no acredita nada, porque lo que falta no se distingue de lo
    que nunca paso. La funcion esta y falla, en vez de no estar, para que el
    intento quede dicho en el codigo y con su test, y no dependa de que nadie
    se acuerde de la regla.
    """
    raise OperacionNoPermitida(
        f"El registro de auditoria es append-only: la fila {fila_id} no se borra."
    )
