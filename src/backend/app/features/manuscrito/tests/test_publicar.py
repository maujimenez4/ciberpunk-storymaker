"""Publicar: la tirada inmutable, y que sea de una pieza.

Publicar es **afirmar que los diez capitulos pasaron su puerta** (regla de
dominio 14), no que estan escritos. De ahi que lo primero que hace el servicio
sea mirar los trabajos y no los textos: un capitulo escrito y escalado existe,
se lee bien y no puede ir en un regalo.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conftest import ObraConOutline
from app.features.escena.modelos import Escena
from app.features.escritura.modelos import Trabajo, VersionTexto
from app.features.manuscrito import (
    CapituloPublicado,
    CapituloSinPuerta,
    VersionPublicada,
    ensamblar_manuscrito,
    publicar,
)
from app.features.manuscrito.modelos import CuadroDeDefectos, Dedicatoria, FichaDeLectura

CAPITULOS = 10


async def _integrar(
    sesion: AsyncSession, obra: ObraConOutline, *, escalado: int | None = None
) -> None:
    """Diez capitulos escritos, con su texto vigente y su trabajo cerrado.

    `escalado` deja uno en `ESCALADA`: es el estado que R-2 dice que tiene que
    impedir la publicacion, y el unico que distingue «escrito» de «aprobado».
    """
    for numero, capitulo in enumerate(obra.capitulos, start=1):
        # `escena.capitulo_id` es unico: la cardinalidad capitulo-escena es 1:1
        # (decision P-C). La fixture ya trae la del primero, asi que crear otra
        # aqui choca contra la restriccion en vez de contra el codigo.
        if capitulo.id == obra.escena.capitulo_id:
            escena = obra.escena
        else:
            escena = Escena(
                capitulo_id=capitulo.id,
                version_obra_id=obra.version_obra.id,
                orden_discurso=numero,
                tiempo_historia=f"dia {numero}",
                pov="Nadia",
                lugar="El invernadero",
                presentes=["Nadia", "Teo"],
                objetivo_del_pov="Que Teo confiese",
                obstaculo="Teo no habla",
                resultado="si-pero",
                valor_entrada="confianza",
                valor_salida="sospecha",
                extension_objetivo=1200,
                densidad_de_dialogo_objetivo=0.4,
                distancia_psiquica=3,
            )
            sesion.add(escena)
            await sesion.flush()

        sesion.add(
            VersionTexto(
                escena_id=escena.id,
                numero=1,
                texto=f"Texto del capitulo {numero}.",
                vigente=True,
                run_id=f"run-{numero}",
            )
        )
        sesion.add(
            Trabajo(
                obra_id=obra.obra.id,
                escena_id=escena.id,
                capitulo_id=capitulo.id,
                tipo="escribir_escena",
                estado="ESCALADA" if numero == escalado else "INTEGRADA",
                run_id=f"run-{numero}",
            )
        )
    await sesion.flush()


@pytest.fixture
async def integrada(sesion: AsyncSession, obra_con_outline: ObraConOutline) -> ObraConOutline:
    await _integrar(sesion, obra_con_outline)
    return obra_con_outline


async def test_publicar_fija_los_textos_y_no_los_recalcula(
    sesion: AsyncSession, integrada: ObraConOutline
) -> None:
    """RF-PUB-01. Es **la** razon de ser de esta tabla.

    Se publica, se regenera el capitulo 3 y la tirada sigue apuntando al texto
    de antes. Si resolviera la version vigente al leer, el enlace ya repartido
    cambiaria de contenido sin que nadie lo tocara.
    """
    version = await publicar(sesion, integrada.obra.id)
    fijado = await _texto_de(sesion, version.id, numero=3)

    escena = (
        await sesion.execute(select(Escena).where(Escena.capitulo_id == integrada.capitulos[2].id))
    ).scalar_one()
    vieja = (
        await sesion.execute(select(VersionTexto).where(VersionTexto.escena_id == escena.id))
    ).scalar_one()
    vieja.vigente = False
    sesion.add(
        VersionTexto(
            escena_id=escena.id,
            numero=2,
            texto="OTRO TEXTO, regenerado despues de publicar.",
            vigente=True,
            run_id="run-3b",
        )
    )
    await sesion.flush()

    assert await _texto_de(sesion, version.id, numero=3) == fijado
    assert "OTRO TEXTO" not in fijado


async def test_publicar_otra_vez_no_altera_la_anterior(
    sesion: AsyncSession, integrada: ObraConOutline
) -> None:
    """CA-24: una tirada publicada es intocable, incluso para la siguiente."""
    primera = await publicar(sesion, integrada.obra.id)
    antes = await _instantanea(sesion, primera.id)

    await _regenerar(sesion, integrada, numero=4, texto="Capitulo 4, otra vez.")
    await publicar(sesion, integrada.obra.id)

    assert await _instantanea(sesion, primera.id) == antes


async def test_la_ficha_dice_en_que_capitulos_aparece_cada_entrada(
    sesion: AsyncSession, integrada: ObraConOutline
) -> None:
    """RF-PUB-05, v3.1. Una entrada sin capitulos obliga a releer la novela."""
    version = await publicar(sesion, integrada.obra.id)
    ficha = (
        await sesion.execute(select(FichaDeLectura).where(FichaDeLectura.version_id == version.id))
    ).scalar_one()

    assert ficha.entradas
    assert all("capitulos" in e for e in ficha.entradas)
    assert any(e["capitulos"] for e in ficha.entradas)


async def test_el_cuadro_de_defectos_incluye_la_cobertura_de_personalizacion(
    sesion: AsyncSession, integrada: ObraConOutline
) -> None:
    """La juntura de T6 con `calidad`.

    No basta con que el cuadro exista: sin la cobertura, el regalo puede salir
    sin un elemento que el comprador pidio y el cuadro diria que todo esta bien.
    """
    version = await publicar(sesion, integrada.obra.id)
    cuadro = (
        await sesion.execute(
            select(CuadroDeDefectos).where(CuadroDeDefectos.version_id == version.id)
        )
    ).scalar_one()

    assert "cobertura" in cuadro.defectos[0] or any("cobertura" in d for d in cuadro.defectos)


async def test_publicar_es_atomico(
    sesion: AsyncSession, integrada: ObraConOutline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RF-PUB-08: o queda la tirada entera, o no queda nada.

    Media publicacion es peor que ninguna: una `VersionPublicada` con su token
    repartible y sin capitulos sirve una novela en blanco, y el enlace ya salio.
    """

    def explota(*_a: object, **_k: object) -> None:
        raise RuntimeError("fallo al guardar el cuadro")

    monkeypatch.setattr("app.features.manuscrito.service._cuadro_de_defectos", explota)

    with pytest.raises(RuntimeError):
        await publicar(sesion, integrada.obra.id)

    assert await _cuantas(sesion, integrada.obra.id) == 0


