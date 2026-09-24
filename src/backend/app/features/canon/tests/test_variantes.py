"""El canon declara las variantes de un nombre, que es lo que `CA-16` pedia.

**La deuda, dicha como la dejo la Fase 2:** `nombres_literales` sabe distinguir
la forma canonica de una variante declarada -- `NombreDeCanon` tiene el campo
desde entonces --, pero **no habia donde declararlas**, asi que la unica fuente
de nombres era `SELECT DISTINCT entidad FROM hecho_canon` y todas llegaban sin
variantes. El validador no rechazaba «Mari» por declararla incompatible: la
rechazaba porque nadie se la habia dado.

Por eso aqui **no se toca el validador** (`features/calidad` es de T4 en esta
misma ola): se le da de donde leer.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from app.features.calidad import NombreDeCanon
from app.features.canon import declarar_variantes, leer_nombres_del_canon
from app.features.canon.modelos import VarianteDeNombre
from app.features.obra.modelos import HechoCanon, Obra


async def _hecho(sesion, obra, entidad: str, valor: str = "verde") -> HechoCanon:
    hecho = HechoCanon(
        obra_id=obra.id, entidad=entidad, atributo="ojos", valor=valor, origen="brief"
    )
    sesion.add(hecho)
    await sesion.flush()
    return hecho


async def test_el_canon_declara_una_variante_de_un_nombre(sesion, obra):
    """RF-VAL-03: la diferencia entre un error de grafia y un apodo tiene que
    estar **en el canon**, declarada, no en la astucia del validador."""
    await _hecho(sesion, obra, "María")
    await declarar_variantes(sesion, obra_id=obra.id, forma_canonica="María", variantes=["Mari"])

    assert await leer_nombres_del_canon(sesion, obra_id=obra.id) == (
        NombreDeCanon(forma_canonica="María", variantes=("Mari",)),
    )


async def test_un_nombre_sin_variantes_declaradas_sigue_siendo_estricto(sesion, obra):
    """`CA-16` tiene dos mitades y esta es la otra: «Maria» por «María» sigue
    siendo defecto. Declarar variantes no relaja al que no las declara."""
    await _hecho(sesion, obra, "Nala")

    assert await leer_nombres_del_canon(sesion, obra_id=obra.id) == (
        NombreDeCanon(forma_canonica="Nala", variantes=()),
    )


async def test_las_variantes_llegan_ordenadas_y_sin_repetir(sesion, obra):
    """El orden lo decide el nombre y no el `rowid`: dos lecturas del mismo
    canon tienen que dar la misma tupla, o el paquete deja de ser reproducible.
    """
    await _hecho(sesion, obra, "María")
    await declarar_variantes(
        sesion, obra_id=obra.id, forma_canonica="María", variantes=["Mari", "Marieta"]
    )
    await declarar_variantes(sesion, obra_id=obra.id, forma_canonica="María", variantes=["Mari"])

    nombres = await leer_nombres_del_canon(sesion, obra_id=obra.id)
    assert nombres[0].variantes == ("Mari", "Marieta")


async def test_solo_llegan_los_nombres_de_esa_obra(sesion, obra):
    """Dos obras comparten base (P-07). Un nombre de la otra colado aqui haria
    que el validador aceptara una grafia que este canon no declara."""
    otra = Obra(titulo="La otra", genero="romance", tono="calido", nivel_de_calor=1)
    sesion.add(otra)
    await sesion.flush()

    await _hecho(sesion, otra, "Teo")
    await declarar_variantes(sesion, obra_id=otra.id, forma_canonica="Teo", variantes=["Teito"])
    await _hecho(sesion, obra, "María")

    assert await leer_nombres_del_canon(sesion, obra_id=obra.id) == (
        NombreDeCanon(forma_canonica="María", variantes=()),
    )


async def test_una_variante_en_blanco_no_entra(sesion, obra):
    """Es R-2 de la Fase 1 otra vez: la cadena vacia es subcadena de cualquier
    cosa, y una variante vacia haria que el validador diera por declarado
    cualquier nombre."""
    sesion.add(VarianteDeNombre(obra_id=obra.id, forma_canonica="María", variante="   "))
    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_la_misma_variante_no_se_declara_dos_veces(sesion, obra):
    """Dos filas iguales no dicen nada nuevo y harian que la tupla leida
    dependiera de cuantas veces se declaro."""
    sesion.add_all(
        [
            VarianteDeNombre(obra_id=obra.id, forma_canonica="María", variante="Mari"),
            VarianteDeNombre(obra_id=obra.id, forma_canonica="María", variante="Mari"),
        ]
    )
    with pytest.raises(IntegrityError):
        await sesion.flush()


async def test_una_variante_de_una_obra_que_no_existe_no_entra(sesion, obra):
    """`foreign_keys=ON`: un canon sin obra no es el canon de nadie."""
    sesion.add(VarianteDeNombre(obra_id=9999, forma_canonica="María", variante="Mari"))
    with pytest.raises(IntegrityError):
        await sesion.flush()
