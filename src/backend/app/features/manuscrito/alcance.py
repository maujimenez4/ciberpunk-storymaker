"""Que capitulos rehace una peticion, y sobre cuales se vuelve a mirar (plan-5 T4).

**Son dos conjuntos distintos y la spec los separa a proposito.** RF-PET-03 dice
que los afectados salen del **uso registrado** del hecho -- `hecho_usado_en` --.
RF-PET-04 dice que se revalida sobre los posteriores **al origen del hecho
sustituido**, no sobre los regenerados. Regenerar no es revalidar.

**El uso registrado es una sobreaproximacion declarada** (`architecture.md`
§4.3): se anota lo que entro en el paquete, no lo que la prosa acabo usando. Se
rehace de mas, nunca de menos.

**`desde` llega como parametro, y es una desviacion del plan.** El plan hacia
que este modulo importara `origen_del_hecho` de `canon`; `canon -> obra ->
manuscrito` ya existe, asi que ese import cerraria un ciclo entre features
(`CLAUDE.md` §5.1 regla 5). No se inventa una segunda forma de preguntar el
origen: quien llama pregunta a `canon.origen_del_hecho` y pasa la respuesta.

**Las tablas de otras features se leen por SQL con su nombre** (`CLAUDE.md` §5.1).
"""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class Alcance:
    """Lo que una peticion va a mover, en numeros de capitulo."""

    hecho_canon_id: int
    desde: int | None
    a_regenerar: tuple[int, ...]
    a_revalidar: tuple[int, ...]

    @property
    def vacio(self) -> bool:
        """R-3. Ningun capitulo se apoya en el hecho: no hay prosa que rehacer, y
        tampoco version nueva que publicar. No significa peticion invalida."""
        return not self.a_regenerar


async def alcance_de_la_peticion(
    sesion: AsyncSession, *, obra_id: int, hecho_canon_id: int, desde: int | None
) -> Alcance:
    """RF-PET-03 y RF-PET-04. `desde` es `canon.origen_del_hecho`: `None` para un
    hecho del brief, y entonces se revalida la novela entera (R-1)."""
    a_regenerar = tuple(
        int(n)
        for n in (
            await sesion.execute(
                text(
                    "SELECT DISTINCT c.numero FROM hecho_usado_en AS u "
                    "JOIN capitulo AS c ON c.id = u.capitulo_id "
                    "WHERE u.hecho_canon_id = :hecho AND c.obra_id = :obra "
                    "ORDER BY c.numero"
                ),
                {"hecho": hecho_canon_id, "obra": obra_id},
            )
        )
        .scalars()
        .all()
    )
    corte = 0 if desde is None else desde
    a_revalidar = tuple(
        int(n)
        for n in (
            await sesion.execute(
                text(
                    "SELECT c.numero FROM capitulo AS c "
                    "WHERE c.obra_id = :obra AND c.numero > :corte ORDER BY c.numero"
                ),
                {"obra": obra_id, "corte": corte},
            )
        )
        .scalars()
        .all()
    )
    return Alcance(
        hecho_canon_id=hecho_canon_id,
        desde=desde,
        a_regenerar=a_regenerar,
        a_revalidar=a_revalidar,
    )
