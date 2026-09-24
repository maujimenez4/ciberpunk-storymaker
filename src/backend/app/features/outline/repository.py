"""Acceso a las tablas de la feature `outline`: `version_obra` y `capitulo`.

**`obra` se lee por nombre de tabla, no importando su modelo.** Una feature solo
importa de `commons/` y del `__init__.py` de otra (`CLAUDE.md` §5.1), y el de
`obra` no exporta sus tablas. Es el mismo trato que la Tarea 2 le dio a las
claves ajenas —`capitulo.obra_id` apunta a `"obra.id"` por nombre, sin que las
dos features se conozcan—, y aqui se extiende a la lectura. La `table()` de
abajo **no es una tabla nueva**: no se declara sobre `Base.metadata`, asi que no
la ve `create_all` ni el `--autogenerate` de Alembic.
"""

import json
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import column, func, select, table
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.outline.modelos import Capitulo, VersionObra
from app.features.outline.schemas import CapituloDelOutline

_obra = table(
    "obra",
    column("id"),
    column("titulo"),
    column("genero"),
    column("tono"),
    column("nivel_de_calor"),
    column("elementos_obligatorios"),
    column("destinatario_id"),
)

# El destinatario se lee por nombre de tabla, igual que `obra` y por el mismo
# motivo: es de otra feature y una feature no importa los ficheros internos de
# otra (`CLAUDE.md` §5.1).
_destinatario = table(
    "destinatario",
    column("id"),
    column("nombre"),
    column("edad"),
    column("rasgos"),
    column("recuerdos_aportados"),
)


@dataclass(frozen=True)
class DatosDeObra:
    """Lo que el Arquitecto necesita saber de la obra para planificarla.

    Es un `dataclass` propio y no la fila cruda: lo que sale del repositorio no
    es un modelo de base de datos de otra feature, y asi el servicio no depende
    de la forma de una tabla que no es suya.

    **El destinatario y los elementos obligatorios entraron el 2026-09-24, y
    conviene el porque.** Hasta entonces esto llevaba cuatro campos -- titulo,
    genero, tono y nivel de calor --, y la primera corrida real lo destapo: el
    Arquitecto devolvio `"titulo": "Novela para [DESTINATARIO_PERSONALIZADO]"`
    y dos personajes inventados. No se equivoco: se le pidio personalizar sin
    darle con que.

    Dos consecuencias, y las dos son del producto y no del codigo:

    - `CLAUDE.md` §1 llama modo de fallo a «la novela es correcta y podria ser
      de cualquiera». Con cuatro campos ese fallo no es un riesgo: es el
      resultado garantizado.
    - La **regla de dominio 11** -- todo elemento obligatorio aparece en al menos
      un capitulo -- era **incumplible por construccion**: si «el perro Luna» no
      llega al Arquitecto, no hay outline que lo contenga ni hecho que lo
      respalde, y el validador que la comprueba vigila algo que el sistema no
      puede producir.
    """

    id: int
    titulo: str
    genero: str
    tono: str
    nivel_de_calor: int
    elementos_obligatorios: list[str] = field(default_factory=list)
    destinatario: dict[str, Any] | None = None

    def como_brief(self) -> dict[str, Any]:
        """El brief que entra al prompt, sin el `id`: no es dato de la historia.

        **Los vetos no salen aqui.** Son guardarrailes y se aplican en codigo
        sobre el capitulo (`CLAUDE.md` §11); meterlos en el prompt del
        Arquitecto los convertiria en una sugerencia, y una regla de seguridad
        que depende de que el modelo obedezca no es una regla.
        """
        brief: dict[str, Any] = {
            "titulo": self.titulo,
            "genero": self.genero,
            "tono": self.tono,
            "nivel_de_calor": self.nivel_de_calor,
            "elementos_obligatorios": list(self.elementos_obligatorios),
        }
        if self.destinatario is not None:
            brief["destinatario"] = dict(self.destinatario)
        return brief