async def test_la_dedicatoria_no_entra_en_el_manuscrito_ensamblado(
    sesion: AsyncSession, integrada: ObraConOutline
) -> None:
    """CA-30, movido desde T2: aqui **si** hay manuscrito contra el que comprobar.

    El `len(manuscrito) > 0` no es relleno. Sin el, un ensamblado que devolviera
    la cadena vacia cumpliria el criterio sin comprobar nada -- que es justo por
    lo que este criterio no podia vivir en T2.
    """
    sesion.add(Dedicatoria(obra_id=integrada.obra.id, texto="Para Marta."))
    await sesion.flush()

    manuscrito = await ensamblar_manuscrito(sesion, integrada.obra.id)

    assert len(manuscrito) > 0
    assert "Para Marta." not in manuscrito


async def test_publicar_dos_veces_sin_cambios_no_crea_una_tirada_nueva(
    sesion: AsyncSession, integrada: ObraConOutline
) -> None:
    """R-1. Lo que no vale es **dos tiradas que el lector no sabe distinguir**.

    Se devuelve la que ya hay. Crear una segunda identica repartiria dos
    enlaces al mismo contenido y una `ficha` duplicada, y nadie -- ni el
    comprador -- sabria cual mandar.
    """
    primera = await publicar(sesion, integrada.obra.id)
    segunda = await publicar(sesion, integrada.obra.id)

    assert segunda.id == primera.id
    assert await _cuantas(sesion, integrada.obra.id) == 1


