"""Preexistente o introducido: contra el cuadro guardado, no contra la memoria.

RF-PET-05 y el **cuadro de defectos** de `definitions.md`: los defectos vigentes
de una `VersionPublicada`, guardados **con ella** al publicar (RF-PUB-04). Es
contra eso, y solo contra eso, contra lo que se compara (plan-5 T5).

## La identidad de un defecto, y lo que NO puede llevar dentro

Un `Defecto` se identifica en `calidad` por su codigo, su cita y el
desplazamiento sobre una `VersionDeTexto` concreta. Para clasificar **eso no
sirve**, porque la regeneracion produce **otra** `VersionDeTexto`:

- **`version_texto_id` fuera.** Es distinto por construccion en todo capitulo
  regenerado; dentro de la huella, todos sus defectos saldrian introducidos y
  `CA-25` seria incumplible sin que cayera ningun test (R-2).
- **El desplazamiento fuera.** Una frase reescrita mas arriba mueve lo de detras.
- **El numero de capitulo dentro.** Una muletilla marcada en el 3 no tapa la del 8.
- **`hecho_canon_id` dentro.** Un `CAN-01` contra otro hecho es otro defecto.

**La cita se normaliza solo en sus espacios.** No se usa
`commons/domain/normalizacion`, que quita acentos y plurales: «Maria» por
«María» **es** el defecto que `CA-16` persigue.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.calidad import Defecto
from app.features.manuscrito.modelos import CuadroDeDefectos


@dataclass(frozen=True, slots=True)
class Huella:
    """Lo que hace que dos defectos sean el mismo defecto en dos textos distintos."""

    capitulo: int
    codigo: str
    cita: str
    hecho_canon_id: str | None


def huella_de(defecto: Defecto, *, capitulo: int) -> Huella:
    return Huella(
        capitulo=capitulo,
        codigo=defecto.codigo,
        cita=" ".join(defecto.cita.split()),
        hecho_canon_id=defecto.hecho_canon_id,
    )


@dataclass(frozen=True, slots=True)
class Clasificacion:
    """Los dos montones, y los dos presentes: RF-PET-07 conserva la peticion con
    su resultado, y «se publico con tres defectos que ya estaban» es parte de el."""

    preexistentes: tuple[Defecto, ...]
    introducidos: tuple[Defecto, ...]

    @property
    def impide_publicar(self) -> bool:
        """RF-PET-06. **Solo** un introducido. Derivada, no bandera aparte."""
        return bool(self.introducidos)


def clasificar_contra_el_cuadro(
    hallados: Sequence[tuple[int, Defecto]],
    cuadro: Sequence[tuple[int, Defecto]],
) -> Clasificacion:
    """Cada par es `(numero de capitulo, defecto)`. El numero viaja fuera del
    `Defecto` porque `calidad.Defecto` no lo lleva y no se le anade."""
    conocidos = {huella_de(defecto, capitulo=capitulo) for capitulo, defecto in cuadro}
    preexistentes: list[Defecto] = []
    introducidos: list[Defecto] = []
    for capitulo, defecto in hallados:
        destino = (
            preexistentes if huella_de(defecto, capitulo=capitulo) in conocidos else introducidos
        )
        destino.append(defecto)
    return Clasificacion(preexistentes=tuple(preexistentes), introducidos=tuple(introducidos))


def defectos_de_las_entradas(entradas: Sequence[dict[str, Any]]) -> list[tuple[int, Defecto]]:
    """Las entradas de `cuadro_de_defectos.defectos` que son defectos.

    El cuadro guarda tambien la cobertura de §11 (`{"cobertura": ...}`), que no
    es un `Defecto` —senala una ausencia y no tiene cita—, asi que se salta. La
    forma de un defecto guardado la fija `service.entrada_del_cuadro`.
    """
    pares: list[tuple[int, Defecto]] = []
    for entrada in entradas:
        if "defecto" in entrada and "capitulo" in entrada:
            pares.append((int(entrada["capitulo"]), Defecto.model_validate(entrada["defecto"])))
    return pares


async def cuadro_guardado(
    sesion: AsyncSession, *, version_publicada_id: int
) -> list[tuple[int, Defecto]]:
    """El cuadro de una tirada, listo para `clasificar_contra_el_cuadro`.

    Una version sin cuadro devuelve lista vacia: todo lo que se halle saldra
    introducido, que es la direccion segura.
    """
    defectos = (
        await sesion.execute(
            select(CuadroDeDefectos.defectos).where(
                CuadroDeDefectos.version_id == version_publicada_id
            )
        )
    ).scalar_one_or_none()
    return defectos_de_las_entradas(defectos or [])