async def leer_obra(sesion: AsyncSession, obra_id: int) -> DatosDeObra | None:
    """`None` si no existe. Quien decide que hacer con eso es el servicio.

    **`LEFT JOIN` sobre el destinatario y no `JOIN`.** `obra.destinatario_id`
    es 0..1 a proposito -- una obra puede existir sin destinatario --, y un
    `JOIN` la haria desaparecer de la consulta: la obra sin destinatario
    dejaria de poder planificarse, que es peor que planificarla sin el.
    """
    fila = (
        await sesion.execute(
            select(
                _obra.c.id,
                _obra.c.titulo,
                _obra.c.genero,
                _obra.c.tono,
                _obra.c.nivel_de_calor,
                _obra.c.elementos_obligatorios,
                _destinatario.c.nombre,
                _destinatario.c.edad,
                _destinatario.c.rasgos,
                _destinatario.c.recuerdos_aportados,
            )
            .select_from(
                _obra.join(
                    _destinatario,
                    _obra.c.destinatario_id == _destinatario.c.id,
                    isouter=True,
                )
            )
            .where(_obra.c.id == obra_id)
        )
    ).first()
    if fila is None:
        return None
    return DatosDeObra(
        id=fila.id,
        titulo=fila.titulo,
        genero=fila.genero,
        tono=fila.tono,
        nivel_de_calor=fila.nivel_de_calor,
        elementos_obligatorios=_lista(fila.elementos_obligatorios),
        destinatario=None
        if fila.nombre is None
        else {
            "nombre": fila.nombre,
            "edad": fila.edad,
            "rasgos": _lista(fila.rasgos),
            "recuerdos_aportados": _lista(fila.recuerdos_aportados),
        },
    )


def _lista(crudo: Any) -> list[str]:
    """Las columnas JSON vuelven como lista, como texto o como `None`.

    Leidas por nombre de tabla -- sin el modelo que declara el tipo `JSON` --
    SQLite las devuelve tal cual estan guardadas, asi que aqui se normaliza en
    vez de confiar en la forma.
    """
    if crudo is None:
        return []
    if isinstance(crudo, str):
        return list(json.loads(crudo))
    return list(crudo)


async def cuenta_capitulos(sesion: AsyncSession, obra_id: int) -> int:
    """Cuantos capitulos tiene ya la obra. Cero significa «sin planificar»."""
    return (
        await sesion.execute(
            select(func.count()).select_from(Capitulo).where(Capitulo.obra_id == obra_id)
        )
    ).scalar_one()


async def siguiente_numero_de_version(sesion: AsyncSession, obra_id: int) -> int:
    """La biblia se versiona, no se edita (RF-PLA-01): la primera es la 1."""
    ultima = (
        await sesion.execute(
            select(func.max(VersionObra.numero)).where(VersionObra.obra_id == obra_id)
        )
    ).scalar_one()
    return 1 if ultima is None else int(ultima) + 1


async def guardar_outline(
    sesion: AsyncSession,
    obra_id: int,
    numero: int,
    biblia: dict[str, Any],
    capitulos: list[CapituloDelOutline],
) -> tuple[VersionObra, list[Capitulo]]:
    """La biblia congelada y sus capitulos, en una sola escritura.

    El `flush` no es de conveniencia: pone en el camino de escritura las
    restricciones de `capitulo` —el numero unico por obra, el rango de
    extension— en vez de dejarlas para el `commit` de quien llame.

    **El plan dramatico se persiste desde el cierre de la ola 2.** Lugar,
    objetivo, obstaculo y giro previsto son columnas de `capitulo` (RF-PLA-04);
    antes no lo eran y el outline se perdia al guardar.

    **Y el `beat_de_genero`, desde la Fase 3.** Tambien se tiraba, con el
    resultado de que `CA-32` se cumplia sobre la salida del agente y no sobre lo
    guardado. `escena.beat_de_genero` sigue existiendo y ahora puede **heredar**
    el del capitulo en vez de decidirlo otra vez.
    """
    version = VersionObra(obra_id=obra_id, numero=numero, biblia=biblia)
    sesion.add(version)
    await sesion.flush()

    filas = [
        Capitulo(
            obra_id=obra_id,
            numero=capitulo.numero,
            titulo=capitulo.titulo,
            pov_dominante=capitulo.pov_dominante,
            gancho_de_apertura=capitulo.gancho_de_apertura,
            tipo_de_corte_final=capitulo.tipo_de_corte_final,
            extension_objetivo=capitulo.extension_objetivo,
            lugar=capitulo.lugar,
            objetivo=capitulo.objetivo,
            obstaculo=capitulo.obstaculo,
            # El giro previsto es el par entrada -> salida del Arquitecto.
            giro_de_valor_previsto=f"{capitulo.valor_entrada} -> {capitulo.valor_salida}",
            # `BeatDeGenero` es un `StrEnum`: lo que se guarda es su valor, que
            # es contra lo que compara el `CheckConstraint` de la tabla.
            beat_de_genero=None
            if capitulo.beat_de_genero is None
            else capitulo.beat_de_genero.value,
        )
        for capitulo in capitulos
    ]
    sesion.add_all(filas)
    await sesion.flush()
    return version, filas