async def test_una_tirada_nueva_sucede_a_la_anterior(
    sesion: AsyncSession, integrada: ObraConOutline
) -> None:
    """La cadena de republicaciones tiene que ser recorrible hacia atras."""
    primera = await publicar(sesion, integrada.obra.id)
    await _regenerar(sesion, integrada, numero=4, texto="Capitulo 4, reescrito.")
    segunda = await publicar(sesion, integrada.obra.id)

    assert segunda.id != primera.id
    assert segunda.ordinal == primera.ordinal + 1
    assert segunda.sucede_a_id == primera.id


async def test_con_un_capitulo_escalado_no_se_publica_y_dice_cual(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """R-2, CA-23 y regla de dominio 14. **El matiz es «cual».**

    «No se puede publicar» sin nombre obliga a abrir la base para encontrarlo.
    """
    await _integrar(sesion, obra_con_outline, escalado=7)

    with pytest.raises(CapituloSinPuerta) as fallo:
        await publicar(sesion, obra_con_outline.obra.id)

    assert "7" in str(fallo.value)
    assert await _cuantas(sesion, obra_con_outline.obra.id) == 0


async def test_un_capitulo_sin_trabajo_tampoco_se_publica(
    sesion: AsyncSession, obra_con_outline: ObraConOutline
) -> None:
    """Regla de dominio 14 por el otro lado: **no tener puerta no es pasarla**.

    Un capitulo sin trabajo no ha sido rechazado; simplemente nadie lo valido.
    Si esto pasara, un capitulo escrito a mano entraria en el regalo sin que
    ningun validador lo hubiera mirado.
    """
    await _integrar(sesion, obra_con_outline)
    await sesion.execute(
        Trabajo.__table__.delete().where(Trabajo.capitulo_id == obra_con_outline.capitulos[4].id)
    )

    with pytest.raises(CapituloSinPuerta) as fallo:
        await publicar(sesion, obra_con_outline.obra.id)

    assert "5" in str(fallo.value)


# --- ayudas de lectura, no del servicio ------------------------------------


async def _texto_de(sesion: AsyncSession, version_id: int, *, numero: int) -> str:
    capitulo = (
        await sesion.execute(
            select(CapituloPublicado).where(
                CapituloPublicado.version_id == version_id,
                CapituloPublicado.numero == numero,
            )
        )
    ).scalar_one()
    texto = (
        await sesion.execute(
            select(VersionTexto.texto).where(VersionTexto.id == capitulo.version_texto_id)
        )
    ).scalar_one()
    return str(texto)


async def _instantanea(sesion: AsyncSession, version_id: int) -> list[tuple[int, int, bool]]:
    filas = (
        await sesion.execute(
            select(
                CapituloPublicado.numero,
                CapituloPublicado.version_texto_id,
                CapituloPublicado.cambiado,
            )
            .where(CapituloPublicado.version_id == version_id)
            .order_by(CapituloPublicado.numero)
        )
    ).all()
    return [(f[0], f[1], f[2]) for f in filas]


async def _cuantas(sesion: AsyncSession, obra_id: int) -> int:
    filas = (
        await sesion.execute(select(VersionPublicada.id).where(VersionPublicada.obra_id == obra_id))
    ).all()
    return len(filas)


async def _regenerar(
    sesion: AsyncSession, obra: ObraConOutline, *, numero: int, texto: str
) -> None:
    escena = (
        await sesion.execute(
            select(Escena).where(Escena.capitulo_id == obra.capitulos[numero - 1].id)
        )
    ).scalar_one()
    for vieja in (
        (await sesion.execute(select(VersionTexto).where(VersionTexto.escena_id == escena.id)))
        .scalars()
        .all()
    ):
        vieja.vigente = False
    await sesion.flush()
    sesion.add(
        VersionTexto(
            escena_id=escena.id,
            numero=99,
            texto=texto,
            vigente=True,
            run_id=f"run-{numero}-otra",
        )
    )
    await sesion.flush()
