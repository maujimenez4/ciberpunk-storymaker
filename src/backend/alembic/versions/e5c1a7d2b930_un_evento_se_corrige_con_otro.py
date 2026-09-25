"""un evento se corrige con otro que lo sustituye

Corregir no edita (`CLAUDE.md` §4.2), tambien en el ledger. `hecho_canon` tenia
`sustituye_a` y `evento` no, asi que un evento mal extraido no tenia correccion
posible: el disparador impide el `UPDATE`. Corrida real, obra 3. Las dos vistas
derivadas dejan fuera el evento sustituido.

Decision de maujimenez4, 2026-09-25 (cambio de esquema, `CLAUDE.md` §3.7).

Revision ID: e5c1a7d2b930
Revises: d3a91f6e2b70
Create Date: 2026-09-25 12:00:00

"""

from collections.abc import Sequence

from alembic import op

revision: str = "e5c1a7d2b930"
down_revision: str | Sequence[str] | None = "d3a91f6e2b70"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_VISTAS = """
CREATE VIEW estado_en_t AS
SELECT ev.obra_id      AS obra_id,
       t.value         AS personaje,
       ev.id           AS evento_id,
       ev.tiempo_historia AS tiempo_historia,
       esc.orden_discurso AS sabe_desde
FROM evento ev
JOIN json_each(ev.testigos) t
LEFT JOIN escena esc ON esc.id = ev.escena_id{filtro};
CREATE VIEW cronologia AS
SELECT ev.id            AS evento_id,
       ev.obra_id       AS obra_id,
       ev.tiempo_historia AS tiempo_historia,
       ev.lugar         AS lugar,
       ev.participantes AS participantes,
       ev.testigos      AS testigos,
       ev.excluye       AS excluye,
       esc.orden_discurso AS orden_discurso
FROM evento ev
LEFT JOIN escena esc ON esc.id = ev.escena_id{filtro};
"""

_FILTRO = "\nWHERE NOT EXISTS (SELECT 1 FROM evento s WHERE s.sustituye_a = ev.id)"


def _recrear_vistas(filtro: str) -> None:
    op.execute("DROP VIEW IF EXISTS cronologia")
    op.execute("DROP VIEW IF EXISTS estado_en_t")
    for sentencia in _VISTAS.format(filtro=filtro).split(";"):
        if sentencia.strip():
            op.execute(sentencia)


def upgrade() -> None:
    # `ADD COLUMN` nativo y no el modo batch: batch recrea la tabla y `evento`
    # perderia sus disparadores de *append-only*.
    op.execute(
        "ALTER TABLE evento ADD COLUMN sustituye_a INTEGER"
        " CONSTRAINT fk_evento_sustituye_a REFERENCES evento (id)"
    )
    _recrear_vistas(_FILTRO)


def downgrade() -> None:
    _recrear_vistas("")
    op.execute("ALTER TABLE evento DROP COLUMN sustituye_a")
