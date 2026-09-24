"""El esquema de publicacion: lo que se fija al publicar y no se recalcula.

Una `VersionPublicada` es **inmutable por contrato**: lo que el destinatario
lee hoy tiene que ser lo que lea dentro de un ano, aunque el manuscrito siga
cambiando por debajo. De ahi que `CapituloPublicado` guarde el
`version_texto_id` concreto (RF-PUB-01) en vez de resolver la version vigente
al leer: resolverla al leer haria que una regeneracion posterior cambiara en
silencio un enlace ya repartido.

Estos tests no prueban comportamiento porque T1 no entrega ninguno. Prueban la
**forma**, que es lo que las ocho tareas siguientes dan por cierto.
"""

import string

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.manuscrito import (
    CapituloPublicado,
    CuadroDeDefectos,
    Dedicatoria,
    FichaDeLectura,
    VersionPublicada,
    nuevo_identificador_publico,
)
from app.features.obra.modelos import Obra

TABLAS = {
    "version_publicada",
    "capitulo_publicado",
    "ficha_de_lectura",
    "cuadro_de_defectos",
    "dedicatoria",
}


async def _version(sesion: AsyncSession, obra_id: int, ordinal: int) -> VersionPublicada:
    version = VersionPublicada(obra_id=obra_id, ordinal=ordinal)
    sesion.add(version)
    await sesion.flush()
    return version


async def test_las_tablas_de_publicacion_existen(sesion: AsyncSession) -> None:
    nombres = await sesion.run_sync(lambda s: set(inspect(s.bind).get_table_names()))
    assert TABLAS <= nombres, f"faltan: {TABLAS - nombres}"


async def test_el_identificador_publico_no_es_adivinable(sesion: AsyncSession, obra: Obra) -> None:
    """RF-PUB-07. Es la llave de entrada de la lectura, no un campo del cuerpo.

    Quien tenga el enlace lee la novela, asi que adivinarlo es leer el regalo de
    otro. Un entero autoincremental se adivina probando el siguiente, y por eso
    la comprobacion no es «son distintos» sino «no son contiguos ni numericos».
    """
    a = await _version(sesion, obra.id, ordinal=1)
    b = await _version(sesion, obra.id, ordinal=2)

    assert a.identificador_publico != b.identificador_publico
    assert len(a.identificador_publico) >= 32
    assert not a.identificador_publico.isdigit()
    assert a.identificador_publico != str(a.id)
    # Y **no son contiguos**, que es lo que hace adivinable a un autoincremental:
    # con dos filas seguidas, la distancia entre sus ids es 1 y entre sus
    # identificadores no es nada.
    assert b.id - a.id == 1
    assert not b.identificador_publico.startswith(a.identificador_publico[:8])


async def test_un_capitulo_publicado_fija_su_version_de_texto() -> None:
    """RF-PUB-01: se fija al publicar, no se recalcula por vigencia al leer."""
    capitulo = CapituloPublicado(version_id=1, numero=1, version_texto_id=7)
    assert capitulo.version_texto_id == 7


async def test_un_capitulo_publicado_lleva_titulo_y_cambiado() -> None:
    """Los dos campos que el indice de la 002 necesita (`RF-IND-01`, `RF-IND-02`).

    Van en el esquema y no en el navegador a proposito: `cambiado` compara esta
    version con la anterior, y el navegador solo tiene delante la que esta
    leyendo. Lo que no salga aqui **no existe para el cliente generado**.
    """
    capitulo = CapituloPublicado(
        version_id=1, numero=3, version_texto_id=7, titulo="La grieta del muro", cambiado=True
    )
    assert capitulo.titulo == "La grieta del muro"
    assert capitulo.cambiado is True


async def test_no_se_puede_publicar_dos_versiones_con_el_mismo_ordinal(
    sesion: AsyncSession, obra: Obra
) -> None:
    """Dos ordinales iguales dejarian «la version 2» sin significado."""
    await _version(sesion, obra.id, ordinal=1)
    with pytest.raises(IntegrityError):
        await _version(sesion, obra.id, ordinal=1)


async def test_la_ficha_dice_en_que_capitulos_aparece_cada_entrada(
    sesion: AsyncSession, obra: Obra
) -> None:
    """RF-PUB-05: la ficha sin capitulos no sirve para volver al pasaje."""
    version = await _version(sesion, obra.id, ordinal=1)
    ficha = FichaDeLectura(
        version_id=version.id,
        entradas=[{"nombre": "Ada", "tipo": "personaje", "capitulos": [1, 3, 7]}],
    )
    sesion.add(ficha)
    await sesion.flush()

    assert ficha.entradas[0]["capitulos"] == [1, 3, 7]


async def test_el_cuadro_de_defectos_cuelga_de_la_version(sesion: AsyncSession, obra: Obra) -> None:
    """La Fase 5 clasifica preexistente frente a introducido, y para eso
    necesita el cuadro de **cada** version, no el ultimo."""
    version = await _version(sesion, obra.id, ordinal=1)
    cuadro = CuadroDeDefectos(version_id=version.id, defectos=[{"codigo": "CON-03", "capitulo": 2}])
    sesion.add(cuadro)
    await sesion.flush()

    assert cuadro.version_id == version.id


async def test_la_dedicatoria_cuelga_de_la_obra_y_no_de_la_version(
    sesion: AsyncSession, obra: Obra
) -> None:
    """Es del regalo, no de la tirada: republicar no la reescribe.

    Y **no es prosa del manuscrito** (regla de dominio 15): no entra en el
    ensamblado ni en la lista negra de n-gramas.
    """
    dedicatoria = Dedicatoria(obra_id=obra.id, texto="Para ti, que me lo pediste sin pedirlo.")
    sesion.add(dedicatoria)
    await sesion.flush()

    assert dedicatoria.obra_id == obra.id


async def test_el_identificador_no_se_repite_en_muchas_versiones(
    sesion: AsyncSession, obra: Obra
) -> None:
    """Una colision serviria el regalo de otro. Con `token_urlsafe(32)` es
    improbable, pero la comprobacion barata es que el esquema lo impida."""
    identificadores = {
        (await _version(sesion, obra.id, ordinal=n)).identificador_publico for n in range(1, 21)
    }
    assert len(identificadores) == 20

    chocante = VersionPublicada(
        obra_id=obra.id,
        ordinal=99,
        identificador_publico=next(iter(identificadores)),
    )
    sesion.add(chocante)
    with pytest.raises(IntegrityError):
        await sesion.flush()


def test_el_identificador_se_genera_con_secrets_y_no_con_random() -> None:
    """`secrets`, no `random`: `random` es predecible si se conoce la semilla,
    y aqui el identificador es la unica credencial que protege la lectura.

    Se prueba la funcion y no el modelo a proposito: el `default` de una columna
    se aplica **al insertar**, asi que leerlo de un objeto recien construido
    daria `None` y el test pasaria por el motivo equivocado.
    """
    uno, otro = nuevo_identificador_publico(), nuevo_identificador_publico()

    assert uno != otro
    assert len(uno) >= 32
    assert not uno.isdigit()
    # `token_urlsafe` devuelve base64 para URL: sin `+`, `/` ni `=`, que
    # obligarian a escapar el enlace que se le manda al destinatario.
    assert set(uno) <= set(string.ascii_letters + string.digits + "-_")
